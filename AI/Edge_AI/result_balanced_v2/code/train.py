from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

import train_hr_imu_only as hr
import train_edge_ai_fall_model as core


ROOT = Path("result_balanced_v2")
DATASET_DIR = ROOT / "dataset"
REBUILT_DIR = DATASET_DIR / "rebuilt"
SPLIT_DIR = DATASET_DIR / "split"
CODE_DIR = ROOT / "code"
MODELS_DIR = ROOT / "models"
LOGS_DIR = ROOT / "logs"
RESULTS_DIR = ROOT / "results"
DOCS_DIR = ROOT / "docs"


def mkdirs() -> None:
    for p in [REBUILT_DIR, SPLIT_DIR, CODE_DIR, MODELS_DIR, LOGS_DIR, RESULTS_DIR, DOCS_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def evaluate_binary(y_true: np.ndarray, probs: np.ndarray, threshold: float = 0.5) -> dict[str, object]:
    pred = (probs >= threshold).astype(np.int32)
    acc = accuracy_score(y_true, pred)
    precision = precision_score(y_true, pred, zero_division=0)
    recall = recall_score(y_true, pred, zero_division=0)
    f1 = f1_score(y_true, pred, zero_division=0)
    cm = confusion_matrix(y_true, pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    far = fp / (fp + tn) if (fp + tn) else 0.0
    miss = fn / (fn + tp) if (fn + tp) else 0.0
    return {
        "accuracy": float(acc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_alarm_rate": float(far),
        "miss_rate": float(miss),
        "confusion_matrix": cm.tolist(),
    }


def build_model(train_x: np.ndarray) -> tf.keras.Model:
    norm = tf.keras.layers.Normalization(axis=-1, name="balanced_norm")
    norm.adapt(train_x.reshape(-1, train_x.shape[-1]))
    inputs = tf.keras.Input(shape=(100, 6), name="imu_window")
    x = norm(inputs)
    x = tf.keras.layers.Conv1D(16, 3, activation="relu", padding="same")(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    x = tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same")(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="fall_prob")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="balanced_hr_imu_tinycnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="binary_crossentropy",
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    return model


def convert_tflite(model: tf.keras.Model, train_x: np.ndarray, out_path: Path) -> bytes:
    export_dir = ROOT / "saved_model_for_tflite"
    if export_dir.exists():
        shutil.rmtree(export_dir)
    model.export(export_dir)
    samples = train_x[np.random.choice(len(train_x), size=min(200, len(train_x)), replace=False)]

    def representative():
        for sample in samples:
            yield [sample[np.newaxis, ...].astype(np.float32)]

    converter = tf.lite.TFLiteConverter.from_saved_model(str(export_dir))
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    blob = converter.convert()
    out_path.write_bytes(blob)
    shutil.rmtree(export_dir, ignore_errors=True)
    return blob


def export_header(blob: bytes, out_path: Path) -> None:
    tokens = [f"0x{b:02x}" for b in blob]
    lines = [", ".join(tokens[i:i + 12]) for i in range(0, len(tokens), 12)]
    text = "#ifndef FALL_DETECTION_MODEL_H\n#define FALL_DETECTION_MODEL_H\n\n#include <stddef.h>\n\nconst unsigned char fall_detection_model_tflite[] = {\n  " + ",\n  ".join(lines) + f"\n}};\n\nconst unsigned int fall_detection_model_tflite_len = {len(blob)};\n\n#endif\n"
    write_text(out_path, text)


def plot_training(history_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(history_df["epoch"], history_df["loss"], label="Train Loss")
    ax.plot(history_df["epoch"], history_df["val_loss"], label="Validation Loss")
    ax.set_title("Loss vs Epoch")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "training_loss.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(history_df["epoch"], history_df["accuracy"], label="Train Accuracy")
    ax.plot(history_df["epoch"], history_df["val_accuracy"], label="Validation Accuracy")
    ax.set_title("Accuracy vs Epoch")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "training_accuracy.png", dpi=150)
    plt.close(fig)


def plot_confusion(cm: list[list[int]]) -> None:
    arr = np.asarray(cm)
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(arr, cmap="Blues")
    ax.set_title("Confusion Matrix")
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_xticks([0, 1], labels=["non-fall", "fall"])
    ax.set_yticks([0, 1], labels=["non-fall", "fall"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(arr[i, j]), ha="center", va="center")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=150)
    plt.close(fig)


def plot_roc_pr(y_true: np.ndarray, probs: np.ndarray) -> tuple[float, float]:
    fpr, tpr, _ = roc_curve(y_true, probs)
    roc_auc = float(auc(fpr, tpr))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.set_title("ROC Curve")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "roc_curve.png", dpi=150)
    plt.close(fig)

    precision, recall, _ = precision_recall_curve(y_true, probs)
    pr_auc = float(auc(recall, precision))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(recall, precision, label=f"PR AUC = {pr_auc:.4f}")
    ax.set_title("Precision-Recall Curve")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "precision_recall_curve.png", dpi=150)
    plt.close(fig)
    return roc_auc, pr_auc


def plot_class_distribution(before_fall: int, before_non: int, after_fall: int, after_non: int) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["fall", "non-fall"], [after_fall, after_non], color=["#c44e52", "#4c72b0"])
    ax.set_title("Balanced Class Distribution")
    ax.set_xlabel("Class")
    ax.set_ylabel("Number of Windows")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "class_distribution.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(2)
    width = 0.35
    ax.bar(x - width / 2, [before_fall, before_non], width, label="Before balancing")
    ax.bar(x + width / 2, [after_fall, after_non], width, label="After balancing")
    ax.set_title("Window Distribution Before vs After Balancing")
    ax.set_xlabel("Class")
    ax.set_ylabel("Number of Windows")
    ax.set_xticks(x, ["fall", "non-fall"])
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "window_distribution.png", dpi=150)
    plt.close(fig)


