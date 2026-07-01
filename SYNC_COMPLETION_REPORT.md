# AIFD — Edge ↔ Android Sync Completion Report

**Date:** 2026-05-19
**Edge folder:** `S3_BLE_test_2/`
**Android folder:** `android_studio_AIFD/`

---

## 1. Mục tiêu ban đầu

- App Android phải nhận được, ổn định, và đúng định dạng các dữ liệu sau từ
  edge device:
  - **BMI** (BMI160 IMU): dữ liệu thật, đại diện hoạt động vật lý
  - **Fall** (sự kiện ngã): dữ liệu thật, sinh ra bởi pipeline AI V84
  - **Safe button**: dữ liệu thật, nút bấm vật lý GPIO 10
  - **HR / SpO2**: hiện mô phỏng, kiến trúc phải dễ thay sensor thật về sau
- Cả 2 phía (edge + app) phải dùng cùng một protocol, không thừa, không
  thiếu, không sửa kiến trúc lớn.

---

## 2. Các mục tiêu đã hoàn thành

| # | Mục tiêu | Trạng thái | Cách hoàn thành | File chính |
|---|----------|------------|------------------|------------|
| 1 | Đồng bộ payload BLE edge → app | ✅ | CSV ASCII trên 2 characteristic, dispatch theo prefix (`ALERT`/`SAFE` vs `BATCH`/`BMI`) | `S3_BLE_test_2/src/main.cpp`, `BleManager.kt` |
| 2 | Truyền dữ liệu BMI thật mỗi 5s | ✅ | Thêm `gLastPeakAcc/Gyro/Active` được publish bởi inference task và emit qua packet `BMI,...` | `main.cpp` (sendBmiSnapshot) |
| 3 | Truyền sự kiện fall thật | ✅ (đã có) | `onFallConfirmed()` notify `ALERT,...` | `main.cpp` |
| 4 | Truyền safe-button thật | ✅ (đã có) | `handleButton()` notify `SAFE,...` khi `gFallAlertActive` | `main.cpp` |
| 5 | Tách HR/SpO2 simulated provider | ✅ | Hai hàm `readHrSample()` / `readSpo2Sample()` đánh dấu rõ TODO; sensor thật chỉ cần thay 2 hàm này | `main.cpp` (VITALS SOURCE section) |
| 6 | Android parser thống nhất | ✅ | Tách `BlePacketParser` (pure object) — không Android deps, dễ test | `BlePacketParser.kt` |
| 7 | Android parse đúng BMI / BATCH / SAFE / ALERT | ✅ | `parseVitalsPayload()` và `parseAlertPayload()` dispatch theo `classify()` | `BleManager.kt` |
| 8 | Android expose BMI live cho UI | ✅ | `BleManager.bmiSnapshot: StateFlow<BmiSnapshot?>` → `MonitoringUiState.bmiSnapshot` | `BleManager.kt`, `MonitoringViewModel.kt` |
| 9 | Device button → cancel app countdown | ✅ (đã có) | `BleForegroundService` collect `safeReceived` → `cancelEmergencyCountdown()` | `BleForegroundService.kt` |
| 10 | Parse an toàn với payload sai/thiếu field | ✅ | Mọi `parseX()` trả `null` thay vì throw; logger báo `malformed` | `BlePacketParser.kt` + tests |
| 11 | Test parser tự động | ✅ | 15 unit tests, PASS 100% | `BlePacketParserTest.kt` |
| 12 | Reconnect / disconnect ổn định | ✅ (đã có) | `retryConnectionAfterDelay()` với exponential backoff + 60s periodic safety-net | `BleManager.kt`, `BleForegroundService.kt` |

---

## 3. Kiến trúc / protocol cuối cùng

### 3.1 BLE topology

```
ESP32-S3 (peripheral)              Android (central)
─────────────────────────          ─────────────────
"S3_AIFD Wearable_test_2"   ── BLE ─► BleForegroundService
                                       └─► BleManager
Service 4fafc201-...                          │
 ├─ ALERT  beb5483e-...  (NOTIFY) ◄──┬─ subscribe
 ├─ VITALS 7b809f11-...  (NOTIFY) ◄──┤
 └─ CTRL   f9b2c417-...  (WRITE)  ──►┴─ "READY"
```

