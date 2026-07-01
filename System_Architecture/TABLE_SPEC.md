# TABLE_SPEC — Bảng tổng hợp toàn bộ chỉ tiêu kỹ thuật (CaraFall / AIFD)

> Bảng liệt kê **mọi chỉ tiêu** của dự án theo định dạng: **Chỉ tiêu ban đầu → Hiện trạng → Đã đạt chưa → Note**.
> Đồng bộ với [MASTER_SPECIFICATION.md](MASTER_SPECIFICATION.md). Số liệu truy vết về mã nguồn (commit `dien-zinex`, 2026-06-08).

**Chú thích cột "Đạt?" — trạng thái đáp ứng chỉ tiêu:**

| Ký hiệu | Ý nghĩa | Diễn giải |
|:--:|---|---|
| ✅ | **Đạt** | Đáp ứng đầy đủ chỉ tiêu, có bằng chứng xác thực (test PASS / đo đạc / mã nguồn). |
| 🟡 | **Đạt một phần** | Đáp ứng phần lớn nhưng còn điểm chưa trọn vẹn, còn phụ thuộc, hoặc còn 1 lỗi nhỏ. |
| 🔴 | **Chưa đạt** | Còn khoảng cách lớn so với chỉ tiêu → cần xử lý ưu tiên (xem §12 MASTER). |
| ⬜ | **Chưa đánh giá** | Chưa đo / chưa chạy test nên chưa đủ căn cứ kết luận. |
| ➖ | **Không áp dụng** | Dòng mang tính mô tả/tham khảo, không phải chỉ tiêu cần "đạt". |

---

## A. Chỉ tiêu cấp hệ thống (System-level)

| # | Đề mục | Chỉ tiêu ban đầu (M1) | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| A1 | Độ chính xác phát hiện ngã | Accuracy ≥ 95% | Acc 93.10%, Recall 98.51%, F1 93.45% | 🟡 | Recall vượt mong đợi (bỏ sót 1.49%); Accuracy dưới 95%. Ưu tiên Recall là đúng cho thiết bị y tế. |
| A2 | Độ trễ phát hiện (edge) | < 2 s | 1 cửa sổ = 2.0 s + inference (~vài chục ms) | ✅ | Mỗi lần suy luận trên cửa sổ 2 s liền kề. |
| A3 | Độ trễ End-to-End (ngã→chuông) | < 30 s | 15 s đếm ngược + vài giây gọi | ✅ | `AT_EMG_04` PASS. |
| A4 | Sai số nhịp tim (HR) | ±2 BPM | **Đang giả lập** (`esp_random`) | 🔴 | Chưa tích hợp driver PPG thật — không nghiệm thu được. |
| A5 | Sai số SpO2 | ±3% | **Đang giả lập** | 🔴 | Như A4. |
| A6 | Gọi cứu hộ khẩn cấp | Tức thì < 3 s sau countdown | TelecomManager + fallback ACTION_DIAL | ✅ | `IT_EMERGENCY_CALL` 7/7 PASS. |
| A7 | Tuổi thọ pin | > 6 ngày | ~17 h (mô phỏng, pin 1000 mAh) | 🔴 | Khoảng cách lớn. Cần light-sleep (→ ~44.5 h). Xem R1. |
| A8 | Khả năng mở rộng | > 100 users | MongoDB Atlas + auth đa vai trò | ✅ | Kiến trúc hỗ trợ; chưa load-test thực. |
| A9 | Cân nặng thiết bị | ≤ 70 g | Phụ thuộc cơ khí/vỏ | ⬜ | Chưa cân đo. |
| A10 | Chi phí BOM | < 2.500.000 đ | Phụ thuộc linh kiện | ⬜ | Chưa chốt BOM. |

---

