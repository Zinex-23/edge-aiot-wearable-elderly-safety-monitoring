#!/usr/bin/env python3
"""
power_sim.py — Mô phỏng hiệu năng & tuổi thọ pin cho firmware AIFD adaptive RTOS
(ESP32-S3 Super Mini) trong src/main.cpp.

Trình mô phỏng này:
  1. Tái hiện đúng các SystemMode + hằng số timing của firmware
     (IDLE 10Hz, MOTION_CAPTURE 50Hz/100-sample/2s, FALL_WATCH, ALERT,
      vitals 25s, MAX_QUIET_WINDOWS...).
  2. Mô hình dòng tiêu thụ (mA) của từng linh kiện: ESP32-S3, BMI160,
     MAX30102, WS2812, buzzer, BLE, + overhead board Super Mini (LDO+LED nguồn).
  3. Chạy mô phỏng Monte-Carlo 24h theo kịch bản sinh hoạt người cao tuổi
     (ngủ / ngồi nghỉ / vận động) để tính thời gian ở mỗi mode.
  4. Tính dung lượng tiêu thụ (mAh) → tuổi thọ pin với pin 1000 mAh.

So sánh 4 cấu hình:
  - V1 (always-on)      : 50Hz + BLE streaming liên tục, LED xanh sáng (firmware cũ)
  - V2 (như hiện tại)   : adaptive, NHƯNG CPU không light-sleep (đúng code hiện tại)
  - V2 + light-sleep    : thêm esp_light_sleep khi idle (TODO #2)
  - V2 + light-sleep + sensor-opt : thêm BMI low-power + MAX shutdown khi idle

LƯU Ý: đây là số liệu MÔ HÌNH HÓA (datasheet + kinh nghiệm), KHÔNG phải đo thực.
Chỉnh các hằng số bên dưới theo phép đo thực tế (đồng hồ µA) để chính xác hơn.

Chạy:  python3 power_sim.py
       python3 power_sim.py --battery 1000 --seed 1 --plot
"""

import argparse
import random
from dataclasses import dataclass

# =====================================================================
# 1. MÔ HÌNH DÒNG TIÊU THỤ LINH KIỆN  (đơn vị: mA)
#    Nguồn: datasheet + đo điển hình. Sửa theo phép đo của bạn.
# =====================================================================
# Overhead cố định của board Super Mini: LDO AMS1117 (Iq ~5mA) + LED nguồn
# luôn sáng. KHÔNG bỏ được nếu không sửa phần cứng (gỡ LED / thay LDO).
BOARD_OVERHEAD       = 6.0

# ESP32-S3 @240MHz, ngăn xếp BLE bật (advertising / connected idle)
CPU_ACTIVE           = 38.0
# ESP32-S3 light sleep (CPU dừng, RTC + RAM giữ) — chỉ có khi thêm esp_light_sleep
CPU_LIGHT_SLEEP      = 1.5
# Dòng PHỤ TRỘI khi đang chạy TFLite Invoke() (burst dual-core)
CPU_INFER_EXTRA      = 22.0
# Thời gian 1 lần inference (giây) — đo [INFER] latency của bạn (~30-50ms)
INFER_DURATION_S     = 0.040

# BMI160
BMI_NORMAL           = 0.95   # acc + gyro normal mode (firmware dùng cả 2)
BMI_LOWPOWER_ACC     = 0.18   # chỉ acc low-power (tối ưu khi idle)

# MAX30102 (PPG) — default setup bật LED đỏ/IR liên tục
MAX_ON               = 1.20
MAX_SHUTDOWN         = 0.001  # shutdown mode (tối ưu khi không đo)

# WS2812 RGB (1 pixel) @ brightness ~20%
LED_OFF              = 0.60   # chip vẫn tiêu thụ quiescent dù "tắt"
LED_SOLID_ON         = 8.0    # sáng liên tục
LED_BLINK_AVG        = 4.3    # ~50% duty (FALL_WATCH/ALARM) -> trung bình

# Buzzer (chỉ kêu khi ALARM)
BUZZER_ON            = 35.0

# BLE: phụ trội trung bình khi đã kết nối (sự kiện connection interval)
BLE_CONNECTED_EXTRA  = 3.0
# Phụ trội trung bình khi streaming liên tục (V1: BMI mỗi 5s + vitals)
BLE_STREAM_EXTRA     = 5.0