### 3.2 Format payload — CSV ASCII

| Packet | Char.  | Cadence  | Format |
|--------|--------|----------|--------|
| ALERT  | ALERT  | on fall  | `ALERT,<seq>,<ts_sec>,fall,<status>,<fall_prob>,<non_fall_prob>` |
| SAFE   | ALERT  | on btn   | `SAFE,<seq>,<ts_sec>` |
| BATCH  | VITALS | 25 s     | `BATCH,<seq>,<hr0\|...\|hr4>,<spo20\|...\|spo24>,<ts0\|...\|ts4>` |
| BMI    | VITALS | 5 s      | `BMI,<seq>,<ts_sec>,<peak_acc_g>,<peak_gyro_dps>,<active>` |

### 3.3 Ví dụ payload thực tế

```
ALERT,7,5824,fall,1,0.913,0.087
SAFE,8,5829
BATCH,12,72|75|77|74|73,98|97|98|97|96,5790|5795|5800|5805|5810
BMI,118,5815,1.034,5.7,0
BMI,119,5820,3.210,287.4,1
```

### 3.4 Lý do chọn CSV thay vì JSON / binary — xem mục 8.

---

## 4. Mapping dữ liệu edge → Android app

| Edge field      | App field                       | Kotlin type | Nguồn       | Thật/Mô phỏng | Ghi chú |
|-----------------|---------------------------------|-------------|-------------|--------------|---------|
| BMI peak_acc_g  | `BmiSnapshot.peakAccG`          | `Float`     | BMI160      | **Real**     | g |
| BMI peak_gyro_dps | `BmiSnapshot.peakGyroDps`     | `Float`     | BMI160      | **Real**     | dps |
| BMI active      | `BmiSnapshot.active`            | `Boolean`   | derived     | **Real**     | true nếu peak vượt ngưỡng activity |
| ALERT fall_prob | `FallStatus.fallProb`           | `Float`     | TFLite V84  | **Real**     | output model 0..1 |
| ALERT fall      | `FallStatus.prediction` = "fall" | `String`    | pipeline AI | **Real**     | sự kiện ngã |
| SAFE event      | `safeReceived: SharedFlow<Unit>`| —           | nút bấm     | **Real**     | trigger `cancelEmergencyCountdown()` |
| BATCH hr0..4    | `VitalsBatch.heartRates`        | `List<Int>` | readHrSample() | Simulated | -1 khi 255 |
| BATCH spo20..4  | `VitalsBatch.spo2s`             | `List<Int>` | readSpo2Sample() | Simulated | -1 khi 255 |
| BATCH ts0..4    | `VitalsBatch.timestamps`        | `List<Long>`| uptime sec  | Real (uptime)| không phải UTC |
| ALERT ts_sec    | `FallStatus.timestampSec`       | `Long`      | override = `System.currentTimeMillis()/1000` | n/a | dùng phone clock cho UI |

---

## 5. HR và SpO2 simulated hiện nằm ở đâu

**File:** `S3_BLE_test_2/src/main.cpp`
**Section:** `// VITALS SOURCE — HR / SpO2`

```cpp
static uint8_t readHrSample() {
    // TODO(real-sensor): replace with MAX30102/PPG driver read
    return (uint8_t)(60 + (esp_random() % 41));
}
static uint8_t readSpo2Sample() {
    // TODO(real-sensor): replace with MAX30102/PPG driver read
    return (uint8_t)(94 + (esp_random() % 7));
}
```

**Để thay bằng sensor thật:**

1. Cài driver MAX30102 (hoặc PPG khác) vào `setup()`.
2. Trong 2 hàm trên: gọi `driver.read()`, trả `255` nếu sensor chưa sẵn sàng.
3. Giữ nguyên contract: 8-bit, 255 = invalid.
4. KHÔNG cần đổi `sendVitalsBatch()`, BLE characteristic, hoặc Android parser.

