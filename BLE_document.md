# BLE Protocol & Architecture Document — AIFD System

> Tài liệu này mô tả toàn bộ cơ chế BLE giữa ESP32-S3 (firmware `S3_AIFD_V1`) và Android app (`android_studio_AIFD`).  
> Mục đích: làm nền tảng để vẽ sơ đồ khối trực quan.

---

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────┐
│                 ESP32-S3 (GATT SERVER)           │
│  - Advertising "S3_AIFD_V1"                     │
│  - 1 Service + 3 Characteristics                │
│  - Nhận "READY" → bắt đầu gửi data             │
└───────────────────┬─────────────────────────────┘
                    │  BLE GATT (Notify + Write)
┌───────────────────▼─────────────────────────────┐
│              Android (GATT CLIENT)               │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │         BleForegroundService            │    │
│  │  - Owns BleManager (singleton)          │    │
│  │  - Keeps alive khi app background       │    │
│  │  - 15s countdown khi phát hiện ngã      │    │
│  │  - WakeLock + Emergency Call            │    │
│  └──────────────┬──────────────────────────┘    │
│                 │ Kotlin Flow / StateFlow         │
│  ┌──────────────▼──────────────────────────┐    │
│  │     BleManager (Core BLE logic)         │    │
│  │  - GATT connect / subscribe / parse     │    │
│  │  - Publish: fallDetected, vitalsBatch,  │    │
│  │            bmiSnapshot, safeReceived    │    │
│  └──────────────┬──────────────────────────┘    │
│                 │                                │
│  ┌──────────────▼──────────────────────────┐    │
│  │  ViewModels (AlertVM, MonitoringVM, ...) │    │
│  │  → Compose UI                           │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 2. GATT Structure (BLE Layer)

### Service
| Item | Value |
|------|-------|
| Service UUID | `4fafc201-1fb5-459e-8fcc-c5c9c331914b` |
| Device Name (Advertising) | `S3_AIFD_V1` |

### Characteristics

| Tên | UUID | Property | Hướng dữ liệu | Mô tả |
|-----|------|----------|--------------|-------|
| **ALERT** | `beb5483e-...` | READ + NOTIFY | ESP32 → Android | Gửi khi phát hiện ngã (ALERT) hoặc xác nhận an toàn (SAFE) |
| **VITALS** | `7b809f11-...` | READ + NOTIFY | ESP32 → Android | Gửi HR/SpO2 batch và BMI160 peak snapshot |
| **CONTROL** | `f9b2c417-...` | READ + WRITE | Android → ESP32 | Handshake: Android ghi "READY" để mở kênh dữ liệu |

---

## 3. Luồng kết nối (Connection Flow)

### 3.1 Phía ESP32 — Advertising & Accept

```
[Boot]
  │
  ├─ initBMI160()    → bmiOk
  ├─ initModel()     → modelOk  
  ├─ NimBLEDevice::init("S3_AIFD_V1")
  ├─ NimBLEDevice::deleteAllBonds()   ← xóa bond cũ, tránh GATT 133
  ├─ createServer() + createService() + createCharacteristics()
  ├─ service.start()
  └─ adv.start()  →  LED: YELLOW blink (Advertising)

[Android kết nối đến]
  └─ BleServerCb::onConnect()
       ├─ gBleConnected = true
       ├─ gBleReady = false          ← chưa sẵn sàng gửi data
       └─ LED: GREEN solid (Connected, chờ READY)

[Android ghi "READY" vào CONTROL char]
  └─ ControlCb::onWrite("READY")
       ├─ gBleReady = true           ← MỞ kênh dữ liệu
       ├─ reply: "ACK:READY"
       └─ sendInstantVitals()        ← gửi ngay 1 BATCH packet
```

**Điều kiện guard:** Tất cả `notifyAlert()` và `notifyVitals()` đều kiểm tra `gBleReady == true` trước khi gửi. Nếu chưa READY → silently skip.

### 3.2 Phía Android — Auto-Connect

```
[App khởi động / BleForegroundService.onCreate()]
  │
  ├─ BleManager.autoConnectBondedEsp32()
  │    ├─ Priority 1: targetAddress (MAC đã lưu SharedPreferences)
  │    ├─ Priority 2: bondedDevices.firstOrNull { name starts "ESP32"/"S3" }
  │    └─ connectGatt(device)
  │
  └─ Periodic safety-net: mỗi 60s nếu chưa connected → retry

[connectGatt(device)]
  │
  ├─ isConnecting = true
  ├─ arm watchdog timer (12s) → nếu không có callback → forceCloseGatt() + retry
  ├─ 200ms delay để stack settle
  └─ device.connectGatt(context, autoConnect=false, gattCallback, TRANSPORT_LE)
```

