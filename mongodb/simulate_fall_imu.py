"""
simulate_fall_imu.py
--------------------
Mô phỏng dữ liệu IMU (accelerometer + gyroscope) của ESP32-S3 khi xảy ra sự kiện ngã.

Thông số firmware (S3_AIFD_V1/src/main.cpp):
  - Sampling rate : 50 Hz  (SAMPLE_PERIOD_MS = 20)
  - Window size   : 100 samples = 2 s
  - ACC range     : ±8 g   (REG_ACC_RANGE = 0x03)
  - GYR range     : ±2000 dps (REG_GYR_RANGE = 0x00)
  - CANDIDATE_ACC_THRESHOLD  = 7.5 g
  - CANDIDATE_GYRO_THRESHOLD = 240 dps

Các giai đoạn mô phỏng (trên cửa sổ 2 s):
  Phase 1 — Pre-fall  (0.0 – 0.75 s)  : đứng/đi bộ nhẹ, az ≈ 1g
  Phase 2 — Tilting   (0.75 – 0.90 s) : bắt đầu nghiêng, gyro tăng dần
  Phase 3 — Free-fall (0.90 – 0.95 s) : rơi tự do, acc giảm mạnh
  Phase 4 — Impact    (0.95 – 1.05 s) : va chạm, đỉnh acc > 8g, gyro > 400 dps
  Phase 5 — Oscillation (1.05 – 1.4 s): dao động tắt dần sau va chạm
  Phase 6 — Still     (1.4 – 2.0 s)   : nằm yên, az ≈ 1g (hoặc vị trí nằm)

Chạy: python simulate_fall_imu.py
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
import matplotlib.patches as mpatches

# ─── Constants ────────────────────────────────────────────────────────────────
SAMPLE_RATE   = 50        # Hz
DURATION_S    = 2.0       # giây
N_SAMPLES     = int(SAMPLE_RATE * DURATION_S)  # = 100
dt            = 1.0 / SAMPLE_RATE               # = 0.02 s
t             = np.linspace(0, DURATION_S - dt, N_SAMPLES)  # t[0]=0.00, t[99]=1.98

# Firmware thresholds (để vẽ đường tham chiếu)
CANDIDATE_ACC_THRESHOLD  = 7.5   # g
CANDIDATE_GYRO_THRESHOLD = 240.0 # dps

# ─── Mô phỏng profile ngã ─────────────────────────────────────────────────────
rng = np.random.default_rng(seed=42)

def _gauss_noise(n, std=0.04):
    return rng.normal(0, std, n)

def _make_envelope(t, center, width, shape="gauss"):
    """Tạo envelope hình chuông tại 'center' với 'width'."""
    if shape == "gauss":
        return np.exp(-0.5 * ((t - center) / width) ** 2)
    elif shape == "exp_decay":
        mask = t >= center
        out = np.zeros_like(t)
        out[mask] = np.exp(-(t[mask] - center) / width)
        return out
    return np.zeros_like(t)


# ── Accelerometer ─────────────────────────────────────────────────────────────
#
# Phase 1 – Pre-fall (0–0.75s): Ax≈0, Ay≈0, Az≈1g (trọng lực)
# Phase 2 – Tilting  (0.75–0.90s): Az giảm dần, Ay bắt đầu tăng
# Phase 3 – Free-fall (0.90–0.95s): |acc| giảm về ~0 (weightlessness)
# Phase 4 – Impact   (0.95–1.05s): đỉnh to, multi-direction
# Phase 5 – Oscillation (1.05–1.4s): dao động tắt dần
# Phase 6 – Still   (1.4–2.0s): Az ≈ 1g (nằm, trọng lực chiếu vào trục khác)

ax_sim = np.zeros(N_SAMPLES)
ay_sim = np.zeros(N_SAMPLES)
az_sim = np.ones(N_SAMPLES) * 1.0  # baseline: trọng lực trên Z

# Tilting onset: Az giảm dần khi cơ thể nghiêng (0.75–0.90s)
tilt_start, tilt_end = 0.75, 0.90
mask_tilt = (t >= tilt_start) & (t < tilt_end)
tilt_phase = (t[mask_tilt] - tilt_start) / (tilt_end - tilt_start)  # 0→1
az_sim[mask_tilt] -= tilt_phase * 0.6    # Az giảm từ 1g → 0.4g
ay_sim[mask_tilt] += tilt_phase * 0.5    # Ay tăng nhẹ (nghiêng người)

# Free-fall: acc → ~0 (0.90–0.95s)
mask_ff = (t >= 0.90) & (t < 0.95)
ff_phase = (t[mask_ff] - 0.90) / 0.05
az_sim[mask_ff] = 0.4 * (1 - ff_phase) + 0.0 * ff_phase
ay_sim[mask_ff] = 0.5 * (1 - ff_phase)

# Impact (0.95–1.05s): đỉnh mạnh
# Z-axis: peak dương lớn nhất (bề mặt tiếp xúc)
# X-axis: peak âm mạnh (hất ngã sang bên)
# Y-axis: peak dương trung bình
impact_center = 0.975
az_sim += 11.5  * _make_envelope(t, impact_center, 0.022)   # peak ~+12g
ax_sim += -10.5 * _make_envelope(t, impact_center, 0.028)   # peak ~-11g
ay_sim +=  8.5  * _make_envelope(t, impact_center + 0.02, 0.025)  # peak ~+9g (lệch pha nhẹ)

# Oscillation sau impact (1.05–1.4s): damped sinusoidal
osc_decay = _make_envelope(t, 1.05, 0.14, shape="exp_decay")
freq_osc  = 8.0  # Hz dao động thân người sau va chạm
ax_sim += 5.0 * osc_decay * np.sin(2 * np.pi * freq_osc * (t - 1.05))
ay_sim += 4.0 * osc_decay * np.cos(2 * np.pi * freq_osc * (t - 1.05))
az_sim += 2.5 * osc_decay * np.sin(2 * np.pi * (freq_osc * 0.8) * (t - 1.05) + 0.5)

# Settling (1.4–2.0s): nằm im, trọng lực chiếu vào Az ≈ 1g
mask_still = t >= 1.4
settle_phase = np.clip((t[mask_still] - 1.4) / 0.2, 0, 1)
ax_sim[mask_still] *= (1 - settle_phase) * 0.3
ay_sim[mask_still] *= (1 - settle_phase) * 0.3
az_sim[mask_still] = az_sim[mask_still] * (1 - settle_phase) + 1.0 * settle_phase

# Thêm noise thực tế
ax_sim += _gauss_noise(N_SAMPLES, 0.06)
ay_sim += _gauss_noise(N_SAMPLES, 0.06)
az_sim += _gauss_noise(N_SAMPLES, 0.06)

# Clamp trong ±16g (BMI160 có thể bão hòa ở ±8g nhưng mô phỏng để thấy đỉnh rõ)
# Trong thực tế, firmware dùng ±8g range nên giá trị > 8g là bão hòa
ax_sim = np.clip(ax_sim, -14.0, 14.0)
ay_sim = np.clip(ay_sim, -14.0, 14.0)
az_sim = np.clip(az_sim, -14.0, 14.0)


# ── Gyroscope ─────────────────────────────────────────────────────────────────
#
# Phase 1-2: nhỏ, noise
# Phase 2   (Tilting): gyro bắt đầu tăng dần (xoay người)
# Phase 4   (Impact): đỉnh lớn >400 dps, multi-axis
# Phase 5   (Oscillation): dao động tắt dần
# Phase 6   (Still): gần 0

gx_sim = np.zeros(N_SAMPLES)
gy_sim = np.zeros(N_SAMPLES)
gz_sim = np.zeros(N_SAMPLES)

# Tilting: gyro tăng chậm (0.75–0.95s)
mask_pre = (t >= 0.75) & (t < 0.95)
pre_env  = (t[mask_pre] - 0.75) / 0.20
gz_sim[mask_pre] += pre_env * 80    # xoay dần trước khi ngã
gy_sim[mask_pre] += pre_env * 50

# Impact burst (0.95–1.1s)
gx_sim +=  430.0 * _make_envelope(t, 0.97,  0.030)
gy_sim += -480.0 * _make_envelope(t, 0.985, 0.030)
gz_sim +=  520.0 * _make_envelope(t, 0.975, 0.025)

# Oscillation damped (1.05–1.4s)
g_decay = _make_envelope(t, 1.08, 0.12, shape="exp_decay")
gx_sim += 200.0 * g_decay * np.sin(2 * np.pi * 6.0 * (t - 1.08))
gy_sim += 240.0 * g_decay * np.cos(2 * np.pi * 6.0 * (t - 1.08))
gz_sim += 160.0 * g_decay * np.sin(2 * np.pi * 5.5 * (t - 1.08) + 0.8)

# Noise
gx_sim += _gauss_noise(N_SAMPLES, 3.0)
gy_sim += _gauss_noise(N_SAMPLES, 3.0)
gz_sim += _gauss_noise(N_SAMPLES, 3.0)

# Clamp trong ±600 dps (hiển thị rõ)
gx_sim = np.clip(gx_sim, -600, 600)
gy_sim = np.clip(gy_sim, -600, 600)
gz_sim = np.clip(gz_sim, -600, 600)

# ─── Tính SMA (Signal Magnitude Area) — tương tự firmware ────────────────────
acc_mag  = np.sqrt(ax_sim**2 + ay_sim**2 + az_sim**2)
gyro_mag = np.sqrt(gx_sim**2 + gy_sim**2 + gz_sim**2)

# ─── Vẽ biểu đồ ──────────────────────────────────────────────────────────────
plt.style.use("seaborn-v0_8-whitegrid")
fig = plt.figure(figsize=(14, 10), facecolor="#0d1117")
fig.patch.set_facecolor("#0d1117")

gs = gridspec.GridSpec(3, 1, hspace=0.42, figure=fig)
ax_acc  = fig.add_subplot(gs[0])
ax_gyro = fig.add_subplot(gs[1])
ax_mag  = fig.add_subplot(gs[2])

AXIS_BG   = "#161b22"
GRID_CLR  = "#21262d"
TEXT_CLR  = "#e6edf3"
MUTED_CLR = "#8b949e"

def _style_axes(ax, title, ylabel):
    ax.set_facecolor(AXIS_BG)
    ax.set_title(title, color=TEXT_CLR, fontsize=12, fontweight="bold", pad=8)
    ax.set_ylabel(ylabel, color=MUTED_CLR, fontsize=10)
    ax.set_xlabel("Time (s)", color=MUTED_CLR, fontsize=9)
    ax.tick_params(colors=MUTED_CLR, which="both")
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID_CLR)
    ax.grid(True, color=GRID_CLR, linewidth=0.6)
    ax.set_xlim(0, DURATION_S)

# ── Plot 1: Acceleration ───────────────────────────────────────────────────────
_style_axes(ax_acc, "Accelerometer — Fall Event Simulation (50 Hz)", "Acceleration (g)")
ax_acc.plot(t, ax_sim, color="#58a6ff", lw=1.4, label="X-axis")
ax_acc.plot(t, ay_sim, color="#ff7b72", lw=1.4, label="Y-axis")
ax_acc.plot(t, az_sim, color="#3fb950", lw=1.4, label="Z-axis")
ax_acc.axhline( CANDIDATE_ACC_THRESHOLD, color="#d29922", lw=0.9, ls="--", alpha=0.7,
                label=f"Threshold +{CANDIDATE_ACC_THRESHOLD:.1f}g")
ax_acc.axhline(-CANDIDATE_ACC_THRESHOLD, color="#d29922", lw=0.9, ls="--", alpha=0.7)
ax_acc.set_ylim(-15, 15)
ax_acc.legend(loc="upper left", facecolor=AXIS_BG, edgecolor=GRID_CLR,
              labelcolor=TEXT_CLR, fontsize=8.5, ncol=4)

# Annotation: impact
ax_acc.annotate("Impact!", xy=(0.975, 12), xytext=(1.22, 12.5),
                color="#ff7b72", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#ff7b72", lw=1.1))

# ── Plot 2: Gyroscope ─────────────────────────────────────────────────────────
_style_axes(ax_gyro, "Gyroscope — Fall Event Simulation (50 Hz)", "Angular Velocity (°/s)")
ax_gyro.plot(t, gx_sim, color="#58a6ff", lw=1.4, label="X-axis")
ax_gyro.plot(t, gy_sim, color="#ff7b72", lw=1.4, label="Y-axis")
ax_gyro.plot(t, gz_sim, color="#3fb950", lw=1.4, label="Z-axis")
ax_gyro.axhline( CANDIDATE_GYRO_THRESHOLD, color="#d29922", lw=0.9, ls="--", alpha=0.7,
                 label=f"Threshold +{CANDIDATE_GYRO_THRESHOLD:.0f}°/s")
ax_gyro.axhline(-CANDIDATE_GYRO_THRESHOLD, color="#d29922", lw=0.9, ls="--", alpha=0.7)
ax_gyro.set_ylim(-650, 650)
ax_gyro.legend(loc="upper left", facecolor=AXIS_BG, edgecolor=GRID_CLR,
               labelcolor=TEXT_CLR, fontsize=8.5, ncol=4)

# ── Plot 3: Magnitude (SMA) ───────────────────────────────────────────────────
_style_axes(ax_mag, "Signal Magnitude (|acc| and |gyro|) — Gate View", "Magnitude")
ax_mag.plot(t, acc_mag,  color="#58a6ff", lw=1.6, label="|acc| (g)")
ax_mag2 = ax_mag.twinx()
ax_mag2.set_facecolor(AXIS_BG)
ax_mag2.plot(t, gyro_mag, color="#3fb950", lw=1.6, label="|gyro| (°/s)")
ax_mag2.tick_params(colors=MUTED_CLR)
ax_mag2.set_ylabel("|gyro| (°/s)", color=MUTED_CLR, fontsize=10)
ax_mag.axhline(CANDIDATE_ACC_THRESHOLD, color="#d29922", lw=1.0, ls="--", alpha=0.7,
               label=f"ACC_THRESHOLD {CANDIDATE_ACC_THRESHOLD}g")
ax_mag.set_ylim(0, 20)
ax_mag2.set_ylim(0, 900)
ax_mag2.spines["right"].set_edgecolor(GRID_CLR)
ax_mag2.spines["top"].set_edgecolor(GRID_CLR)
ax_mag2.spines["left"].set_edgecolor(GRID_CLR)
ax_mag2.spines["bottom"].set_edgecolor(GRID_CLR)
ax_mag.axvspan(0.95, 1.1, alpha=0.12, color="#ff7b72", label="Impact zone")

# Merge legends
lines_a, labels_a = ax_mag.get_legend_handles_labels()
lines_b, labels_b = ax_mag2.get_legend_handles_labels()
ax_mag.legend(lines_a + lines_b, labels_a + labels_b,
              loc="upper left", facecolor=AXIS_BG, edgecolor=GRID_CLR,
              labelcolor=TEXT_CLR, fontsize=8.5, ncol=4)

# Vùng phase labels trên toàn biểu đồ (chỉ trên subplot acc)
phase_labels = [
    (0.00, 0.75, "Pre-fall"),
    (0.75, 0.95, "Tilt"),
    (0.95, 1.10, "Impact"),
    (1.10, 1.45, "Oscillation"),
    (1.45, 2.00, "Still"),
]
phase_colors = ["#1f6feb22", "#9e6a0322", "#da363622", "#6e40c922", "#1f6feb11"]
for (t0, t1, label), color in zip(phase_labels, phase_colors):
    ax_acc.axvspan(t0, t1, alpha=0.22, color=color, zorder=0)
    ax_acc.text((t0 + t1) / 2, 13.5, label, ha="center", va="top",
                color=TEXT_CLR, fontsize=7.5, alpha=0.85,
                bbox=dict(facecolor="#0d1117", edgecolor="none", alpha=0.6, pad=1))

# Chú thích chung
fig.text(0.01, 0.01,
         f"Sampling Rate: {SAMPLE_RATE} Hz  |  Window: {N_SAMPLES} samples = {DURATION_S}s  "
         f"|  dt = {dt*1000:.0f} ms  |  ACC ±8g  |  GYR ±2000 °/s\n"
         f"Firmware: S3_AIFD_V1 (CANDIDATE_ACC≥{CANDIDATE_ACC_THRESHOLD}g OR GYRO≥{CANDIDATE_GYRO_THRESHOLD}°/s triggers AI inference)",
         color=MUTED_CLR, fontsize=8, ha="left", va="bottom")

plt.suptitle("Figure: IMU Sensor Simulation — Fall Impact Event (ESP32-S3 @ 50 Hz)",
             color=TEXT_CLR, fontsize=13, fontweight="bold", y=1.00)

# ─── Xuất file PNG ────────────────────────────────────────────────────────────
OUT_PNG = "fall_imu_simulation_50hz.png"
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"✓ Đã lưu: {OUT_PNG}")

# ─── In thống kê nhanh ───────────────────────────────────────────────────────
print("\n=== Thống kê dữ liệu mô phỏng ===")
print(f"  Số mẫu    : {N_SAMPLES}  ({SAMPLE_RATE} Hz × {DURATION_S}s)")
print(f"  dt        : {dt*1000:.0f} ms")
print(f"  ACC peak  : ax={ax_sim.max():.1f}g  ay={ay_sim.max():.1f}g  az={az_sim.max():.1f}g")
print(f"  ACC trough: ax={ax_sim.min():.1f}g  ay={ay_sim.min():.1f}g  az={az_sim.min():.1f}g")
print(f"  GYR peak  : gx={gx_sim.max():.0f}°/s  gy={gy_sim.max():.0f}°/s  gz={gz_sim.max():.0f}°/s")
print(f"  GYR trough: gx={gx_sim.min():.0f}°/s  gy={gy_sim.min():.0f}°/s  gz={gz_sim.min():.0f}°/s")
print(f"  |acc| max : {acc_mag.max():.2f}g  (threshold: {CANDIDATE_ACC_THRESHOLD}g)")
print(f"  |gyro| max: {gyro_mag.max():.1f}°/s  (threshold: {CANDIDATE_GYRO_THRESHOLD}°/s)")
print(f"\n  → CANDIDATE_ACC gate  : {'PASS ✓' if acc_mag.max() > CANDIDATE_ACC_THRESHOLD else 'FAIL ✗'}")
print(f"  → CANDIDATE_GYRO gate : {'PASS ✓' if gyro_mag.max() > CANDIDATE_GYRO_THRESHOLD else 'FAIL ✗'}")

plt.show()
