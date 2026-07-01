# AIFD — Tài liệu Tính năng Đầy đủ

**Dự án:** Intelligent Edge AIoT Wearable System for Real-Time Safety Monitoring of Elderly People  
**Tên ứng dụng:** AIFD (AI Fall Detection)  
**Nền tảng:** Android (Jetpack Compose · MVVM · BLE)  
**Phiên bản tài liệu:** 1.0 — Dựa trên toàn bộ source code hiện tại

---

## Mục lục

1. [Kiến trúc tổng quan](#1-kiến-trúc-tổng-quan)
2. [Luồng dữ liệu BLE](#2-luồng-dữ-liệu-ble)
3. [Tính năng xác thực & tài khoản](#3-tính-năng-xác-thực--tài-khoản)
4. [Màn hình Home](#4-màn-hình-home)
5. [Màn hình Health (Monitoring)](#5-màn-hình-health-monitoring)
6. [Màn hình Alerts (Lịch sử cảnh báo)](#6-màn-hình-alerts-lịch-sử-cảnh-báo)
7. [Màn hình Settings (Cài đặt)](#7-màn-hình-settings-cài-đặt)
8. [Màn hình FallAlert (SOS khẩn cấp)](#8-màn-hình-fallalert-sos-khẩn-cấp)
9. [Màn hình Device Pairing & Detail](#9-màn-hình-device-pairing--detail)
10. [Màn hình Profile](#10-màn-hình-profile)
11. [BLE Backend — BleManager](#11-ble-backend--blemanager)
12. [BLE Backend — BleForegroundService](#12-ble-backend--bleforegroundservice)
13. [Lưu trữ dữ liệu — VitalsStore](#13-lưu-trữ-dữ-liệu--vitalsstore)
14. [ViewModel Layer](#14-viewmodel-layer)
15. [Điều hướng & Navigation](#15-điều-hướng--navigation)
16. [UI Components tái sử dụng](#16-ui-components-tái-sử-dụng)
17. [Đa ngôn ngữ (Localization)](#17-đa-ngôn-ngữ-localization)
18. [Giao diện & Theme](#18-giao-diện--theme)
19. [Quyền hệ thống (Permissions)](#19-quyền-hệ-thống-permissions)
20. [Lưu trữ cục bộ — SharedPreferences](#20-lưu-trữ-cục-bộ--sharedpreferences)
21. [Tài khoản & Dữ liệu Demo](#21-tài-khoản--dữ-liệu-demo)
22. [Cấu trúc file nguồn](#22-cấu-trúc-file-nguồn)

---

## 1. Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────┐
│                      Android App                        │
│                                                         │
│  MainActivity                                           │
│    ├── Permissions (BLE, CALL_PHONE, LOCATION, NOTIF)  │
│    ├── Bluetooth enable prompt                          │
│    ├── Theme / Language state (rememberSaveable)        │
│    └── AppNavigation                                    │
│          ├── Login / Register / RoleSelection           │
│          ├── Bottom Nav: Home │ Health │ Alerts │ Sett  │
│          ├── FallAlert (fullscreen SOS)                 │
│          ├── DevicePairing / DeviceDetail               │
│          ├── EventDetail                                │
│          └── Profile                                    │
│                                                         │
│  ViewModels (AndroidViewModel, viewModelScope)          │
│    ├── HomeViewModel     → healthData, device status    │
│    ├── MonitoringViewModel → charts, currentHR/SpO2     │
│    ├── DeviceViewModel   → scan, connect, disconnect    │
│    └── AlertViewModel    → fall events, countdown       │
│                                                         │
│  BleForegroundService (Foreground Service)              │
│    └── BleManager                                       │
│          ├── GATT Client (4 characteristics)            │
│          ├── Exponential backoff reconnect              │
│          └── StateFlows: bleState, sensorData,          │
│                          vitalsBatch, fallDetected,     │
│                          nearbyDevices                  │
│                                                         │
│  VitalsStore (In-memory + SharedPreferences)            │
│    ├── Live buffer 25s                                  │
│    ├── 12 × 5-min buckets (1h chart)                   │
│    └── 24 × 1h buckets (24h chart)                     │
└─────────────────────────────────────────────────────────┘
              │ BLE GATT
┌─────────────────────────────────────────────────────────┐
│                   ESP32-S3 Wearable                     │
│  Characteristics:                                       │
│   STATUS  beb5483e — ALERT payload (fall event)         │
│   VITALS  7b809f11 — BATCH payload (HR + SpO2)          │
│   CONTROL f9b2c417 — Command from phone                 │
│   IMU     6d3b70a9 — Raw IMU data stream                │
└─────────────────────────────────────────────────────────┘
```

**Pattern:** MVVM + Foreground Service + Repository (VitalsStore)  
**UI:** Jetpack Compose + Material 3  
**Concurrency:** Kotlin Coroutines + StateFlow

---

## 2. Luồng dữ liệu BLE

### Giao thức từ ESP32 → Android

| Đặc điểm | UUID | Hướng | Tần suất |
|-----------|------|--------|----------|
| STATUS | `beb5483e-...` | ESP32 → App (Notify) | Khi phát hiện ngã |
| VITALS | `7b809f11-...` | ESP32 → App (Notify) | Mỗi 2 giây |
| CONTROL | `f9b2c417-...` | App → ESP32 (Write) | Theo yêu cầu |
| IMU | `6d3b70a9-...` | ESP32 → App (Notify) | Liên tục |

### Định dạng payload

**ALERT (ngã):**
```
ALERT,<seq>,<timestamp>,fall,<1>,<fallProb>,<nonFallProb>
Ví dụ: ALERT,42,1747200000,fall,1,0.990,0.010
```

**BATCH (sinh hiệu):**
```
BATCH,<seq>,<heartRate>,<spO2>,<timestamp>
Ví dụ: BATCH,17,80,97,1747200002000
```

**IMU:**
```
IMU5|<ts>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>|...
```

### Luồng xử lý trong app
```
BLE Notify → BleManager.onCharacteristicChanged()
    │
    ├── STATUS char → parse ALERT → fallDetected.emit()
    │       └── BleForegroundService → handleFallDetected()
    │               ├── WakeLock bật màn hình
    │               ├── Notification SOS
    │               ├── Broadcast → MainActivity → FallAlertScreen
    │               └── Đếm ngược 15s → tự gọi điện
    │
    └── VITALS char → parse BATCH → vitalsBatch.emit()
            └── sensorData.update(heartRate, spo2)
                    ├── HomeViewModel.sensorData.collect()
                    │       └── _uiState.update (ngay lập tức)
                    └── MonitoringViewModel.sensorData.collect()
                            ├── _uiState.update (ngay lập tức)
                            └── VitalsStore.addReading()
                                    ├── liveBuffer (25s)
                                    ├── fiveMinBuckets (1h chart)
                                    └── hourlyBuckets (24h chart)
```

---

## 3. Tính năng xác thực & tài khoản

### Đăng nhập (LoginScreen)
- Form username + password
- Tài khoản thật: `dien572` / `dien562003`
- Tài khoản demo: `000` / `000` (dữ liệu giả lập)
- Hiển thị lỗi khi sai thông tin
- Điều hướng sang màn hình đăng ký
- Lưu trạng thái đăng nhập vào SharedPreferences (`logged_in`, `username`)

### Đăng ký (RegisterScreen)
- Nhập: username, password, tên người đeo, tên người chăm sóc, tuổi, giới tính, số điện thoại khẩn cấp
- Lưu toàn bộ profile vào SharedPreferences
- Sau đăng ký → đăng nhập tự động

### Chọn vai trò (RoleSelectionScreen)
- Hai lựa chọn: **Người đeo (Wearer)** / **Người chăm sóc (Caregiver)**
- Lưu vai trò (`user_role`) vào SharedPreferences
- Hiển thị sau đăng nhập lần đầu hoặc khi đổi vai trò

### Đăng xuất
- Xóa `logged_in`, `username`, `user_role` khỏi SharedPreferences
- Quay về màn hình đăng nhập
- Dialog xác nhận trước khi đăng xuất

### Chuyển đổi tài khoản
- Khi đổi tài khoản: reset toàn bộ ViewModel state (HomeViewModel + MonitoringViewModel)
- Xóa dữ liệu cảm biến cũ (`last_heart_rate`, `last_spo2`, `hr_history`, v.v.)
- `LaunchedEffect(username)` trong AppNavigation kích hoạt `resetForUser()`

---

## 4. Màn hình Home

### Hiển thị
- **Tên người dùng** theo vai trò: tên người đeo (Wearer) hoặc tên người chăm sóc (Caregiver)
- **Badge cảnh báo** trên tab Alerts — số lượng sự kiện đang chờ (PENDING)

### Card thiết bị (DeviceCard)
- Tên thiết bị BLE đang kết nối
- Trạng thái: Connected / Disconnected / Connecting (badge màu xanh/đỏ/vàng)
- % Pin thiết bị
- Nhấn → điều hướng đến DeviceDetailScreen (chỉ Wearer)
- Khi chưa kết nối: nút "Kết nối thiết bị" → DevicePairingScreen

### Card sức khỏe
- **Heart Rate** (nhịp tim): giá trị hiện tại (bpm) + badge trạng thái (Normal/High/Low)
- **Blood Oxygen SpO2**: giá trị hiện tại (%) + badge trạng thái
- Nhấn card → điều hướng sang màn hình Health/Monitoring

### Card bước chân
- Số bước hiện tại / mục tiêu (mặc định 10,000 bước/ngày)
- Thanh tiến trình (LinearProgressIndicator)

### Nút SOS khẩn cấp (chỉ Wearer)
- Nút lớn màu đỏ, animation nhấp nháy
- Nhấn → kích hoạt FallAlertScreen + ghi nhận sự kiện

### Dữ liệu nguồn
- HomeViewModel đọc từ `ble.sensorData.collect()` — cập nhật ngay lập tức khi BLE gửi dữ liệu
- Khi app khởi động: khôi phục giá trị cuối từ SharedPreferences (`last_heart_rate`, `last_spo2`)

---

## 5. Màn hình Health (Monitoring)

### Tab chuyển đổi
- **Heart Rate** / **Blood Oxygen (SpO2)**
- Chuyển tab giữ nguyên TimeRange đang chọn

### Bộ chọn khoảng thời gian (TimeRangeSelector)
- **LIVE** — Giá trị hiện tại theo thời gian thực (không có biểu đồ trend)
- **1H** — 1 giờ gần nhất (12 điểm × 5 phút)
- **24H** — 24 giờ gần nhất (24 điểm × 1 giờ)
- FilterChip UI với animation chọn

### Card giá trị hiện tại (Current)
- Hiển thị HR hoặc SpO2 lớn (displaySmall typography)
- Đơn vị: bpm / %
- Badge trạng thái: Normal (xanh) / High (đỏ) / Low (vàng)
- **Nguồn dữ liệu:** `ble.sensorData` — cùng nguồn với Home (đồng bộ thời gian thực)

### Biểu đồ đường (LineChart) — chỉ mode 1H và 24H

**Trục Y:**
- Label giá trị max (rawMax) được đặt đúng tọa độ Y của điểm dữ liệu max
- Đường guide ngang mờ tại vị trí max để dễ đọc
- Y-scale làm tròn bội số 5 → scale ổn định khi dữ liệu dao động

**Trục X:**
- 5 label thời gian thực (HH:mm) phân bố đều
- **Mode 1H:** từ `now-60min` → `now` (ví dụ: 13:30, 13:45, 14:00, 14:15, 14:30)
- **Mode 24H:** từ `now-24h` → `now` theo từng 6 giờ (cùng giờ ngày hôm qua đến hiện tại)

**Các chấm dữ liệu:**
- Dot tại mỗi bucket có dữ liệu (màu của metric)
- Dot được chọn: halo + dot lớn + lõi trắng
- Khoảng trống khi bucket = 0 (không có dữ liệu)

**Tương tác tap:**
- Nhấn vào chấm → Tooltip hiện phía trên
- Tooltip: giá trị + đơn vị (ví dụ: "80 bpm") + thời điểm bucket ("14:35")
- Nhấn lại → ẩn tooltip

**Vùng fill:**
- Gradient dọc từ màu metric (40% alpha) xuống trong suốt
- Smooth cubic Bezier curves giữa các điểm

### Stats Row (chỉ khi có dữ liệu, mode 1H/24H)
- **Average** (Trung bình) / **Min** (Thấp nhất) / **Max** (Cao nhất)
- Tính từ chart data đang hiển thị → đồng nhất với biểu đồ

### Banner thông tin
- **Khi chưa kết nối / không có dữ liệu:** thông báo "Kết nối thiết bị để xem dữ liệu"
- **Khi có dữ liệu:** hiển thị thông tin ngưỡng bình thường (HR 60-100 bpm, SpO2 ≥ 95%)

### Biểu đồ bước chân hàng tuần (StepsBarChart)
- 7 cột tương ứng 7 ngày trong tuần
- Màu: tertiary theme color
- Background bar + filled bar

### Nguồn dữ liệu chi tiết

| Mode | Dữ liệu hiện tại | Dữ liệu biểu đồ |
|------|-----------------|-----------------|
| LIVE | `sensorData.heartRate` (mới nhất) | Không có biểu đồ |
| 1H | `sensorData.heartRate` (mới nhất) | `VitalsStore.get1hChart()` — trung bình 12 bucket × 5 phút |
| 24H | `sensorData.heartRate` (mới nhất) | `VitalsStore.get24hChart()` — trung bình 24 bucket × 1 giờ |

---

## 6. Màn hình Alerts (Lịch sử cảnh báo)

### Danh sách sự kiện (HistoryScreen)
- Hiển thị danh sách `FallEvent` theo thời gian (mới nhất trước)
- Mỗi sự kiện: icon loại sự kiện, tiêu đề, timestamp, badge trạng thái
- Nhấn vào → EventDetailScreen

### Loại sự kiện (EventType)
- `FALL` — Phát hiện ngã
- `ALERT` — Cảnh báo thủ công
- `DISCONNECT` — Mất kết nối thiết bị
- `LOW_BATTERY` — Pin yếu

### Trạng thái sự kiện (EventStatus)
- `PENDING` — Đang chờ xử lý (đóng góp vào badge đếm trên Home)
- `RESOLVED` — Đã giải quyết (người dùng chọn "Tôi ổn")
- `DISMISSED` — Đã bỏ qua

### Chi tiết sự kiện (EventDetailScreen)
- Thời gian xảy ra, loại sự kiện, tên thiết bị
- Vị trí (nếu có)
- Phản hồi của người dùng ("I'm Safe" / "Called for Help")
- Nút quay lại

---

## 7. Màn hình Settings (Cài đặt)

### Phần Appearance (Giao diện)
- **Theme:** Sáng / Tối / Hệ thống — Dialog chọn với dấu tích
- **Language:** Tiếng Anh / Tiếng Việt — Dialog chọn với dấu tích
- **Role (Vai trò):** Wearer / Caregiver — Chuyển đổi không cần đăng xuất

### Phần Account
- **Profile** → điều hướng đến ProfileScreen

### Nút Xóa dữ liệu sức khỏe (Clear Health Data)
- Màu đỏ với icon Delete
- Dialog xác nhận trước khi xóa
- Xóa: VitalsStore (in-memory + SharedPreferences: `vitals_5min`, `vitals_1h`)
- Xóa: `last_heart_rate`, `last_spo2`, `monitoring_hr_live`, `monitoring_spo2_live`
- Reset UI về trạng thái rỗng

### Nút Đăng xuất (Log Out)
- Màu đỏ
- Dialog xác nhận trước khi đăng xuất

### Phiên bản ứng dụng
- Hiển thị "AIFD v1.0.0" ở cuối màn hình

---

## 8. Màn hình FallAlert (SOS khẩn cấp)

### Kích hoạt
- **Tự động:** ESP32 gửi ALERT payload → BleForegroundService → broadcast `ACTION_FALL_DETECTED` → MainActivity → FallAlertScreen
- **Thủ công:** Người dùng nhấn nút SOS trên HomeScreen

### Giao diện
- Fullscreen, ẩn bottom navigation bar
- Đếm ngược **15 giây** hiển thị rõ ràng
- Thông báo: "Phát hiện ngã — Bạn có ổn không?"

### Hành động người dùng
- **"Tôi ổn" (Dismiss as Safe):**
  - Hủy đếm ngược
  - Ghi sự kiện FALL với status `RESOLVED`, response "I'm Safe"
  - Quay về HomeScreen
  - Tắt âm thanh cảnh báo
  - Giải phóng WakeLock
  - Cancel notification SOS

- **"Gọi khẩn cấp" (Call for Help):**
  - Hủy đếm ngược
  - Gọi số điện thoại người chăm sóc (từ `userProfile.caregiverPhone`)
  - Kiểm tra quyền `CALL_PHONE` — nếu chưa có thì request, fallback sang ACTION_DIAL
  - Ghi sự kiện với status `PENDING`, response "Called for Help"
  - Quay về HomeScreen

### Hành vi nền (Background)
- **Notification "I'm Safe":** Nút Dismiss trên notification khi app ở background
- **Notification "Call":** Nút gọi ngay trên notification
- Khi đếm ngược hết → **tự động gọi điện** (không cần người dùng tương tác)
- WakeLock bật màn hình kể cả khi khóa màn hình

### Hiển thị trên màn hình khóa
- `setShowWhenLocked(true)` + `setTurnScreenOn(true)` (Android 8.1+)
- `FLAG_SHOW_WHEN_LOCKED | FLAG_TURN_SCREEN_ON` (Android cũ hơn)

---

## 9. Màn hình Device Pairing & Detail

### DevicePairingScreen

**Hiển thị:**
- Danh sách thiết bị BLE đã ghép đôi (bonded) — luôn hiển thị, tên null → fallback "ESP32 (xx:xx)"
- Thiết bị đã dùng trước đây được đánh dấu "★ Previously Used"
- Danh sách thiết bị tìm thấy qua scan active

**Scan:**
- Scan có ScanFilter theo Service UUID — fallback scan không lọc nếu thất bại
- Timeout scan: 10 giây
- Hiển thị RSSI (cường độ tín hiệu)
- Nút "Scan" bắt đầu quét lại

**Kết nối:**
- Nhấn thiết bị → kết nối GATT
- Thanh tiến trình kết nối
- Sau khi kết nối: lưu MAC (`device_mac`) và tên (`device_name`) vào SharedPreferences

**Chỉ Wearer** mới có thể truy cập màn hình này.

### DeviceDetailScreen

**Thông tin thiết bị:**
- Tên, địa chỉ MAC, firmware version
- % Pin, cường độ tín hiệu
- Trạng thái kết nối + thời gian sync cuối

**Hành động:**
- **Đổi tên:** Đổi tên hiển thị (lưu local, không gửi BLE)
- **Reconnect:** Thử kết nối lại
- **Disconnect:** Ngắt kết nối, về HomeScreen
- **Quay lại**

---

## 10. Màn hình Profile

### Thông tin hiển thị & chỉnh sửa
- Username
- Tên người đeo (wearerName), Tuổi (wearerAge), Giới tính (wearerGender)
- Tên người chăm sóc (caregiverName)
- Số điện thoại khẩn cấp (caregiverPhone) — dùng cho cuộc gọi SOS
- Nút Lưu → `onUpdateProfile` → persist vào SharedPreferences

---

## 11. BLE Backend — BleManager

### Kết nối

**Auto-connect khi khởi động:**
- Strategy 1: Tìm trong danh sách bonded devices — tên bắt đầu bằng "ESP32" hoặc "S3"
- Strategy 2: Fallback theo MAC đã lưu (`device_mac` trong SharedPreferences)
- Kích hoạt khi app mở, khi Bluetooth bật lại, và định kỳ mỗi 60s (safety-net)

**Exponential Backoff khi reconnect:**

| Lần thử | Delay |
|---------|-------|
| 1 | 2 giây |
| 2 | 5 giây |
| 3 | 10 giây |
| 4 | 20 giây |
| 5+ | 60 giây |

Reset về 0 khi kết nối thành công.

**Xử lý GATT Error 133:**
- Disconnect + close GATT + null ref → retry sau delay

**GATT Cache Refresh:**
- Gọi `gatt.refresh()` qua reflection mỗi lần kết nối
- Đảm bảo Android không cache service list cũ (cần thiết khi firmware thêm characteristic mới)

### 4 GATT Characteristics

| Characteristic | UUID | CCCD |
|---------------|------|------|
| STATUS | `beb5483e-4634-4f13-aff6-1a9e74e7a7e1` | Notify ✓ |
| VITALS | `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` | Notify ✓ |
| CONTROL | `f9b2c417-...` | Write |
| IMU | `6d3b70a9-...` | Notify ✓ |

CCCD được ghi **tuần tự** (xếp hàng queue) tránh race condition.

### StateFlows public API

| Flow | Kiểu | Mô tả |
|------|------|-------|
| `bleState` | `BleState` | Connected / Disconnected / Scanning / Error |
| `sensorData` | `SensorData` | HR và SpO2 reading mới nhất |
| `vitalsBatch` | `VitalsBatch` | Mảng HR + SpO2 từ một BATCH packet |
| `fallDetected` | `FallStatus` | Emit khi nhận ALERT fall |
| `nearbyDevices` | `List<ScannedDevice>` | Thiết bị tìm thấy qua scan |

### Parse dữ liệu
- STATUS `ALERT,...` → parse fallProb, nonFallProb, sequence, timestamp → emit `fallDetected`
- VITALS `BATCH,...` → parse HR, SpO2 → emit `vitalsBatch` + update `sensorData`
- Validation: HR hợp lệ 30–220, SpO2 hợp lệ 50–100

---

## 12. BLE Backend — BleForegroundService

### Loại Service
- **Foreground Service** — Android không thể kill
- Persistent notification (channel: `aifd_ble_monitoring`)
- `START_STICKY` — tự khởi động lại nếu bị kill
- Dùng `SupervisorJob + Dispatchers.Main` coroutine scope

### Notification Channels

| Channel | ID | Độ ưu tiên | Mục đích |
|---------|-----|-----------|---------|
| BLE Monitoring | `aifd_ble_monitoring` | Low | Notification thường trực "Đang giám sát" |
| Fall Alert | `aifd_fall_alerts` | Max (IMPORTANCE_HIGH) | Cảnh báo ngã — heads-up |
| Disconnect | (ID: 1003) | Default | Thông báo mất kết nối (có thể tắt) |

### Notification IDs
- `1001` — Monitoring thường trực
- `1002` — Fall Alert SOS
- `1003` — Disconnect notification

### Broadcast Actions

| Action | Chiều | Mô tả |
|--------|-------|-------|
| `ACTION_FALL_DETECTED` | Service → MainActivity | Điều hướng đến FallAlertScreen |
| `ACTION_DISMISS_SAFE` | Service/UI → AppNavigation | Quay về Home |
| `ACTION_CALL_HELP` | Notification → Service | Gọi ngay từ notification |
| `ACTION_CONNECTION_STATE` | Service → broadcast | Cập nhật trạng thái kết nối |

### WakeLock
- `SCREEN_BRIGHT_WAKE_LOCK | ACQUIRE_CAUSES_WAKEUP | ON_AFTER_RELEASE`
- Timeout tối đa 60 giây
- Bật khi phát hiện ngã, giải phóng khi dismiss hoặc sau 60s

### Auto-reconnect safety net
- Mỗi 60 giây kiểm tra — nếu không connected → gọi `autoConnectBondedEsp32()`

### Phản hồi sự kiện Bluetooth
- Lắng nghe `BluetoothAdapter.ACTION_STATE_CHANGED`
- Khi BT bật lại → tự động reconnect

### Binder (LocalBinder)
- Cho phép Activity/ViewModel bind để truy cập `bleManager`, `isFallAlertActive`, `countdownSeconds`

---

## 13. Lưu trữ dữ liệu — VitalsStore

### Mô hình bộ nhớ

```
liveBuffer (ArrayDeque)
  └── Raw readings trong 25 giây gần nhất

fiveMinBuckets (LinkedHashMap<Long, Bucket>)
  └── 12 buckets × 5 phút = 1 giờ
  └── Bucket key = floor(ts / 300_000) * 300_000

hourlyBuckets (LinkedHashMap<Long, Bucket>)
  └── 24 buckets × 1 giờ = 24 giờ
  └── Bucket key = floor(ts / 3_600_000) * 3_600_000
```

### Struct Bucket
Mỗi bucket lưu: `startMs, hrSum, hrCount, spo2Sum, spo2Count`  
Tính trung bình: `hrAvg = hrSum / hrCount`

### Validation dữ liệu đầu vào
- HR: phải trong khoảng [30, 220]
- SpO2: phải trong khoảng [50, 100]
- Giá trị ngoài ngưỡng → bỏ qua

### API công khai

| Phương thức | Mô tả |
|-------------|-------|
| `addReading(hr, spo2)` | Thêm reading vào tất cả buffer/bucket |
| `getLiveHR()` | Max HR trong 25s gần nhất |
| `getLiveSpO2()` | Max SpO2 trong 25s gần nhất |
| `get1hChart(isHR)` | 12 điểm trung bình (0 nếu không có dữ liệu) |
| `get24hChart(isHR)` | 24 điểm trung bình (0 nếu không có dữ liệu) |
| `clearAll()` | Xóa bộ nhớ + SharedPreferences |
| `saveToPrefs()` | Serialize + persist vào SharedPreferences |

### Persistence (SharedPreferences)
- Key `vitals_5min`: chuỗi CSV pipe-separated — `"ts,hrSum,hrCount,spo2Sum,spo2Count|..."`
- Key `vitals_1h`: cùng định dạng cho 24 hourly buckets
- Ghi tự động: throttle 30 giây/lần
- Đọc khi khởi động: chỉ restore bucket còn trong cửa sổ thời gian hợp lệ

---

## 14. ViewModel Layer

### HomeViewModel
- Bind `BleForegroundService` để truy cập `BleManager`
- `observeBleData()`: collect `sensorData` → cập nhật `healthData` ngay lập tức
- Persist `last_heart_rate`, `last_spo2`, `last_vital_timestamp`, `hr_history`, `spo2_history`
- `resetForUser(username)`: khôi phục từ SharedPreferences hoặc mock data
- `updateDevice(device)`: đồng bộ từ DeviceViewModel qua `LaunchedEffect`

### MonitoringViewModel
- `observeBleData()`: collect `sensorData` → cập nhật `currentHR/SpO2` + `healthData` **ngay lập tức** (đồng bộ với Home)
- `observeBleData()`: collect `vitalsBatch` → `VitalsStore.addReading()` (cho chart)
- `startLiveTick()`: mỗi 1 giây → cập nhật `chartData` từ VitalsStore (1h/24h)
- `selectTab()`, `selectTimeRange()`: thay đổi view mode + refresh chart
- `getStats()`: triple (avg, min, max) từ chartData hiện tại
- `clearVitalsData()`: xóa VitalsStore + SharedPreferences + reset UI

### DeviceViewModel
- `startScan()`: BLE scan với timeout 10s
- `connectToDevice(nearby)`: kết nối GATT
- `disconnectDevice()`: ngắt kết nối
- `reconnectDevice()`: kết nối lại theo địa chỉ đã lưu
- `renameDevice(name)`: đổi tên hiển thị
- `cancelEmergencyCountdown()`, `callNow()`: delegate đến Service
- Persist `device_mac`, `device_name` khi kết nối thành công
- `pendingScan`: cờ để retry scan sau khi Service bind xong

### AlertViewModel
- `triggerFallAlert()`: kích hoạt từ UI (nút SOS)
- `dismissAsSafe()`: ghi sự kiện RESOLVED + cancel countdown
- `callForHelp()`: ghi sự kiện PENDING + delegate `callNow()` đến Service
- `selectEvent(id)` / `getSelectedEvent()`: quản lý sự kiện đang xem
- `observeServiceState()`: collect `isFallAlertActive`, `countdownSeconds` từ Service

---

## 15. Điều hướng & Navigation

### Sơ đồ màn hình

```
[Chưa đăng nhập]
    LoginScreen ←→ RegisterScreen

[Đã đăng nhập, chưa chọn vai trò]
    RoleSelectionScreen

[Đã đăng nhập + có vai trò]
    Bottom Navigation Bar:
    ┌──────────────────────────────────────┐
    │  Home │ Health │ Alerts │ Settings   │
    └──────────────────────────────────────┘
    
    HomeScreen
      ├──► MonitoringScreen (Health tab)
      ├──► DevicePairingScreen (Wearer only)
      ├──► DeviceDetailScreen (Wearer only)
      └──► FallAlertScreen (SOS)
    
    MonitoringScreen
    
    HistoryScreen (Alerts tab)
      └──► EventDetailScreen
    
    SettingsScreen
      └──► ProfileScreen
    
    DevicePairingScreen ← SettingsScreen / HomeScreen
    DeviceDetailScreen  ← HomeScreen / SettingsScreen
```

### Ẩn Bottom Nav Bar
Bottom navigation ẩn trên các màn hình: FallAlert, DevicePairing, DeviceDetail, EventDetail.

### Animations chuyển màn hình
- Forward: Slide Left + FadeIn (400ms)
- Back: Slide Right + FadeIn (400ms)
- `popUpTo` để tránh back stack tích lũy

### Xử lý Intent từ Notification
- `onNewIntent()` trong MainActivity bắt `ACTION_FALL_DETECTED`
- `LaunchedEffect(startOnFallAlert)` → navigate đến FallAlertScreen

### Dismiss SOS từ ngoài app
- BroadcastReceiver trong AppNavigation lắng nghe `ACTION_DISMISS_SAFE`
- Tự động `popBackStack` về Home khi nhận broadcast

---

## 16. UI Components tái sử dụng

### LineChart (`Charts.kt`)
- Canvas-based, density-aware (tất cả padding/text size dùng dp/sp)
- Y-axis: label max value đúng vị trí Y tương ứng + guide line ngang
- X-axis: 5 label HH:mm thực tế (chỉ mode 1H và 24H)
- Dots tại mỗi bucket có dữ liệu
- Tap detection → tooltip (value + thời gian bucket)
- Smooth Bezier curves giữa các điểm liền kề
- Gap handling: bucket = 0 tạo khoảng trống trong đường
- Y-scale ổn định: round về bội số 5

### StepsBarChart (`Charts.kt`)
- Canvas-based bar chart
- Background bar + filled bar cho mỗi ngày
- Tự scale theo maxVal

### DeviceCard (`DeviceCard.kt`)
- Hiển thị thông tin thiết bị BLE
- Badge trạng thái màu sắc

### StatusBadge (`StatusBadge.kt`)
- Chip hiển thị trạng thái (Normal/High/Low)
- Màu sắc tùy chỉnh

### StatCard (`StatCard.kt`)
- Card hiển thị một metric (label + value)
- Dùng trong Stats Row

### SectionHeader (`SectionHeader.kt`)
- Tiêu đề phần trong danh sách settings

---

## 17. Đa ngôn ngữ (Localization)

### Ngôn ngữ hỗ trợ
- **Tiếng Anh (English)** — mặc định
- **Tiếng Việt (Vietnamese)**

### Cơ chế
- `AppStrings(language)`: class tập trung tất cả chuỗi UI, lazy computed properties
- `ProvideAppStrings(language)`: CompositionLocal cung cấp strings cho toàn bộ cây Compose
- `AppLocalizations.strings`: truy cập strings từ bất kỳ Composable nào
- Thay đổi ngôn ngữ: cập nhật ngay lập tức không cần restart

### Phạm vi dịch
Tất cả text hiển thị trên UI bao gồm: tên màn hình, label, button, dialog, thông báo, trạng thái thiết bị, thông báo lỗi, chuỗi xác nhận logout/clear data, thông tin sức khỏe.

---

## 18. Giao diện & Theme

### Chế độ theme
- **Light** — giao diện sáng
- **Dark** — giao diện tối
- **System** — theo cài đặt hệ thống Android

### Material Design 3
- `AIFDTheme`: theme chính dựa trên Material3
- `AIFDThemeExt`: màu mở rộng (`warning`, `safe`) không có trong M3 mặc định
- Dynamic color: không dùng (để đảm bảo nhất quán trên mọi thiết bị)

### Color Scheme
- **Primary**: màu chính của app
- **Error**: màu cảnh báo / HR cao
- **Tertiary**: màu bước chân
- `warning`: màu vàng cho trạng thái LOW
- `safe`: màu xanh lá cho trạng thái NORMAL

### Typography
- Display, Headline, Title, Body, Label theo Material3 Type Scale
- Font chính: hệ thống mặc định

### Edge-to-edge
- `enableEdgeToEdge()` trong MainActivity
- `navigationBarsPadding()` trên các màn hình có bottom content

---

## 19. Quyền hệ thống (Permissions)

| Quyền | Mục đích | SDK yêu cầu |
|-------|----------|------------|
| `BLUETOOTH_SCAN` | Quét BLE | API 31+ |
| `BLUETOOTH_CONNECT` | Kết nối BLE | API 31+ |
| `ACCESS_FINE_LOCATION` | BLE scan (required trước API 31) | All |
| `ACCESS_COARSE_LOCATION` | BLE scan fallback | All |
| `CALL_PHONE` | Gọi điện khẩn cấp tự động | All |
| `POST_NOTIFICATIONS` | Hiển thị notification | API 33+ |
| `FOREGROUND_SERVICE` | Chạy BLE service nền | All |
| `WAKE_LOCK` | Bật màn hình khi phát hiện ngã | All |

Tất cả quyền được yêu cầu khi khởi động (`LaunchedEffect(Unit)` trong MainActivity).  
`CALL_PHONE` được yêu cầu lại tại FallAlertScreen nếu chưa được cấp, fallback sang `ACTION_DIAL`.

---

## 20. Lưu trữ cục bộ — SharedPreferences

**File:** `aifd_prefs` (MODE_PRIVATE)

### Xác thực & Phiên
| Key | Kiểu | Mô tả |
|-----|------|-------|
| `logged_in` | Boolean | Trạng thái đăng nhập |
| `username` | String | Username hiện tại |
| `user_role` | String | WEARER hoặc CAREGIVER |

### Profile người dùng
| Key | Kiểu | Mô tả |
|-----|------|-------|
| `caregiver_name` | String | Tên người chăm sóc |
| `caregiver_phone` | String | Số ĐT khẩn cấp (dùng cho SOS call) |
| `wearer_name` | String | Tên người đeo |
| `wearer_age` | String | Tuổi người đeo |
| `wearer_gender` | String | Giới tính người đeo |

### Cài đặt ứng dụng
| Key | Kiểu | Mô tả |
|-----|------|-------|
| `theme_mode` | String | LIGHT / DARK / SYSTEM |
| `app_language` | String | ENGLISH / VIETNAMESE |

### Thiết bị BLE
| Key | Kiểu | Mô tả |
|-----|------|-------|
| `device_name` | String | Tên thiết bị đã kết nối |
| `device_mac` | String | MAC address thiết bị |

### Dữ liệu sinh hiệu
| Key | Kiểu | Mô tả |
|-----|------|-------|
| `last_heart_rate` | Int | HR cuối cùng nhận được |
| `last_spo2` | Int | SpO2 cuối cùng nhận được |
| `last_vital_timestamp` | Long | Timestamp của reading cuối |
| `hr_history` | String | CSV lịch sử HR (24 điểm) |
| `spo2_history` | String | CSV lịch sử SpO2 (24 điểm) |
| `vitals_5min` | String | VitalsStore 5-min buckets (pipe-separated) |
| `vitals_1h` | String | VitalsStore hourly buckets (pipe-separated) |

---

## 21. Tài khoản & Dữ liệu Demo

### Tài khoản thật
- Username: `dien572`, Password: `dien562003`
- Kết nối BLE thật với ESP32
- Dữ liệu thực từ cảm biến

### Tài khoản demo (000)
- Username: `000`, Password: `000`
- Sử dụng `MockDataProvider` — không cần thiết bị thật
- Mock health data: HR ~72 bpm, SpO2 ~97%, pin 85%
- Mock chart data: generated với Gaussian distribution
- Mock events: danh sách fall events giả lập
- Mock emergency contacts
- MockDataProvider.DEMO_MODE flag kiểm soát hành vi

### MockDataProvider cung cấp
- `createHealthData()`: HealthData ngẫu nhiên trong ngưỡng bình thường
- `generateChartData(mean, std, min, max, points)`: chuỗi dữ liệu giả lập với phân phối Gaussian
- `weeklySteps`: 7 ngày bước chân giả
- `fallEvents`: danh sách sự kiện ngã mẫu
- `emergencyContacts`: liên hệ khẩn cấp mẫu
- `device`: DeviceInfo giả với pin 85%, signal -55 dBm

---

## 22. Cấu trúc file nguồn

```
app/src/main/java/com/aifd/
├── MainActivity.kt                    # Entry point, permissions, theme, session
├── ble/
│   └── BleManager.kt                 # GATT client, scan, connect, parse BLE data
├── data/
│   ├── Models.kt                     # Data classes: HealthData, FallEvent, DeviceInfo, ...
│   ├── MockDataProvider.kt           # Dữ liệu giả lập cho demo
│   └── VitalsStore.kt                # Lưu trữ & tổng hợp HR/SpO2 (live + 1h + 24h)
├── navigation/
│   └── AppNavigation.kt              # NavHost, BottomNavBar, route definitions
├── service/
│   └── BleForegroundService.kt       # Foreground service, fall detection, emergency call
├── ui/
│   ├── components/
│   │   ├── Charts.kt                 # LineChart + StepsBarChart
│   │   ├── DeviceCard.kt
│   │   ├── SectionHeader.kt
│   │   ├── StatCard.kt
│   │   └── StatusBadge.kt
│   ├── localization/
│   │   └── AppStrings.kt             # Tất cả chuỗi UI (EN + VI)
│   ├── screens/
│   │   ├── AlertScreen.kt            # FallAlertScreen (SOS)
│   │   ├── DeviceDetailScreen.kt
│   │   ├── DevicePairingScreen.kt
│   │   ├── EventDetailScreen.kt
│   │   ├── HistoryScreen.kt          # Danh sách sự kiện
│   │   ├── HomeScreen.kt
│   │   ├── LoginScreen.kt
│   │   ├── MonitoringScreen.kt       # Health page (HR + SpO2 charts)
│   │   ├── ProfileScreen.kt
│   │   ├── RegisterScreen.kt
│   │   ├── RoleSelectionScreen.kt
│   │   └── SettingsScreen.kt
│   └── theme/
│       ├── Color.kt                  # Color definitions + AIFDThemeExt
│       ├── Theme.kt                  # AIFDTheme, AppThemeMode
│       └── Type.kt                   # Typography
└── viewmodel/
    ├── AlertViewModel.kt
    ├── DeviceViewModel.kt
    ├── HomeViewModel.kt
    └── MonitoringViewModel.kt
```

---

*Tài liệu được tạo từ source code thực tế — cập nhật lần cuối: 2026-05-14*
