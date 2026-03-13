#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


LABEL_NAME_TO_ID = {
    "fall": 0,
    "sit": 1,
    "walk": 2,
    "hand": 3,
    "crouching": 4,
}

ACTIVITY_TO_LABEL = {
    "F01": "fall",
    "F02": "fall",
    "F03": "fall",
    "F04": "fall",
    "F05": "fall",
    "F06": "fall",
    "F07": "fall",
    "F08": "fall",
    "D01": "walk",
    "D02": "walk",
    "D03": "walk",
    "D07": "walk",
    "D04": "sit",
    "D05": "sit",
    "D09": "hand",
    "D10": "hand",
    "D11": "hand",
    "D06": "crouching",
    "D08": "crouching",
}

META_COLS = [
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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create WEDA 50Hz dataset with 5 labels.")
    parser.add_argument(
        "--input-csv",
        default="/home/dsoft1/CAPSTONE/Code/data_processing/train_ready/windows_all.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/dsoft1/CAPSTONE/Code/data_processing/train_ready/data_set_5-label",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input_csv)
    df = df[df["source"] == "WEDA"].copy().reset_index(drop=True)

    df["label_name"] = df["activity_code"].map(ACTIVITY_TO_LABEL)
    if df["label_name"].isna().any():
        missing = sorted(df.loc[df["label_name"].isna(), "activity_code"].unique().tolist())
        raise RuntimeError(f"Missing label mapping for activity_code: {missing}")

    df["binary_label"] = df["label"].astype(int)
    df["label"] = df["label_name"].map(LABEL_NAME_TO_ID).astype(int)

    rng = np.random.default_rng(args.seed)
    subjects = sorted(df["subject_id"].unique().tolist())
    rng.shuffle(subjects)

    n_subjects = len(subjects)
    n_train = round(n_subjects * 0.6)
    n_val = round(n_subjects * 0.2)
    n_test = n_subjects - n_train - n_val

    split_map = {
        "train": sorted(subjects[:n_train]),
        "validation": sorted(subjects[n_train : n_train + n_val]),
        "test": sorted(subjects[n_train + n_val : n_train + n_val + n_test]),
    }

    subject_to_split = {subject_id: "train" for subject_id in split_map["train"]}
    subject_to_split.update({subject_id: "validation" for subject_id in split_map["validation"]})
    subject_to_split.update({subject_id: "test" for subject_id in split_map["test"]})

    df["split"] = df["subject_id"].map(subject_to_split)
    if df["split"].isna().any():
        raise RuntimeError("Found rows without assigned split.")

    feature_cols = sorted(c for c in df.columns if c not in META_COLS + ["split"])
    df = df[META_COLS + feature_cols + ["split"]]

    df.to_csv(out_dir / "windows_all.csv", index=False)
    df[df["split"] == "train"].drop(columns=["split"]).to_csv(out_dir / "train.csv", index=False)
    df[df["split"] == "validation"].drop(columns=["split"]).to_csv(
        out_dir / "validation.csv", index=False
    )
    df[df["split"] == "test"].drop(columns=["split"]).to_csv(out_dir / "test.csv", index=False)

    (out_dir / "subject_splits.json").write_text(json.dumps(split_map, indent=2), encoding="utf-8")
    (out_dir / "label_mapping.json").write_text(
        json.dumps(
            {
                "label_name_to_id": LABEL_NAME_TO_ID,
                "activity_to_label": ACTIVITY_TO_LABEL,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {}
    for split_name, sdf in df.groupby("split"):
        summary[split_name] = {
            "rows": int(len(sdf)),
            "subjects": int(sdf["subject_id"].nunique()),
            "trials": int(sdf["trial_id"].nunique()),
            "labels": {k: int(v) for k, v in sdf["label_name"].value_counts().sort_index().items()},
        }
    (out_dir / "split_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Output directory: {out_dir}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