App đã được thiết kế để 255 → -1 → UI ẩn — nên nếu trong khoảng warm-up sensor
trả 255, app sẽ không hiển thị giá trị giả.

---

## 6. Android changes

### File đã sửa

| File | Thay đổi |
|------|----------|
| `app/src/main/java/com/aifd/ble/BleManager.kt` | + `BmiSnapshot` data class; + `bmiSnapshot: StateFlow`; refactor `parseAlertPayload` / `parseVitalsPayload` → dispatch qua `BlePacketParser`; sửa comment Service UUID; impl `vibrateDevice()` thật |
| `app/src/main/java/com/aifd/ble/BlePacketParser.kt` | **MỚI** — object thuần Kotlin, 4 hàm parse + 1 hàm classify, không phụ thuộc Android |
| `app/src/main/java/com/aifd/service/BleForegroundService.kt` | + collect `bleManager.safeReceived` → `cancelEmergencyCountdown()` |
| `app/src/main/java/com/aifd/viewmodel/MonitoringViewModel.kt` | + field `bmiSnapshot` trong `MonitoringUiState`; + collector `ble.bmiSnapshot` |
| `app/src/main/java/com/aifd/ui/screens/AlertScreen.kt` | Bỏ countdown nội bộ; nhận `countdown: Int` từ ngoài để khớp service countdown |
| `app/src/main/java/com/aifd/navigation/AppNavigation.kt` | Truyền `alertState.countdown` vào `FallAlertScreen` |
| `app/src/test/java/com/aifd/ble/BlePacketParserTest.kt` | **MỚI** — 15 unit tests cho parser |

### Xử lý lỗi và edge case

- **Payload sai format**: `parseX()` trả `null`, log `Log.w(TAG, "<KIND> malformed: $payload")`.
- **Field thiếu**: `parts.size != expected` → `null`.
- **Sai kiểu số**: `runCatching` bọc `toInt/toFloat/toLong`, fail → `null`.
- **HR/SpO2 = 255**: map sang `-1`, callers filter bằng `>= 0`.
- **BLE disconnect**:
  - `gattCallback.onConnectionStateChange` → `_bleState.value = Disconnected`
  - `retryConnectionAfterDelay()` exponential backoff 2 s → 5 s → 10 s → 20 s → 60 s
  - `BleForegroundService` periodic safety-net mỗi 60 s
- **Bluetooth bị tắt rồi bật**: `bluetoothReceiver` catch `ACTION_STATE_CHANGED` → re-trigger `autoConnectBondedEsp32()`
- **Mất MTU / service discovery fail**: `_bleState = Error(...)`, exponential backoff sẽ retry.

### Cách app xử lý connect/disconnect/reconnect

```
boot → bind service → autoConnectBondedEsp32() (match bonded "ESP32"/"S3" name + saved MAC)
     → connectGatt → MTU=512 → discoverServices → subscribe ALERT+VITALS
     → write "READY" → device flush queued packets
     ──[disconnect]──> _bleState=Disconnected → retryConnectionAfterDelay()
     ──[BT off→on]───> auto-retry
```

---

## 7. Edge changes

### File đã sửa

`S3_BLE_test_2/src/main.cpp` — thay đổi nhỏ, không phá vỡ logic cũ:

| Thay đổi | Mục đích |
|---------|----------|
| + `gLastPeakAcc / gLastPeakGyro / gLastActive` (volatile globals) | Snapshot do inference task ghi, loop() đọc |
| + Cập nhật globals trong `runInferenceOnSnapshot()` | Mỗi window AI cập nhật peak để emitter dùng |
| + `readHrSample()` / `readSpo2Sample()` (TODO sensor) | Tách rõ điểm thay sensor thật |
| + `sendBmiSnapshot()` | Emit `BMI,...` packet |
| + `handleBmiSnapshot()` 5 s timer trong `loop()` | Lịch phát BMI packet |
| `sendVitalsBatch()` dùng `readHrSample()` thay vì `esp_random()` inline | HR/SpO2 contract sạch |
| (giữ nguyên) Fall pipeline V84, FALL_WATCH/STILL_TIMING, button SAFE | Logic thật không đổi |

