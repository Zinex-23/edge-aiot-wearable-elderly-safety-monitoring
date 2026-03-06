#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


NON_FEATURE_COLS = {
    "source",
    "subject_id",
    "trial_id",
    "activity_code",
    "label",
    "source_freq_hz",
    "window_index",
    "start_index",
    "num_samples",
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_ready = script_dir / "train_ready"
    parser = argparse.ArgumentParser(
        description="Train fall detection model from train/validation/test split files."
    )
    parser.add_argument("--train-csv", default=str(default_ready / "train.csv"))
    parser.add_argument("--val-csv", default=str(default_ready / "validation.csv"))
    parser.add_argument("--test-csv", default=str(default_ready / "test.csv"))
    parser.add_argument("--artifacts-dir", default=str(script_dir / "artifacts"))
    parser.add_argument(
        "--model-type",
        choices=["logistic", "extra_trees", "random_forest"],
        default="logistic",
        help="Use logistic for tiny ESP32 model. Trees are much larger.",
    )
    parser.add_argument("--seed", type=int, default=42)

    # Tree params
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--min-samples-leaf", type=int, default=2)
    parser.add_argument("--max-depth", type=int, default=14, help="0 means unlimited.")
    parser.add_argument(
        "--max-features",
        default="0.5",
        help="max_features for tree ensemble. Supports 'sqrt', 'log2', 'none' or numeric fraction.",
    )

    # Shared training params
    parser.add_argument(
        "--class-weight",
        default="balanced",
        help="class_weight value. Example: balanced, balanced_subsample, none.",
    )

    # Logistic + export params
    parser.add_argument("--logistic-c", type=float, default=1.0)
    parser.add_argument(
        "--top-k",
        type=int,
        default=0,
        help="Selected features for ESP header. 0 means use all features.",
    )
    parser.add_argument(
        "--quantize-int8",
        action="store_true",
        default=True,
        help="Quantize logistic weights to int8 in exported header.",
    )
    parser.add_argument(
        "--no-quantize-int8",
        dest="quantize_int8",
        action="store_false",
        help="Keep logistic weights in float32 in header.",
    )
    parser.add_argument(
        "--export-header",
        default=str(script_dir / "wrist_band_fall.h"),
        help="Path for generated C header model.",
    )
    parser.add_argument(
        "--header-model-name",
        default="wrist_band_fall_model",
        help="C symbol prefix used for tree export (emlearn).",
    )
    return parser.parse_args()


def find_feature_columns(df: pd.DataFrame) -> List[str]:
    return sorted(c for c in df.columns if c not in NON_FEATURE_COLS)


def split_xy(df: pd.DataFrame, feature_cols: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    x = df[feature_cols].to_numpy(dtype=np.float64, copy=True)
    y = df["label"].to_numpy(dtype=np.int64, copy=True)
    return x, y


def impute_and_standardize(
    x_train: np.ndarray, x_val: np.ndarray, x_test: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = np.nanmean(x_train, axis=0)
    mean[np.isnan(mean)] = 0.0

    x_train_filled = np.where(np.isnan(x_train), mean, x_train)
    x_val_filled = np.where(np.isnan(x_val), mean, x_val)
    x_test_filled = np.where(np.isnan(x_test), mean, x_test)

    std = np.std(x_train_filled, axis=0)
    std[std < 1e-8] = 1.0

    x_train_z = (x_train_filled - mean) / std
    x_val_z = (x_val_filled - mean) / std
    x_test_z = (x_test_filled - mean) / std
    return x_train_z, x_val_z, x_test_z, mean, std


def optimize_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, float]:
    best_t = 0.5
    best_f1 = -1.0
    for t in np.linspace(0.05, 0.95, 181):
        y_pred = (y_prob >= t).astype(int)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = float(f1)
            best_t = float(t)
    return best_t, best_f1


def evaluate(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> Dict[str, object]:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    metrics: Dict[str, object] = {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "predicted_positive": int(y_pred.sum()),
        "predicted_negative": int((y_pred == 0).sum()),
        "true_positive_count": int((y_true == 1).sum()),
        "true_negative_count": int((y_true == 0).sum()),
    }

    unique_labels = np.unique(y_true)
    if len(unique_labels) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
    return metrics


def save_predictions(df: pd.DataFrame, y_prob: np.ndarray, threshold: float, out_path: Path) -> None:
    keep_cols = [c for c in ["source", "subject_id", "trial_id", "activity_code", "label"] if c in df.columns]
    out = df[keep_cols].copy()
    out["prob_fall"] = y_prob
    out["pred_label"] = (y_prob >= threshold).astype(int)
    out.to_csv(out_path, index=False)


def build_include_guard(path: Path) -> str:
    raw = path.name.upper()
    cleaned = []
    for ch in raw:
        cleaned.append(ch if ch.isalnum() else "_")
    guard = "".join(cleaned)
    if not guard.endswith("_H"):
        guard += "_H"
    return guard


def parse_max_features(value: str) -> object:
    lowered = value.strip().lower()
    if lowered == "none":
        return None
    if lowered in {"sqrt", "log2"}:
        return lowered
    parsed = float(value)
    if parsed <= 0.0:
        raise ValueError(f"Invalid --max-features value '{value}'. Use sqrt/log2/none or positive float.")
    return parsed


def parse_class_weight(value: str) -> object:
    lowered = value.strip().lower()
    if lowered == "none":
        return None
    return value


def export_tree_header(
    model: object,
    feature_cols: List[str],
    threshold: float,
    out_path: Path,
    model_name: str,
) -> None:
    try:
        import emlearn
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing dependency 'emlearn'. Install with: pip install emlearn") from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".h", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    cmodel = emlearn.convert(model, dtype="float")
    cmodel.save(name=model_name, file=str(tmp_path), format="c", include_proba=True)
    generated = tmp_path.read_text(encoding="utf-8")
    tmp_path.unlink(missing_ok=True)

    include_guard = build_include_guard(out_path)
    wrapped = f"""#ifndef {include_guard}
#define {include_guard}

#ifdef __cplusplus
extern "C" {{
#endif

{generated}

#define WRIST_BAND_FALL_FEATURE_COUNT {len(feature_cols)}
#define WRIST_BAND_FALL_THRESHOLD {threshold:.8f}f

static inline float wrist_band_fall_predict_proba(const float *features, int32_t features_length) {{
    float out[2] = {{0.0f, 0.0f}};
    {model_name}_predict_proba(features, features_length, out, 2);
    return out[1];
}}

static inline int32_t wrist_band_fall_predict_label(const float *features, int32_t features_length) {{
    const float p_fall = wrist_band_fall_predict_proba(features, features_length);
    return (p_fall >= WRIST_BAND_FALL_THRESHOLD) ? 1 : 0;
}}

#ifdef __cplusplus
}}
#endif

#endif  // {include_guard}
"""
    out_path.write_text(wrapped, encoding="utf-8")


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


def export_logistic_header(
    feature_cols: List[str],
    mean: np.ndarray,
    std: np.ndarray,
    weights: np.ndarray,
    bias: float,
    threshold: float,
    out_path: Path,
    top_k: int,
    quantize_int8: bool,
) -> Dict[str, object]:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    d = int(weights.shape[0])
    if int(top_k) <= 0:
        k = d
    else:
        k = min(max(1, int(top_k)), d)
    order = np.argsort(np.abs(weights))[::-1]
    selected_idx = np.sort(order[:k]).astype(np.int32)

    w_sel = weights[selected_idx].astype(np.float64)
    m_sel = mean[selected_idx].astype(np.float64)
    s_sel = std[selected_idx].astype(np.float64)
    s_sel[np.abs(s_sel) < 1e-8] = 1.0

    out = []
    include_guard = build_include_guard(out_path)
    out.append(f"#ifndef {include_guard}")
    out.append(f"#define {include_guard}")
    out.append("")
    out.append("#include <stdint.h>")
    out.append("#include <math.h>")
    out.append("")
    out.append(f"#define WRIST_BAND_FALL_FEATURE_COUNT {d}")
    out.append(f"#define WRIST_BAND_FALL_SELECTED_FEATURE_COUNT {k}")
    out.append("")
    out.append(c_array_int("wrist_band_fall_feature_index", selected_idx, "uint16_t"))
    out.append(c_array_float("wrist_band_fall_mean", m_sel.astype(np.float32)))
    out.append(c_array_float("wrist_band_fall_std", s_sel.astype(np.float32)))
    out.append(f"static const float wrist_band_fall_bias = {float(bias):.9g}f;")
    out.append(f"static const float WRIST_BAND_FALL_THRESHOLD = {float(threshold):.9g}f;")
    out.append("")

    if quantize_int8:
        max_abs = float(np.max(np.abs(w_sel))) if w_sel.size > 0 else 0.0
        w_scale = max_abs / 127.0 if max_abs > 0 else 1.0
        w_q = np.clip(np.round(w_sel / w_scale), -127, 127).astype(np.int8)
        out.append(c_array_int("wrist_band_fall_w_q", w_q.astype(np.int32), "int8_t"))
        out.append(f"static const float wrist_band_fall_w_scale = {w_scale:.9g}f;")
        out.append("")
        mul_expr = "((float)wrist_band_fall_w_q[i] * wrist_band_fall_w_scale)"
    else:
        out.append(c_array_float("wrist_band_fall_w", w_sel.astype(np.float32)))
        out.append("")
        mul_expr = "wrist_band_fall_w[i]"

    out.append("static inline float wrist_band_fall_predict_proba(const float *features, int32_t features_length) {")
    out.append("  (void)features_length;")
    out.append("  float z = wrist_band_fall_bias;")
    out.append("  for (int i = 0; i < WRIST_BAND_FALL_SELECTED_FEATURE_COUNT; ++i) {")
    out.append("    uint16_t idx = wrist_band_fall_feature_index[i];")
    out.append("    float x = features[idx];")
    out.append("    float xn = (x - wrist_band_fall_mean[i]) / wrist_band_fall_std[i];")
    out.append(f"    z += xn * {mul_expr};")
    out.append("  }")
    out.append("  if (z > 40.0f) return 1.0f;")
    out.append("  if (z < -40.0f) return 0.0f;")
    out.append("  return 1.0f / (1.0f + expf(-z));")
    out.append("}")
    out.append("")
    out.append("static inline int32_t wrist_band_fall_predict_label(const float *features, int32_t features_length) {")
    out.append("  const float p = wrist_band_fall_predict_proba(features, features_length);")
    out.append("  return (p >= WRIST_BAND_FALL_THRESHOLD) ? 1 : 0;")
    out.append("}")
    out.append("")
    out.append(f"#endif  // {include_guard}")
    out.append("")
    out_path.write_text("\n".join(out), encoding="utf-8")

    bytes_index = int(k * 2)
    bytes_mean = int(k * 4)
    bytes_std = int(k * 4)
    bytes_weights = int(k * (1 if quantize_int8 else 4))
    bytes_scalars = 8  # bias + threshold
    bytes_quant = 4 if quantize_int8 else 0
    bytes_total = bytes_index + bytes_mean + bytes_std + bytes_weights + bytes_scalars + bytes_quant

    selected_names = [feature_cols[int(i)] for i in selected_idx.tolist()]
    return {
        "selected_feature_count": k,
        "quantize_int8": bool(quantize_int8),
        "parameter_bytes": bytes_total,
        "parameter_kb": round(bytes_total / 1024.0, 4),
        "selected_features": selected_names,
        "header_size_bytes": out_path.stat().st_size,
    }


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train_csv)
    val_df = pd.read_csv(args.val_csv)
    test_df = pd.read_csv(args.test_csv)

    feature_cols = find_feature_columns(train_df)
    if not feature_cols:
        raise RuntimeError("No feature columns found in training csv.")

    x_train_raw, y_train = split_xy(train_df, feature_cols)
    x_val_raw, y_val = split_xy(val_df, feature_cols)
    x_test_raw, y_test = split_xy(test_df, feature_cols)

    class_weight = parse_class_weight(args.class_weight)
    model_name = ""
    model_path = None
    logistic_export_meta = None

    if args.model_type == "logistic":
        x_train, x_val, x_test, mean, std = impute_and_standardize(x_train_raw, x_val_raw, x_test_raw)
        model = LogisticRegression(
            C=float(args.logistic_c),
            class_weight=class_weight,
            random_state=args.seed,
            solver="liblinear",
            max_iter=3000,
        )
        model.fit(x_train, y_train)
        model_name = "LogisticRegression"

        train_prob = model.predict_proba(x_train)[:, 1]
        val_prob = model.predict_proba(x_val)[:, 1]
        test_prob = model.predict_proba(x_test)[:, 1]

        best_threshold, best_val_f1 = optimize_threshold(y_val, val_prob)
        train_metrics = evaluate(y_train, train_prob, best_threshold)
        val_metrics = evaluate(y_val, val_prob, best_threshold)
        test_metrics = evaluate(y_test, test_prob, best_threshold)

        weights = model.coef_[0].astype(np.float64)
        bias = float(model.intercept_[0])

        model_path = artifacts_dir / "logistic_fall_model.joblib"
        npz_path = artifacts_dir / "model_weights.npz"
        features_path = artifacts_dir / "feature_columns.json"
        metrics_path = artifacts_dir / "metrics.json"
        val_pred_path = artifacts_dir / "validation_predictions.csv"
        test_pred_path = artifacts_dir / "test_predictions.csv"
        header_path = Path(args.export_header).resolve()

        joblib.dump({"model": model, "mean": mean, "std": std, "feature_cols": feature_cols}, model_path)
        np.savez(
            npz_path,
            weights=weights.astype(np.float32),
            bias=np.asarray([bias], dtype=np.float32),
            mean=mean.astype(np.float32),
            std=std.astype(np.float32),
            threshold=np.asarray([best_threshold], dtype=np.float32),
            feature_names=np.asarray(feature_cols),
        )
        with features_path.open("w", encoding="utf-8") as f:
            json.dump(feature_cols, f, indent=2)

        logistic_export_meta = export_logistic_header(
            feature_cols=feature_cols,
            mean=mean,
            std=std,
            weights=weights,
            bias=bias,
            threshold=best_threshold,
            out_path=header_path,
            top_k=args.top_k,
            quantize_int8=bool(args.quantize_int8),
        )

        payload = {
            "model": model_name,
            "params": {
                "model_type": args.model_type,
                "logistic_c": args.logistic_c,
                "class_weight": args.class_weight,
                "seed": args.seed,
                "top_k": args.top_k,
                "quantize_int8": bool(args.quantize_int8),
            },
            "selected_threshold": best_threshold,
            "best_validation_f1": best_val_f1,
            "feature_count": len(feature_cols),
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics,
            "esp32_export": logistic_export_meta,
            "files": {
                "joblib": str(model_path),
                "npz": str(npz_path),
                "header": str(header_path),
            },
        }
        with metrics_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        save_predictions(val_df, val_prob, best_threshold, val_pred_path)
        save_predictions(test_df, test_prob, best_threshold, test_pred_path)

        print(f"Saved model: {model_path}")
        print(f"Saved compact weights: {npz_path}")
        print(f"Saved metrics: {metrics_path}")
        print(f"Saved C header model: {header_path}")
        print(f"Feature count: {len(feature_cols)}")
        print(f"Selected threshold (from validation): {best_threshold:.3f}")
        if logistic_export_meta is not None:
            print(
                "ESP export - "
                f"selected={logistic_export_meta['selected_feature_count']} "
                f"params={logistic_export_meta['parameter_kb']} KB "
                f"header_size={round(logistic_export_meta['header_size_bytes']/1024.0,2)} KB"
            )
        print(
            "Validation - "
            f"F1={val_metrics['f1']:.4f} "
            f"Recall={val_metrics['recall']:.4f} "
            f"Precision={val_metrics['precision']:.4f} "
            f"AUC={val_metrics['roc_auc'] if val_metrics['roc_auc'] is not None else 'NA'}"
        )
        print(
            "Test - "
            f"F1={test_metrics['f1']:.4f} "
            f"Recall={test_metrics['recall']:.4f} "
            f"Precision={test_metrics['precision']:.4f} "
            f"AUC={test_metrics['roc_auc'] if test_metrics['roc_auc'] is not None else 'NA'}"
        )
        return

    # Tree models (bigger, not ideal for ESP32-C2)
    max_depth = None if args.max_depth == 0 else args.max_depth
    max_features = parse_max_features(args.max_features)

    common_kwargs = dict(
        n_estimators=args.n_estimators,
        min_samples_leaf=args.min_samples_leaf,
        max_depth=max_depth,
        max_features=max_features,
        class_weight=class_weight,
        random_state=args.seed,
    )
    if args.model_type == "extra_trees":
        model = ExtraTreesClassifier(n_jobs=-1, **common_kwargs)
        model_name = "ExtraTreesClassifier"
        model_stem = "et_fall_model"
    else:
        model = RandomForestClassifier(n_jobs=-1, **common_kwargs)
        model_name = "RandomForestClassifier"
        model_stem = "rf_fall_model"

    # Use imputed raw features for trees.
    mean = np.nanmean(x_train_raw, axis=0)
    mean[np.isnan(mean)] = 0.0
    x_train = np.where(np.isnan(x_train_raw), mean, x_train_raw)
    x_val = np.where(np.isnan(x_val_raw), mean, x_val_raw)
    x_test = np.where(np.isnan(x_test_raw), mean, x_test_raw)

    model.fit(x_train, y_train)
    train_prob = model.predict_proba(x_train)[:, 1]
    val_prob = model.predict_proba(x_val)[:, 1]
    test_prob = model.predict_proba(x_test)[:, 1]

    best_threshold, best_val_f1 = optimize_threshold(y_val, val_prob)
    train_metrics = evaluate(y_train, train_prob, best_threshold)
    val_metrics = evaluate(y_val, val_prob, best_threshold)
    test_metrics = evaluate(y_test, test_prob, best_threshold)

    model_path = artifacts_dir / f"{model_stem}.joblib"
    features_path = artifacts_dir / "feature_columns.json"
    metrics_path = artifacts_dir / "metrics.json"
    val_pred_path = artifacts_dir / "validation_predictions.csv"
    test_pred_path = artifacts_dir / "test_predictions.csv"
    header_path = Path(args.export_header).resolve()

    joblib.dump(model, model_path)
    with features_path.open("w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=2)

    payload = {
        "model": model_name,
        "params": {
            "model_type": args.model_type,
            "n_estimators": args.n_estimators,
            "min_samples_leaf": args.min_samples_leaf,
            "max_depth": args.max_depth,
            "max_features": args.max_features,
            "class_weight": args.class_weight,
            "seed": args.seed,
        },
        "selected_threshold": best_threshold,
        "best_validation_f1": best_val_f1,
        "feature_count": len(feature_cols),
        "train": train_metrics,
        "validation": val_metrics,
        "test": test_metrics,
    }
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    save_predictions(val_df, val_prob, best_threshold, val_pred_path)
    save_predictions(test_df, test_prob, best_threshold, test_pred_path)

    header_export_ok = True
    header_export_error = ""
    try:
        export_tree_header(
            model=model,
            feature_cols=feature_cols,
            threshold=best_threshold,
            out_path=header_path,
            model_name=args.header_model_name,
        )
    except Exception as exc:  # pragma: no cover
        header_export_ok = False
        header_export_error = str(exc)

    print(f"Saved model: {model_path}")
    print(f"Saved metrics: {metrics_path}")
    if header_export_ok:
        print(f"Saved C header model: {header_path}")
        print(f"Header size: {round(header_path.stat().st_size/1024/1024, 3)} MB")
    else:
        print(f"Header export skipped/failed: {header_export_error}")
    print(f"Feature count: {len(feature_cols)}")
    print(f"Selected threshold (from validation): {best_threshold:.3f}")
    print(
        "Validation - "
        f"F1={val_metrics['f1']:.4f} "
        f"Recall={val_metrics['recall']:.4f} "
        f"Precision={val_metrics['precision']:.4f} "
        f"AUC={val_metrics['roc_auc'] if val_metrics['roc_auc'] is not None else 'NA'}"
    )
    print(
        "Test - "
        f"F1={test_metrics['f1']:.4f} "
        f"Recall={test_metrics['recall']:.4f} "
        f"Precision={test_metrics['precision']:.4f} "
        f"AUC={test_metrics['roc_auc'] if test_metrics['roc_auc'] is not None else 'NA'}"
    )
    print("Note: Tree models are usually too large for ESP32-C2. Prefer --model-type logistic.")


if __name__ == "__main__":
    main()
