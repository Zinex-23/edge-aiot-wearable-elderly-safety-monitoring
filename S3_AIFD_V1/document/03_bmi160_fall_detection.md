# 03 — BMI160 + AI Fall Detection

**Ngày tạo:** 2026-05-15 | **Cập nhật lần cuối:** 2026-05-16
**File code:** [`src/main.cpp`](../src/main.cpp)
**Model đang dùng:** `fall_detection_v50.h` (V50 — Best Overall, F1=91.68%, Recall=96.64%)

---

## 1. Kiến trúc tổng quan

```
   BMI160 ──I2C(50Hz)──▶ Ring buffer (100 mẫu = 2s)
                            │
                            ▼ mỗi 2s (luôn chạy)
                  ┌─ Pre-activity gate ─────────────────────────┐
                  │  peak_acc > 2.0g  OR  peak_gyro > 50 dps?  │
                  │  Yes → activityCount++ (max 3)              │
                  │  No  → activityCount-- (min 0)              │
                  │  activityCount < 1 → AI blocked (ngủ/nghỉ) │
                  └────────────────┬───────────────────────────-┘
                                   │ activityCount >= 1
                                   ▼
                  ┌─ Lớp 1: Candidate filter ──────────────────┐
                  │  peak_acc > 7.5g  OR  peak_gyro > 240 dps  │
                  │  Bỏ qua nếu chuyển động không đủ mạnh      │
                  └────────────────┬───────────────────────────-┘
                                   │ pass
                                   ▼
                  ┌─ Lớp 2: TFLite Micro inference ────────────┐
                  │  fall_prob >= 0.65                          │
                  │  (Model V50: 4×Conv1D [32,48,64,96], K5)   │
                  └────────────────┬───────────────────────────-┘
                                   │ fall?
                                   ▼
                  ┌─ Lớp 3: Impact gyro check ─────────────────┐
                  │  peak_gyro trong 2s window >= 20 dps       │
                  │  Lọc "đặt tay nhẹ" không có rotation       │
                  └────────────────┬───────────────────────────-┘
                                   │ pass
                                   ▼
                  ┌─ Lớp 4: Post-fall stillness check ─────────┐
                  │  0.5s cuối window: mean_acc ∈ [0.6, 1.7]g  │
                  │                   mean_gyro < 100 dps       │
                  └────────────────┬───────────────────────────-┘
                                   │ pass → fallPending = true
                                   ▼
                  ┌─ Lớp 5: FALL_WATCH (tối đa 10s = 5 window) ┐
                  │  Mỗi 2s check stillness                    │
                  │  Thấy stillness → vào STILL_TIMING         │
                  │  Hết 5 window, không im → về IDLE          │
                  └────────────────┬───────────────────────────-┘
                                   │ stillness found (bất kỳ window nào)
                                   ▼
                  ┌─ Lớp 6: STILL_TIMING ───────────────────────┐
                  │  Đo thời gian nằm im liên tục               │
                  │  Cử động → về IDLE                          │
                  │  Nằm im >= 5s → ALARM                       │
                  │  (Bypass activity gate — người đang nằm)    │
                  └────────────────┬───────────────────────────-┘
                                   │ >= 5s confirmed
                                   ▼
                          Force STATE_BLINK_BUZZ
                        (LED nhấp nháy + buzzer kêu)

   Button ──debounce──▶ Cycle state (hoạt động độc lập, bất kỳ lúc nào)
```

---

## 2. Chi tiết từng lớp lọc

### Pre-activity gate (chạy trước mọi lớp)

Theo dõi người có đang hoạt động gần đây không. AI bị chặn khi người đang ngủ / nằm yên lâu, tránh false positive ban đêm.

AI chỉ chạy khi **ĐỀU** 2 điều kiện:

```cpp
// Điều kiện 1: gyro > 50dps trong 3 window LIÊN TIẾP
static const float  ACTIVITY_GYRO_THRESHOLD  = 50.0f;  // dps
static const int    ACTIVITY_WINDOW_COUNT    = 3;

// Điều kiện 2: ít nhất 1 trong 3 window có impact cực mạnh
static const float  HIGH_IMPACT_ACC_MIN      = 10.0f;  // g
static const float  HIGH_IMPACT_GYRO_MIN     = 400.0f; // dps

// Model threshold (tăng từ 0.42 → giảm false positive)
static const float  FALL_DECISION_THRESHOLD  = 0.65f;
```

