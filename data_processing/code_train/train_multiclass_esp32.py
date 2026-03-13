#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)


NON_FEATURE_COLS = {
    "source",
    "subject_id",
    "trial_id",
    "activity_code",
    "label",
    "label_name",
    "binary_label",
    "source_freq_hz",
    "window_index",
    "start_index",
    "num_samples",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train compact multiclass model for ESP32-S3.")
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--val-csv", required=True)
    parser.add_argument("--test-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--c", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--top-k",
        type=int,
        default=0,
        help="Keep only top-k features by aggregated abs weight. 0 keeps all.",
    )
    return parser.parse_args()


def feature_columns(df: pd.DataFrame) -> List[str]:
    return sorted(c for c in df.columns if c not in NON_FEATURE_COLS)


def split_xy(df: pd.DataFrame, cols: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    x = df[cols].to_numpy(dtype=np.float64, copy=True)
    y = df["label"].to_numpy(dtype=np.int64, copy=True)
    return x, y


def impute_and_standardize(
    x_train: np.ndarray,
    x_val: np.ndarray,
    x_test: np.ndarray,
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


def evaluate_split(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_names: List[str],
    fall_label_id: int,
) -> Dict[str, object]:
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    fall_true = (y_true == fall_label_id).astype(int)
    fall_pred = (y_pred == fall_label_id).astype(int)
    fall_p, fall_r, fall_f1, _ = precision_recall_fscore_support(
        fall_true, fall_pred, average="binary", zero_division=0
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(label_names))),
        target_names=label_names,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(label_names))))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(macro_p),
        "macro_recall": float(macro_r),
        "macro_f1": float(macro_f1),
        "weighted_precision": float(weighted_p),
        "weighted_recall": float(weighted_r),
        "weighted_f1": float(weighted_f1),
        "fall_precision": float(fall_p),
        "fall_recall": float(fall_r),
        "fall_f1": float(fall_f1),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }


def select_top_k_features(
    feature_cols: List[str],
    mean: np.ndarray,
    std: np.ndarray,
    coef: np.ndarray,
    top_k: int,
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray]:
    if top_k <= 0 or top_k >= len(feature_cols):
        return feature_cols, mean, std, coef

    importance = np.abs(coef).sum(axis=0)
    selected_idx = np.sort(np.argsort(importance)[::-1][:top_k])
    selected_cols = [feature_cols[int(i)] for i in selected_idx]
    return selected_cols, mean[selected_idx], std[selected_idx], coef[:, selected_idx]


def build_include_guard(path: Path) -> str:
    chars = []
    for ch in path.name.upper():
        chars.append(ch if ch.isalnum() else "_")
    out = "".join(chars)
    if not out.endswith("_H"):
        out += "_H"
    return out


def c_array_float(name: str, arr: np.ndarray, per_line: int = 8) -> str:
    vals = [f"{float(x):.9g}f" for x in arr.reshape(-1).tolist()]
    lines = []
    for i in range(0, len(vals), per_line):
        lines.append("  " + ", ".join(vals[i : i + per_line]))
    body = ",\n".join(lines)
    return f"static const float {name}[{arr.size}] = {{\n{body}\n}};\n"