# =====================================================================
# 2. HẰNG SỐ TIMING — khớp với firmware src/main.cpp
# =====================================================================
MOTION_MONITOR_PERIOD_S = 0.100   # 10 Hz idle poll
SAMPLE_PERIOD_S         = 0.020   # 50 Hz capture
WINDOW_SIZE             = 100      # 100 samples = 2 s
WINDOW_DURATION_S       = WINDOW_SIZE * SAMPLE_PERIOD_S   # 2.0 s
MAX_QUIET_WINDOWS       = 1
VITALS_PERIOD_S         = 25.0
ALERT_DURATION_S        = 30.0    # alarm kêu tới khi user bấm SAFE (giả định 30s)


# =====================================================================
# 3. KỊCH BẢN SINH HOẠT 24h (người cao tuổi đeo thiết bị)
#    Mỗi giai đoạn: số giờ + xác suất "có chuyển động" trong mỗi giây.
#    p_motion thấp = phần lớn thời gian nằm im (idle, tiết kiệm pin).
# =====================================================================
@dataclass
class Phase:
    name: str
    hours: float
    p_motion_per_s: float   # xác suất bắt đầu 1 đợt vận động mỗi giây

DEFAULT_SCENARIO = [
    Phase("Ngủ (nằm im)",        8.0, 0.002),   # gần như bất động
    Phase("Ngồi nghỉ / xem TV",  9.0, 0.020),   # thỉnh thoảng cử động
    Phase("Đi lại / vận động",   6.5, 0.120),   # vận động thường xuyên
    Phase("Sinh hoạt nặng",      0.5, 0.300),   # nấu ăn, lên xuống cầu thang
]
# Số lần ngã giả lập trong ngày (mỗi lần kích hoạt ALERT + buzzer)
FALLS_PER_DAY = 0


# =====================================================================
# 4. DÒNG TIÊU THỤ THEO MODE  (mA) — tổ hợp linh kiện theo từng cấu hình
# =====================================================================
@dataclass
class PowerProfile:
    name: str
    light_sleep_idle: bool = False   # CPU light-sleep khi idle
    sensor_opt_idle: bool = False    # BMI low-power + MAX shutdown khi idle
    always_on: bool = False          # V1: luôn 50Hz + stream (bỏ qua adaptive)
    ble_connected: bool = True       # có điện thoại kết nối

    def current_idle(self) -> float:
        """Dòng khi MODE_IDLE_MONITOR (không có chuyển động)."""
        if self.always_on:
            # V1 không có idle thực — luôn chạy full pipeline
            return self.current_capture()
        cpu = CPU_LIGHT_SLEEP if self.light_sleep_idle else CPU_ACTIVE
        bmi = BMI_LOWPOWER_ACC if self.sensor_opt_idle else BMI_NORMAL
        mx  = MAX_SHUTDOWN if self.sensor_opt_idle else MAX_ON
        ble = BLE_CONNECTED_EXTRA if (self.ble_connected and not self.light_sleep_idle) else 0.0
        return BOARD_OVERHEAD + cpu + bmi + mx + LED_OFF + ble

    def current_capture(self) -> float:
        """Dòng khi MODE_MOTION_CAPTURE / AI_INFERENCE (50Hz + inference)."""
        infer_avg = CPU_INFER_EXTRA * (INFER_DURATION_S / WINDOW_DURATION_S)
        ble = BLE_CONNECTED_EXTRA if self.ble_connected else 0.0
        if self.always_on:
            ble = BLE_STREAM_EXTRA  # V1 stream BMI/vitals liên tục
        return (BOARD_OVERHEAD + CPU_ACTIVE + infer_avg +
                BMI_NORMAL + MAX_ON + LED_OFF + ble)

    def current_fall_watch(self) -> float:
        """FALL_WATCH: như capture + LED đỏ nhấp nháy."""
        return self.current_capture() - LED_OFF + LED_BLINK_AVG

    def current_alert(self) -> float:
        """ALERT: CPU active + LED đỏ + buzzer + BLE."""
        ble = BLE_STREAM_EXTRA if self.always_on else BLE_CONNECTED_EXTRA
        return (BOARD_OVERHEAD + CPU_ACTIVE + BMI_NORMAL + MAX_ON +
                LED_BLINK_AVG + BUZZER_ON + ble)


