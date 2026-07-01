# 05 — Fall Detection Pipeline & Thông số ngưỡng

**Phiên bản:** S3_BLE_test_2 | **Cập nhật:** 2026-05-19
**Model AI:** TFLite V84 — F1=93.45%, Recall=98.51%, Threshold=0.42

---

## 1. Tổng quan pipeline (7 tầng lọc)

```
IMU 50Hz (BMI160 ±2g / ±2000dps)
    │
    ▼ mỗi 100 mẫu = 1 window (2s)
[1] CANDIDATE GATE
    │
    ▼
[2] ACTIVITY GATE
    │
    ▼
[3] HIGH-IMPACT GATE
    │
    ▼
[4] IMPACT CHECK
    │
    ▼
[5] AI WINDOW (6s)  ←── TFLite V84
    │
    ▼
[6] FALL STATE MACHINE  (FALL_WATCH → STILL_TIMING)
    │
    ▼
[7] ALARM  →  BLE ALERT + Còi + Đèn
```

---

## 2. Thông số ngưỡng

### 2.1 Gates (tầng lọc trước AI)

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `CANDIDATE_ACC_THRESHOLD` | **7.5 g** | Peak acc cần có trong window để coi là ứng viên |
| `CANDIDATE_GYRO_THRESHOLD` | **240 dps** | Peak gyro cần có (OR với acc) |
| `ACTIVITY_ACC_THRESHOLD` | **2.0 g** | Ngưỡng acc cho "đang hoạt động" (tích lũy window) |
| `ACTIVITY_GYRO_THRESHOLD` | **50 dps** | Ngưỡng gyro cho "đang hoạt động" (tích lũy window) |
| `ACTIVITY_WINDOW_COUNT` | **3 windows** | Cần 3 window liên tiếp vượt ngưỡng activity |
| `HIGH_IMPACT_ACC_MIN` | **2.0 g** | Ít nhất 1 window trong streak phải có peak acc > này |
| `HIGH_IMPACT_GYRO_MIN` | **300 dps** | VÀ peak gyro > này (đồng thời) |
| `FALL_IMPACT_GYRO_MIN` | **20 dps** | Peak gyro của window hiện tại (check thêm trước AI) |

### 2.2 AI Window

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `AI_WINDOW_DURATION_MS` | **6000 ms (6s)** | Sau khi có peak → AI chạy tối đa 6s (= 3 windows) |
| `FALL_DECISION_THRESHOLD` | **0.42** | fall_prob >= 0.42 → AI xác định là ngã |

> **Logic AI window:** Peak mở công tắc AI 6s. Trong 6s đó, mỗi window (2s) chạy inference 1 lần. Hết 6s không có fall → tắt, reset `highImpactSeen`, chờ peak mới. Fall phát hiện trong 6s → đóng window, FSM tiếp quản.

### 2.3 Fall State Machine

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `FALL_WATCH_WINDOWS` | **5 windows (10s)** | Sau khi AI xác nhận fall, chờ tối đa 5 window trước khi check nằm im |
| `CANCEL_ACC_THRESHOLD` | **3.5 g** | Trong FALL_WATCH/STILL_TIMING: huỷ nếu peak acc > này |
| `CANCEL_GYRO_THRESHOLD` | **150 dps** | Trong FALL_WATCH/STILL_TIMING: huỷ nếu peak gyro > này (OR) |
| `FALL_STILL_DURATION_MS` | **5000 ms (5s)** | Cần nằm im liên tục bao lâu để xác nhận ngã thật |
| `FALL_MONITOR_TIMEOUT_MS` | **10000 ms (10s)** | Cửa sổ theo dõi tối đa của STILL_TIMING |

### 2.4 Stillness check

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `STILLNESS_SAMPLES` | **25 mẫu (0.5s cuối window)** | Dùng 25 mẫu cuối để tính mean |
| `STILLNESS_ACC_MIN` | **0.6 g** | mean_acc phải >= (nằm im có trọng lực) |
| `STILLNESS_ACC_MAX` | **1.7 g** | mean_acc phải <= (không vận động) |
| `STILLNESS_GYRO_MAX` | **100 dps** | mean_gyro phải <= |

---

## 3. Logic chi tiết từng tầng