Cơ chế mỗi 2s:
- `gyro > 50dps` → `activityCount++` | không vượt → `activityCount = 0` + reset `highImpactSeen`
- `acc > 10g VÀ gyro > 400dps` → `highImpactSeen = true`
- AI chỉ chạy khi: `activityCount >= 3` **VÀ** `highImpactSeen == true`

Log: `[ACT] acc=X.XXg gyro=XX.Xdps | gyro_active=Y count=X/3 impact=Y AI=ON`

Ví dụ:
```
Đi bộ bình thường: gyro~80dps, acc~2g → count=3, impact=N → AI OFF ✅
Chạy bộ + vấp nhẹ: gyro~150dps, acc~6g → count=3, impact=N → AI OFF ✅
Chạy bộ + té mạnh: gyro~350dps, acc~12g → count=3, impact=Y → AI ON ✅
```

Ví dụ:
```
Nằm ngủ: count=0,0,0,0 → AI OFF liên tục
Đi bộ:   count=1,2,3   → AI ON từ window thứ 3
Đứng yên giữa chừng: count=3,3,0,0 → AI OFF ngay khi nghỉ, reset về 0
Đang đi và vấp té: count=3,3,3... → AI ON → phát hiện ngã ✅
```

Lý do dùng **consecutive** (reset về 0) thay vì decay:
- Đảm bảo người đang thực sự VẬN ĐỘNG liên tục trước khi té
- Không ai đứng bình thường đột ngột ngã — phải có vận động trước
- Loại bỏ va chạm nhẹ lẻ tẻ ban đêm (chỉ 1–2 window active, không đủ 3)

### Lớp 1 — Candidate filter

Chạy sau pre-activity gate, tránh gọi TFLite khi chuyển động không đủ mạnh.

```cpp
static const float CANDIDATE_ACC_THRESHOLD  = 7.5f;   // g
static const float CANDIDATE_GYRO_THRESHOLD = 240.0f; // dps
```

Log: `[PEAK] acc=X.XXg gyro=XXX.Xdps -> candidate / skip`

### Lớp 2 — TFLite Micro inference

Model V50 nhận 100×6 mẫu int8 và trả về xác suất ngã.

```cpp
static const float FALL_DECISION_THRESHOLD = 0.65f;
```

Log: `[INFER] fall_prob=0.992 -> FALL?`

### Lớp 3 — Impact gyro check

Ngã thật phải có rotation mạnh trong window (xoay người khi ngã). Phân biệt với "đặt tay nhẹ xuống".

```cpp
static const float FALL_IMPACT_GYRO_MIN = 20.0f;  // dps
```

Log: `[IMPACT] peak_acc=X.XXg peak_gyro=XXX.Xdps -> OK / reject`

### Lớp 4 — Post-fall stillness (0.5s cuối window)

Sau impact, người ngã thật bắt đầu nằm im. Kiểm tra 25 mẫu cuối (0.5s) của window.

```cpp
static const int   STILLNESS_SAMPLES  = 25;    // 0.5s @ 50Hz
static const float STILLNESS_ACC_MIN  = 0.6f;  // g
static const float STILLNESS_ACC_MAX  = 1.7f;  // g  (trọng lực ≈ 1g khi nằm im)
static const float STILLNESS_GYRO_MAX = 100.0f; // dps
```

Log: `[STILL] mean_acc=X.XXg mean_gyro=XX.Xdps -> STILL (pass) / moving (reject)`

### Lớp 5 — Stillness duration (>5s)

Sau khi window 1 pass hết 4 lớp trên, không kêu alarm ngay. Thay vào đó theo dõi người có tiếp tục nằm im không. Nếu cử động bất kỳ lúc nào → hủy. Nằm im liên tục >= 5s → kêu alarm.

```cpp
static const uint32_t FALL_STILL_DURATION_MS = 5000;  // 5s
```

Mỗi 2s check 1 lần (theo inference stride). Thực tế alarm kêu sau khoảng **6–8s** kể từ lúc ngã (2s window 1 + >= 5s nằm im → window kiểm tra ≥ 6s).