# =====================================================================
# 5. MÔ PHỎNG 24h — đếm thời gian ở mỗi mode theo kịch bản
# =====================================================================
@dataclass
class SimResult:
    seconds_idle: float = 0.0
    seconds_capture: float = 0.0
    seconds_fall_watch: float = 0.0
    seconds_alert: float = 0.0
    n_motion_events: int = 0
    n_inferences: int = 0

    @property
    def total_s(self):
        return (self.seconds_idle + self.seconds_capture +
                self.seconds_fall_watch + self.seconds_alert)


def simulate_day(scenario, falls_per_day, seed=0) -> SimResult:
    """Mô phỏng từng giây 24h. Trả về thời gian ở mỗi mode.

    Logic khớp firmware: 1 đợt chuyển động giữ high-rate sống ít nhất
    (1 window + MAX_QUIET_WINDOWS) trước khi về idle.
    """
    rng = random.Random(seed)
    res = SimResult()

    # Thời lượng tối thiểu 1 đợt capture (giây): window kích hoạt + quiet windows
    min_capture_s = WINDOW_DURATION_S * (1 + MAX_QUIET_WINDOWS)

    # Lịch các lần ngã (random trong ngày)
    fall_times = sorted(rng.uniform(0, 86400) for _ in range(falls_per_day))
    fi = 0

    t = 0.0
    for phase in scenario:
        phase_end = t + phase.hours * 3600.0
        while t < phase_end:
            # Ngã?
            if fi < len(fall_times) and t >= fall_times[fi]:
                res.seconds_alert += ALERT_DURATION_S
                t += ALERT_DURATION_S
                fi += 1
                continue

            # Bắt đầu một đợt chuyển động?
            if rng.random() < phase.p_motion_per_s:
                # đợt capture kéo dài min..(min + vài window) tùy mức vận động
                extra = rng.expovariate(1.0 / (WINDOW_DURATION_S * 2))
                dur = min_capture_s + extra
                dur = min(dur, phase_end - t)
                res.seconds_capture += dur
                res.n_motion_events += 1
                res.n_inferences += int(dur / WINDOW_DURATION_S)
                t += dur
            else:
                # idle 1 giây
                res.seconds_idle += 1.0
                t += 1.0
    return res


def energy_mAh(res: SimResult, prof: PowerProfile):
    """Tích phân dòng theo thời gian -> mAh tiêu thụ trong 24h + breakdown."""
    e_idle    = prof.current_idle()       * res.seconds_idle       / 3600.0
    e_capture = prof.current_capture()    * res.seconds_capture    / 3600.0
    e_watch   = prof.current_fall_watch() * res.seconds_fall_watch / 3600.0
    e_alert   = prof.current_alert()      * res.seconds_alert      / 3600.0
    total = e_idle + e_capture + e_watch + e_alert
    return total, dict(idle=e_idle, capture=e_capture,
                       fall_watch=e_watch, alert=e_alert)


# =====================================================================
# 6. BÁO CÁO
# =====================================================================
def human_time(hours: float) -> str:
    if hours >= 48:
        return f"{hours/24:.1f} ngày ({hours:.0f} h)"
    return f"{hours:.1f} h"


