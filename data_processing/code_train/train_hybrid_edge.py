#!/usr/bin/env python3
"""
Hybrid Edge AI training for fall detection using engineered window features.

Stage 1 (cheap gate):
    A single threshold on one low-cost feature (for example acc_mag_max)
    filters obvious non-fall windows.

Stage 2 (ML classifier):
    A stronger model runs only on gated windows and outputs fall probability.

This script is designed for datasets shaped like:
    train.csv / validation.csv / test.csv
with metadata columns + feature columns + label column.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

METADATA_COLS = {
    "label",
    "subject_id",
    "trial_id",
    "activity_code",
    "window_index",
    "start_index",
    "num_samples",
}

GATE_FEATURE_CANDIDATES = [
    "acc_mag_max",
    "acc_mag_std",
    "acc_mag_mean",
    "acc_mag_energy",
    "gyro_mag_max",
    "gyro_mag_std",
    "gyro_mag_mean",
    "gyro_mag_energy",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Hybrid Edge AI fall detector.")
    parser.add_argument(
        "--preset",
        choices=[
            "default",
            "esp32c3_safe",
            "esp32s3_quality",
            "esp32s3_max_quality",
        ],
        default="default",
        help="Apply a predefined hyperparameter profile for target hardware.",
    )
    parser.add_argument("--train-csv", default="train.csv")
    parser.add_argument("--val-csv", default="validation.csv")
    parser.add_argument("--test-csv", default="test.csv")
    parser.add_argument("--min-gate-recall", type=float, default=0.98)
    parser.add_argument("--rf-trees", type=int, default=400)
    parser.add_argument(
        "--rf-max-depth",
        type=int,
        default=None,
        help="Maximum depth for stage-2 RandomForest trees (smaller = lighter model).",
    )
    parser.add_argument(
        "--rf-min-samples-leaf",
        type=int,
        default=2,
        help="Minimum samples per leaf for stage-2 RandomForest.",
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--drop-source",
        action="store_true",
        help="Drop source/source_freq_hz from stage-2 features.",
    )
    parser.add_argument(
        "--gate-source",
        default="ALL",
        help="Fit gate on a validation source only (e.g. WEDA, UP). Default: ALL.",
    )
    parser.add_argument("--output-dir", default="hybrid_artifacts")
    return parser.parse_args()


def apply_preset(args: argparse.Namespace) -> argparse.Namespace:
    if args.preset == "default":
        return args

    profiles = {
        # Tuned for ESP32-C3 memory budget (~<=250KB model artifact in this dataset).
        "esp32c3_safe": {
            "min_gate_recall": 0.90,
            "rf_trees": 12,
            "rf_max_depth": 8,
            "rf_min_samples_leaf": 5,
            "drop_source": True,
            "gate_source": "ALL",
        },
        # Tuned for ESP32-S3 quality with much better metrics and still practical size.
        "esp32s3_quality": {
            "min_gate_recall": 0.90,
            "rf_trees": 40,
            "rf_max_depth": 12,
            "rf_min_samples_leaf": 4,
            "drop_source": False,
            "gate_source": "ALL",
        },
        # Higher quality, larger size. Use when flash partition allows bigger model.
        "esp32s3_max_quality": {
            "min_gate_recall": 0.90,
            "rf_trees": 50,
            "rf_max_depth": 12,
            "rf_min_samples_leaf": 2,
            "drop_source": True,
            "gate_source": "ALL",
        },
    }

    profile = profiles[args.preset]
    args.min_gate_recall = profile["min_gate_recall"]
    args.rf_trees = profile["rf_trees"]
    args.rf_max_depth = profile["rf_max_depth"]
    args.rf_min_samples_leaf = profile["rf_min_samples_leaf"]
    args.drop_source = profile["drop_source"]
    args.gate_source = profile["gate_source"]
    return args


def safe_div(n: float, d: float) -> float:
    return float(n / d) if d else 0.0


def gate_stats(y: np.ndarray, gate_mask: np.ndarray) -> Dict[str, float]:
    positives = float((y == 1).sum())
    negatives = float((y == 0).sum())
    tp_gate = float(((y == 1) & gate_mask).sum())
    fp_gate = float(((y == 0) & gate_mask).sum())
    return {
        "gate_pass_rate": float(gate_mask.mean()),
        "gate_recall_on_fall": safe_div(tp_gate, positives),
        "gate_fpr_on_non_fall": safe_div(fp_gate, negatives),
    }


def apply_gate(values: np.ndarray, threshold: float, op: str) -> np.ndarray:
    if op == ">=":
        return values >= threshold
    if op == "<=":
        return values <= threshold
    raise ValueError(f"Unsupported gate operation: {op}")


def search_best_gate(
    train_df: pd.DataFrame, val_df: pd.DataFrame, min_gate_recall: float
) -> Dict[str, float]:
    y_val = val_df["label"].to_numpy()
    candidates: List[Dict[str, float]] = []

    for feature in GATE_FEATURE_CANDIDATES:
        if feature not in train_df.columns or feature not in val_df.columns:
            continue
        train_values = train_df[feature].dropna().to_numpy()
        if train_values.size < 10:
            continue
        quantiles = np.linspace(0.0, 1.0, 201)
        thresholds = np.unique(np.quantile(train_values, quantiles))
        val_values = val_df[feature].to_numpy()
        for threshold in thresholds:
            for op in (">=", "<="):
                gate_mask = apply_gate(val_values, float(threshold), op)
                stats = gate_stats(y_val, gate_mask)
                candidates.append(
                    {
                        "feature": feature,
                        "threshold": float(threshold),
                        "op": op,
                        **stats,
                    }
                )

    if not candidates:
        raise RuntimeError("No valid gate candidates were found.")

    feasible = [c for c in candidates if c["gate_recall_on_fall"] >= min_gate_recall]
    if feasible:
        feasible.sort(
            key=lambda c: (
                c["gate_pass_rate"],
                c["gate_fpr_on_non_fall"],
                -c["gate_recall_on_fall"],
            )
        )
        return feasible[0]

    candidates.sort(
        key=lambda c: (-c["gate_recall_on_fall"], c["gate_pass_rate"], c["gate_fpr_on_non_fall"])
    )
    return candidates[0]


def build_stage2_pipeline(
    x_train: pd.DataFrame,
    rf_trees: int,
    rf_max_depth: int | None,
    rf_min_samples_leaf: int,
    random_state: int,
) -> Pipeline:
    num_cols = [c for c in x_train.columns if pd.api.types.is_numeric_dtype(x_train[c])]
    cat_cols = [c for c in x_train.columns if c not in num_cols]

    transformers = []
    if num_cols:
        transformers.append(
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                num_cols,
            )
        )
    if cat_cols:
        transformers.append(
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                cat_cols,
            )
        )
    if not transformers:
        raise RuntimeError("No features available for stage-2 model.")

    pre = ColumnTransformer(transformers=transformers, remainder="drop")
    clf = RandomForestClassifier(
        n_estimators=rf_trees,
        max_depth=rf_max_depth,
        class_weight="balanced_subsample",
        random_state=random_state,
        n_jobs=-1,
        min_samples_leaf=rf_min_samples_leaf,
    )
    return Pipeline(steps=[("pre", pre), ("clf", clf)])


def choose_decision_threshold(y_true: np.ndarray, proba: np.ndarray) -> float:
    thresholds = np.linspace(0.05, 0.95, 181)
    best_t = 0.50
    best_f1 = -1.0
    for t in thresholds:
        pred = (proba >= t).astype(int)
        f1 = f1_score(y_true, pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = float(t)
    return best_t


def eval_split(
    df: pd.DataFrame,
    stage2_model: Pipeline,
    feature_cols: List[str],
    gate_feature: str,
    gate_threshold: float,
    gate_op: str,
    decision_threshold: float,
) -> Dict[str, float]:
    y = df["label"].to_numpy()
    gate_mask = apply_gate(df[gate_feature].to_numpy(), gate_threshold, gate_op)

    proba = np.zeros(len(df), dtype=float)
    if gate_mask.any():
        proba[gate_mask] = stage2_model.predict_proba(df.loc[gate_mask, feature_cols])[:, 1]
    pred = (proba >= decision_threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    metrics = {
        "n_rows": int(len(df)),
        "fall_ratio": float(y.mean()),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y, proba)),
        "roc_auc": float(roc_auc_score(y, proba)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "fpr": safe_div(fp, fp + tn),
        "fnr": safe_div(fn, fn + tp),
    }
    metrics.update(gate_stats(y, gate_mask))
    return metrics


def eval_per_source(
    df: pd.DataFrame,
    stage2_model: Pipeline,
    feature_cols: List[str],
    gate_feature: str,
    gate_threshold: float,
    gate_op: str,
    decision_threshold: float,
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    if "source" not in df.columns:
        return out

    for source, group in df.groupby("source"):
        out[str(source)] = eval_split(
            group,
            stage2_model,
            feature_cols,
            gate_feature,
            gate_threshold,
            gate_op,
            decision_threshold,
        )
    return out


def main() -> None:
    args = parse_args()
    args = apply_preset(args)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train_csv)
    val_df = pd.read_csv(args.val_csv)
    test_df = pd.read_csv(args.test_csv)

    gate_val_df = val_df
    if args.gate_source.upper() != "ALL":
        gate_val_df = val_df[val_df["source"] == args.gate_source].copy()
        if gate_val_df.empty:
            raise RuntimeError(
                f"--gate-source {args.gate_source} not found in validation data."
            )

    gate = search_best_gate(train_df, gate_val_df, args.min_gate_recall)
    gate_feature = str(gate["feature"])
    gate_threshold = float(gate["threshold"])
    gate_op = str(gate["op"])

    drop_cols = set(METADATA_COLS)
    if args.drop_source:
        drop_cols.update({"source", "source_freq_hz"})
    feature_cols = [c for c in train_df.columns if c not in drop_cols]

    train_gate_mask = apply_gate(train_df[gate_feature].to_numpy(), gate_threshold, gate_op)
    train_stage2 = train_df.loc[train_gate_mask].copy()
    if train_stage2["label"].nunique() < 2:
        raise RuntimeError(
            "Stage-2 gated training set has only one class. "
            "Reduce --min-gate-recall or use a lower gate threshold."
        )

    stage2_model = build_stage2_pipeline(
        train_stage2[feature_cols],
        args.rf_trees,
        args.rf_max_depth,
        args.rf_min_samples_leaf,
        args.random_state,
    )
    stage2_model.fit(train_stage2[feature_cols], train_stage2["label"])

    val_gate_mask = apply_gate(val_df[gate_feature].to_numpy(), gate_threshold, gate_op)
    val_proba = np.zeros(len(val_df), dtype=float)
    if val_gate_mask.any():
        val_proba[val_gate_mask] = stage2_model.predict_proba(
            val_df.loc[val_gate_mask, feature_cols]
        )[:, 1]
    decision_threshold = choose_decision_threshold(val_df["label"].to_numpy(), val_proba)

    metrics = {
        "config": {
            "gate_feature": gate_feature,
            "gate_threshold": gate_threshold,
            "gate_op": gate_op,
            "decision_threshold": decision_threshold,
            "min_gate_recall_requested": args.min_gate_recall,
            "gate_source_for_search": args.gate_source,
            "drop_source": bool(args.drop_source),
            "preset": args.preset,
            "rf_trees": args.rf_trees,
            "rf_max_depth": args.rf_max_depth,
            "rf_min_samples_leaf": args.rf_min_samples_leaf,
            "random_state": args.random_state,
            "n_stage2_train_rows": int(len(train_stage2)),
            "n_stage2_train_fall": int(train_stage2["label"].sum()),
            "n_stage2_train_non_fall": int(len(train_stage2) - train_stage2["label"].sum()),
        },
        "validation": eval_split(
            val_df,
            stage2_model,
            feature_cols,
            gate_feature,
            gate_threshold,
            gate_op,
            decision_threshold,
        ),
        "test": eval_split(
            test_df,
            stage2_model,
            feature_cols,
            gate_feature,
            gate_threshold,
            gate_op,
            decision_threshold,
        ),
        "validation_per_source": eval_per_source(
            val_df,
            stage2_model,
            feature_cols,
            gate_feature,
            gate_threshold,
            gate_op,
            decision_threshold,
        ),
        "test_per_source": eval_per_source(
            test_df,
            stage2_model,
            feature_cols,
            gate_feature,
            gate_threshold,
            gate_op,
            decision_threshold,
        ),
    }

    model_bundle = {
        "stage2_model": stage2_model,
        "feature_cols": feature_cols,
        "gate_feature": gate_feature,
        "gate_threshold": gate_threshold,
        "gate_op": gate_op,
        "decision_threshold": decision_threshold,
    }
    model_path = output_dir / "hybrid_model.joblib"
    joblib.dump(model_bundle, model_path)
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("Hybrid model trained.")
    print(f"- Gate: {gate_feature} {gate_op} {gate_threshold:.6f}")
    print(f"- Decision threshold: {decision_threshold:.3f}")
    print(
        f"- Stage2 train rows: {metrics['config']['n_stage2_train_rows']}/{len(train_df)} "
        f"({metrics['config']['n_stage2_train_rows']/len(train_df):.3f})"
    )
    print(f"- Preset: {args.preset}")
    print(f"- Model size: {os.path.getsize(model_path)/1024:.1f} KB")
    print("- Validation:", json.dumps(metrics["validation"], indent=2))
    print("- Test:", json.dumps(metrics["test"], indent=2))
    print(f"- Saved model: {model_path}")
    print(f"- Saved metrics: {output_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
