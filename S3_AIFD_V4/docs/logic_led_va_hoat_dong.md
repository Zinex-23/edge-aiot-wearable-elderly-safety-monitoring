# S3_AIFD_V1 — Logic Đèn LED & Logic Hoạt Động

> Tài liệu này mô tả chi tiết logic vận hành của firmware `S3_AIFD_V1` dựa trên phân tích `src/main.cpp`
> và tài liệu `how-to-use-model-on-esp32s3.md`.

---

## 1. Tổng quan phần cứng liên quan

| GPIO | Chức năng |
|------|-----------|
| `GPIO 4` (`PIN_LED_VCC`) | Cấp nguồn cho module RGB WS2812 (kéo HIGH khi boot) |
| `GPIO 5` (`PIN_LED_DI`) | Data line WS2812 (NeoPixel) |
| `GPIO 7` (`PIN_BUZZER`) | Còi báo động (PWM 2300 Hz) |
| `GPIO 10` (`PIN_BUTTON`) | Nút nhấn (INPUT\_PULLUP, active-LOW) |
| `GPIO 8/9` (`SDA/SCL`) | I2C — kết nối BMI160 và MAX30102 |

---

## 2. Logic Đèn LED (State Machine)

### 2.1 Sáu trạng thái LED

```
LED_BOOT        → LED_ADVERTISING → LED_CONNECTED
                                 ↓          ↓
                            LED_WARNING  LED_FALL_WATCH
                                              ↓
                                          LED_ALARM
```

### 2.2 Bảng mô tả chi tiết

| Tên Trạng Thái | Màu | Kiểu nhấp nháy | Còi | Điều kiện kích hoạt |
|----------------|-----|----------------|-----|---------------------|
| `LED_BOOT` | 🔵 Xanh dương | Nhấp nháy chậm (500ms) | Tắt | Thiết bị vừa khởi động, đang `setup()` |
| `LED_ADVERTISING` | 🟡 Vàng | Nhấp nháy chậm (500ms)* | Tắt | BLE đang quảng bá, chưa kết nối |
| `LED_CONNECTED` | 🟢 Xanh lá | **Sáng tĩnh** (không nhấp nháy)* | Tắt | BLE đã kết nối, handshake READY xong |
| `LED_WARNING` | 🟡 Vàng | Nhấp nháy nhanh (250ms) | Tắt | Mất kết nối BLE hoặc lỗi cảm biến |
| `LED_FALL_WATCH` | 🔴 Đỏ | Nhấp nháy chậm (500ms) | Tắt | AI phát hiện fall candidate, đang theo dõi |
| `LED_ALARM` | 🔴 Đỏ | Nhấp nháy nhanh (250ms) | **BẬT** (2300Hz) | Ngã được xác nhận hoàn toàn |

> **\* Ghi chú đặc biệt — `gWearerActive` gate:**
> `LED_ADVERTISING` và `LED_CONNECTED` **chỉ sáng/nhấp nháy khi `gWearerActive = true`**.
> Nếu người đeo chưa tích lũy đủ `ACTIVITY_WINDOW_COUNT = 1` window active, LED ở hai trạng thái này
> sẽ **tắt hoàn toàn** để tránh báo hiệu nhầm khi thiết bị chưa thực sự được đeo.

### 2.3 Sơ đồ chuyển trạng thái LED

```
[BOOT] ──setup() xong──►
  ├── BMI160 hoặc Model lỗi ──► [WARNING] (vĩnh viễn, phải reboot)
  └── OK ──────────────────────► [ADVERTISING]
                                      │
              BLE client kết nối ────►│
                                   [CONNECTED]
                                      │
              BLE mất kết nối ───────►│
                                   [WARNING] (tự động trở về [ADVERTISING] sau 3 giây)
                                      │
              AI phát hiện fall ─────►│
                                   [FALL_WATCH]
                                      │
              Xác nhận ngã ──────────►│
                                   [ALARM] ◄── còi 2300Hz bật
                                      │
              Nhấn nút (SAFE) ────────►[CONNECTED] hoặc [ADVERTISING]
```

### 2.4 Quy tắc độ ưu tiên LED

Khi `gFallAlertActive = true` (alarm đang hoạt động), các sự kiện BLE connect/disconnect **không được phép** đổi LED. Chỉ khi alarm được tắt (nhấn nút) thì LED mới chuyển về trạng thái BLE.

---

## 3. Logic Hoạt Động Tổng Thể (Pipeline)

