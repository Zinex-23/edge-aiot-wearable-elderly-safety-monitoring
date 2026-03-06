import argparse
import json
from pathlib import Path
from typing import List

import numpy as np


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Export compact ESP32 artifacts from model_weights.npz")
    parser.add_argument("--model-npz", type=str, default=str(root / "artifacts" / "model_weights.npz"))
    parser.add_argument(
        "--feature-json", type=str, default=str(root / "train_ready" / "feature_columns.json")
    )
    parser.add_argument("--out-dir", type=str, default=str(root / "artifacts_esp32"))
    parser.add_argument("--top-k", type=int, default=64, help="Keep top-k features by |weight|")
    parser.add_argument(
        "--quantize-int8",
        action="store_true",
        default=True,
        help="Quantize weights to int8 (mean/std kept float32)",
    )
    parser.add_argument(
        "--no-quantize-int8",
        dest="quantize_int8",
        action="store_false",
        help="Keep float32 weights in generated header",
    )
    return parser.parse_args()


def c_array_int(name: str, arr: np.ndarray, ctype: str, per_line: int = 16) -> str:
    vals = [str(int(x)) for x in arr.tolist()]
    lines = []
    for i in range(0, len(vals), per_line):
        lines.append("  " + ", ".join(vals[i : i + per_line]))
    body = ",\n".join(lines) if lines else ""
    return f"static const {ctype} {name}[{len(arr)}] = {{\n{body}\n}};\n"


def c_array_float(name: str, arr: np.ndarray, per_line: int = 8) -> str:
    vals = [f"{float(x):.9g}f" for x in arr.tolist()]
    lines = []
    for i in range(0, len(vals), per_line):
        lines.append("  " + ", ".join(vals[i : i + per_line]))
    body = ",\n".join(lines) if lines else ""
    return f"static const float {name}[{len(arr)}] = {{\n{body}\n}};\n"


def build_header(
    full_dim: int,
    selected_idx: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    bias: float,
    threshold: float,
    quantize_int8: bool,
    weights: np.ndarray,
) -> str:
    top_k = len(selected_idx)
    out = []
    out.append("#ifndef FALL_MODEL_ESP32_H")
    out.append("#define FALL_MODEL_ESP32_H")
    out.append("")
    out.append("#include <stdint.h>")
    out.append("#include <math.h>")
    out.append("")
    out.append(f"#define FD_FULL_FEATURE_DIM {full_dim}")
    out.append(f"#define FD_SELECTED_FEATURE_DIM {top_k}")
    out.append("")
    out.append(c_array_int("fd_feature_index", selected_idx.astype(np.int32), "uint16_t"))
    out.append(c_array_float("fd_mean", mean.astype(np.float32)))
    out.append(c_array_float("fd_std", std.astype(np.float32)))
    out.append(f"static const float fd_bias = {bias:.9g}f;")
    out.append(f"static const float fd_threshold = {threshold:.9g}f;")
    out.append("")

    if quantize_int8:
        max_abs = float(np.max(np.abs(weights))) if weights.size else 0.0
        w_scale = max_abs / 127.0 if max_abs > 0 else 1.0
        w_q = np.clip(np.round(weights / w_scale), -127, 127).astype(np.int8)
        out.append(c_array_int("fd_w_q", w_q.astype(np.int32), "int8_t"))
        out.append(f"static const float fd_w_scale = {w_scale:.9g}f;")
        out.append("")
        mul_expr = "((float)fd_w_q[i] * fd_w_scale)"
    else:
        out.append(c_array_float("fd_w", weights.astype(np.float32)))
        out.append("")
        mul_expr = "fd_w[i]"

    out.append("static inline float fd_predict_proba(const float *x_full) {")
    out.append("  float z = fd_bias;")
    out.append("  for (int i = 0; i < FD_SELECTED_FEATURE_DIM; ++i) {")
    out.append("    uint16_t idx = fd_feature_index[i];")
    out.append("    float x = x_full[idx];")
    out.append("    float xn = (x - fd_mean[i]) / fd_std[i];")
    out.append(f"    z += xn * {mul_expr};")
    out.append("  }")
    out.append("  if (z > 40.0f) return 1.0f;")
    out.append("  if (z < -40.0f) return 0.0f;")
    out.append("  return 1.0f / (1.0f + expf(-z));")
    out.append("}")
    out.append("")
    out.append("static inline int fd_predict_label(const float *x_full) {")
    out.append("  return fd_predict_proba(x_full) >= fd_threshold ? 1 : 0;")
    out.append("}")
    out.append("")
    out.append("#endif")
    out.append("")
    return "\n".join(out)


