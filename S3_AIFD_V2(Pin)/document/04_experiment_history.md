# 04 — Lịch sử thí nghiệm & điều chỉnh tham số

**Bắt đầu:** 2026-05-15 | **Cập nhật:** 2026-05-16
**Mục đích:** Ghi lại tất cả các lần thay đổi tham số, lý do và kết quả quan sát để tránh lặp lại thí nghiệm đã làm.

---

## Thí nghiệm 1 — Baseline state machine (2026-05-15)

**Trạng thái:** Hoàn thành ✅

**Cấu hình:**
- 3 LED (GPIO 4/5/6) + Buzzer (GPIO 7) + Nút (GPIO 10)
- 5 state: ALL_ON → GREEN → YELLOW → RED → BLINK_BUZZ → (lặp)
- Debounce: 30ms

**Kết quả:** Hoạt động đúng. Nút nhấn chuyển state mượt, không bị dội.

---

## Thí nghiệm 2 — Tích hợp BMI160 + Model Balanced V2 (2026-05-15)

**Trạng thái:** Hoàn thành ✅

**Model:** `result_balanced_v2/fall_detection_model.h`
- Accuracy: 90.80% | Recall: 98.36% | F1: 91.43% | FAR: 16.73% | Size: 10.71 KB

**Tham số ban đầu:**
```
FALL_DECISION_THRESHOLD  = 0.40
CANDIDATE_ACC_THRESHOLD  = 1.8g
CANDIDATE_GYRO_THRESHOLD = 50 dps
FALL_CONFIRM_COUNT       = 2
STILLNESS_SAMPLES        = 25 (0.5s)
STILLNESS_ACC_MIN/MAX    = [0.6, 1.4]g
STILLNESS_GYRO_MAX       = 15 dps
```

**Vấn đề:** Model quá nhạy — xê dịch nhẹ đã báo ngã (false positive cao).

---

## Thí nghiệm 3 — Tăng ngưỡng lần 1 (2026-05-15)

**Trạng thái:** Thất bại ❌ — bỏ lỡ ngã thật

**Thay đổi:**
```
FALL_DECISION_THRESHOLD  = 0.65  (từ 0.40)
CANDIDATE_ACC_THRESHOLD  = 2.5g  (từ 1.8g)
CANDIDATE_GYRO_THRESHOLD = 80 dps (từ 50 dps)
FALL_CONFIRM_COUNT       = 2     (giữ nguyên)
```

**Vấn đề phát hiện ra:** `FALL_CONFIRM_COUNT = 2` không hoạt động vì:
- Window 1 (đang ngã): fall_prob cao → pass
- Window 2 (đã nằm yên): fall_prob = 0 → **reset đếm**

→ Không bao giờ đạt đủ 2 window liên tiếp.

---

## Thí nghiệm 4 — Sửa voting logic (2026-05-15)

**Trạng thái:** Hoàn thành ✅

**Thay đổi:**
```
FALL_CONFIRM_COUNT = 1  (từ 2)
```

**Kết quả:** Phát hiện ngã thành công. Log hoạt động đúng:
```
[INFER] fall_prob=0.992 -> FALL?
[STILL] mean_acc=0.99g mean_gyro=0.2dps -> STILL (pass)
[FALL]  confirmed 1/1
[STATE] ALL_ON -> BLINK_BUZZ (fall confirmed)
```

---

## Thí nghiệm 5 — Giảm ngưỡng (2026-05-15)

**Trạng thái:** Thất bại ❌ — tăng false positive

**Thay đổi:**
```
FALL_DECISION_THRESHOLD  = 0.50  (từ 0.65)
CANDIDATE_ACC_THRESHOLD  = 1.8g  (từ 2.5g)
CANDIDATE_GYRO_THRESHOLD = 50 dps (từ 80 dps)
```

**Vấn đề:** "Đặt tay về vị trí đứng im" kích hoạt alarm — model thấy "chuyển động → đứng yên" = ngã.

---

## Thí nghiệm 6 — Thêm Impact gyro check (2026-05-15)

**Trạng thái:** Hoàn thành ✅

**Lý do:** Ngã thật có rotation mạnh (xoay người khi ngã). "Đặt tay nhẹ" thì gyro thấp suốt.

**Thêm:**
```
FALL_IMPACT_GYRO_MIN = 20 dps  (peak gyro trong 2s window)
```

**Kết quả:** False positive "đặt tay" bị loại. Log:
```
[IMPACT] peak_acc=X.XXg peak_gyro=4.3dps -> reject (no rotation)
```

---

## Thí nghiệm 7 — Chuyển sang Model V50 (2026-05-16)

**Trạng thái:** Hoàn thành ✅

**Lý do:** V50 là model tốt nhất toàn diện (F1=91.68%, FAR=14.18% — thấp hơn Balanced V2).

**Model cũ:** `result_balanced_v2/fall_detection_model.h` (10.71 KB)
**Model mới:** `model_updated_version_50/models/fall_detection_v50.h` (41.85 KB)

File `.h` được tạo bằng:
```bash
xxd -i fall_detection_v50.tflite | sed 's/^unsigned char .*/const unsigned char fall_detection_model_tflite[] = {/' > fall_detection_v50.h
```