### 3.1 Luồng khởi động (`setup()`)

```
setup()
  │
  ├── GPIO init (LED VCC HIGH, Button PULLUP, Buzzer LOW)
  ├── NeoPixel init → applyLedState(LED_BOOT) → đèn xanh nhấp nháy
  ├── I2C init (100kHz, SDA=8, SCL=9)
  ├── BMI160 init → tự dò địa chỉ 0x68 / 0x69
  │     ACC: ±8g @100Hz | GYRO: ±2000dps @100Hz
  ├── MAX30102 init (HR/SpO2 — hiện tại chỉ đọc IR để xác nhận ngón tay)
  ├── TFLite Model init (fall_detection_v84.h, arena 60KB)
  ├── FreeRTOS:
  │     ├── Task IMU_SAMPLE  → Core 0, Priority MAX-1, Stack 4KB
  │     └── Task AI_INFER   → Core 1, Priority 1,     Stack 8KB
  ├── BLE init:
  │     ├── Device name: "S3_AIFD_V1"
  │     ├── deleteAllBonds() — xóa bond cũ tránh lỗi sau reflash
  │     ├── Service UUID: 4fafc201-...
  │     ├── CharAlert  (NOTIFY) — gửi ALERT / SAFE
  │     ├── CharVitals (NOTIFY) — gửi BATCH / BMI
  │     └── CharControl (WRITE) — nhận READY / PING
  └── LED:
        ├── Nếu lỗi BMI hoặc Model → [WARNING] vĩnh viễn
        └── OK → [ADVERTISING]
```

### 3.2 Hai FreeRTOS Task song song

#### Task 1: `IMU_SAMPLE` (Core 0, cao nhất)

```
Chạy mỗi 20ms (50Hz)
  │
  ├── Đọc BMI160 qua I2C → ImuSample {ax,ay,az,gx,gy,gz,tsMs}
  │     ax/ay/az: chia 16384.0 → đơn vị g
  │     gx/gy/gz: chia 16.4   → đơn vị deg/s
  │
  ├── Lấy mutex → pushSample() vào ring buffer kWindowSize=100
  │
  ├── Kiểm tra: windowCount >= 100 AND samplesSinceInference >= 100
  │     └── Nếu đủ → xTaskNotifyGive(gInferenceTask)
  │
  └── Nhả mutex
```

#### Task 2: `AI_INFER` (Core 1)

```
Chờ notify từ IMU_SAMPLE
  │
  ├── Nếu gFallAlertActive = true → bỏ qua (alarm đang kêu, không inference)
  │
  ├── Lấy mutex → snapshotWindow() copy 100 mẫu mới nhất → nhả mutex
  │
  ├── runInferenceOnSnapshot():
  │     ├── Tính maxAcc = max(|A| trong 100 mẫu)  — A = sqrt(ax²+ay²+az²)
  │     ├── Tính maxGyr = max(|G| trong 100 mẫu)  — G = sqrt(gx²+gy²+gz²)
  │     │
  │     ├── [CANDIDATE GATE]
  │     │     candidateActive = maxAcc > 7.5g OR maxGyro > 240dps
  │     │
  │     ├── [ACTIVITY GATE]
  │     │     activityActive = maxAcc > 2.0g OR maxGyro > 50dps
  │     │     ├── Nếu active: activityCount++ (tối đa 1), idleCount = 0
  │     │     └── Nếu idle:   idleCount++ → nếu >= 3: reset activityCount & highImpactSeen
  │     │
  │     ├── gWearerActive = (activityCount >= 1)  ← gate LED
  │     │
  │     ├── Nếu !candidateActive OR activityCount < 1 → trả về (fallProb=0, skip AI)
  │     │
  │     ├── [HIGH IMPACT GATE]
  │     │     highImpactSeen |= (maxAcc > 2.0g AND maxGyro > 300dps)
  │     │     Nếu !highImpactSeen → skip AI
  │     │
  │     ├── [IMPACT GYRO GATE]
  │     │     Nếu maxGyro < 20dps → skip AI (không đủ xoay)
  │     │
  │     ├── [AI WINDOW]
  │     │     Mở cửa sổ 6 giây kể từ khi peak đầu tiên pass tất cả gate
  │     │     Nếu đã quá 6s → đóng cửa sổ, reset highImpactSeen, skip AI
  │     │
  │     └── [TFLite Inference]
  │           ├── Quantize 100×6 float → int8 (scale từ tensor params)
  │           ├── Invoke model
  │           └── Dequantize output → fallProb [0.0, 1.0]
  │
  ├── checkStillness(): kiểm tra 25 mẫu cuối xem người có nằm im không
  │     stillness = STILLNESS_ACC_MIN(0.6g) ≤ mean_acc ≤ STILLNESS_ACC_MAX(1.7g)
  │                 AND mean_gyro ≤ STILLNESS_GYRO_MAX(100dps)
  │
  └── updateFallStateMachine(fallProb, stillnessNow, ...)
```

