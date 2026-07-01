"""
Train fall detection models V51-V60.
Output per version mirrors V50 structure:
  model_updated_version_XX/
    models/  fall_detection_vXX.tflite
             fall_detection_vXX.h         (variable: fall_detection_model_tflite)
    results/ metrics_vXX.md, metrics_summary.txt, threshold_metrics.csv
             confusion_matrix.png, dashboard.png, decision_analysis.png
             roc_curve.png, training_curves.png, error_analysis.png
    docs/    experiment_report.md
    README.md

Architecture strategy vs V50 baseline [32,48,64,96]/K5/D20/LR=3e-4/cw=1.2:
  V51: cw=1.0  + score=rec*1.0-far*3.0   -> minimize FAR
  V52: cw=1.5  + score=rec*2.5-far*1.5   -> maximize Recall
  V53: [32,48,64,96] / K7 / D20          -> wider temporal context
  V54: [32,48,64,96] / K5 / D32          -> deeper dense layer
  V55: [48,64,80,96] / K5 / D20          -> more conv filters
  V56: [32,48,64,96] / K5 / D20 / drop=0.5 -> more dropout
  V57: [32,48,64,96] / K5 / D20 / L2=5e-4  -> stronger regularization
  V58: [32,48,64,96] / K5 / D20 / LR=1e-4  -> finer LR
  V59: [32,48,64,96] / K5 / D20 / batch=32  -> smaller batch
  V60: K3/K5/K5/K3 mixed kernels / D20      -> mixed temporal receptive field
"""

import json
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, precision_recall_curve, auc
)

BASE_DIR  = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
DATA_DIR  = BASE_DIR / "AI/Edge_AI/result_balanced_v2/dataset/rebuilt"
AI_DIR    = BASE_DIR / "AI"

