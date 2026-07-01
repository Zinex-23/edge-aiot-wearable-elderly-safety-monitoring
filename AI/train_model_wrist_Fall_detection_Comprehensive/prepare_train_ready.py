#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


CHANNELS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]
UP_REQUIRED = [
    "subject_id",
    "activity_id",
    "trial_id",
    "is_fall",
    "WRST_ACC_X",
    "WRST_ACC_Y",
    "WRST_ACC_Z",
    "WRST_ANG_X",
    "WRST_ANG_Y",
    "WRST_ANG_Z",
]

WEDA_ACCEL_COLS = ["accel_x_list", "accel_y_list", "accel_z_list"]
WEDA_GYRO_COLS = ["gyro_x_list", "gyro_y_list", "gyro_z_list"]
META_COLS = [
    "source",
    "subject_id",
    "trial_id",
    "activity_code",
    "label",
    "source_freq_hz",
    "window_index",
    "start_index",
    "num_samples",
]


@dataclass
class TrialData:
    source: str
    subject_id: str
    trial_id: str
    activity_code: str
    label: int
    source_freq_hz: float
    values: np.ndarray  # shape: [n_samples, 6]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build train-ready windows from UP-Fall wrist and WEDA-FALL 50Hz."
    )
    parser.add_argument(
        "--up-csv",
        default="/home/dsoft1/Downloads/Fall_UP_Dataset/up_fall_wrist.csv",
        help="Path to UP-Fall wrist csv.",
    )
    parser.add_argument(
        "--weda-50hz-dir",
        default="/home/dsoft1/Downloads/WEDA-FALL-main/dataset/50Hz",
        help="Path to WEDA-FALL 50Hz directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/dsoft1/Downloads/train_model_wrist_Fall_detection_Comprehensive/train_ready",
        help="Directory for generated windows and splits.",
    )
    parser.add_argument(
        "--window-seconds",
        type=float,
        default=2.0,
        help="Window length in seconds.",
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=0.5,
        help="Window overlap ratio in [0, 1).",
    )
    parser.add_argument(
        "--up-freq",
        type=float,
        default=4.0,
        help="Effective UP-Fall wrist sampling frequency (Hz).",
    )
    parser.add_argument(
        "--weda-freq",
        type=float,
        default=50.0,
        help="WEDA-FALL 50Hz frequency (Hz).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for subject split.")
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not (0.0 <= args.overlap < 1.0):
        raise ValueError("--overlap must be in [0, 1).")
    total = args.train_ratio + args.val_ratio + args.test_ratio
    if not np.isclose(total, 1.0):
        raise ValueError("train/val/test ratios must sum to 1.0.")


def stats(prefix: str, x: np.ndarray) -> Dict[str, float]:
    p25 = float(np.percentile(x, 25))
    p75 = float(np.percentile(x, 75))
    return {
        f"{prefix}_mean": float(np.mean(x)),
        f"{prefix}_std": float(np.std(x)),
        f"{prefix}_min": float(np.min(x)),
        f"{prefix}_max": float(np.max(x)),
        f"{prefix}_median": float(np.median(x)),
        f"{prefix}_p25": p25,
        f"{prefix}_p75": p75,
        f"{prefix}_iqr": p75 - p25,
        f"{prefix}_energy": float(np.mean(np.square(x))),
        f"{prefix}_abs_mean": float(np.mean(np.abs(x))),
    }


def extract_features(window: np.ndarray) -> Dict[str, float]:
    feats: Dict[str, float] = {}
    for idx, name in enumerate(CHANNELS):
        feats.update(stats(name, window[:, idx]))

    acc_mag = np.linalg.norm(window[:, :3], axis=1)
    gyro_mag = np.linalg.norm(window[:, 3:], axis=1)
    feats.update(stats("acc_mag", acc_mag))
    feats.update(stats("gyro_mag", gyro_mag))
    return feats


def load_up_trials(up_csv: Path, source_freq_hz: float) -> List[TrialData]:
    df = pd.read_csv(up_csv)
    missing = [c for c in UP_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"UP csv missing columns: {missing}")

    numeric_cols = [
        "WRST_ACC_X",
        "WRST_ACC_Y",
        "WRST_ACC_Z",
        "WRST_ANG_X",
        "WRST_ANG_Y",
        "WRST_ANG_Z",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=numeric_cols)

    trials: List[TrialData] = []
    grouped = df.groupby(["subject_id", "activity_id", "trial_id"], sort=False)
    for (subject_id, activity_id, trial_id), g in grouped:
        values = g[numeric_cols].to_numpy(dtype=np.float64, copy=True)
        if len(values) < 2:
            continue
        label = int(g["is_fall"].iloc[0])
        sid = str(subject_id).zfill(2)
        aid = str(activity_id).zfill(2)
        tid = str(trial_id).zfill(2)
        trials.append(
            TrialData(
                source="UP",
                subject_id=f"UP_{sid}",
                trial_id=f"UP_S{sid}_A{aid}_T{tid}",
                activity_code=f"A{aid}",
                label=label,
                source_freq_hz=source_freq_hz,
                values=values,
            )
        )
    return trials


