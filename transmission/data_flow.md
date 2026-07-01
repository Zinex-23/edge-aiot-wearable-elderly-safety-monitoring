# Luồng Dữ Liệu: ESP32 → Android App

## Tổng quan kiến trúc

```
[BMI160] ──I2C──┐
                ├──► [ESP32-S3] ──BLE 5.0──► [Android App]
[MAX30102] ──I2C──┘
```

---

## 1. Phía Thiết Bị Biên (ESP32 Firmware)

### 1.1 Thu thập dữ liệu IMU — 50 Hz (mỗi 20ms)

```
Loop (mỗi 20ms):
  readImuSample(BMI160)
    → ax, ay, az  [đơn vị: g,  LSB/g = 16384]
    → gx, gy, gz  [đơn vị: dps, LSB/dps = 16.4]
  pushImuSample() → circular buffer (100 mẫu)
  maybeSampleVitals()      ← mỗi 5 giây
  maybeDispatchVitalsBatch() ← mỗi 25 giây
  feedBleImuStream()       ← mỗi 5 mẫu (100ms)
```

### 1.2 Thu thập sinh hiệu (MAX30102)

| Tần suất lấy mẫu | Tần suất gửi BLE |
|---|---|
| Mỗi 5 giây (1 mẫu) | Mỗi 25 giây (1 batch = 5 mẫu) |

- Giá trị hợp lệ: HR (nhịp tim), SpO2 (0–100)
- Giá trị không hợp lệ (không đặt ngón tay): `255`

### 1.3 Pipeline AI — Phát hiện té ngã

```
Mỗi 100 mẫu IMU (= 2 giây):
  │
  ▼
[Candidate Filter]
  maxAccMag > 1.8g  OR  maxGyroMag > 50 dps?
  │ KHÔNG → fallProb = 0.0, bỏ qua inference (tiết kiệm điện)
  │ CÓ   ↓
  ▼
[Quantize Input]
  (100, 6) float32 → (100, 6) INT8
  quantized = round(value / scale) + zero_point
  │
  ▼
[TFLite Micro Invoke — TinyCNN]
  Input:  tensor shape [1, 100, 6]  (INT8)
  Output: tensor shape [1, 1] hoặc [1, 2]  (INT8)
  │
  ▼
[Dequantize Output]
  fallProb = (output[0] - zero_point) × scale  ∈ [0.0, 1.0]
  │
  ▼
[Threshold Decision]
  fallProb >= 0.40f?
  │ KHÔNG → không làm gì
  │ CÓ   ↓
  ▼
[Tạo FallAlertPacket]
  → queueOrSendFallAlert()
```

---

## 2. Giao thức BLE GATT

### 2.1 Service & Characteristics

| Characteristic | UUID | Mode | Dữ liệu |
|---|---|---|---|
| **STATUS** | `beb5483e-...` | READ + NOTIFY | Cảnh báo té ngã |
| **VITALS** | `7b809f11-...` | READ + NOTIFY | Batch sinh hiệu |
| **IMU** | `6d3b70a9-...` | READ + NOTIFY | Raw IMU stream (chưa dùng ở app) |
| **CONTROL** | `f9b2c417-...` | READ + WRITE | Handshake lệnh |

Service UUID: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`

### 2.2 Trình tự kết nối (Handshake)

```
ESP32                              Android App
  │                                     │
  │◄──────── BLE Scan (bonded) ─────────│  (tìm thiết bị tên "ESP32...")
  │                                     │
  │◄──────── CONNECT ───────────────────│
  │  onConnect(): bleClientReady=false  │
  │                                     │
  │◄── Enable CCCD (STATUS notify) ─────│  writeDescriptor()
  │◄── Enable CCCD (VITALS notify) ─────│  writeDescriptor()  [queue tuần tự]
  │                                     │
  │◄── WRITE "READY" (CONTROL char) ────│  sendReadyCommand()
  │  bleClientReady = true              │
  │  flushBleBacklog()                  │  (gửi dữ liệu tích lũy khi offline)
  │                                     │
  │──► NOTIFY (STATUS/VITALS) ──────────►│  onCharacteristicChanged()
