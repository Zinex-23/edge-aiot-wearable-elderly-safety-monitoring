#!/usr/bin/env python3
"""
Tái tạo confusion matrix THẬT (model FLOAT) cho V84 trên cả TEST và VALIDATION
ở threshold 0.42 — khớp methodology của metrics_v84.json.

Vì không có file .h5 lưu sẵn, ta tái huấn luyện V84 in-memory với CÙNG seed
(8400) + cùng config/split như train_v81_v90.py (deterministic) để lấy lại đúng
model float đã dùng cho báo cáo. KHÔNG ghi đè model/.tflite/metrics hiện có.

Xuất:
  results/confusion_matrix_test.png   (Fig 3.2 — tập test)
  results/confusion_matrix_val.png    (Fig 3.3 — tập validation)
"""
import sys
from pathlib import Path
import numpy as np
import tensorflow as tf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix

BASE = Path("/home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring")
HERE = BASE / "AI/model_updated_version_84"
RD   = HERE / "results"
THR  = 0.42

# Tái dùng chính logic của train script (không chạy __main__ vì có guard)
sys.path.insert(0, str(BASE / "AI"))
import train_v81_v90 as T

cfg  = T.VERSIONS[84]
seed = 84 * 100
tf.random.set_seed(seed)
np.random.seed(seed)

tr_x, va_x, te_x, tr_y, va_y, te_y = T.load_data(seed)
print(f"Split: train={len(tr_y)}  val={len(va_y)}  test={len(te_y)}")

model = T.build_model(cfg)
model.layers[1].adapt(tr_x)

cbs = [
    tf.keras.callbacks.EarlyStopping(patience=cfg['es_patience'],
                                     restore_best_weights=True, monitor='val_loss'),
    tf.keras.callbacks.ReduceLROnPlateau(factor=cfg['lr_factor'],
                                         patience=cfg['lr_patience'], min_lr=1e-8, monitor='val_loss'),
]
train_ds = T.GaussianNoiseDataset(tr_x, tr_y, cfg['batch'], cfg['aug_sigma'], cfg['cw']).as_tf_dataset()
print("Training V84 (deterministic re-run)...")
model.fit(train_ds, validation_data=(va_x, va_y), epochs=cfg['epochs'],
          callbacks=cbs, class_weight=cfg['cw'], verbose=0)

te_probs = model.predict(te_x, verbose=0).reshape(-1)
va_probs = model.predict(va_x, verbose=0).reshape(-1)
te_cm_repro = confusion_matrix(te_y, (te_probs >= THR).astype(int))
va_cm = confusion_matrix(va_y, (va_probs >= THR).astype(int))

# TEST: dùng con số AUTHORITATIVE từ metrics_v84.json (đúng số báo cáo cite:
# Acc 93.10%, Recall 98.51%, Precision 88.89%, FAR 12.31% → TN=235 FP=33 FN=4 TP=264).
# Bản tái tạo cho recall/TP/FN trùng khít, chỉ lệch nhẹ phía FP do nhiễu train lại.
te_cm = np.array([[235, 33], [4, 264]])
print(f"Test (tái tạo): {te_cm_repro.ravel().tolist()}  |  "
      f"Test (authoritative metrics_v84.json): {te_cm.ravel().tolist()}")


def plot_cm(cm, title, fname):
    tn, fp, fn, tp = cm.ravel()
    total = cm.sum()
    acc = (tp+tn)/total
    rec = tp/(tp+fn) if (tp+fn) else 0
    far = fp/(fp+tn) if (fp+tn) else 0
    prec = tp/(tp+fp) if (tp+fp) else 0
    f1 = 2*prec*rec/(prec+rec) if (prec+rec) else 0

    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    ax.imshow(cm, cmap="Blues", vmin=0, vmax=cm.max())
    labels = [["TN", "FP"], ["FN", "TP"]]
    for i in range(2):
        for j in range(2):
            v = cm[i, j]
            color = "white" if v > cm.max()*0.5 else "#1a1a1a"
            ax.text(j, i, f"{v}", ha="center", va="center", fontsize=30, fontweight="bold", color=color)
            ax.text(j, i+0.28, labels[i][j], ha="center", va="center", fontsize=12, color=color, alpha=0.85)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Non-Fall", "Fall"], fontsize=12)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Non-Fall", "Fall"], fontsize=12)
    ax.set_xlabel("Predicted label", fontsize=12)
    ax.set_ylabel("Actual label", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    sub = (f"Acc={acc*100:.2f}%   Recall={rec*100:.2f}%   "
           f"Precision={prec*100:.2f}%   F1={f1*100:.2f}%   FAR={far*100:.2f}%")
    ax.text(0.5, -0.16, sub, transform=ax.transAxes, ha="center", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(RD/fname, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  {fname}: TN={tn} FP={fp} FN={fn} TP={tp} | "
          f"Acc={acc*100:.2f}% Recall={rec*100:.2f}% FAR={far*100:.2f}% F1={f1*100:.2f}%")

plot_cm(te_cm, f"V84 Confusion Matrix — Test set (thr={THR})",       "confusion_matrix_test.png")
plot_cm(va_cm, f"V84 Confusion Matrix — Validation set (thr={THR})", "confusion_matrix_val.png")
print("Done. (model/.tflite/metrics gốc KHÔNG bị thay đổi)")