### 3.3 Fall Detection State Machine (FSM)

```
                ┌───────────────────────────────────────────────────┐
                │                    FDS_IDLE                       │
                │  LED: ADVERTISING / CONNECTED                     │
                └───────────────┬───────────────────────────────────┘
                                │ fallProb >= 0.42 AND stillnessNow = true
                                ▼
                ┌───────────────────────────────────────────────────┐
                │                 FDS_FALL_WATCH                    │
                │  LED: FALL_WATCH (đỏ nhấp nháy chậm)             │
                │  fallWatchLeft = FALL_WATCH_WINDOWS-1 = 4         │
                └──────┬────────────────────────┬───────────────────┘
                       │                        │
         cancelActive = true                fallWatchLeft > 0:
         (peakAcc>3.5g OR                  fallWatchLeft--
          peakGyro>150dps)                 [tiếp tục theo dõi]
                       │                        │
                       ▼                fallWatchLeft == 0:
                  FDS_IDLE                      │
                (LED về BLE)                    ▼
                              ┌─────────────────────────────────────┐
                              │            FDS_STILL_TIMING         │
                              │  Theo dõi tối đa 10 giây           │
                              │  LED: vẫn FALL_WATCH               │
                              └──────────────┬──────────────────────┘
                                             │
                              ┌──────────────┼──────────────────────┐
                              │              │                      │
                     isMoving=true    nằm im liên tục        timeout 10s
                    (reset timer)     >= 5 giây              không đủ bằng chứng
                     [vẫn trong      → onFallConfirmed()        → FDS_IDLE
                    STILL_TIMING]              │
                                              ▼
                              ┌───────────────────────────────────────┐
                              │             LED_ALARM                 │
                              │  Đỏ nhấp nháy nhanh + Còi 2300Hz     │
                              │  Gửi BLE: ALERT,seq,ts,fall,1,prob   │
                              └───────────────┬───────────────────────┘
                                              │ Nhấn nút
                                              ▼
                              ┌───────────────────────────────────────┐
                              │  gFallAlertActive = false             │
                              │  fallDetectState = FDS_IDLE           │
                              │  Gửi BLE: SAFE,seq,ts                │
                              │  LED về CONNECTED / ADVERTISING       │
                              └───────────────────────────────────────┘
```

---

## 4. Logic Nút Nhấn (Button)

Nút được debounce 30ms, phát hiện cạnh xuống (LOW).

| Trạng thái hiện tại | Hành động khi nhấn |
|---------------------|---------------------|
| `gFallAlertActive = true` (ALARM đang kêu) | Tắt còi, gửi `SAFE,seq,ts`, trở về `FDS_IDLE`, LED về BLE |
| `gFallAlertActive = false` (bình thường) | Kích hoạt ngã thủ công (SOS/test): `LED_ALARM` + gửi `ALERT,...,1.000,0.000` |

---

## 5. Logic Giao tiếp BLE

### 5.1 Handshake

```
App Android kết nối
  → gBleConnected = true, gBleReady = false
  → LED → CONNECTED

App ghi "READY" vào CharControl
  → gBleReady = true
  → ACK: "ACK:READY"
  → Gửi ngay một gói BATCH vitals tức thì (sendInstantVitals)
```

### 5.2 Các gói BLE được gửi

| Packet | Characteristic | Tần suất | Format |
|--------|---------------|----------|--------|
| `BATCH` | CharVitals | Mỗi 25 giây + ngay sau READY | `BATCH,<seq>,<hr0\|...\|hr4>,<spo2_0\|...\|spo2_4>,<ts0\|...\|ts4>` |
| `BMI` | CharVitals | Mỗi 5 giây | `BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>` |
| `ALERT` | CharAlert | Khi xác nhận ngã / nhấn SOS | `ALERT,<seq>,<ts_sec>,fall,1,<fall_prob>,<non_fall_prob>` |
| `SAFE` | CharAlert | Khi nhấn nút sau alarm | `SAFE,<seq>,<ts_sec>` |