`platformio.ini` cập nhật:
```
-I ../AI/model_updated_version_50/models
```

---

## Thí nghiệm 8 — Tăng candidate threshold × 3 (2026-05-16)

**Trạng thái:** Đang test 🔄

**Lý do:** Tiếp tục còn false positive, muốn yêu cầu impact mạnh hơn trước khi chạy model.

**Thay đổi:**
```
CANDIDATE_ACC_THRESHOLD  = 7.5g   (từ 2.5g, ×3)
CANDIDATE_GYRO_THRESHOLD = 240 dps (từ 80 dps, ×3)
```

**Quan sát:** Ngưỡng rất cao — chỉ những cú ngã mạnh mới lọt vào inference.

---

## Thí nghiệm 9 — Thêm stillness duration 5s (2026-05-16)

**Trạng thái:** Đang test 🔄

**Lý do:** Sau khi window 1 phát hiện ngã, không kêu alarm ngay — xác nhận người có thực sự nằm im lâu không (ngã thật khác va chạm nhất thời).

**Thêm:**
```
FALL_STILL_DURATION_MS = 5000  // 5s nằm im liên tục
```

**Logic:**
- Window 1 pass 4 lớp lọc → `fallPending = true`, bắt đầu đếm
- Mỗi 2s: check stillness
  - Nằm im → tiếp tục đếm
  - Cử động → hủy hoàn toàn
- Đủ 5s nằm im → ALARM

**Thời gian từ ngã đến alarm:** ~6–8s (2s window 1 + 5s+ nằm im).

---

## Thí nghiệm 10 — Điều chỉnh stillness range (2026-05-16)

**Trạng thái:** Đang test 🔄

**Các lần thử:**

| Lần | ACC_MAX | GYRO_MAX | Kết quả |
|-----|---------|----------|---------|
| 1   | 1.4g    | 15 dps   | Quá chặt — rejected nhiều cú ngã thật |
| 2   | 2.5g    | 300 dps  | Quá lỏng — gần như luôn pass |
| 3 (hiện tại) | 1.7g | 100 dps | Đang test |

**Tham số hiện tại:**
```
STILLNESS_ACC_MIN  = 0.6g
STILLNESS_ACC_MAX  = 1.7g
STILLNESS_GYRO_MAX = 100 dps
```

---

## Thí nghiệm 11 — Train V61-V70 (2026-05-16)

**Trạng thái:** Hoàn thành ✅

**Chiến lược:** Kết hợp các kỹ thuật hiệu quả nhất từ V1–V60 chưa từng ghép với nhau:
- V22 arch [16,32,48,64]/K5 + D32 + batch=32
- V54 (D32) + V59 (batch=32) combo
- V27 arch [32,64,64,96]/K3/D32 + batch=32
- 5 conv layers (novel)

**Kết quả nổi bật:**

| Version | F1 | Recall | FAR | Size | Ghi chú |
|---|---|---|---|---|---|
| **V64** | **93.17%** | 96.64% | **10.82%** | 62.09KB | 🏆 Best Overall mới |
| V66 | 92.09% | 95.52% | 11.94% | 46.81KB | Compact + balanced |
| V70 | 91.14% | 94.03% | 12.31% | 83.25KB | 5 layers |

**V64** = V27 arch [32,64,64,96]/K3/D32 + batch=32 — vượt V54 (93.07%) về F1.

**Bài học:** [32,64,64,96]/K3 + D32 + batch=32 là bộ tham số tốt nhất. V50's K5 không phải lúc nào cũng thắng K3 nếu D32+batch=32 bù lại.

---

## Tham số đang áp dụng (2026-05-16)

```cpp
// Model
#include "fall_detection_v50.h"
FALL_DECISION_THRESHOLD   = 0.65f

// Candidate filter
CANDIDATE_ACC_THRESHOLD   = 7.5f    // g
CANDIDATE_GYRO_THRESHOLD  = 240.0f  // dps

// Impact check
FALL_IMPACT_GYRO_MIN      = 20.0f   // dps

// Stillness check (0.5s cuối window 1)
STILLNESS_SAMPLES         = 25
STILLNESS_ACC_MIN         = 0.6f    // g
STILLNESS_ACC_MAX         = 1.7f    // g
STILLNESS_GYRO_MAX        = 100.0f  // dps

// Stillness duration (sau window 1)
FALL_STILL_DURATION_MS    = 5000    // ms

// Voting
FALL_CONFIRM_COUNT        = 1
```

---

## Bài học rút ra

| # | Bài học |
|---|---------|
| 1 | `FALL_CONFIRM_COUNT = 2` không hoạt động vì window sau ngã thật trả `fall_prob=0` |
| 2 | Model Balanced V2 có FAR=16.73% — nhiều false positive hơn V50 (14.18%) |
| 3 | Ngưỡng model 0.40 (khuyến nghị gốc) quá nhạy cho môi trường thực tế |
| 4 | "Đặt tay nhẹ xuống" có signature giống ngã: chuyển động → im — cần impact gyro check |
| 5 | Stillness duration 5s hiệu quả phân biệt ngã thật vs va chạm nhất thời |
| 6 | STILLNESS_GYRO_MAX = 15 dps quá chặt (gyro vẫn ~46 dps ngay sau ngã) |