def export_multiclass_header(
    out_path: Path,
    feature_cols: List[str],
    label_names: List[str],
    mean: np.ndarray,
    std: np.ndarray,
    coef: np.ndarray,
    intercept: np.ndarray,
) -> Dict[str, object]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    include_guard = build_include_guard(out_path)
    class_count = len(label_names)
    feature_count = len(feature_cols)
    label_literal = "{ " + ", ".join(json.dumps(name) for name in label_names) + " }"

    lines = [
        f"#ifndef {include_guard}",
        f"#define {include_guard}",
        "",
        "#include <math.h>",
        "#include <stdint.h>",
        "",
        f"#define EDGE_MC_CLASS_COUNT {class_count}",
        f"#define EDGE_MC_FEATURE_COUNT {feature_count}",
        "",
        c_array_float("edge_mc_mean", mean.astype(np.float32)),
        c_array_float("edge_mc_std", std.astype(np.float32)),
        c_array_float("edge_mc_coef", coef.astype(np.float32)),
        c_array_float("edge_mc_intercept", intercept.astype(np.float32)),
        f"static const char *edge_mc_label_names[EDGE_MC_CLASS_COUNT] = {label_literal};",
        "",
        "static inline void edge_mc_predict_scores(const float *features, float *scores) {",
        "  for (int c = 0; c < EDGE_MC_CLASS_COUNT; ++c) {",
        "    float z = edge_mc_intercept[c];",
        "    const int base = c * EDGE_MC_FEATURE_COUNT;",
        "    for (int i = 0; i < EDGE_MC_FEATURE_COUNT; ++i) {",
        "      const float x = (features[i] - edge_mc_mean[i]) / edge_mc_std[i];",
        "      z += x * edge_mc_coef[base + i];",
        "    }",
        "    scores[c] = z;",
        "  }",
        "}",
        "",
        "static inline int edge_mc_predict_label(const float *features) {",
        "  float scores[EDGE_MC_CLASS_COUNT];",
        "  edge_mc_predict_scores(features, scores);",
        "  int best_idx = 0;",
        "  float best_score = scores[0];",
        "  for (int c = 1; c < EDGE_MC_CLASS_COUNT; ++c) {",
        "    if (scores[c] > best_score) {",
        "      best_score = scores[c];",
        "      best_idx = c;",
        "    }",
        "  }",
        "  return best_idx;",
        "}",
        "",
        f"#endif  // {include_guard}",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")

    bytes_total = feature_count * 4 * 2 + coef.size * 4 + intercept.size * 4
    return {
        "header_size_bytes": int(out_path.stat().st_size),
        "parameter_bytes": int(bytes_total),
        "parameter_kb": round(bytes_total / 1024.0, 4),
        "feature_count": feature_count,
        "class_count": class_count,
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train_csv)
    val_df = pd.read_csv(args.val_csv)
    test_df = pd.read_csv(args.test_csv)

    feature_cols = feature_columns(train_df)
    x_train_raw, y_train = split_xy(train_df, feature_cols)
    x_val_raw, y_val = split_xy(val_df, feature_cols)
    x_test_raw, y_test = split_xy(test_df, feature_cols)
    x_train, x_val, x_test, mean, std = impute_and_standardize(x_train_raw, x_val_raw, x_test_raw)

    labels_df = (
        pd.concat(
            [
                train_df[["label", "label_name"]],
                val_df[["label", "label_name"]],
                test_df[["label", "label_name"]],
            ]
        )
        .drop_duplicates()
        .sort_values("label")
    )
    label_names = labels_df["label_name"].tolist()
    fall_label_id = (
        int(labels_df.loc[labels_df["label_name"] == "fall", "label"].iloc[0])
        if "fall" in labels_df["label_name"].values
        else 0
    )

    model = LogisticRegression(
        C=float(args.c),
        class_weight="balanced",
        random_state=args.seed,
        solver="lbfgs",
        multi_class="multinomial",
        max_iter=5000,
    )
    model.fit(x_train, y_train)

    y_train_pred = model.predict(x_train)
    y_val_pred = model.predict(x_val)
    y_test_pred = model.predict(x_test)

    selected_feature_cols, selected_mean, selected_std, selected_coef = select_top_k_features(
        feature_cols,
        mean,
        std,
        model.coef_,
        args.top_k,
    )

    bundle = {
        "model": model,
        "feature_cols": feature_cols,
        "label_names": label_names,
        "mean": mean,
        "std": std,
        "selected_feature_cols": selected_feature_cols,
        "selected_mean": selected_mean,
        "selected_std": selected_std,
        "selected_coef": selected_coef,
        "intercept": model.intercept_,
    }
    joblib.dump(bundle, output_dir / "multiclass_esp32_model.joblib")

    header_meta = export_multiclass_header(
        output_dir / "multiclass_esp32_model.h",
        selected_feature_cols,
        label_names,
        selected_mean,
        selected_std,
        selected_coef,
        model.intercept_,
    )

    metrics = {
        "config": {
            "model_type": "logistic_multinomial",
            "c": float(args.c),
            "seed": int(args.seed),
            "top_k": int(args.top_k),
            "labels": label_names,
            "feature_count": len(feature_cols),
            "selected_feature_count": len(selected_feature_cols),
        },
        "train": evaluate_split(y_train, y_train_pred, label_names, fall_label_id),
        "validation": evaluate_split(y_val, y_val_pred, label_names, fall_label_id),
        "test": evaluate_split(y_test, y_test_pred, label_names, fall_label_id),
        "esp32_export": header_meta,
    }
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved model: {output_dir / 'multiclass_esp32_model.joblib'}")
    print(f"Saved header: {output_dir / 'multiclass_esp32_model.h'}")
    print(f"Saved metrics: {output_dir / 'metrics.json'}")
    print(f"Selected feature count: {len(selected_feature_cols)}")
    print(
        f"Header size: {header_meta['header_size_bytes']/1024.0:.2f} KB, "
        f"params: {header_meta['parameter_kb']:.2f} KB"
    )
    for split_name in ("train", "validation", "test"):
        split_metrics = metrics[split_name]
        print(
            f"{split_name}: acc={split_metrics['accuracy']:.4f} "
            f"macro_f1={split_metrics['macro_f1']:.4f} "
            f"fall_f1={split_metrics['fall_f1']:.4f}"
        )


if __name__ == "__main__":
    main()