### 3.3 GATT Callback Chain (Android)

```
onConnectionStateChange(STATE_CONNECTED)
  │
  ├─ refreshGattCache()          ← xóa cache Android GATT cũ
  ├─ requestMtu(512)
  └─────────────────────────────────┐
                                    ▼
onMtuChanged(mtu, status)
  └─ gatt.discoverServices()
                                    ▼
onServicesDiscovered(status)
  ├─ getService(SERVICE_UUID)
  ├─ queueNotification(ALERT_CHAR)   ← enable CCCD notify
  ├─ queueNotification(VITALS_CHAR)  ← enable CCCD notify
  └─ writeNextDescriptor()           ← viết sequential (BLE chỉ cho 1 tại một lúc)
                                    ▼
onDescriptorWrite() × 2
  └─ sau khi cả 2 xong:
       ├─ _bleState = Connected(address, name)
       ├─ resetReconnectBackoff()
       └─ delay 100ms → sendReadyCommand()
                                    ▼
sendReadyCommand()
  └─ writeCharacteristic(CONTROL_CHAR, "READY")
                                    ▼
ESP32 nhận "READY" → gBleReady=true → bắt đầu gửi notify
```

### 3.4 Reconnect & Error Handling

| Sự kiện | Android xử lý |
|---------|--------------|
| GATT Error 133 | Xóa bond (removeBond) + forceCloseGatt() + retry |
| Disconnect (status ≠ 133) | forceCloseGatt() + exponential backoff retry |
| Connect watchdog timeout (12s) | forceCloseGatt() + isConnecting=false + retry |
| Bluetooth tắt (BroadcastReceiver) | resetConnectingState() |
| Bluetooth bật lại | resetConnectingState() + autoConnectBondedEsp32() |

**Exponential Backoff:**
```
Attempt 0 → 2s
Attempt 1 → 5s
Attempt 2 → 10s
Attempt 3 → 20s
Attempt 4+ → 60s
```

---

## 4. Packet Formats (CSV over BLE)

Tất cả packet là **plain UTF-8 string**, phân cách bằng dấu phẩy `,`.  
Giá trị `255` trong BATCH = sensor không sẵn sàng (parsed thành `-1` ở Android).

### 4.1 ALERT Packet — ESP32 → Android (qua ALERT characteristic)

```
ALERT,<seq>,<ts_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
```

| Field | Ví dụ | Mô tả |
|-------|-------|-------|
| `seq` | `3` | Sequence counter (tăng dần) |
| `ts_sec` | `142` | Thời gian thiết bị (uptime giây); Android dùng wall-clock để ghi log |
| `prediction` | `fall` | Luôn là "fall" khi gửi ALERT |
| `status_code` | `1` | 1 = fall confirmed |
| `fall_prob` | `0.873` | Xác suất ngã (0.0 – 1.0) |
| `non_fall_prob` | `0.127` | Xác suất không ngã |

**Ví dụ:** `ALERT,3,142,fall,1,0.873,0.127`

**Giá trị ban đầu khi boot:** `ALERT,0,0,idle,0,0.000,1.000`

### 4.2 SAFE Packet — ESP32 → Android (qua ALERT characteristic)

```
SAFE,<seq>,<ts_sec>
```

Gửi khi người dùng bấm nút vật lý trên thiết bị trong lúc đang alarm.

**Ví dụ:** `SAFE,4,155`

### 4.3 BATCH Packet — ESP32 → Android (qua VITALS characteristic)

```
BATCH,<seq>,<hr0|hr1|hr2|hr3|hr4>,<spo2_0|...|spo2_4>,<ts0|...|ts4>
```

Gửi mỗi 25 giây, chứa 5 mẫu cách nhau 5 giây.

| Field | Ví dụ | Mô tả |
|-------|-------|-------|
| `seq` | `2` | Sequence counter |
| HR list | `72\|75\|68\|255\|70` | Nhịp tim (bpm), 255 = không có dữ liệu |
| SpO2 list | `97\|98\|96\|255\|97` | Độ bão hòa O2 (%), 255 = không có dữ liệu |
| Timestamp list | `120\|125\|130\|135\|140` | Uptime giây tại mỗi mẫu |