# ─────────────────────────────────────────────────────────────────────────────
# VERSION CONFIGS
# ─────────────────────────────────────────────────────────────────────────────
VERSIONS = {
    51: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.0},
        thr_score=lambda rec, far: rec * 1.0 - far * 3.0,
        note="V50 base, cw=1:1, FAR-penalized scoring",
    ),
    52: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.5},
        thr_score=lambda rec, far: rec * 2.5 - far * 1.5,
        note="V50 base, cw=1:1.5, Recall-maximizing scoring",
    ),
    53: dict(
        filters=[32, 48, 64, 96], kernels=[7, 7, 7, 7], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="K7 kernels — larger temporal receptive field",
    ),
    54: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=32,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="V50 base + Dense=32 (more classification capacity)",
    ),
    55: dict(
        filters=[48, 64, 80, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="Wider filters [48,64,80,96] — more feature capacity",
    ),
    56: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.5, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="V50 base + Dropout=0.5 (more regularization)",
    ),
    57: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.4, l2=5e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="V50 base + L2=5e-4 (stronger weight decay)",
    ),
    58: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=1e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="V50 base + LR=1e-4 (finer convergence)",
    ),
    59: dict(
        filters=[32, 48, 64, 96], kernels=[5, 5, 5, 5], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=32, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="V50 base + BatchSize=32 (better generalization)",
    ),
    60: dict(
        filters=[32, 48, 64, 96], kernels=[3, 5, 5, 3], dense=20,
        lr=3e-4, dropout=0.4, l2=1e-4, batch=64, epochs=200,
        class_weight={0: 1.0, 1: 1.2},
        thr_score=lambda rec, far: rec * 1.5 - far * 2.0,
        note="Mixed kernels K3/K5/K5/K3 — multi-scale temporal context",
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────
def build_windows(df, label, window_size=100, stride=50):
    cols = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']
    data = df[cols].values
    windows, labels = [], []
    for i in range(0, len(data) - window_size + 1, stride):
        windows.append(data[i:i + window_size])
        labels.append(label)
    return np.array(windows), np.array(labels)

def load_data(seed):
    fall_df     = pd.read_csv(DATA_DIR / "fall.csv")
    non_fall_df = pd.read_csv(DATA_DIR / "non_fall.csv")
    fall_x, fall_y = build_windows(fall_df, 1)
    non_x,  non_y  = build_windows(non_fall_df, 0)

    np.random.seed(seed)
    n = min(len(fall_y), len(non_y))
    fi = np.random.choice(len(fall_y), size=n, replace=False)
    ni = np.random.choice(len(non_y),  size=n, replace=False)

    X = np.concatenate([fall_x[fi], non_x[ni]])
    y = np.concatenate([fall_y[fi], non_y[ni]])

    tr_x, tmp_x, tr_y, tmp_y = train_test_split(X, y, test_size=0.30, stratify=y, random_state=seed)
    va_x, te_x, va_y, te_y   = train_test_split(tmp_x, tmp_y, test_size=0.50, stratify=tmp_y, random_state=seed)
    return tr_x, va_x, te_x, tr_y, va_y, te_y

# ─────────────────────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────────────────────
def build_model(cfg):
    reg = tf.keras.regularizers.l2(cfg['l2'])
    inp = tf.keras.Input(shape=(100, 6))
    x   = tf.keras.layers.Normalization(axis=-1)(inp)

    for i, (f, k) in enumerate(zip(cfg['filters'], cfg['kernels'])):
        x = tf.keras.layers.Conv1D(f, k, padding='same', kernel_regularizer=reg)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        # MaxPool for all except last conv block
        if i < len(cfg['filters']) - 1:
            x = tf.keras.layers.MaxPooling1D(2)(x)

    x   = tf.keras.layers.GlobalAveragePooling1D()(x)
    x   = tf.keras.layers.Dropout(cfg['dropout'])(x)
    x   = tf.keras.layers.Dense(cfg['dense'], activation='relu', kernel_regularizer=reg)(x)
    out = tf.keras.layers.Dense(1, activation='sigmoid')(x)

    m = tf.keras.Model(inp, out)
    m.compile(
        optimizer=tf.keras.optimizers.Adam(cfg['lr']),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    return m

# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def export_tflite(model, train_x, models_dir, version):
    def rep_data():
        for _ in range(200):
            yield [train_x[np.random.randint(len(train_x))][np.newaxis].astype(np.float32)]

    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = rep_data
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type  = tf.int8
    conv.inference_output_type = tf.int8
    tflite = conv.convert()

    tflite_path = models_dir / f"fall_detection_v{version}.tflite"
    tflite_path.write_bytes(tflite)

    # Header — variable name = fall_detection_model_tflite (compatible with main.cpp)
    tokens = [f"0x{b:02x}" for b in tflite]
    lines  = [", ".join(tokens[i:i+12]) for i in range(0, len(tokens), 12)]
    header = (
        f"#ifndef FALL_DETECTION_V{version}_H\n"
        f"#define FALL_DETECTION_V{version}_H\n\n"
        f"// Model V{version} — variable name compatible with S3_BLE/src/main.cpp\n"
        f"const unsigned char fall_detection_model_tflite[] = {{\n  "
        + ",\n  ".join(lines)
        + f"\n}};\nconst unsigned int fall_detection_model_tflite_len = {len(tflite)};\n\n"
        f"#endif // FALL_DETECTION_V{version}_H\n"
    )
    (models_dir / f"fall_detection_v{version}.h").write_text(header)
    return len(tflite) / 1024  # KB

# ─────────────────────────────────────────────────────────────────────────────
# PLOTS
# ─────────────────────────────────────────────────────────────────────────────
def make_plots(version, history, cm, test_probs, test_x, test_y,
               df_thr, best_thr, results_dir):
    # Training curves
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(history.history['loss'],     label='Train')
    axes[0].plot(history.history['val_loss'], label='Val')
    axes[0].set_title(f'V{version} Loss'); axes[0].legend()
    axes[1].plot(history.history['accuracy'],     label='Train')
    axes[1].plot(history.history['val_accuracy'], label='Val')
    axes[1].set_title(f'V{version} Accuracy'); axes[1].legend()
    plt.tight_layout()
    plt.savefig(results_dir / "training_curves.png", dpi=150); plt.close()

    # Confusion matrix
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap='Blues')
    plt.title(f'V{version} Confusion Matrix (thr={best_thr:.2f})')
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha='center', va='center', fontsize=14, color='black')
    plt.xticks([0, 1], ['Non-Fall', 'Fall']); plt.yticks([0, 1], ['Non-Fall', 'Fall'])
    plt.savefig(results_dir / "confusion_matrix.png", dpi=150); plt.close()

    # Decision analysis
    plt.figure(figsize=(10, 5))
    plt.plot(df_thr['threshold'], df_thr['recall'], label='Recall')
    plt.plot(df_thr['threshold'], df_thr['far'],    label='FAR')
    plt.axvline(best_thr, color='r', ls='--', label=f'Best thr={best_thr:.2f}')
    plt.title(f'V{version} Decision Analysis'); plt.legend()
    plt.savefig(results_dir / "decision_analysis.png", dpi=150); plt.close()

    # ROC
    fpr, tpr, _ = roc_curve(test_y, test_probs)
    rauc = auc(fpr, tpr)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f'AUC={rauc:.3f}'); plt.plot([0,1],[0,1],'k--')
    plt.title(f'V{version} ROC Curve'); plt.legend()
    plt.savefig(results_dir / "roc_curve.png", dpi=150); plt.close()

    # Error analysis
    test_preds = (test_probs >= best_thr).astype(int)
    fn_idx = np.where((test_preds == 0) & (test_y == 1))[0]
    fp_idx = np.where((test_preds == 1) & (test_y == 0))[0]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    if len(fn_idx): axes[0].plot(test_x[fn_idx[0]]); axes[0].set_title('False Negative sample')
    if len(fp_idx): axes[1].plot(test_x[fp_idx[0]]); axes[1].set_title('False Positive sample')
    plt.tight_layout()
    plt.savefig(results_dir / "error_analysis.png", dpi=150); plt.close()

    # Dashboard
    fig = plt.figure(figsize=(15, 10))
    fig.suptitle(f'V{version} Training Dashboard', fontsize=18)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.plot(history.history['loss'], label='Train'); ax1.plot(history.history['val_loss'], label='Val')
    ax1.set_title('Loss History'); ax1.legend()
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.imshow(cm, cmap='Blues'); ax2.set_title('Confusion Matrix')
    for i in range(2):
        for j in range(2):
            ax2.text(j, i, str(cm[i, j]), ha='center', va='center', color='black')
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.plot(df_thr['threshold'], df_thr['recall'], label='Recall')
    ax3.plot(df_thr['threshold'], df_thr['far'],    label='FAR')
    ax3.axvline(best_thr, color='r', ls='--'); ax3.set_title('Threshold Analysis'); ax3.legend()
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.bar(['Fall', 'Non-Fall'], [int(np.sum(test_y == 1)), int(np.sum(test_y == 0))],
            color=['tomato', 'steelblue'])
    ax4.set_title('Test Set Distribution')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(results_dir / "dashboard.png", dpi=200); plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXPERIMENT
# ─────────────────────────────────────────────────────────────────────────────
def run_version(version, cfg):
    print(f"\n{'='*24} V{version} {'='*24}")
    print(f"  Note: {cfg['note']}")

    out_dir     = AI_DIR / f"model_updated_version_{version}"
    models_dir  = out_dir / "models"
    results_dir = out_dir / "results"
    docs_dir    = out_dir / "docs"
    for d in [models_dir, results_dir, docs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    seed = version * 100
    tf.random.set_seed(seed)
    tr_x, va_x, te_x, tr_y, va_y, te_y = load_data(seed)

    model = build_model(cfg)
    model.layers[1].adapt(tr_x)
    model.summary(print_fn=lambda s: None)  # suppress to keep log clean

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=25, restore_best_weights=True, monitor='val_loss'),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.2, patience=10, min_lr=1e-7),
    ]

    history = model.fit(
        tr_x, tr_y,
        validation_data=(va_x, va_y),
        epochs=cfg['epochs'],
        batch_size=cfg['batch'],
        callbacks=callbacks,
        class_weight=cfg['class_weight'],
        verbose=0,
    )

    # Threshold tuning on validation set
    va_probs = model.predict(va_x, verbose=0).reshape(-1)
    best_thr, best_score = 0.5, -1
    thr_rows = []
    for thr in np.arange(0.05, 0.95, 0.01):
        preds  = (va_probs >= thr).astype(int)
        rec    = recall_score(va_y, preds, zero_division=0)
        f1     = f1_score(va_y, preds, zero_division=0)
        cm_v   = confusion_matrix(va_y, preds)
        tn_v, fp_v, _, _ = cm_v.ravel()
        far    = fp_v / (fp_v + tn_v) if (fp_v + tn_v) > 0 else 0
        score  = cfg['thr_score'](rec, far)
        thr_rows.append({"threshold": round(float(thr), 2), "recall": rec, "far": far, "f1": f1})
        if score > best_score:
            best_score, best_thr = score, float(thr)

    df_thr = pd.DataFrame(thr_rows)
    df_thr.to_csv(results_dir / "threshold_metrics.csv", index=False)

    # Test evaluation
    te_probs = model.predict(te_x, verbose=0).reshape(-1)
    te_preds = (te_probs >= best_thr).astype(int)
    cm       = confusion_matrix(te_y, te_preds)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "version":          version,
        "accuracy":         float(accuracy_score(te_y, te_preds)),
        "precision":        float(precision_score(te_y, te_preds, zero_division=0)),
        "recall":           float(recall_score(te_y, te_preds, zero_division=0)),
        "f1":               float(f1_score(te_y, te_preds, zero_division=0)),
        "false_alarm_rate": float(fp / (fp + tn)) if (fp + tn) > 0 else 0,
        "miss_rate":        float(fn / (fn + tp)) if (fn + tp) > 0 else 0,
        "best_threshold":   best_thr,
        "config":           {k: str(v) for k, v in cfg.items() if k != 'thr_score'},
    }
    (results_dir / f"metrics_v{version}.json").write_text(json.dumps(metrics, indent=2))

    # metrics_vXX.md
    md = (
        f"# Model V{version}: {cfg['note']}\n\n"
        f"| Metric | Value |\n| :--- | :--- |\n"
        f"| Accuracy | **{metrics['accuracy']*100:.2f}%** |\n"
        f"| Recall (Sensitivity) | **{metrics['recall']*100:.2f}%** |\n"
        f"| Precision | **{metrics['precision']*100:.2f}%** |\n"
        f"| F1-score | **{metrics['f1']*100:.2f}%** |\n"
        f"| False Alarm Rate | **{metrics['false_alarm_rate']*100:.2f}%** |\n"
        f"| Miss Rate | **{metrics['miss_rate']*100:.2f}%** |\n"
    )
    (results_dir / f"metrics_v{version}.md").write_text(md)

    # metrics_summary.txt
    summary = (
        f"Accuracy:  {metrics['accuracy']:.4f}\n"
        f"Recall:    {metrics['recall']:.4f}\n"
        f"Precision: {metrics['precision']:.4f}\n"
        f"F1:        {metrics['f1']:.4f}\n"
        f"FAR:       {metrics['false_alarm_rate']:.4f}\n"
        f"MissRate:  {metrics['miss_rate']:.4f}\n"
        f"Threshold: {best_thr:.2f}\n"
    )
    (results_dir / "metrics_summary.txt").write_text(summary)

    # Plots
    make_plots(version, history, cm, te_probs, te_x, te_y, df_thr, best_thr, results_dir)

    # TFLite export
    size_kb = export_tflite(model, tr_x, models_dir, version)
    metrics['size_kb'] = size_kb

    # experiment_report.md
    report = (
        f"# Experiment Report — Model V{version}\n\n"
        f"## Config\n"
        f"- Architecture: {len(cfg['filters'])}×Conv1D {cfg['filters']}, Kernels={cfg['kernels']}, Dense={cfg['dense']}\n"
        f"- LR: {cfg['lr']} | Dropout: {cfg['dropout']} | L2: {cfg['l2']} | Batch: {cfg['batch']}\n"
        f"- Class weight: {cfg['class_weight']}\n"
        f"- Note: {cfg['note']}\n\n"
        f"## Results\n"
        f"- Accuracy: {metrics['accuracy']:.4f}\n"
        f"- Recall:   {metrics['recall']:.4f}\n"
        f"- F1:       {metrics['f1']:.4f}\n"
        f"- FAR:      {metrics['false_alarm_rate']:.4f}\n"
        f"- Size:     {size_kb:.2f} KB\n"
        f"- Threshold: {best_thr:.2f}\n"
    )
    (docs_dir / "experiment_report.md").write_text(report)

    # README.md
    readme = (
        f"# Model V{version}\n\n"
        f"**{cfg['note']}**\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| F1 | {metrics['f1']*100:.2f}% |\n"
        f"| Recall | {metrics['recall']*100:.2f}% |\n"
        f"| FAR | {metrics['false_alarm_rate']*100:.2f}% |\n"
        f"| Size | {size_kb:.2f} KB |\n\n"
        f"## Files\n"
        f"- `models/fall_detection_v{version}.tflite` — INT8 quantized\n"
        f"- `models/fall_detection_v{version}.h` — C header (variable: `fall_detection_model_tflite`)\n"
        f"- `results/metrics_v{version}.md` — detailed metrics\n"
        f"- `results/dashboard.png` — training dashboard\n"
        f"- `docs/experiment_report.md` — full report\n\n"
        f"## Deploy to ESP32-S3\n"
        f"In `S3_BLE/platformio.ini`:\n"
        f"```\nbuild_flags = -I ../AI/model_updated_version_{version}/models\n```\n"
        f"In `S3_BLE/src/main.cpp`:\n"
        f"```cpp\n#include \"fall_detection_v{version}.h\"\n```\n"
    )
    (out_dir / "README.md").write_text(readme)

    print(f"  V{version} done: Acc={metrics['accuracy']:.4f} Rec={metrics['recall']:.4f} "
          f"F1={metrics['f1']:.4f} FAR={metrics['false_alarm_rate']:.4f} Size={size_kb:.2f}KB")
    return metrics