## B. Phần cứng & MCU (Module M1)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| B1 | Vi điều khiển | ESP32-S3 Mini, dual-core 240 MHz | ESP32-S3 (board `esp32-s3-devkitm-1`), 240 MHz | ✅ | |
| B2 | Flash | đủ chứa model + app | 4 MB; firmware V2 dùng **64.2%** (841,873 B) | ✅ | Còn dư ~35% flash. |
| B3 | RAM | đủ cho TFLite arena | dùng **31.6%** (103,704 / 327,680 B) | ✅ | Arena TFLite 60 KB. |
| B4 | IMU | BMI160 6 trục, 50 Hz | BMI160, ODR 100 Hz, lấy mẫu 50 Hz | ✅ | |
| B5 | Dải đo gyro | ±2000 dps | ±2000 dps (`REG_GYR_RANGE=0x00`) | ✅ | |
| B6 | Dải đo accel | ±16 g (spec cũ) | **±2 g** (`REG_ACC_RANGE=0x03`, 16384 LSB/g) | 🔴 | Mâu thuẫn ngưỡng 7.5 g (vector max ~3.46 g). Xem R3 — cần xác minh/đổi ±16g. |
| B7 | Cảm biến sinh hiệu | MAX30102 HR/SpO2 | Có phần cứng; **dữ liệu đang giả lập** | 🟡 | Phần cứng OK (`UT_MAX_*` PASS); driver đo thật chưa nối vào pipeline. |
| B8 | Ngoại vi cảnh báo | LED + buzzer | WS2812 (GPIO5) + buzzer 2300 Hz (GPIO7) | ✅ | |
| B9 | Nút tương tác | nút SAFE/SOS | nút GPIO10 pull-up, ngắt FALLING | ✅ | |

---

## C. Firmware & RTOS (Module M2)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| C1 | Tần số lấy mẫu | 50 Hz | `SAMPLE_PERIOD_MS=20` (50 Hz) | ✅ | |
| C2 | Cửa sổ AI | 100 mẫu = 2 s | `kWindowSize=100` | ✅ | |
| C3 | Bước trượt cửa sổ (on-device) | **không overlap** | `kInferenceStride=100` → **KHÔNG overlap** | ✅ | Mỗi 2 s suy luận 1 lần. (Training dùng stride 50 để augmentation — tách rời.) |
| C4 | Kiến trúc RTOS | đa nhiệm thời gian thực | FreeRTOS: 6 task (Motion/HighRate/AI/BLE/Button/LED) | ✅ | Bản V2 adaptive. |
| C5 | Build firmware | biên dịch thành công | PlatformIO **[SUCCESS]** | ✅ | Xác minh khi rà soát. |
| C6 | Tối ưu điện năng | idle không chạy full 50 Hz | V2: 10 Hz idle → 50 Hz khi có motion; LED off khi idle | 🟡 | Đã adaptive nhưng **chưa light-sleep** → idle ~50 mA. Xem R1. |
| C7 | Pipeline an toàn | giữ nguyên logic phát hiện | Gates + TFLite + FSM giữ **byte-for-byte** giữa V1↔V2 | ✅ | |

---

## D. Mô hình AI (Module M3)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng (V84) | Đạt? | Note |
|---|---|---|---|:--:|---|
| D1 | Model production | TinyCNN ≤ ~64 KB | **V84** [32,64,64,96]/K3/D32, INT8, **62.09 KB** | ✅ | 63,576 bytes — fit ESP32-S3. |
| D2 | Recall (độ nhạy) | càng cao càng tốt (ưu tiên) | **98.51%** | ✅ | Top 3 trong 90 phiên bản. |
| D3 | F1-score | — | **93.45%** | ✅ | Cao nhất trong 90 phiên bản. |
| D4 | FAR (báo nhầm) | < 10% (M3, Slide 21) | model 12.31%; pipeline gate hạ thấp thực tế | 🟡 | Model thuần 12.31%; cascade gates + FSM giảm FAR thực địa (`AT_ADL_REJECT` 5/5 PASS). |
| D5 | Ngưỡng quyết định | tối ưu Recall/FAR | **0.42** | ✅ | `FALL_DECISION_THRESHOLD`. |
| D6 | Lượng tử hóa | INT8 cho MCU | Post-training INT8 | ✅ | |
| D7 | Dataset | cân bằng Fall:ADL | 1:1 — 1,628/1,628 (3,256 cửa sổ), 50 Hz | ✅ | Nguồn HR_IMU (SisFall-style F01–F08 / D01–D11). |
| D8 | Chống overfit | regularization | Gaussian noise σ=0.05 + Dropout 0.4 + L2 3e-4, dừng epoch 78 | ✅ | Train/val loss gap 0.019. |
| D9 | Số phiên bản thử nghiệm | — | **90 (V1→V90)** | ➖ | Có quy trình chọn định lượng (`model_selection_V84.md`). |