def save_code_files() -> None:
    write_text(CODE_DIR / "preprocess.py", "from train_hr_imu_only import normalize_hr_file, rebuild_class_dataset\n")
    write_text(CODE_DIR / "windowing.py", "from train_hr_imu_only import build_windows\n")
    write_text(CODE_DIR / "train.py", Path("train_balanced_hr_imu_v2.py").read_text(encoding="utf-8"))
    write_text(CODE_DIR / "evaluate.py", "from train_balanced_hr_imu_v2 import evaluate_binary\n")
    write_text(CODE_DIR / "convert_tflite.py", "from train_balanced_hr_imu_v2 import convert_tflite\n")
    write_text(CODE_DIR / "export_header.py", "from train_balanced_hr_imu_v2 import export_header\n")


def main() -> None:
    core.set_seeds()
    mkdirs()

    fall_files, non_fall_files = hr.collect_files()
    fall_df, fall_seg, fall_logs = hr.rebuild_class_dataset(fall_files, "fall")
    non_df, non_seg, non_logs = hr.rebuild_class_dataset(non_fall_files, "non_fall")
    fall_df[hr.TARGET_COLUMNS].to_csv(REBUILT_DIR / "fall.csv", index=False)
    non_df[hr.TARGET_COLUMNS].to_csv(REBUILT_DIR / "non_fall.csv", index=False)

    fall_x, fall_y, fall_meta = hr.build_windows(fall_df, 1, "fall")
    non_x, non_y, non_meta = hr.build_windows(non_df, 0, "non_fall")

    before_fall = int(len(fall_y))
    before_non = int(len(non_y))
    keep = min(before_fall, before_non)
    fall_idx = np.random.choice(np.arange(before_fall), size=keep, replace=False)
    non_idx = np.random.choice(np.arange(before_non), size=keep, replace=False)

    fall_x_bal = fall_x[fall_idx]
    fall_y_bal = fall_y[fall_idx]
    fall_meta_bal = fall_meta.iloc[fall_idx].reset_index(drop=True)
    non_x_bal = non_x[non_idx]
    non_y_bal = non_y[non_idx]
    non_meta_bal = non_meta.iloc[non_idx].reset_index(drop=True)

    x = np.concatenate([fall_x_bal, non_x_bal], axis=0)
    y = np.concatenate([fall_y_bal, non_y_bal], axis=0)
    meta = pd.concat([fall_meta_bal, non_meta_bal], ignore_index=True)

    idx = np.arange(len(y))
    train_idx, temp_idx, train_labels, temp_labels = train_test_split(
        idx,
        y,
        test_size=0.30,
        random_state=core.SEED,
        stratify=y,
    )
    val_idx, test_idx, _, _ = train_test_split(
        temp_idx,
        temp_labels,
        test_size=0.50,
        random_state=core.SEED,
        stratify=temp_labels,
    )

    def subset(indices: np.ndarray):
        return x[indices], y[indices], meta.iloc[indices].reset_index(drop=True)

    train_x, train_y, train_meta = subset(train_idx)
    val_x, val_y, val_meta = subset(val_idx)
    test_x, test_y, test_meta = subset(test_idx)

    np.savez_compressed(SPLIT_DIR / "train_windows.npz", x=train_x, y=train_y)
    np.savez_compressed(SPLIT_DIR / "val_windows.npz", x=val_x, y=val_y)
    np.savez_compressed(SPLIT_DIR / "test_windows.npz", x=test_x, y=test_y)
    train_meta.to_csv(SPLIT_DIR / "train_window_metadata.csv", index=False)
    val_meta.to_csv(SPLIT_DIR / "val_window_metadata.csv", index=False)
    test_meta.to_csv(SPLIT_DIR / "test_window_metadata.csv", index=False)

    dataset_summary = pd.DataFrame(
        [
            {
                "class_name": "fall",
                "source_files_found": len(fall_files),
                "valid_files_used": sum(1 for x in fall_logs if x["used"]),
                "skipped_files": sum(1 for x in fall_logs if not x["used"]),
                "raw_rows": sum(int(x["raw_rows"]) for x in fall_logs),
                "final_rows_kept": len(fall_df),
            },
            {
                "class_name": "non_fall",
                "source_files_found": len(non_fall_files),
                "valid_files_used": sum(1 for x in non_logs if x["used"]),
                "skipped_files": sum(1 for x in non_logs if not x["used"]),
                "raw_rows": sum(int(x["raw_rows"]) for x in non_logs),
                "final_rows_kept": len(non_df),
            },
        ]
    )
    dataset_summary.to_csv(DATASET_DIR / "dataset_summary.csv", index=False)

    after_fall = int(np.sum(y == 1))
    after_non = int(np.sum(y == 0))
    total = len(y)
    window_summary = pd.DataFrame(
        [
            {
                "class_name": "fall",
                "before_balancing_windows": before_fall,
                "after_balancing_windows": after_fall,
                "percentage_of_total": after_fall / total if total else 0.0,
                "train_window_count": int(np.sum(train_y == 1)),
                "validation_window_count": int(np.sum(val_y == 1)),
                "test_window_count": int(np.sum(test_y == 1)),
            },
            {
                "class_name": "non_fall",
                "before_balancing_windows": before_non,
                "after_balancing_windows": after_non,
                "percentage_of_total": after_non / total if total else 0.0,
                "train_window_count": int(np.sum(train_y == 0)),
                "validation_window_count": int(np.sum(val_y == 0)),
                "test_window_count": int(np.sum(test_y == 0)),
            },
        ]
    )
    window_summary.to_csv(DATASET_DIR / "window_summary.csv", index=False)

    model = build_model(train_x)
    checkpoint = LOGS_DIR / "best.weights.h5"
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint, monitor="val_loss", save_best_only=True, save_weights_only=True),
    ]
    history = model.fit(
        train_x,
        train_y,
        validation_data=(val_x, val_y),
        epochs=60,
        batch_size=32,
        callbacks=callbacks,
        verbose=0,
    )
    model.load_weights(checkpoint)
    history_df = pd.DataFrame(history.history)
    history_df.insert(0, "epoch", np.arange(1, len(history_df) + 1))
    history_df.to_csv(LOGS_DIR / "history.csv", index=False)

    val_probs = model.predict(val_x, verbose=0).reshape(-1)
    thresholds = np.arange(0.30, 0.91, 0.05)
    sweep_rows = []
    for thr in thresholds:
        sweep_rows.append({"threshold": float(thr), **evaluate_binary(val_y, val_probs, float(thr))})
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(RESULTS_DIR / "threshold_metrics.csv", index=False)
    selected_threshold = float(sweep_df.sort_values(["f1", "recall", "false_alarm_rate"], ascending=[False, False, True]).iloc[0]["threshold"])

    test_probs = model.predict(test_x, verbose=0).reshape(-1)
    metrics = evaluate_binary(test_y, test_probs, selected_threshold)

    model.save(MODELS_DIR / "best_model.keras")
    blob = convert_tflite(model, train_x, MODELS_DIR / "fall_detection_model.tflite")
    export_header(blob, MODELS_DIR / "fall_detection_model.h")
    tflite_info = hr.core.tflite_details(blob)

    plot_training(history_df)
    plot_confusion(metrics["confusion_matrix"])
    roc_auc, pr_auc = plot_roc_pr(test_y, test_probs)
    plot_class_distribution(before_fall, before_non, after_fall, after_non)

    write_text(
        LOGS_DIR / "training_log.txt",
        "\n".join(
            [
                f"before_fall_windows={before_fall}",
                f"before_non_fall_windows={before_non}",
                f"after_fall_windows={after_fall}",
                f"after_non_fall_windows={after_non}",
                f"selected_threshold={selected_threshold:.2f}",
            ]
        ),
    )
    write_text(
        LOGS_DIR / "config.json",
        json.dumps(
            {
                "epochs": 60,
                "batch_size": 32,
                "window_size": 100,
                "stride": 50,
                "selected_threshold": selected_threshold,
            },
            indent=2,
        ),
    )

    metrics_summary = "\n".join(
        [
            "Balanced HR_IMU V2 Summary",
            "",
            f"Fall windows before balancing: {before_fall}",
            f"Non-fall windows before balancing: {before_non}",
            f"Fall windows after balancing: {after_fall}",
            f"Non-fall windows after balancing: {after_non}",
            f"Final ratio fall:non-fall = {after_fall}:{after_non}",
            f"Total windows used for training pipeline: {total}",
            "",
            f"Train fall/non-fall: {int(np.sum(train_y == 1))}/{int(np.sum(train_y == 0))}",
            f"Validation fall/non-fall: {int(np.sum(val_y == 1))}/{int(np.sum(val_y == 0))}",
            f"Test fall/non-fall: {int(np.sum(test_y == 1))}/{int(np.sum(test_y == 0))}",
            "",
            f"Accuracy: {metrics['accuracy']:.4f}",
            f"Precision: {metrics['precision']:.4f}",
            f"Recall: {metrics['recall']:.4f}",
            f"F1-score: {metrics['f1']:.4f}",
            f"False alarm rate: {metrics['false_alarm_rate']:.4f}",
            f"Miss rate: {metrics['miss_rate']:.4f}",
            f"Confusion matrix: {metrics['confusion_matrix']}",
            f"ROC AUC: {roc_auc:.4f}",
            f"PR AUC: {pr_auc:.4f}",
            f"TFLite size KB: {len(blob)/1024.0:.2f}",
            f"TFLite input shape: {tflite_info['input_shape']}",
            f"TFLite output shape: {tflite_info['output_shape']}",
        ]
    )
    write_text(RESULTS_DIR / "metrics_summary.txt", metrics_summary)

    readme = f"""# Result Balanced V2

This run uses only HR_IMU data and balances the dataset after windowing by undersampling the larger class.

Key counts:
- fall windows before balancing: {before_fall}
- non-fall windows before balancing: {before_non}
- fall windows after balancing: {after_fall}
- non-fall windows after balancing: {after_non}
- total balanced windows: {total}

Training used 60 epochs with early stopping enabled and a lightweight TinyCNN for ESP32-S3.
"""
    write_text(ROOT / "README.md", readme)

    experiment_report = f"""# Experiment Report

## Dataset

Only HR_IMU data was used.

Before balancing:
- fall windows: {before_fall}
- non-fall windows: {before_non}

After balancing:
- fall windows: {after_fall}
- non-fall windows: {after_non}
- ratio: 1:1

## Training

- epochs: 60
- batch size: 32
- optimizer: Adam
- loss: binary_crossentropy

## Final Metrics

- accuracy: {metrics['accuracy']:.4f}
- precision: {metrics['precision']:.4f}
- recall: {metrics['recall']:.4f}
- F1-score: {metrics['f1']:.4f}
- false alarm rate: {metrics['false_alarm_rate']:.4f}
- miss rate: {metrics['miss_rate']:.4f}
"""
    write_text(DOCS_DIR / "experiment_report.md", experiment_report)

    deployment_notes = f"""# ESP32 Deployment Notes

Files:
- `models/fall_detection_model.tflite`
- `models/fall_detection_model.h`

Input:
- shape: 100 x 6
- channels: ax, ay, az, gx, gy, gz
- sample rate: 50 Hz

Inference threshold:
- selected probability threshold: {selected_threshold:.2f}
"""
    write_text(DOCS_DIR / "esp32_deployment_notes.md", deployment_notes)

    save_code_files()

    print(f"Original fall windows: {before_fall}")
    print(f"Original non-fall windows: {before_non}")
    print(f"Balanced fall windows: {after_fall}")
    print(f"Balanced non-fall windows: {after_non}")
    print(f"Total windows used: {total}")


if __name__ == "__main__":
    main()