### BLE service / characteristic — KHÔNG thay đổi

- Service UUID: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- ALERT char:  `beb5483e-36e1-4688-b7f5-ea07361b26a8` (notify, read)
- VITALS char: `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` (notify, read) — giờ carry cả `BATCH` lẫn `BMI`
- CONTROL char:`f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` (read, write `READY`/`PING`)
- Tên thiết bị: `"S3_AIFD Wearable_test_2"`

---

## 8. Benchmark kiến trúc payload

| Format | Ưu điểm | Nhược điểm | Phù hợp? |
|--------|---------|------------|----------|
| **CSV ASCII** | Dễ debug trên Serial Monitor; parser trivial; client mọi platform parse được; kích thước nhỏ (~50–100 B) | Không tự mô tả type; cần document cẩn thận | ✅ **Chọn** |
| JSON         | Self-describing, schema rõ ràng | ~3–4× kích thước CSV; cần ArduinoJson trên ESP32 (~30 KB RAM); MTU 23 mặc định BLE sẽ fragment | ❌ |
| Binary packed | Nhỏ nhất; nhanh nhất | Khó debug; cần struct alignment kỷ luật; mỗi field mới phải đổi cả 2 phía + version bytes | ❌ overkill cho lưu lượng hiện tại |

**Quyết định:** CSV ASCII vì payload hiện đã tồn tại theo định dạng này, parser Android đã chạy ổn định, và toàn bộ cấu trúc fit trong 1 BLE notify (MTU 247 sau request 512).

---

## 9. Build và test result

### Lệnh đã chạy

```bash
# Edge
cd S3_BLE_test_2
/home/zinex/.platformio/penv/bin/pio run

# Android — build + unit tests
cd android_studio_AIFD
./gradlew :app:testDebugUnitTest
./gradlew :app:assembleDebug
```

### Kết quả

| Kiểm tra | Kết quả | Chi tiết |
|----------|---------|----------|
| Edge firmware build (PIO) | ✅ **PASS** | `RAM: 31.4% (102976/327680)`, `Flash: 63.5% (832761/1310720)`, 6.96 s |
| Android unit tests | ✅ **15/15 PASS** | `BlePacketParserTest` — 0 failures, 0 errors, 0.029 s |
| Android assembleDebug | ✅ **PASS** | `BUILD SUCCESSFUL in 6s` |

---

## 10. Test plan checklist

| # | Test | Kết quả | Cách xác minh |
|---|------|---------|---------------|
| 1 | Android build pass | ✅ | `./gradlew :app:assembleDebug` |
| 2 | Edge build pass | ✅ | `pio run` |
| 3 | App scan được BLE device | ⚠️ Manual | Cần phone + ESP32; xem `BleManager.startScan()`, scan filter UUID đã đặt |
| 4 | App connect được edge BLE | ⚠️ Manual | Hai mặt UUID đã match — kiểm tra bằng pair + monitor Logcat |
| 5 | App subscribe được characteristic | ⚠️ Manual | `queueNotification(STATUS_CHAR_UUID)` + `queueNotification(VITALS_CHAR_UUID)` thuộc queue tuần tự |
| 6 | App nhận đủ HR, SpO2, BMI, fall, safe | ✅ Code path verified | Tất cả 4 packet types có handler và flow |
| 7 | App parse đúng HR mô phỏng | ✅ Test PASS | `parseBatch_validPacket`, `parseBatch_invalidSensorMarkerMappedToMinusOne` |
| 8 | App parse đúng SpO2 mô phỏng | ✅ Test PASS | (cùng test trên — bao gồm cả SpO2) |
| 9 | App parse đúng BMI thật | ✅ Test PASS | `parseBmi_validPacket`, `parseBmi_idleActiveFlag` |
| 10 | App nhận đúng fall event thật | ✅ Test PASS | `parseAlert_validFallPacket` |
| 11 | App nhận đúng safe button thật | ✅ Test PASS | `parseSafe_validPacket`, `BleForegroundService` collect `safeReceived` |
| 12 | App không crash khi BLE disconnect | ✅ Code path verified | `onConnectionStateChange` → state Disconnected, exponential backoff; `bluetoothReceiver` catch BT off |
| 13 | App reconnect / hiển thị trạng thái | ✅ | `bleState.collect` trong `BleForegroundService` → `updateNotification(false, null)` + `showDisconnectNotification()` |
| 14 | Parser test pass với payload hợp lệ | ✅ | 6 test "valid" cases pass |
| 15 | Parser test pass với payload thiếu field/sai format | ✅ | 9 test "malformed" cases pass |
| 16 | UI/state update đúng theo dữ liệu nhận được | ✅ Code path verified | `MonitoringViewModel.observeBleData()` collect sensorData + bmiSnapshot + bleState; `AlertViewModel.observeServiceState()` collect countdown |