---

## E. BLE Communication (Module M4)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| E1 | Chuẩn không dây | BLE 5.0 | BLE (NimBLE-Arduino) | ✅ | |
| E2 | MTU | 247 bytes (spec cũ) | App yêu cầu **512** (`requestMtu(512)`) | ✅ | Payload max ~140 B << MTU → không phân mảnh. |
| E3 | Tầm phủ | 10–15 m (indoor) | Ổn định gần; **drop xuyên tường 8 m** | 🟡 | `IT_BLE_05` **FAIL** (RSSI −82 dBm, packet loss). |
| E4 | Cấu trúc GATT | 1 service + char riêng | 1 service + ALERT/VITALS/CONTROL | ✅ | UUID cố định. |
| E5 | Gói tin | ALERT/SAFE/BATCH/BMI | Đúng 4 loại, CSV UTF-8 | ✅ | `BlePacketParser` unit-tested. |
| E6 | Handshake | READY trước khi stream | READY → ACK:READY → flush FIFO | ✅ | Queue offline trong RAM. |
| E7 | Độ trễ truyền | conn. interval 20–45 ms | theo NimBLE default | ✅ | Update delay < 500 ms (`UT_APP`). |
| E8 | Tên quảng bá | thống nhất | firmware = `S3_AIFD_V1`; test plan ghi `ESP32-fall-detection-BLE` | 🟡 | Cần thống nhất 1 tên (D5 trong master). |

---

## F. Android App (Module M5)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| F1 | Nền tảng | Android 10+ | minSdk **26** (8.0), target/compile **34** | ✅ | Hỗ trợ rộng hơn yêu cầu. |
| F2 | Ngôn ngữ/UI | Kotlin | Kotlin + Jetpack Compose | ✅ | |
| F3 | Hiển thị vitals | HR/SpO2, refresh ≥ 0.2 Hz | BATCH mỗi 25 s, cập nhật UI | ✅ | (HR/SpO2 đang giả lập — xem A4/A5.) |
| F4 | Trạng thái FALL/NON-FALL | update < 500 ms | FallAlertScreen ≤ ~2 s sau ALERT | ✅ | `IT_EDGE_01` PASS. |
| F5 | Chạy nền liên tục | service bất tử | `BleForegroundService` (connectedDevice) | ✅ | Vượt Doze (`IT_EMG_04`). |
| F6 | Gọi điện khẩn cấp | mọi trạng thái máy | 7 ngữ cảnh PASS | ✅ | Khóa màn hình, DND, đang gọi… |
| F7 | Đa vai trò | WEARER/CAREGIVER | Có, routing theo role | ✅ | |
| F8 | Auto-reconnect BLE | < 60 s không thao tác | backoff 2/5/10/20/60 s + watchdog 12 s | ✅ | `IT_BLE_04` PASS. |
| F9 | Hủy cảnh báo | nút "Tôi ổn" + nút cứng | Đếm ngược 15 s, hủy 2 đường | ✅ | App `dismissAsSafe` + gói SAFE. |

---

## G. Cloud & Database (Module M6)

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| G1 | Nền tảng backend | (spec cũ: ThingsBoard/MQTT) | **Flask REST + MongoDB Atlas** (Render) | ✅ | **KHÔNG dùng ThingsBoard.** Đã sửa tài liệu. |
| G2 | Giao thức | — | HTTP/JSON (OkHttp) | ✅ | |
| G3 | Lưu trữ | NoSQL document | MongoDB: `users/vitals/fall_events/sensor_readings_new` | ✅ | |
| G4 | Xác thực | đăng nhập đa vai trò | `/api/auth/*` (register/login/profile/password) | ✅ | `UT_CLOUD` 4/4 PASS. |
| G5 | Push notification | caregiver từ xa | Firebase Cloud Messaging (FCM) | ✅ | Token lưu qua `/api/auth/fcm-token`. |
| G6 | Đồng bộ offline | không mất sự kiện | cache local → sync khi online | ✅ | `IT_OFFLINE_FIRST` 3/3 PASS. |
| G7 | Toàn vẹn dữ liệu | write ack | insert MongoDB trả `ok=true` | ✅ | `IT_CLOUD_01/02` PASS. |