def load_weda_trials(weda_50hz_dir: Path, source_freq_hz: float) -> List[TrialData]:
    if not weda_50hz_dir.exists():
        raise FileNotFoundError(f"WEDA directory not found: {weda_50hz_dir}")

    trials: List[TrialData] = []
    file_pat = re.compile(r"^U(\d+)_R(\d+)_accel\.csv$")

    for activity_dir in sorted(p for p in weda_50hz_dir.iterdir() if p.is_dir()):
        activity_code = activity_dir.name
        label = 1 if activity_code.startswith("F") else 0

        for accel_file in sorted(activity_dir.glob("*_accel.csv")):
            m = file_pat.match(accel_file.name)
            if not m:
                continue
            user_id, trial_num = m.groups()
            stem = accel_file.name.replace("_accel.csv", "")
            gyro_file = activity_dir / f"{stem}_gyro.csv"
            if not gyro_file.exists():
                continue

            acc_df = pd.read_csv(accel_file, encoding="utf-8-sig")
            gyro_df = pd.read_csv(gyro_file, encoding="utf-8-sig")
            if not all(c in acc_df.columns for c in WEDA_ACCEL_COLS):
                continue
            if not all(c in gyro_df.columns for c in WEDA_GYRO_COLS):
                continue

            acc = acc_df[WEDA_ACCEL_COLS].apply(pd.to_numeric, errors="coerce")
            gyr = gyro_df[WEDA_GYRO_COLS].apply(pd.to_numeric, errors="coerce")
            n = min(len(acc), len(gyr))
            if n < 2:
                continue
            acc = acc.iloc[:n].dropna()
            gyr = gyr.iloc[:n].dropna()
            n = min(len(acc), len(gyr))
            if n < 2:
                continue
            arr = np.column_stack(
                [
                    acc.iloc[:n, 0].to_numpy(np.float64),
                    acc.iloc[:n, 1].to_numpy(np.float64),
                    acc.iloc[:n, 2].to_numpy(np.float64),
                    gyr.iloc[:n, 0].to_numpy(np.float64),
                    gyr.iloc[:n, 1].to_numpy(np.float64),
                    gyr.iloc[:n, 2].to_numpy(np.float64),
                ]
            )

            uid = f"{int(user_id):02d}"
            rid = f"{int(trial_num):02d}"
            trials.append(
                TrialData(
                    source="WEDA",
                    subject_id=f"WEDA_{uid}",
                    trial_id=f"WEDA_{activity_code}_U{uid}_R{rid}",
                    activity_code=activity_code,
                    label=label,
                    source_freq_hz=source_freq_hz,
                    values=arr,
                )
            )

    return trials


def generate_windows(
    trials: Iterable[TrialData], window_seconds: float, overlap: float
) -> pd.DataFrame:
    records: List[Dict[str, float]] = []

    for trial in trials:
        n = len(trial.values)
        window_size = max(2, int(round(window_seconds * trial.source_freq_hz)))
        step = max(1, int(round(window_size * (1.0 - overlap))))

        if n < window_size:
            continue

        w_idx = 0
        for start in range(0, n - window_size + 1, step):
            seg = trial.values[start : start + window_size]
            rec: Dict[str, float] = {
                "source": trial.source,
                "subject_id": trial.subject_id,
                "trial_id": trial.trial_id,
                "activity_code": trial.activity_code,
                "label": trial.label,
                "source_freq_hz": trial.source_freq_hz,
                "window_index": w_idx,
                "start_index": start,
                "num_samples": window_size,
            }
            rec.update(extract_features(seg))
            records.append(rec)
            w_idx += 1

    if not records:
        raise RuntimeError("No windows generated. Check source paths and parameters.")
    return pd.DataFrame.from_records(records)


def split_counts(n: int, train_ratio: float, val_ratio: float, test_ratio: float) -> Tuple[int, int, int]:
    if n <= 0:
        return 0, 0, 0
    if n == 1:
        return 1, 0, 0
    if n == 2:
        return 1, 1, 0

    n_train = int(round(n * train_ratio))
    n_val = int(round(n * val_ratio))
    n_test = n - n_train - n_val

    if n_val == 0:
        n_val = 1
        n_train = max(1, n_train - 1)
    if n_test == 0:
        n_test = 1
        n_train = max(1, n_train - 1)

    while (n_train + n_val + n_test) > n:
        if n_train >= max(n_val, n_test) and n_train > 1:
            n_train -= 1
        elif n_val >= n_test and n_val > 1:
            n_val -= 1
        elif n_test > 1:
            n_test -= 1
        else:
            break

    while (n_train + n_val + n_test) < n:
        n_train += 1

    return n_train, n_val, n_test


