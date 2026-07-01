# BLE Protocol — ESP32 ↔ Android App

> Tài liệu mô tả chính xác định dạng dữ liệu mà Android app nhận (và gửi) qua BLE GATT.  
> Nguồn: `BleManager.kt` — đọc trực tiếp từ parsing logic thực tế trong code.

---

## 1. Thông tin kết nối

| Thuộc tính | Giá trị |
|-----------|---------|
| **Service UUID** | `4fafc201-1fb5-459e-8fcc-c5c9c331914b` |
| **MTU yêu cầu** | 512 bytes (thực tế thiết bị có thể trả về ít hơn, ví dụ 255) |
| **Encoding** | UTF-8 |
| **Loại kết nối** | GATT Client (Android) ↔ GATT Server (ESP32) |
| **Chiến lược kết nối** | Auto-connect via bonded device (tên bắt đầu bằng `ESP32` hoặc `S3`) |

---

## 2. Các Characteristic

| Tên | UUID | Chiều | Loại |
|-----|------|-------|------|
| **STATUS** | `beb5483e-36e1-4688-b7f5-ea07361b26a8` | ESP32 → App | Notify |
| **VITALS** | `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` | ESP32 → App | Notify |
| **CONTROL** | `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` | App → ESP32 | Write |
| **CCCD** | `00002902-0000-1000-8000-00805f9b34fb` | App → ESP32 | Descriptor |

> **Thứ tự subscribe:** STATUS → VITALS (tuần tự, chờ `onDescriptorWrite` xong mới ghi tiếp)

---

## 3. STATUS Characteristic — Phát hiện ngã

### 3.1 Định dạng payload

```
ALERT,<seq>,<timestamp>,<prediction>,<status_code>,<fall_prob>,<non_fall_prob>
```

| Field | Index | Kiểu | Mô tả |
|-------|-------|------|-------|
| Header | `[0]` | String | Luôn là `"ALERT"` |
| `seq` | `[1]` | Int | Số thứ tự packet (tăng dần) |
| `timestamp` | `[2]` | Long | Unix timestamp (giây) |
| `prediction` | `[3]` | String | `"fall"` hoặc `"non_fall"` |
| `status_code` | `[4]` | Int | Mã trạng thái từ ESP32 |
| `fall_prob` | `[5]` | Float | Xác suất ngã (0.0 – 1.0) |
| `non_fall_prob` | `[6]` | Float | Xác suất không ngã (0.0 – 1.0) |

### 3.2 Ví dụ

```
ALERT,42,1747200000,fall,1,0.990,0.010
ALERT,43,1747200005,non_fall,0,0.032,0.968
```

### 3.3 Quy tắc xử lý trong app

```
Nhận payload
  ├── Tách bằng dấu ","
  ├── Kiểm tra: đúng 7 phần VÀ parts[0] == "ALERT"
  │     └── Sai → bỏ qua (không crash)
  └── Nếu parts[3] == "fall":
        ├── Emit FallStatus vào fallDetected flow
        ├── Lưu sự kiện vào SharedPreferences
        ├── Rung thiết bị (3 giây)
        └── Phát âm thanh SOS (ALARM stream, max volume)
```

### 3.4 Data class trong app

```kotlin
data class FallStatus(
    val sequence: Int,
    val timestampSec: Long,
    val prediction: String,   // "fall" | "non_fall"
    val statusCode: Int,
    val fallProb: Float,
    val nonFallProb: Float
)
```

---

## 4. VITALS Characteristic — Dữ liệu sinh hiệu

### 4.1 Định dạng payload

```
BATCH,<seq>,<HR_1>|<HR_2>|...|<HR_n>,<SPO2_1>|<SPO2_2>|...|<SPO2_n>,<TS_1>|<TS_2>|...|<TS_n>
```

| Field | Index | Kiểu | Mô tả |
|-------|-------|------|-------|
| Header | `[0]` | String | Luôn là `"BATCH"` |
| `seq` | `[1]` | Int | Số thứ tự packet |
| `HRs` | `[2]` | String | Danh sách nhịp tim, cách nhau bằng `\|` |
| `SPO2s` | `[3]` | String | Danh sách SpO2, cách nhau bằng `\|` |
| `TSs` | `[4]` | String | Danh sách timestamp (ms), cách nhau bằng `\|` |

### 4.2 Ví dụ

```
BATCH,17,80|82|79|81,97|97|96|97,1747200002000|1747200004000|1747200006000|1747200008000
```

Tức là 4 mẫu đo trong cùng một packet:
| Mẫu | HR (bpm) | SpO2 (%) | Timestamp |
|-----|---------|---------|-----------|
| 1 | 80 | 97 | 1747200002000 |
| 2 | 82 | 97 | 1747200004000 |
| 3 | 79 | 96 | 1747200006000 |
| 4 | 81 | 97 | 1747200008000 |