def main() -> None:
    args = parse_args()
    model_path = Path(args.model_npz).resolve()
    feature_json = Path(args.feature_json).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = np.load(model_path, allow_pickle=True)
    weights = payload["weights"].astype(np.float64)
    mean = payload["mean"].astype(np.float64)
    std = payload["std"].astype(np.float64)
    bias = float(payload["bias"][0])
    threshold = float(payload["threshold"][0])
    full_dim = int(weights.shape[0])

    with feature_json.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if isinstance(loaded, dict):
        feature_cols = loaded["feature_columns"]
    elif isinstance(loaded, list):
        feature_cols = loaded
    else:
        raise ValueError("Unsupported feature_json format: expected dict or list.")
    if len(feature_cols) != full_dim:
        raise ValueError(
            f"Feature dimension mismatch: model={full_dim}, feature_columns={len(feature_cols)}"
        )

    top_k = int(args.top_k)
    if top_k <= 0:
        raise ValueError("--top-k must be > 0")
    top_k = min(top_k, full_dim)

    order = np.argsort(np.abs(weights))[::-1]
    selected_idx = np.sort(order[:top_k])
    w_sel = weights[selected_idx]
    mean_sel = mean[selected_idx]
    std_sel = std[selected_idx]

    # Protect against invalid std
    std_sel = np.where(np.abs(std_sel) < 1e-8, 1.0, std_sel)

    header_text = build_header(
        full_dim=full_dim,
        selected_idx=selected_idx.astype(np.int32),
        mean=mean_sel,
        std=std_sel,
        bias=bias,
        threshold=threshold,
        quantize_int8=bool(args.quantize_int8),
        weights=w_sel,
    )

    header_path = out_dir / "fall_model_esp32.h"
    header_path.write_text(header_text, encoding="utf-8")

    # Compact npz (float32 only, selected features only)
    compact = {
        "selected_index": selected_idx.astype(np.uint16),
        "weights": w_sel.astype(np.float32),
        "mean": mean_sel.astype(np.float32),
        "std": std_sel.astype(np.float32),
        "bias": np.asarray([bias], dtype=np.float32),
        "threshold": np.asarray([threshold], dtype=np.float32),
    }
    compact_npz = out_dir / "model_compact_selected.npz"
    np.savez(compact_npz, **compact)

    selected_names: List[str] = [feature_cols[int(i)] for i in selected_idx.tolist()]
    (out_dir / "selected_features.json").write_text(
        json.dumps(
            {
                "full_feature_dim": full_dim,
                "selected_feature_dim": int(top_k),
                "quantize_int8": bool(args.quantize_int8),
                "selected_index": selected_idx.tolist(),
                "selected_names": selected_names,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Memory estimate (ESP-side params only)
    bytes_index = int(selected_idx.size * 2)
    bytes_mean = int(selected_idx.size * 4)
    bytes_std = int(selected_idx.size * 4)
    bytes_weights = int(selected_idx.size * (1 if args.quantize_int8 else 4))
    bytes_scalars = 8  # bias + threshold as float32
    bytes_quant_scale = 4 if args.quantize_int8 else 0
    bytes_total = bytes_index + bytes_mean + bytes_std + bytes_weights + bytes_scalars + bytes_quant_scale

    report = {
        "model_npz": str(model_path),
        "header_path": str(header_path),
        "compact_npz": str(compact_npz),
        "full_feature_dim": full_dim,
        "selected_feature_dim": int(top_k),
        "quantize_int8": bool(args.quantize_int8),
        "esp_parameter_bytes": bytes_total,
        "esp_parameter_kb": round(bytes_total / 1024.0, 4),
        "breakdown_bytes": {
            "feature_index_u16": bytes_index,
            "mean_f32": bytes_mean,
            "std_f32": bytes_std,
            "weights": bytes_weights,
            "bias_threshold": bytes_scalars,
            "weight_scale": bytes_quant_scale,
        },
        "file_sizes": {
            "header_bytes": header_path.stat().st_size,
            "compact_npz_bytes": compact_npz.stat().st_size,
        },
    }
    report_path = out_dir / "esp32_export_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