**Ví dụ:** `BATCH,2,72|75|68|255|70,97|98|96|255|97,120|125|130|135|140`

**Instant BATCH (gửi ngay khi READY):** chỉ có 1 mẫu, format:
```
BATCH,<seq>,<hr>,<spo2>,<ts_sec>
```

### 4.4 BMI Packet — ESP32 → Android (qua VITALS characteristic)

```
BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>
```

Gửi mỗi 5 giây, là dữ liệu THỰC từ sensor BMI160.

| Field | Ví dụ | Mô tả |
|-------|-------|-------|
| `peak_acc_g` | `1.023` | Peak gia tốc trong window vừa qua (g) |
| `peak_gyro_dps` | `45.2` | Peak gyro trong window vừa qua (deg/s) |
| `active` | `0` hoặc `1` | 1 = vượt ngưỡng activity (>2g hoặc >50dps) |

**Ví dụ:** `BMI,7,145,1.023,45.2,0`

---

## 5. Luồng Data (Data Flow)

### 5.1 Dữ liệu bình thường (Normal Operation)

```
ESP32                                     Android BleManager
  │                                            │
  ├─[mỗi 5s]─ BMI notify ──────────────────►│
  │             "BMI,7,145,1.023,45.2,0"      ├─ parseBmi()
  │                                            └─ _bmiSnapshot.value = BmiSnapshot(...)
  │
  ├─[mỗi 25s]─ BATCH notify ───────────────►│
  │              "BATCH,2,72|75|..."          ├─ parseBatch()
  │                                           ├─ _vitalsBatch.emit(VitalsBatch(...))
  │                                           └─ _sensorData.value = SensorData(hr, spo2)
```

### 5.2 Luồng phát hiện ngã (Fall Detection Flow)

```
ESP32 (Fall Pipeline)                      Android
  │
  ├─ [BMI160 sampling 50Hz]
  ├─ [TFLite inference mỗi 100 mẫu = 2s]
  ├─ [Fall confirmed: FSM → onFallConfirmed()]
  │
  ├─── ALERT notify ──────────────────────►│  BleManager.parseAlertPayload()
  │    "ALERT,3,142,fall,1,0.873,0.127"    ├─ BlePacketParser.parseAlert()
  │    LED: RED blink fast + BUZZER ON     ├─ _fallDetected.emit(FallStatus(...))
  │                                        ├─ vibrateDevice() [500ms × 3]
  │                                        ├─ playAlertSound() [event_sos.wav, ALARM stream]
  │                                        │
  │                                        ▼
  │                               BleForegroundService
  │                                        ├─ handleFallDetected()
  │                                        ├─ acquireWakeLock() [bật màn hình]
  │                                        ├─ showFallAlertNotification()
  │                                        ├─ startActivity(MainActivity, ACTION_FALL_DETECTED)
  │                                        └─ start countdown 15s
  │                                              │
  │                  [User bấm "Tôi ổn" trên app]│
  │                                              ├─ cancelEmergencyCountdown()
  │                                              └─ _isFallAlertActive = false
  │
  │                  [OR: User bấm nút vật lý]
  ├─── SAFE notify ───────────────────────►│  
  │    "SAFE,4,155"                        ├─ _safeReceived.emit(Unit)
  │    LED: GREEN solid                    └─ BleForegroundService.cancelEmergencyCountdown()
  │
  │                  [OR: 15s hết mà không dismiss]
  │                                        └─ placeEmergencyCall() [gọi số caregiver]
```

### 5.3 Manual SOS (Bấm nút khi không có alarm)

```
ESP32                                     Android
  │
  [Button nhấn khi gFallAlertActive=false]
  ├─ gFallAlertActive = true
  ├─ LED: ALARM
  └─── ALERT notify ──────────────────────► (xử lý giống Fall Detection Flow)
       "ALERT,5,200,fall,1,1.000,0.000"
```

---

## 6. Android BLE State Machine

### BleState (trong BleManager)