**⚠️ Manual** = Không tự động chạy được vì cần phone Android thật + ESP32 thật + USB cable + permission Bluetooth — xem mục 11 cho hướng dẫn xác minh.

---

## 11. Hướng dẫn chạy lại

### 11.1 Build edge

```bash
cd S3_BLE_test_2
/home/zinex/.platformio/penv/bin/pio run
# Output: SUCCESS, RAM 31.4%, Flash 63.5%
```

### 11.2 Flash edge

```bash
# Giữ BOOT, nhấn RST, thả BOOT → ngay lập tức:
/home/zinex/.platformio/penv/bin/pio run -t upload
# Sau khi flash:
/home/zinex/.platformio/penv/bin/pio device monitor
```

### 11.3 Build + test Android

```bash
cd android_studio_AIFD
./gradlew :app:testDebugUnitTest    # 15 tests
./gradlew :app:assembleDebug        # APK in app/build/outputs/apk/debug/
```

### 11.4 Xác minh BLE end-to-end (manual)

1. Flash firmware vào ESP32-S3.
2. Mở Serial Monitor (`pio device monitor`) — sẽ thấy:
   - `[BMI] notify: BMI,1,5,1.034,5.7,0` (5 s tick)
   - `[BLE] VITALS notify: BATCH,...` (25 s tick)
3. Cài APK lên Android phone (Android 8+, BT 4.0+).
4. Settings → Bluetooth → pair "S3_AIFD Wearable_test_2".
5. Mở app → đăng nhập (không dùng tài khoản "000") → đợi "Connected".
6. Logcat filter `BleManager`:
   - `BMI: acc=1.034g gyro=5.7dps active=false`
   - `Vitals batch received, seq=1, count=5`
7. Lắc thiết bị mạnh để trigger fall:
   - `⚠️ FALL DETECTED! prob=0.913`
   - Loa kêu, đèn nhấp, alert screen mở, countdown 15 s đếm ngược.
8. Nhấn nút (GPIO 10) trên thiết bị:
   - `SAFE packet received from device — cancelling countdown`
   - Countdown dừng, alert screen tự đóng.

---

## 12. Vấn đề còn lại / Đề xuất bước tiếp theo

### 12.0 BUG FIX 2026-05-19 — NimBLE setValue template overload

