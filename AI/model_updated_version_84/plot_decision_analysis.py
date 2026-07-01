#!/usr/bin/env python3
"""
Vẽ lại biểu đồ Decision Analysis (Threshold Tuning) cho model V84.
Thêm đường F1-score, marker điểm mốc, lưới và đường ngưỡng chọn — theo style
ảnh tham khảo AI/Edge_AI/result_balanced_v2/results/decision_analysis.png.

Nguồn dữ liệu: results/threshold_metrics.csv  (cột: threshold, recall, far, f1)
Xuất:          results/decision_analysis.png  (ghi đè)
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CSV  = HERE / "results" / "threshold_metrics.csv"
OUT  = HERE / "results" / "decision_analysis.png"
SELECTED_THR = 0.42   # best_threshold của V84 (metrics_v84.json)

df = pd.read_csv(CSV).sort_values("threshold").reset_index(drop=True)
thr, recall, far, f1 = df["threshold"], df["recall"], df["far"], df["f1"]

# Marker thưa cho gọn (mỗi 0.05 ≈ mỗi 5 điểm vì CSV bước 0.01)
step = max(1, int(round(0.05 / (thr.iloc[1] - thr.iloc[0]))))

# Màu/marker đồng bộ với ảnh tham khảo
C_F1, C_RECALL, C_FAR = "#1f77b4", "#2ca02c", "#d62728"

fig, axL = plt.subplots(figsize=(11, 6.5))
axR = axL.twinx()  # trục phải cho False Alarm Rate

# ── Trục trái: F1 + Recall ───────────────────────────────────────────
lnF1, = axL.plot(thr, f1, color=C_F1, lw=2, marker="o", markevery=step,
                 markersize=6, label="F1-score")
lnRe, = axL.plot(thr, recall, color=C_RECALL, lw=2, marker="s", markevery=step,
                 markersize=6, label="Recall")
# ── Trục phải: FAR ───────────────────────────────────────────────────
lnFAR, = axR.plot(thr, far, color=C_FAR, lw=2, marker="^", markevery=step,
                  markersize=6, label="False Alarm Rate")

# ── Đường ngưỡng chọn + điểm mốc tại 0.42 ────────────────────────────
i_sel = (thr - SELECTED_THR).abs().idxmin()
lnThr = axL.axvline(SELECTED_THR, color="black", ls="--", lw=1.6,
                    label=f"Selected threshold = {SELECTED_THR:.2f}")

# highlight + annotate giá trị tại ngưỡng chọn
axL.scatter([SELECTED_THR], [f1[i_sel]],     s=120, facecolors="none",
            edgecolors=C_F1, lw=2, zorder=5)
axL.scatter([SELECTED_THR], [recall[i_sel]], s=120, facecolors="none",
            edgecolors=C_RECALL, lw=2, zorder=5)
axR.scatter([SELECTED_THR], [far[i_sel]],    s=120, facecolors="none",
            edgecolors=C_FAR, lw=2, zorder=5)
axL.annotate(f"F1={f1[i_sel]:.3f}", (SELECTED_THR, f1[i_sel]),
             xytext=(8, -16), textcoords="offset points", color=C_F1, fontsize=9, fontweight="bold")
axL.annotate(f"Recall={recall[i_sel]:.3f}", (SELECTED_THR, recall[i_sel]),
             xytext=(8, 8), textcoords="offset points", color=C_RECALL, fontsize=9, fontweight="bold")
axR.annotate(f"FAR={far[i_sel]:.3f}", (SELECTED_THR, far[i_sel]),
             xytext=(8, 8), textcoords="offset points", color=C_FAR, fontsize=9, fontweight="bold")

# ── Trục, lưới, nhãn ─────────────────────────────────────────────────
axL.set_xlabel("Classification Threshold", fontsize=12)
axL.set_ylabel("Score (F1 / Recall)", fontsize=12)
axR.set_ylabel("False Alarm Rate", fontsize=12, color=C_FAR)
axR.tick_params(axis="y", labelcolor=C_FAR)
axL.set_ylim(0.0, 1.05)
axR.set_ylim(0.0, 0.25)
axL.set_xlim(thr.min(), thr.max())
axL.grid(True, ls="--", alpha=0.4)
axL.set_title("V84 Decision Analysis (Threshold Tuning)", fontsize=14, fontweight="bold")

# Legend gộp 2 trục
handles = [lnF1, lnRe, lnFAR, lnThr]
axL.legend(handles, [h.get_label() for h in handles], loc="lower left",
           framealpha=0.95, fontsize=10)

fig.tight_layout()
fig.savefig(OUT, dpi=150)
print(f"Saved: {OUT}")
print(f"Tại threshold={SELECTED_THR}: F1={f1[i_sel]:.4f}  Recall={recall[i_sel]:.4f}  FAR={far[i_sel]:.4f}")