```
Idle ──────────────────────────────────────────────┐
  │                                                 │ disconnect()
  │ autoConnectBondedEsp32()                        │
  ▼                                                 │
Scanning ─── stopScan() ─── Idle                   │
  │                                                 │
  │ (bonded device found → connectGatt)             │
  ▼                                                 │
[Connecting - internal]                             │
  │                                                 │
  ├── GATT 133 / Error ──► Error ──► retry ────────┤
  │                                                 │
  ├── onServicesDiscovered OK                       │
  │   + CCCD written × 2                            │
  │   + READY sent                                  │
  ▼                                                 │
Connected(address, name) ────────────────────────── ┘
  │
  │ onDisconnect / error
  ▼
Disconnected ──► retryConnectionAfterDelay() ──► Idle
```

### LED State Machine (trên ESP32)

| LED State | Màu sắc | Pattern | Điều kiện |
|-----------|---------|---------|-----------|
| BOOT | Xanh dương | Blink chậm 500ms | Đang khởi tạo |
| ADVERTISING | Vàng | Blink chậm 500ms | BLE chưa kết nối |
| CONNECTED | Xanh lá | Solid | BLE đã kết nối + READY |
| WARNING | Vàng | Blink nhanh 250ms | Mất kết nối tạm / lỗi sensor |
| FALL_WATCH | Đỏ | Blink chậm 500ms | FSM đang theo dõi ngã |
| ALARM | Đỏ + BUZZER | Blink nhanh 250ms | Ngã đã xác nhận |

---

## 7. Luồng khởi tạo hoàn chỉnh (Sequence Diagram)

```
ESP32                    Android BleManager         BleForegroundService
  │                            │                            │
  │ [Boot, init, adv]          │                            │
  │ LED: YELLOW blink          │                            │
  │                            │ [Service onCreate]         │
  │                            │◄── bindService() ─────────│
  │                            │                            │
  │                            │ autoConnectBondedEsp32()   │
  │                            │                            │
  │◄─── GATT connect ──────────│                            │
  │ onConnect() → gBleConn=T   │                            │
  │ LED: GREEN                 │                            │
  │                            │                            │
  │                            │◄── onConnectionStateChange(CONNECTED)
  │                            │ requestMtu(512) ──────────►│
  │◄── MTU exchange ───────────│                            │
  │                            │ discoverServices() ───────►│
  │◄── Services discovered ────│                            │
  │                            │ writeDescriptor(ALERT CCCD)│
  │◄── CCCD enabled (ALERT) ───│                            │
  │                            │ writeDescriptor(VITALS CCCD)
  │◄── CCCD enabled (VITALS) ──│                            │
  │                            │ [100ms delay]              │
  │                            │ writeChar(CONTROL,"READY") │
  │ onWrite("READY")           │                            │
  │ gBleReady = true           │                            │
  │ reply "ACK:READY"          │                            │
  │ sendInstantVitals()        │                            │
  │──── BATCH notify ─────────►│                            │
  │                            │ _vitalsBatch.emit()        │
  │                            │──────────────────────────► _isFallAlertActive / flows
  │                            │                            │
  │ [Normal operation]         │                            │
  │──── BMI notify (5s) ──────►│ _bmiSnapshot.value = ...  │
  │──── BATCH notify (25s) ───►│ _vitalsBatch.emit()       │
  │──── ALERT notify (fall) ──►│ _fallDetected.emit()      │
  │                            │──────────────────────────►handleFallDetected()
  │                            │                            │ countdown 15s
  │──── SAFE notify (button) ─►│ _safeReceived.emit()      │
  │                            │──────────────────────────►cancelCountdown()
```

---

## 8. Android-side Data Pipeline (Kotlin Flow)

```
BleManager (raw BLE)
  │
  ├─ _fallDetected:  SharedFlow<FallStatus>     → BleForegroundService → AlertViewModel → UI
  ├─ _safeReceived:  SharedFlow<Unit>           → BleForegroundService → AlertViewModel → UI
  ├─ _vitalsBatch:   SharedFlow<VitalsBatch>    → MonitoringViewModel → UI charts
  ├─ _bmiSnapshot:   StateFlow<BmiSnapshot?>    → MonitoringViewModel → UI
  ├─ _sensorData:    StateFlow<SensorData>      → HomeViewModel → UI cards
  ├─ _bleState:      StateFlow<BleState>        → tất cả ViewModels, BleForegroundService
  ├─ _nearbyDevices: StateFlow<List<Scanned>>   → DevicePairingScreen
  └─ _isVibrating:   StateFlow<Boolean>         → UI feedback
```