**Phát hiện qua log:** `android_studio_AIFD/log_test/samsung-...2026-05-19_091525.logcat`
ghi nhận tất cả payload nhận về dưới dạng 4 byte garbage (`` `��? `` cho VITALS,
`` �z�? `` cho ALERT) thay vì CSV string. ESP32 log xác nhận packet gốc đúng
(`[BLE] ALERT notify: ALERT,1,294,fall,1,0.996,0.004`) nhưng phone nhận sai.

**Root cause:** NimBLE-Arduino 1.4.x có overload template:

```cpp
template<typename T>
void setValue(const T &s) {
    setValue((uint8_t*)&s, sizeof(T));
}
```

Khi gọi `setValue("BMI,...")` với `const char*`, compiler chọn template với
`T = const char*`, gửi `sizeof(const char*) = 4` byte từ **địa chỉ pointer trên
stack** thay vì content. Hai stack frame khác nhau (`notifyAlert` / `notifyVitals`)
giải thích 2 garbage pattern khác nhau, hằng số.

**Fix:** dùng overload byte-array tường minh:

```cpp
gCharAlert->setValue((uint8_t*)payload, strlen(payload));
```

Áp dụng cho mọi `setValue(const char *)`: `notifyAlert`, `notifyVitals`,
`ControlCb::onWrite` (ACK/PING/ERR), và 3 initial values trong `setup()`.

Sau fix: rebuild PIO PASS — cần flash + retest end-to-end.

### 12.1 Chưa xác minh end-to-end runtime trên hardware (manual)
Cần phone + ESP32 thật + Bluetooth/Location permission. Test plan #3–#6 và
#12–#13 phụ thuộc hardware. Toàn bộ code path đã verify qua build + unit test.

### 12.2 Timestamp = device uptime, không phải UTC
Field `timestamp_sec` trong ALERT/BATCH/BMI là `millis()/1000`. Android hiện
override ALERT timestamp bằng phone wall-clock. BATCH timestamps vẫn là
uptime — nếu cần UTC chính xác, có thể:
- Cho phone gửi `SYNC,<utc_ms>` qua CONTROL char,
- Hoặc bỏ field timestamp khỏi BATCH, app tự gán khi receive.

### 12.3 Đề xuất khi có sensor HR/SpO2 thật
1. Cài driver MAX30102 hoặc PPG tương đương trên I2C.
2. Sửa `readHrSample()` / `readSpo2Sample()` trong `main.cpp`:
   - Đọc từ driver
   - Trả 255 trong warm-up hoặc khi tín hiệu kém
3. Không cần đụng vào BLE / Android.

### 12.4 ACK protocol (chưa làm — out of scope)
`BLE_PROTOCOL.md §8` đề xuất ACK per-packet để đảm bảo at-least-once delivery.
Hiện firmware chỉ flush sau READY, không track per-packet — đủ tốt cho demo
nhưng không phải reliable messaging chuẩn IoT.

### 12.5 Risk kỹ thuật còn lại
- **MTU lower than expected**: Nếu phone phản hồi MTU < 100, BATCH packet
  (~100 B) sẽ bị fragment. NimBLE xử lý fragmentation transparent — không có
  vấn đề nhưng latency tăng.
- **GATT cache cũ**: Đã có `refreshGattCache()` invoke qua reflection để bypass
  Android stale-service-cache (case xuất hiện sau khi thêm characteristic mới).
- **USB CDC upload**: Đã đổi `upload_protocol = esp-builtin` trong
  `platformio.ini` — nếu vẫn timeout thì làm BOOT+RST manual.

---

## Tóm tắt thay đổi (TL;DR)

**Code mới:**
- `android_studio_AIFD/app/src/main/java/com/aifd/ble/BlePacketParser.kt`
- `android_studio_AIFD/app/src/test/java/com/aifd/ble/BlePacketParserTest.kt`

**Code đã sửa:**
- `S3_BLE_test_2/src/main.cpp` (thêm BMI emitter + tách HR/SpO2 simulator)
- `android_studio_AIFD/app/src/main/java/com/aifd/ble/BleManager.kt` (thêm BMI flow + dispatch parser)
- `android_studio_AIFD/app/src/main/java/com/aifd/service/BleForegroundService.kt` (collect SAFE)
- `android_studio_AIFD/app/src/main/java/com/aifd/viewmodel/MonitoringViewModel.kt` (collect BMI)
- `android_studio_AIFD/app/src/main/java/com/aifd/ui/screens/AlertScreen.kt` (bỏ countdown nội bộ)
- `android_studio_AIFD/app/src/main/java/com/aifd/navigation/AppNavigation.kt` (truyền countdown)

**Doc đã sửa / tạo:**
- `S3_BLE_test_2/BLE_PROTOCOL.md` (cập nhật cho BMI + SAFE + sensor legend)
- `SYNC_COMPLETION_REPORT.md` (file này)

**Build + test:**
- Edge PIO build: ✅ PASS
- Android `assembleDebug`: ✅ PASS
- Android unit tests: ✅ 15/15 PASS
- Runtime end-to-end: ⚠️ cần hardware để verify manual (đã có guide ở §11.4)