### 5.3 Xử lý ngắt kết nối

Khi BLE mất kết nối:
- Server tự gọi `startAdvertising()` lại
- LED → `LED_WARNING` (vàng nhấp nháy nhanh) trong **3 giây**
- Sau 3 giây → tự chuyển về `LED_ADVERTISING` (vàng nhấp nháy chậm)
- Nếu đang alarm (`gFallAlertActive`) → LED **không bị đổi** cho đến khi alarm được giải quyết

---

## 6. Logic Vitals (HR/SpO2)

Hiện tại là **simulated** vì MAX30102 chỉ đọc IR để detect ngón tay:
- Nếu `irValue >= 50000` (có ngón tay): trả giá trị random HR 65–90 bpm, SpO2 93–99%
- Nếu không có ngón tay: trả `255` (invalid)
- App nhận `255` hiển thị dấu `--`

---

## 7. Tóm tắt các ngưỡng quan trọng

| Tên hằng số | Giá trị | Ý nghĩa |
|-------------|---------|---------|
| `FALL_DECISION_THRESHOLD` | 0.42 | Score fall >= 0.42 → xem là fall |
| `CANDIDATE_ACC_THRESHOLD` | 7.5 g | Ngưỡng gia tốc để vào candidate gate |
| `CANDIDATE_GYRO_THRESHOLD` | 240 dps | Ngưỡng con quay để vào candidate gate |
| `ACTIVITY_ACC_THRESHOLD` | 2.0 g | Ngưỡng activity bình thường |
| `ACTIVITY_GYRO_THRESHOLD` | 50 dps | Ngưỡng activity bình thường |
| `CANCEL_ACC_THRESHOLD` | 3.5 g | Ngưỡng huỷ FALL_WATCH (đủ mạnh để biết người vẫn ổn) |
| `CANCEL_GYRO_THRESHOLD` | 150 dps | Ngưỡng huỷ FALL_WATCH |
| `HIGH_IMPACT_ACC_MIN` | 2.0 g | Tối thiểu gia tốc peak để tính là va chạm mạnh |
| `HIGH_IMPACT_GYRO_MIN` | 300 dps | Tối thiểu con quay peak để tính là va chạm mạnh |
| `FALL_IMPACT_GYRO_MIN` | 20 dps | Gyro tối thiểu trong window để không bị reject ngay |
| `ACTIVITY_WINDOW_COUNT` | 1 | Số window active tối thiểu để mở AI |
| `FALL_WATCH_WINDOWS` | 5 | Số window kiểm tra thêm sau khi AI phát hiện fall |
| `FALL_STILL_DURATION_MS` | 5000 ms | Nằm im liên tục bao lâu để xác nhận ngã |
| `FALL_MONITOR_TIMEOUT_MS` | 10000 ms | Timeout tổng của STILL_TIMING |
| `AI_WINDOW_DURATION_MS` | 6000 ms | AI chỉ chạy trong 6s kể từ peak event |
| `STILLNESS_SAMPLES` | 25 | Số mẫu cuối dùng kiểm tra stillness |
| `SAMPLE_PERIOD_MS` | 20 ms | Tần suất lấy mẫu = 50Hz |
| `kWindowSize` | 100 | Số mẫu mỗi window = 2 giây |

---

## 8. Kiến trúc đa nhiệm tổng hợp

```
Core 0                          Core 1
────────────────────────────    ─────────────────────────────────
IMU_SAMPLE task (pri=MAX-1)     AI_INFER task (pri=1)
  └── đọc BMI160 mỗi 20ms         └── chờ notify
      push ring buffer                snapshot 100 mẫu
      notify AI_INFER                 chạy gate + TFLite
                                      cập nhật FSM
                                      cập nhật gWearerActive

                  loop() - Arduino main thread
                    handleButton()       ← debounce nút
                    handleBlink()        ← cập nhật LED mỗi chu kỳ
                    handleVitalsBatch()  ← gửi HR/SpO2 mỗi 25s
                    handleBmiSnapshot()  ← gửi IMU peak mỗi 5s
                    handleMaxDebug()     ← log IR value mỗi 5s
                    BLE connect/disconnect event handling
```

---

*Tài liệu được tạo tự động từ phân tích `src/main.cpp` — S3_AIFD_V1*