### Tầng 1 — Candidate Gate
```
peak_acc > 7.5g  OR  peak_gyro > 240dps
→ Không: fallProb = 0, skip
→ Có: tiếp tục
```

### Tầng 2 — Activity Gate
```
window này có acc > 2g OR gyro > 50dps?
→ Có: activityCount++ (tối đa 3)
   Nếu cùng lúc acc > 2g VÀ gyro > 300dps: highImpactSeen = true
→ Không: activityCount = 0, highImpactSeen = false (RESET HOÀN TOÀN)

Cần activityCount >= 3 để tiếp tục
```

### Tầng 3 — High-Impact Gate
```
Trong streak 3 window: có ít nhất 1 window với peak_acc > 2g VÀ peak_gyro > 300dps?
→ Không: skip, log "[GATE] highImpact=no"
→ Có: tiếp tục
```

### Tầng 4 — Impact Check
```
peak_gyro của window hiện tại > 20dps?
→ Không: reject, log "[IMPACT] reject"
→ Có: tiếp tục
```

### Tầng 5 — AI Window
```
Peak vừa pass tất cả gates → mở AI window 6s
  Mỗi 2s: chạy TFLite V84 inference trên 100 mẫu (2s @ 50Hz)
  fall_prob >= 0.42 → FALL! → vào FSM
  Hết 6s không có fall → đóng window, highImpactSeen = false
```

### Tầng 6 — Fall State Machine

```
FDS_IDLE
  → AI says fall → FDS_FALL_WATCH (left=5)

FDS_FALL_WATCH (5 windows = 10s)
  → peak > 3.5g OR > 150dps: HUỶ → FDS_IDLE
  → hết 5 windows → FDS_STILL_TIMING

FDS_STILL_TIMING (cửa sổ 10s)
  → peak > 3.5g OR > 150dps: reset stillness timer (VẪN trong STILL_TIMING)
  → nằm im → arm timer 5s
    → đủ 5s liên tục → ALARM
    → cử động trong 5s → reset timer, arm lại khi nằm im
  → hết 10s monitor window → SAFE, về FDS_IDLE
```

---

## 4. LED feedback

| Trạng thái pipeline | Đèn |
|---|---|
| Idle (không cử động) | ⚫⚫⚫ Tắt hết |
| activityCount 1–2 | 🟢🟡🔴 3 đèn sáng |
| activityCount = 3 (gate met) | 🟢⚫⚫ Chỉ xanh |
| Candidate peak / AI window đang mở | 🟢🟡⚫ Xanh + Vàng |
| AI xác định fall (window này) | 🟢🟡🔴 3 đèn sáng |
| FALL_WATCH / STILL_TIMING | 💡💡💡 Nhấp nháy (không còi) |
| Confirmed fall (ALARM) | 💡💡💡 Nhấp nháy + 🔊 Còi |

---

## 5. Nút bấm

| Trạng thái | Nhấn nút |
|---|---|
| Bình thường | 🚨 Trigger fall thủ công (SOS) — gửi ALERT, bật còi |
| Đang alarm | ✅ Xác nhận an toàn — gửi SAFE, tắt còi |

---

## 6. Timeline điển hình (ngã thật)

```
t=0s   Người ngã mạnh (peak 2.96g / 1770dps)
t=0s   AI window mở (6s)
t=0–6s AI chạy mỗi 2s → fall_prob = 0.996 → AI FALL → FSM FALL_WATCH
t=0–10s FALL_WATCH (5 windows)
t=10s  STILL_TIMING bắt đầu
t=15s  Đủ 5s nằm im → ALARM
t=15s  Còi kêu + BLE gửi ALERT → App đếm ngược 15s
t=30s  Không phản hồi → App gọi khẩn cấp
```

---

## 7. Ghi chú về sensor

- **Range acc:** ±2g → max magnitude ~3.46g (saturates ở đó)
- **Range gyro:** ±2000dps — không bị saturate
- `CANDIDATE_ACC_THRESHOLD = 7.5g` **không thể đạt được** với ±2g range
  → Điều kiện candidate thực tế chỉ dựa vào **gyro > 240dps**
- Nếu muốn dùng threshold acc thực tế: cần đổi sensor range lên ±8g hoặc ±16g
  (đổi `REG_ACC_RANGE` và `ACC_LSB_PER_G`) — **nhưng model V84 train trên ±2g, phải re-train**