```

### 2.3 Hàng đợi offline (Queue/Backlog)

| Queue | Sức chứa | Mục đích |
|---|---|---|
| `fallQueue` | 16 packet | Lưu cảnh báo té ngã khi BLE chưa kết nối |
| `vitalsQueue` | 32 packet | Lưu batch sinh hiệu khi BLE chưa kết nối |

Khi app gửi "READY" → ESP32 gọi `flushBleBacklog()` → gửi toàn bộ dữ liệu tích lũy.

---

## 3. Định dạng Payload (CSV Text)

### 3.1 ALERT payload — Kênh STATUS (`beb5483e`)

```
ALERT,<seq>,<timestamp_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
```

**Ví dụ:**
```
ALERT,1,1776729742,fall,1,0.873,0.127
```

| Field | Kiểu | Mô tả |
|---|---|---|
| `seq` | Int | Số thứ tự tăng dần |
| `timestamp_sec` | Long | SIMULATED_EPOCH_BASE + millis/1000 |
| `"fall"` | String | **Hardcoded** — ESP32 chỉ gửi khi đã quyết định té |
| `status_code` | Int | Luôn là `1` khi có cảnh báo |
| `fall_prob` | Float (3 chữ số) | Xác suất ngã ∈ [0.40, 1.00] |
| `non_fall_prob` | Float (3 chữ số) | = 1 - fall_prob |

**Giá trị khởi tạo (trước khi kết nối):**
```
ALERT,0,0,idle,0,0.000,1.000
```

---

### 3.2 BATCH payload — Kênh VITALS (`7b809f11`)

```
BATCH,<seq>,<HR1>|<HR2>|<HR3>|<HR4>|<HR5>,<SPO2_1>|...|<SPO2_5>,<TS1>|...|<TS5>
```

**Ví dụ:**
```
BATCH,5,72|74|75|73|71,98|97|98|97|96,1776729600|1776729605|1776729610|1776729615|1776729620
```

| Field | Kiểu | Mô tả |
|---|---|---|
| `seq` | Int | Số thứ tự tăng dần |
| `HR1..HR5` | Int | Nhịp tim (bpm). `255` = không hợp lệ |
| `SPO2_1..5` | Int | SpO2 (%). `255` = không hợp lệ |
| `TS1..TS5` | Long | Timestamp từng mẫu (giây) |

- Batch được gửi **mỗi 25 giây** (5 mẫu × 5 giây/mẫu)
- App map `255` → `0` khi hiển thị

**Giá trị khởi tạo:**
```
BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0
```

---

### 3.3 IMU5 payload — Kênh IMU (`6d3b70a9`)

```
IMU5|<ts>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>|<ts>,<ax>,...  (5 mẫu)
```

**Ví dụ:**
```
IMU5|1234,0.0123,-0.0045,1.0012,0.12,-0.23,0.05|1254,...
```

> ⚠️ **Hiện tại app KHÔNG subscribe kênh IMU** — ESP32 gửi nhưng app không nhận. Kênh này dành cho dashboard/debug sau này.

---

## 4. Phía Android App

### 4.1 Luồng dữ liệu trong app

```
BleManager.onCharacteristicChanged()
    │
    ├─► STATUS char ──► parseAlertPayload()
    │                       │
    │                       ▼ (prediction=="fall" && fallProb >= 0.40f)
    │                   _fallDetected.tryEmit(FallStatus)
    │                       │
    │                       ▼
    │                   vibrateDevice() + playAlertSound()
    │                       │
    │                       ▼ (collect trong BleForegroundService)
    │                   handleFallDetected()
    │                       ├─ acquireWakeLock (60s)
    │                       ├─ startActivity(ACTION_FALL_DETECTED)
    │                       └─ startEmergencyCountdown (15 giây)
    │                               │ hết giờ → placeEmergencyCall()
    │                               │ hoặc user nhấn "I'm Safe" → cancel
    │
    └─► VITALS char ──► parseVitalsPayload()
                            │
                            ├─ _vitalsBatch.tryEmit(VitalsBatch)   → MonitoringScreen
                            └─ _sensorData.value = SensorData(HR, SpO2) → HomeScreen