Log:
```
[FALL]  detected (1/1) — monitoring stillness for >5s...
[FALL]  still... 2s / 5s
[FALL]  still... 4s / 5s
[FALL]  still... 6s / 5s
[STATE] ALL_ON -> BLINK_BUZZ (still >5s -> fall confirmed)
```

Khi người tự đứng dậy:
```
[FALL]  still... 2s / 5s
[FALL]  moved after 3s — cancelled
```

---

## 3. BMI160 register setup

| Thanh ghi        | Giá trị | Ý nghĩa                         |
| ---------------- | ------- | ------------------------------- |
| `CMD=0x7E`       | `0x11`  | Bật accel normal mode           |
| `CMD=0x7E`       | `0x15`  | Bật gyro normal mode            |
| `ACC_CONF=0x40`  | `0x28`  | ODR 100 Hz, normal averaging    |
| `ACC_RANGE=0x41` | `0x03`  | ±2 g → 16384 LSB/g              |
| `GYR_CONF=0x42`  | `0x28`  | ODR 100 Hz, normal averaging    |
| `GYR_RANGE=0x43` | `0x00`  | ±2000 dps → 16.4 LSB/dps        |

I2C address: 0x69 (SDO không nối GND). Tự dò trong `detectBMI160()`.

---

## 4. Model AI — V50

| Tham số        | Giá trị                                   |
| -------------- | ----------------------------------------- |
| File header    | `fall_detection_v50.h`                    |
| Kiến trúc      | 4×Conv1D [32,48,64,96], Kernel=5, Dense=20 |
| Input shape    | `[1, 100, 6]` int8                        |
| Output         | int8, 1 phần tử (fall probability)        |
| Tensor arena   | 60 KB SRAM                                |
| Model size     | 41.85 KB Flash                            |
| Accuracy       | 91.23%                                    |
| Recall         | 96.64%                                    |
| F1-score       | 91.68%                                    |
| FAR            | 14.18%                                    |
| Threshold      | 0.65 (điều chỉnh từ khuyến nghị 0.40)    |

---

## 5. State machine sau khi tích hợp

| Sự kiện                       | Hành động                                           |
| ----------------------------- | --------------------------------------------------- |
| Nhấn nút                      | Cycle state `0→1→2→3→4→0`                           |
| AI + heuristics báo fall      | `fallPending = true`, bắt đầu đếm 5s              |
| Nằm im >= 5s sau khi pending  | Force `STATE_BLINK_BUZZ` (bất kể state hiện tại)   |
| Cử động trong thời gian pending | Hủy pending, không kêu alarm                      |

---

## 6. Tham số tinh chỉnh

| Triệu chứng | Điều chỉnh |
|---|---|
| **False positive nhiều** | Tăng `FALL_DECISION_THRESHOLD` (→ 0.75), tăng `CANDIDATE_ACC_THRESHOLD`, tăng `FALL_STILL_DURATION_MS` |
| **Bỏ lỡ ngã thật** | Giảm `FALL_DECISION_THRESHOLD` (→ 0.50), giảm `CANDIDATE_ACC_THRESHOLD`, giảm `FALL_STILL_DURATION_MS` |
| **Alarm quá chậm** | Giảm `FALL_STILL_DURATION_MS` (→ 3000ms), giảm `kInferenceStride` (→ 50) |
| **Stillness check quá chặt** | Tăng `STILLNESS_ACC_MAX` (→ 2.0g), tăng `STILLNESS_GYRO_MAX` (→ 150 dps) |
| **Impact check quá chặt** | Giảm `FALL_IMPACT_GYRO_MIN` (→ 10 dps) |

---

## 7. Bộ nhớ & Build

| Thành phần      | RAM / Flash     |
| --------------- | --------------- |
| Tensor arena    | 60 KB SRAM      |
| Ring buffer IMU | ~2.8 KB SRAM    |
| Model V50       | 41.85 KB Flash  |
| Tổng Flash      | ~531 KB (40.5%) |
| Tổng RAM        | ~89 KB (27.3%)  |

```bash
cd S3_BLE
pio run -t upload && pio device monitor
```