def split_subjects(
    windows_df: pd.DataFrame,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> Dict[str, List[str]]:
    rng = np.random.default_rng(seed)
    subject_df = (
        windows_df.groupby("subject_id", as_index=False)["label"]
        .max()
        .rename(columns={"label": "has_fall"})
    )

    fall_subjects = subject_df[subject_df["has_fall"] == 1]["subject_id"].tolist()
    non_fall_subjects = subject_df[subject_df["has_fall"] == 0]["subject_id"].tolist()

    rng.shuffle(fall_subjects)
    rng.shuffle(non_fall_subjects)

    split_map = {"train": [], "validation": [], "test": []}
    for subjects in (fall_subjects, non_fall_subjects):
        n_train, n_val, n_test = split_counts(
            len(subjects), train_ratio, val_ratio, test_ratio
        )
        split_map["train"].extend(subjects[:n_train])
        split_map["validation"].extend(subjects[n_train : n_train + n_val])
        split_map["test"].extend(subjects[n_train + n_val : n_train + n_val + n_test])

    split_map = {k: sorted(v) for k, v in split_map.items()}
    train_set, val_set, test_set = (
        set(split_map["train"]),
        set(split_map["validation"]),
        set(split_map["test"]),
    )
    if train_set & val_set or train_set & test_set or val_set & test_set:
        raise RuntimeError("Subject overlap detected between splits.")
    return split_map


def assign_split(windows_df: pd.DataFrame, split_map: Dict[str, List[str]]) -> pd.DataFrame:
    train_set = set(split_map["train"])
    val_set = set(split_map["validation"])
    test_set = set(split_map["test"])

    def _map(subject_id: str) -> str:
        if subject_id in train_set:
            return "train"
        if subject_id in val_set:
            return "validation"
        if subject_id in test_set:
            return "test"
        return "unassigned"

    out = windows_df.copy()
    out["split"] = out["subject_id"].map(_map)
    out = out[out["split"] != "unassigned"].reset_index(drop=True)
    return out


def summary_by_split(df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for split_name, sdf in df.groupby("split"):
        summary[split_name] = {
            "rows": int(len(sdf)),
            "fall_rows": int((sdf["label"] == 1).sum()),
            "non_fall_rows": int((sdf["label"] == 0).sum()),
            "subjects": int(sdf["subject_id"].nunique()),
            "trials": int(sdf["trial_id"].nunique()),
        }
    return summary


def main() -> None:
    args = parse_args()
    validate_args(args)

    up_csv = Path(args.up_csv)
    weda_dir = Path(args.weda_50hz_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    up_trials = load_up_trials(up_csv, source_freq_hz=args.up_freq)
    weda_trials = load_weda_trials(weda_dir, source_freq_hz=args.weda_freq)
    all_trials = up_trials + weda_trials
    if not all_trials:
        raise RuntimeError("No trials loaded from sources.")

    windows_df = generate_windows(
        all_trials, window_seconds=args.window_seconds, overlap=args.overlap
    )
    split_map = split_subjects(
        windows_df,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
    )
    windows_df = assign_split(windows_df, split_map)

    feature_cols = sorted(c for c in windows_df.columns if c not in (META_COLS + ["split"]))
    windows_df = windows_df[META_COLS + feature_cols + ["split"]]

    windows_all_path = out_dir / "windows_all.csv"
    train_path = out_dir / "train.csv"
    val_path = out_dir / "validation.csv"
    test_path = out_dir / "test.csv"
    split_json_path = out_dir / "subject_splits.json"
    summary_json_path = out_dir / "split_summary.json"

    windows_df.to_csv(windows_all_path, index=False)
    windows_df[windows_df["split"] == "train"].drop(columns=["split"]).to_csv(train_path, index=False)
    windows_df[windows_df["split"] == "validation"].drop(columns=["split"]).to_csv(
        val_path, index=False
    )
    windows_df[windows_df["split"] == "test"].drop(columns=["split"]).to_csv(test_path, index=False)

    with split_json_path.open("w", encoding="utf-8") as f:
        json.dump(split_map, f, indent=2)

    summary = summary_by_split(windows_df)
    with summary_json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Loaded trials: UP={len(up_trials)} WEDA={len(weda_trials)} total={len(all_trials)}")
    print(f"Windows saved: {len(windows_df)}")
    for name in ("train", "validation", "test"):
        info = summary.get(name, {})
        print(
            f"{name:>10}: rows={info.get('rows', 0)} "
            f"fall={info.get('fall_rows', 0)} non_fall={info.get('non_fall_rows', 0)} "
            f"subjects={info.get('subjects', 0)} trials={info.get('trials', 0)}"
        )
    print(f"Output directory: {out_dir}")


if __name__ == "__main__":
    main()
