#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


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
    parser = argparse.ArgumentParser(description="Train multiclass 5-label wearable model.")
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--val-csv", required=True)
    parser.add_argument("--test-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--max-depth", type=int, default=14)
    parser.add_argument("--min-samples-leaf", type=int, default=2)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def feature_columns(df: pd.DataFrame) -> List[str]:
    return sorted(c for c in df.columns if c not in NON_FEATURE_COLS)


def build_model(train_df: pd.DataFrame, cols: List[str], args: argparse.Namespace) -> Pipeline:
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(train_df[c])]
    pre = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_cols,
            )
        ],
        remainder="drop",
    )
    clf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight="balanced_subsample",
        random_state=args.random_state,
        n_jobs=-1,
    )
    return Pipeline(steps=[("pre", pre), ("clf", clf)])


def evaluate_split(
    model: Pipeline, df: pd.DataFrame, cols: List[str], label_names: List[str]
) -> Dict[str, object]:
    y_true = df["label"].to_numpy()
    y_pred = model.predict(df[cols])
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(label_names))))
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(label_names))),
        target_names=label_names,
        output_dict=True,
        zero_division=0,
    )
    return {
        "n_rows": int(len(df)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(args.train_csv)
    val_df = pd.read_csv(args.val_csv)
    test_df = pd.read_csv(args.test_csv)

    cols = feature_columns(train_df)
    labels_df = (
        pd.concat([train_df[["label", "label_name"]], val_df[["label", "label_name"]], test_df[["label", "label_name"]]])
        .drop_duplicates()
        .sort_values("label")
    )
    label_names = labels_df["label_name"].tolist()

    model = build_model(train_df, cols, args)
    model.fit(train_df[cols], train_df["label"])

    metrics = {
        "config": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "random_state": args.random_state,
            "feature_count": len(cols),
            "labels": label_names,
        },
        "train": evaluate_split(model, train_df, cols, label_names),
        "validation": evaluate_split(model, val_df, cols, label_names),
        "test": evaluate_split(model, test_df, cols, label_names),
    }

    bundle = {
        "model": model,
        "feature_cols": cols,
        "label_names": label_names,
    }
    joblib.dump(bundle, output_dir / "multiclass_model.joblib")
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("Saved model:", output_dir / "multiclass_model.joblib")
    print("Saved metrics:", output_dir / "metrics.json")
    for split_name in ("train", "validation", "test"):
        split_metrics = metrics[split_name]
        print(
            f"{split_name}: accuracy={split_metrics['accuracy']:.4f} "
            f"macro_f1={split_metrics['macro_f1']:.4f} "
            f"weighted_f1={split_metrics['weighted_f1']:.4f}"
        )


if __name__ == "__main__":
    main()