---

## H. Kỹ thuật cốt lõi (Techniques)

| # | Đề mục | Mục tiêu kỹ thuật | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| H1 | Sliding window | cấp dữ liệu 2 s cho AI | 100 mẫu, **không overlap** (stride 100) | ✅ | Xem C3. |
| H2 | Cascade multi-gate | lọc trước AI, giảm FAR + điện | candidate → activity(3) → high-impact → impact → AI window 6 s | ✅ | TFLite chỉ chạy khi pass hết gate. |
| H3 | INT8 quantization | thu nhỏ model cho MCU | 62.09 KB, arena 60 KB | ✅ | |
| H4 | Fall FSM (xác nhận) | chống báo nhầm | FALL_WATCH (5 cửa sổ) → STILL_TIMING (nằm im 5 s / theo dõi 10 s) | ✅ | Ngưỡng hủy riêng 3.5g/150dps. |
| H5 | Adaptive RTOS power | không chạy full khi idle | 10 Hz idle, 50 Hz khi motion | 🟡 | Chưa light-sleep (R1). |
| H6 | READY handshake + queue | không mất gói khi app chưa sẵn sàng | queue RAM → flush FIFO sau READY | ✅ | |
| H7 | GATT 133 recovery | kết nối ổn định sau reflash | `deleteAllBonds()` + `removeBond()` khi 133 | ✅ | Ghi trong memory dự án. |
| H8 | Offline-first emergency | cứu hộ không cần net | toàn bộ ngã→gọi qua BLE | ✅ | `IT_OFFLINE_FIRST` PASS. |
| H9 | 15s countdown + dual SAFE | người già hủy dễ | app + nút cứng | ✅ | |
| H10 | In-model Z-score norm | ổn định input INT8 | lớp Normalization (13 params) | ✅ | Không cần buffer thống kê runtime. |

---

## I. Kiểm thử (Test) — tham chiếu

| # | Đề mục | Chỉ tiêu ban đầu | Hiện trạng | Đạt? | Note |
|---|---|---|---|:--:|---|
| I1 | Unit tests | pass toàn bộ | 28/28 PASS | ✅ | 7 bộ module. |
| I2 | Integrated tests | pass toàn bộ | 26/27 PASS, **1 FAIL** | 🟡 | `IT_BLE_05` (xuyên tường 8 m). |
| I3 | Acceptance — ADL Rejection | FAR ≤ 10% | 5/5 PASS (06-03→04) | ✅ | |
| I4 | Acceptance — Emergency | mọi trạng thái | 4/4 PASS (06-04→05) | ✅ | |
| I5 | Acceptance — Edge Cases | điều kiện thực tế | 5/5 PASS (06-04→05) | ✅ | |
| I6 | Acceptance — Fall Detection | 5 kiểu ngã | Pending | ⬜ | Chưa chạy. |
| I7 | Acceptance — Continuous | 8 h liên tục | Pending | ⬜ | Chưa chạy. |
| **—** | **Tổng** | 78 scenarios | **69 executed — 68 PASS, 1 FAIL** | 🟡 | Còn 9 scenario pending. |

---

> **Tổng quan trạng thái:** Phần lõi an toàn (phát hiện ngã, gọi cứu hộ, offline-first) **đạt**. Các điểm 🔴 cần ưu tiên: **tuổi thọ pin (A7), HR/SpO2 thật (A4/A5), dải đo accel (B6)** — chi tiết & khuyến nghị tại §12 của [MASTER_SPECIFICATION.md](MASTER_SPECIFICATION.md).