def run(battery_mah: float, usable_frac: float, seed: int, make_plot: bool):
    res = simulate_day(DEFAULT_SCENARIO, FALLS_PER_DAY, seed=seed)

    profiles = [
        PowerProfile("V1 always-on (firmware cũ)", always_on=True),
        PowerProfile("V2 adaptive (code hiện tại, KHÔNG light-sleep)"),
        PowerProfile("V2 + light-sleep idle (TODO #2)", light_sleep_idle=True),
        PowerProfile("V2 + light-sleep + sensor-opt", light_sleep_idle=True, sensor_opt_idle=True),
    ]

    usable_mah = battery_mah * usable_frac

    print("=" * 78)
    print(" MÔ PHỎNG NĂNG LƯỢNG — AIFD ESP32-S3 Super Mini")
    print("=" * 78)
    print(f" Pin: {battery_mah:.0f} mAh  (dùng được {usable_frac*100:.0f}% = {usable_mah:.0f} mAh)")
    print(f" Kịch bản 24h:")
    for p in DEFAULT_SCENARIO:
        print(f"   - {p.name:<22} {p.hours:>4.1f} h   p_motion={p.p_motion_per_s:.3f}/s")
    print(f" Số lần ngã giả lập: {FALLS_PER_DAY}")
    print("-" * 78)
    print(" PHÂN BỐ THỜI GIAN (mô phỏng):")
    print(f"   IDLE_MONITOR : {res.seconds_idle/3600:6.2f} h  ({res.seconds_idle/res.total_s*100:5.1f}%)")
    print(f"   MOTION/AI    : {res.seconds_capture/3600:6.2f} h  ({res.seconds_capture/res.total_s*100:5.1f}%)")
    print(f"   FALL_WATCH   : {res.seconds_fall_watch/3600:6.2f} h")
    print(f"   ALERT        : {res.seconds_alert/3600:6.2f} h")
    print(f"   Số đợt chuyển động: {res.n_motion_events}   Số lần inference: {res.n_inferences}")
    print("=" * 78)

    header = f" {'Cấu hình':<46}{'I_tb':>8}{'mAh/ngày':>10}{'Tuổi thọ':>14}"
    print(header)
    print("-" * 78)
    baseline_life = None
    for prof in profiles:
        total_mah, _ = energy_mAh(res, prof)
        avg_current = total_mah / 24.0          # mAh/24h = mA trung bình
        life_h = usable_mah / avg_current
        if baseline_life is None and prof.always_on:
            baseline_life = life_h
        print(f" {prof.name:<46}{avg_current:>6.1f}mA {total_mah:>8.1f}  {human_time(life_h):>16}")
    print("=" * 78)

    # Chi tiết breakdown cho cấu hình "code hiện tại"
    cur = profiles[1]
    total_mah, bd = energy_mAh(res, cur)
    print(f"\n CHI TIẾT — {cur.name}:")
    print(f"   Dòng theo mode:  idle={cur.current_idle():.1f}mA  "
          f"capture={cur.current_capture():.1f}mA  "
          f"fall_watch={cur.current_fall_watch():.1f}mA  alert={cur.current_alert():.1f}mA")
    for k, v in bd.items():
        print(f"   năng lượng {k:<11}: {v:6.2f} mAh/ngày  ({v/total_mah*100:5.1f}%)")
    print(f"   => Trung bình {total_mah/24:.1f} mA  =>  "
          f"{usable_mah/(total_mah/24):.1f} h sống với pin {battery_mah:.0f}mAh")

    print("\n GHI CHÚ:")
    print("  • CPU không light-sleep => idle vẫn ~{:.0f}mA (CPU + BLE luôn bật)."
          .format(cur.current_idle()))
    print("    Đây là lý do V2-hiện-tại chỉ hơn V1 chút ít: lợi ích lớn nằm ở")
    print("    light-sleep (TODO #2) — xem 2 dòng cuối bảng.")
    print("  • Sửa các hằng số dòng (đầu file) theo đo thực để có số chính xác.")

    if make_plot:
        _plot(res, profiles, usable_mah)


def _plot(res, profiles, usable_mah):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n[plot] matplotlib chưa cài — bỏ qua (pip install matplotlib)")
        return
    names = [p.name.split(" (")[0] for p in profiles]
    lives = []
    for prof in profiles:
        total_mah, _ = energy_mAh(res, prof)
        lives.append(usable_mah / (total_mah / 24.0))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(names, lives, color=["#c44", "#e90", "#4a4", "#262"])
    ax.set_xlabel("Tuổi thọ pin (giờ)")
    ax.set_title("Tuổi thọ pin theo cấu hình firmware (pin 1000mAh)")
    for b, v in zip(bars, lives):
        ax.text(v + 1, b.get_y() + b.get_height()/2,
                f"{v:.0f}h ({v/24:.1f}d)", va="center")
    ax.invert_yaxis()
    fig.tight_layout()
    out = "power_sim_result.png"
    fig.savefig(out, dpi=120)
    print(f"\n[plot] Đã lưu biểu đồ: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mô phỏng tuổi thọ pin firmware AIFD")
    ap.add_argument("--battery", type=float, default=1000.0, help="Dung lượng pin (mAh)")
    ap.add_argument("--usable", type=float, default=0.85,
                    help="Tỉ lệ dung lượng dùng được (derating, mặc định 0.85)")
    ap.add_argument("--seed", type=int, default=42, help="Seed Monte-Carlo")
    ap.add_argument("--plot", action="store_true", help="Xuất biểu đồ PNG")
    args = ap.parse_args()
    run(args.battery, args.usable, args.seed, args.plot)