def update_experiments_summary(all_results):
    """Append V51-V60 results to experiments_summary.md"""
    summary_path = AI_DIR / "experiments_summary.md"
    existing = summary_path.read_text() if summary_path.exists() else ""

    new_rows = "\n## V51-V60 Results\n\n"
    new_rows += "| Version | Note | Accuracy | Recall | F1 | FAR | Size |\n"
    new_rows += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for m in all_results:
        v   = m['version']
        cfg = VERSIONS[v]
        new_rows += (
            f"| **V{v}** | {cfg['note'][:40]} "
            f"| {m['accuracy']*100:.2f}% | {m['recall']*100:.2f}% "
            f"| {m['f1']*100:.2f}% | {m['false_alarm_rate']*100:.2f}% "
            f"| {m['size_kb']:.2f} KB |\n"
        )

    if "## V51-V60 Results" in existing:
        # Replace section
        idx = existing.index("## V51-V60 Results")
        updated = existing[:idx] + new_rows
    else:
        updated = existing + "\n" + new_rows

    summary_path.write_text(updated)
    print(f"\nUpdated {summary_path}")


if __name__ == "__main__":
    all_results = []
    for v in sorted(VERSIONS.keys()):
        try:
            m = run_version(v, VERSIONS[v])
            all_results.append(m)
        except Exception as e:
            print(f"  ERROR V{v}: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "="*60)
    print("SUMMARY V51-V60")
    print("="*60)
    print(f"{'V':<6} {'Acc':>7} {'Recall':>8} {'F1':>8} {'FAR':>8} {'Size':>8}")
    for m in all_results:
        print(f"V{m['version']:<5} {m['accuracy']*100:>6.2f}% {m['recall']*100:>7.2f}% "
              f"{m['f1']*100:>7.2f}% {m['false_alarm_rate']*100:>7.2f}% {m['size_kb']:>7.2f}KB")

    update_experiments_summary(all_results)
    print("\nAll done. Review results in each model_updated_version_XX/results/ folder.")