---

## 9. Packet Parsing (BlePacketParser)

**Classify → Parse pipeline:**
```
onCharacteristicChanged(payload: String)
  │
  ├─ ALERT char UUID
  │    └─ BlePacketParser.classify(payload)
  │         ├─ "ALERT" → parseAlert() → FallStatus → _fallDetected.emit()
  │         └─ "SAFE"  → parseSafe()  → _safeReceived.emit()
  │
  └─ VITALS char UUID
       └─ BlePacketParser.classify(payload)
            ├─ "BATCH" → parseBatch() → VitalsBatch → _vitalsBatch.emit()
            └─ "BMI"   → parseBmi()   → BmiSnapshot → _bmiSnapshot.value = ...
```

**Rule:** Tất cả parser trả về `null` nếu malformed (không throw exception). BleManager log warning và bỏ qua.

---

## 10. Các điểm kỹ thuật quan trọng

### 10.1 NimBLE setValue() bug workaround (ESP32)
NimBLE-Arduino 1.4.x có buggy template `setValue<T>()` → gửi `sizeof(pointer)=4 bytes` thay vì string.  
**Fix:** Dùng explicit overload `setValue((uint8_t*)s, strlen(s))` thông qua hàm `setStr()`.

### 10.2 Bond Mismatch — GATT Error 133
Khi ESP32 reflash, bond keys cũ trên Android trở thành invalid → kết nối bị từ chối ngay (Error 133).  
**ESP32 fix:** `NimBLEDevice::deleteAllBonds()` trong `setup()`.  
**Android fix:** Khi gặp status=133, gọi `device.removeBond()` trước khi retry.

### 10.3 Sequential CCCD Writes
Android BLE stack chỉ cho phép **1 descriptor write tại một thời điểm**.  
**Fix:** `descriptorWriteQueue` (LinkedList) — chỉ ghi tiếp khi `onDescriptorWrite()` callback về.

### 10.4 isConnecting Guard
Nhiều component gọi `autoConnectBondedEsp32()` đồng thời (Service, ViewModels) → nhiều GATT client song song → wedge BT stack.  
**Fix:** `@Volatile var isConnecting` — skip nếu đã đang kết nối.

### 10.5 Scanner vs Initiator conflict
`startScan()` và `connectGatt()` dùng chung radio LE initiator.  
**Fix:** `@Volatile var scanning` — `autoConnectBondedEsp32()` skip khi đang scan.

### 10.6 Connect Watchdog (12s)
`connectGatt()` có thể không bao giờ callback (BT tắt, stack wedge).  
**Fix:** `connectTimeoutRunnable` post delay 12s → `forceCloseGatt()` + retry.

### 10.7 GATT Cache Refresh
Android cache service discovery từ lần pair trước → characteristics mới (sau khi thêm VITALS char) không được tìm thấy.  
**Fix:** `refreshGattCache()` gọi hidden method `BluetoothGatt.refresh()` ngay sau STATE_CONNECTED.

---

## 11. Tóm tắt cho sơ đồ khối

### Các block chính cần vẽ:

**ESP32 side:**
1. `BMI160 Sensor` → [I2C] → `IMU Ring Buffer` → `Inference Task` → `Fall Detection FSM`
2. `Fall Detection FSM` → `BLE ALERT Notify`
3. `Button Handler` → `BLE ALERT Notify` (manual SOS) hoặc `BLE SAFE Notify`
4. `MAX30102 Sensor` → `Vitals Timer` → `BLE VITALS Notify`
5. `IMU peak cache` → `BMI Timer (5s)` → `BLE VITALS Notify`
6. `BLE CONTROL Char` ← Android (nhận "READY")

**Android side:**
1. `BLE Scan / Bond lookup` → `connectGatt()`
2. `GATT Callback` → `MTU → discoverServices → CCCD write → READY`
3. `ALERT char` → `BlePacketParser` → `fallDetected` / `safeReceived` flows
4. `VITALS char` → `BlePacketParser` → `vitalsBatch` / `bmiSnapshot` flows
5. `BleForegroundService` → `WakeLock + Notification + Countdown + Emergency Call`
6. `AlertViewModel` → `Compose UI (AlertScreen)`

### Thứ tự handshake (quan trọng nhất):
```
Advertising → Connect → MTU → DiscoverServices → EnableNotify(×2) → Write READY → Data flow
```