### 4.3 Giá trị đặc biệt

| Giá trị | Ý nghĩa |
|---------|---------|
| `255` | Cảm biến MAX30102 không đọc được (ngón tay không đặt đúng) → app map về `0` |
| `0` | Không hiển thị / bỏ qua trong chart |

### 4.4 Quy tắc xử lý trong app

```
Nhận payload
  ├── Tách bằng dấu ","
  ├── Kiểm tra: đúng 5 phần VÀ parts[0] == "BATCH"
  │     └── Sai → bỏ qua
  ├── Parse HR list: tách parts[2] bằng "|", map 255 → 0
  ├── Parse SpO2 list: tách parts[3] bằng "|", map 255 → 0
  ├── Parse TS list: tách parts[4] bằng "|"
  ├── Emit VitalsBatch vào vitalsBatch flow (dùng cho VitalsStore / chart)
  └── Lấy phần tử cuối (mẫu mới nhất) cập nhật SensorData (hiển thị real-time)
```

### 4.5 Data classes trong app

```kotlin
data class VitalsBatch(
    val sequence: Int,
    val heartRates: List<Int>,   // 255 đã được map về 0
    val spo2s: List<Int>,        // 255 đã được map về 0
    val timestamps: List<Long>   // milliseconds
)

data class SensorData(
    val heartRate: Int = 0,
    val spo2: Int = 0,
    val timestamp: Long = System.currentTimeMillis()
)
```

---

## 5. CONTROL Characteristic — Lệnh từ App → ESP32

### 5.1 Lệnh hiện có

| Lệnh | Mô tả | Khi nào gửi |
|------|-------|------------|
| `READY` | Thông báo app đã subscribe xong, ESP32 có thể bắt đầu gửi data | Ngay sau khi `All notifications subscribed ✓` |

### 5.2 Định dạng

```
READY
```
Gửi dưới dạng raw UTF-8 bytes, write vào CONTROL Characteristic.

---

## 6. Luồng dữ liệu tổng thể

```
ESP32 (GATT Server)
  │
  ├── STATUS (beb5483e) ──Notify──► BleManager.parseAlertPayload()
  │                                    ├── fallDetected.emit(FallStatus)
  │                                    │     └── BleForegroundService → FallAlertScreen
  │                                    ├── saveFallEvent() → SharedPreferences
  │                                    ├── vibrateDevice()
  │                                    └── playAlertSound() [ALARM stream]
  │
  ├── VITALS (7b809f11) ──Notify──► BleManager.parseVitalsPayload()
  │                                    ├── vitalsBatch.emit(VitalsBatch)
  │                                    │     └── MonitoringViewModel → VitalsStore
  │                                    │           ├── liveBuffer (25s)
  │                                    │           ├── fiveMinBuckets (1h chart)
  │                                    │           └── hourlyBuckets (24h chart)
  │                                    └── sensorData.update(SensorData)
  │                                          ├── HomeViewModel → HomeScreen
  │                                          └── MonitoringViewModel → MonitoringScreen
  │
  └── CONTROL (f9b2c417) ◄─Write─── App gửi "READY" sau khi subscribe xong
```

---

## 7. Validation & Error Handling

| Trường hợp | Hành vi |
|-----------|---------|
| Payload không đủ fields (≠ 7 với ALERT, ≠ 5 với BATCH) | Bỏ qua, không crash |
| Header không khớp (`parts[0] != "ALERT"/"BATCH"`) | Bỏ qua |
| Parse exception (không phải số) | Bắt exception, log error, bỏ qua packet |
| HR hoặc SpO2 = `255` | Map về `0` (invalid reading từ MAX30102) |
| `prediction != "fall"` | Không trigger alert, packet bị bỏ qua |

---

## 8. Lưu ý quan trọng

- **Comment trong BleManager.kt bị lỗi thời**: docstring mô tả format cũ (`prediction,status_code,fall_prob,non_fall_prob`) — thực tế code parse format mới có `ALERT` header và `seq`, `timestamp`.
- **IMU characteristic**: được đề cập trong tài liệu thiết kế nhưng **không có trong BleManager.kt hiện tại** — chưa được implement ở phía Android.
- **BATCH chứa nhiều mẫu**: một packet có thể chứa nhiều reading (pipe-separated). App dùng mẫu cuối (`heartRates.last()`) cho real-time display, toàn bộ batch cho VitalsStore.
- **255 = invalid**: MAX30102 trả về 255 khi không đọc được (ngón tay nhấc lên). App map về 0 và không hiển thị.