```

### 4.2 Threshold app vs firmware

| Vị trí | Giá trị | Tác động |
|---|---|---|
| Firmware (`FALL_DECISION_THRESHOLD`) | `0.40f` | Quyết định **có gửi ALERT hay không** |
| App (`parseAlertPayload`) | `>= 0.40f` | **Redundant** — vì payload đã là "fall" khi firmware gửi |

> Điểm không nhất quán: App kiểm tra lại threshold dù firmware đã lọc trước. Nếu muốn app có thể **tự điều chỉnh sensitivity** độc lập với firmware thì nên giữ và làm nó configurable. Nếu không cần, có thể bỏ check `fallProb >= 0.40f` ở app.

### 4.3 Timestamp không đồng bộ

ESP32 không có RTC (Real-Time Clock). Timestamp trong ALERT và BATCH được tính bằng:

```cpp
SIMULATED_UNIX_EPOCH_BASE_UTC + millis() / 1000
// = 1776729600 + (seconds since boot)
// ≈ 2026-06-19 00:00:00 UTC làm gốc
```

→ Timestamp tăng đúng nhịp thực tế nhưng **không đồng bộ với giờ thực** nếu ESP32 bị reset.

---

## 5. Kiểm tra đồng bộ: Firmware vs App

| Điểm kiểm tra | Firmware | App | Đồng bộ? |
|---|---|---|---|
| Service UUID | `4fafc201-1fb5-459e-8fcc-c5c9c331914b` | `4fafc201-1fb5-459e-8fcc-c5c9c331914b` | ✅ |
| STATUS UUID | `beb5483e-36e1-4688-b7f5-ea07361b26a8` | `beb5483e-36e1-4688-b7f5-ea07361b26a8` | ✅ |
| VITALS UUID | `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` | `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` | ✅ |
| CONTROL UUID | `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` | `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` | ✅ |
| ALERT format | `"ALERT,seq,ts,fall,code,fProb,nfProb"` | Parse 7 fields split by `,` | ✅ |
| BATCH format | `"BATCH,seq,HR1\|...,SPO2\|...,TS\|..."` | Parse 5 fields, pipe-split values | ✅ |
| Handshake | Nhận `"READY"` → `bleClientReady=true` | Gửi `"READY"` sau khi subscribe xong | ✅ |
| Threshold | `0.40f` → quyết định gửi hay không | `>= 0.40f` → redundant check | ⚠️ Redundant |
| Fall prob khi app nhận | Luôn >= 0.40 (đã lọc) | Check lại >= 0.40 | ⚠️ Redundant |
| IMU characteristic | Gửi "IMU5" mỗi 100ms | Không subscribe | ⚠️ Chưa tích hợp |
| Invalid vital | Gửi `255` | Map `255` → `0` | ✅ |
| BLE device name | `"ESP32-fall-detection-BLE"` | Tìm tên bắt đầu bằng `"ESP32"` | ✅ |

---

## 6. Sơ đồ thời gian thực tế

```
t=0ms       t=20ms      t=40ms  ...  t=1980ms    t=2000ms
  │           │           │            │            │
  ▼           ▼           ▼            ▼            ▼
[sample1]  [sample2]  [sample3]  ...  [sample99] [sample100]
                                                    │
                                          windowFull=true
                                          samplesSinceInference >= 100
                                                    │
                                          [Candidate Filter]
                                                    │ pass
                                          [TFLite Invoke] ~10-20ms
                                                    │
                                          fallProb >= 0.40?
                                                    │ YES
                                          [BLE NOTIFY] → App ~1-5ms
                                                    │
                                          [App: 15s countdown]
                                                    │ (no response)
                                          [Emergency Call]
```

**Tổng latency từ ngã đến gửi BLE:** ~2 giây (window) + ~15ms (inference) + BLE latency ≈ **2.0–2.1 giây**
