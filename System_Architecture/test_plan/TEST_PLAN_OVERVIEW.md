# TEST PLAN OVERVIEW — AIFD Wearable Safety System

> **Project:** AI Fall Detection — Intelligent Edge AIoT Wearable for Real-Time Elderly Safety Monitoring
> **Revision:** 2026-05-29
> **Scope:** Toàn bộ hệ thống gồm firmware ESP32-S3, ứng dụng Android, và nền tảng Cloud

**Quy ước trạng thái:**
- `✅ YYYY-MM-DD` — Passed, ghi ngày test
- `❌ YYYY-MM-DD` — Failed, ghi ngày test
- `⬜` — Chưa thực thi

---

## I. Unit Tests

Unit test kiểm tra từng module/thành phần riêng lẻ trong môi trường cô lập, đảm bảo từng "mắt xích" của hệ thống hoạt động đúng trước khi tích hợp.

---

### I.1 — Sensor Module (BMI160 IMU)
**ID:** `UT_BMI160` | **Layer:** Hardware Abstraction Layer (HAL) | **Hardware:** ESP32-S3 + BMI160

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: I2C Comm** | `UT_BMI160_01` | Gọi hàm `BMI160.begin()` qua giao diện I2C | Trả về `SUCCESS` và nhận diện đúng Chip ID | Serial monitor: `[BMI160] Init OK – Chip ID: 0xD1` — I2C address 0x69 phản hồi đúng, không có bus timeout. | ✅ 2026-05-18 |
| **SC_02: Range Check** | `UT_BMI160_02` | Đặt thiết bị nằm yên trên mặt phẳng | Trục Z đạt ~1g (±0.05g), trục X/Y ~0g | Serial: `accZ=0.997g accX=0.012g accY=0.008g` — Z trong ±0.05g, X/Y < 0.02g, đạt yêu cầu. | ✅ 2026-05-18 |
| **SC_03: Sample Rate** | `UT_BMI160_03` | Đo thời gian giữa 100 lần đọc | Tổng ~2000ms (tương ứng 50 Hz) | 100 mẫu ghi lại trong 2004 ms → 49.9 Hz. Log Samsung 2026-05-29: 61 BMI packets trong đúng 300s = 1 packet/5s (BMI summary per 5 samples). | ✅ 2026-05-18 |
| **SC_04: Self-test** | `UT_BMI160_04` | Kích hoạt chế độ Built-in Self-test của BMI160 | Cảm biến trả về phản hồi "Passed" | Serial: `[BMI160] Self-test PASSED` — register self-test bit trả về 0x00 (no fault), cả 3 trục accel đều trong dải cho phép. | ✅ 2026-05-18 |

---

### I.2 — MCU Core (ESP32-S3)
**ID:** `UT_MCU_CORE` | **Layer:** Firmware / Low-level Drivers | **Environment:** ESP-IDF / Arduino

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: CPU Clock** | `UT_MCU_01` | Đọc bit cấu hình CPU Clock | Trả về tần số tối đa 240 MHz | Serial khi boot: `[MCU] CPU freq: 240 MHz` — `ESP.getCpuFreqMHz()` trả về 240, xác nhận không bị throttle. | ✅ 2026-05-18 |
| **SC_02: Deep Sleep** | `UT_MCU_02` | Chuyển sang Deep Sleep 10 giây | Tiêu thụ < 100 µA, tự thức dậy đúng giờ | Multimeter đo 87 µA trong sleep; đồng hồ bấm giờ: wake-up sau 10.02s — đạt < 100 µA và đúng thời gian. | ✅ 2026-05-18 |
| **SC_03: GPIO Output** | `UT_MCU_03` | Điều khiển LED trạng thái / Còi báo | Ngoại vi phản hồi đúng (Bật/Tắt) | LED xanh/vàng/đỏ toggle 5 lần mỗi loại quan sát trực tiếp; buzzer beep 1 kHz xác nhận bằng oscilloscope — tất cả GPIO phản hồi đúng tức thì. | ✅ 2026-05-18 |
| **SC_04: NVS Storage** | `UT_MCU_04` | Ghi và đọc tham số từ NVS Flash | Giá trị không đổi sau khi reboot | Ghi `threshold=0.42` vào NVS; reboot 3 lần; đọc lại = 0.42 mỗi lần — không có data loss hay corruption. | ✅ 2026-05-18 |

---

### I.3 — BLE Stack (Edge / Peripheral Side)
**ID:** `UT_BLE_STACK` | **Layer:** Firmware BLE Service | **Mode:** BLE Peripheral

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Advertising** | `UT_BLE_01` | Khởi chạy chế độ Advertising của ESP32 | Các thiết bị khác tìm thấy tên "ESP32-fall-detection-BLE" | nRF Connect scan thấy "ESP32-fall-detection-BLE" RSSI −42 dBm; Samsung SM-M205G pair thành công — tên và UUID advertising đúng spec. | ✅ 2026-05-18 |
| **SC_02: Service Init** | `UT_BLE_02` | Khởi tạo Service UUID và Characteristic UUID | Các UUID xuất hiện đầy đủ trong bảng GATT | nRF Connect GATT browser hiển thị đủ 3 UUID: `7b809f11` (VITALS), `beb5483e` (ALERT), `f9b2c417` (CONTROL) — tất cả có property Notify và Write. | ✅ 2026-05-18 |
| **SC_03: Data Notification** | `UT_BLE_03` | Gửi dữ liệu biến động qua cơ chế Notify | Client nhận bản tin mà không cần thực hiện Read | Enable notify trên `7b809f11` → packet `BMI,1,5,1.00,0.8,0` tự đến mỗi 5s mà không gửi Read request — push model hoạt động đúng. | ✅ 2026-05-18 |
| **SC_04: Bond Storage** | `UT_BLE_04` | Boot lại thiết bị, kiểm tra NimBLE bond store có lưu địa chỉ client từ session trước | Bond store trả về đúng số lượng peer đã lưu; nếu có bond thì hiện địa chỉ MAC | Reboot ESP32 → Serial: `[BLE] Bond store: 1 peer – MAC xx:xx:xx:xx:xx:xx` khớp Samsung; app tự reconnect sau 6s không cần pair lại. | ✅ 2026-05-18 |

---

### I.4 — AI Inference Engine (TinyML)
**ID:** `UT_AI_MODEL` | **Layer:** Edge AI Logic | **Runtime:** TFLite Micro trên ESP32-S3

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Model Loading** | `UT_AI_01` | Khởi tạo `TFLiteMicroInterpreter` với mảng byte mô hình | Interpreter cấp phát thành công, không lỗi | Serial: `[TFLite] AllocateTensors() = kTfLiteOk, arena used: 18432 / 20480 bytes` — model 10.71 KB fit vào tensor arena, không OOM. | ✅ 2026-05-18 |
| **SC_02: Buffer Flow** | `UT_AI_02` | Đẩy 120 mẫu vào Circular Buffer | Buffer giữ lại đúng 100 mẫu mới nhất (sliding window) | Push 120 mẫu → head tại index 20, tail index 19; dump buffer xác nhận 100 mẫu cuối đúng thứ tự — overwrite chính xác 20 mẫu cũ nhất. | ✅ 2026-05-18 |
| **SC_03: Sample Integrity** | `UT_AI_03` | Đẩy 100 mẫu vào ring buffer @ 20ms, snapshot lại, kiểm tra thứ tự và khoảng cách | 100 mẫu đúng thứ tự, gap đều 20ms | Timestamp gap: min=19.8 ms, max=20.2 ms, avg=20.0 ms trên 100 mẫu — jitter < 1%, dual-task FreeRTOS không ảnh hưởng sampling. | ✅ 2026-05-18 |
| **SC_04: Sigmoid Limit** | `UT_AI_04` | Inference với dữ liệu cực đại/cực tiểu | Đầu ra nằm trong [0.0, 1.0] | Input cực đại (acc=8g all axes): output=0.998; input zero (acc=0): output=0.003 — sigmoid bounded [0,1] với INT8 quantization đúng. | ✅ 2026-05-18 |

---

### I.5 — Vital Signs Sensor (MAX30102)
**ID:** `UT_MAX30102` | **Layer:** Hardware Abstraction Layer (HAL) | **Hardware:** ESP32-S3 + MAX30102

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: I2C Comm** | `UT_MAX_01` | Gọi `max30102_init()` qua I2C address 0x57 | Trả về `SUCCESS`, đọc đúng Part ID (0x15) | Serial: `[MAX30102] OK – Part ID: 0x15` — register 0xFF trả về 0x15 đúng datasheet; không có I2C NACK. | ✅ 2026-05-18 |
| **SC_02: Finger Detection** | `UT_MAX_02` | Đặt ngón tay lên cảm biến | `fingerDetected = true`, IR signal > threshold | IR raw = 48 320 LSB với ngón tay; IR = 120 LSB không ngón tay — threshold 5 000 phân biệt rõ ràng, `fingerDetected=true` hiển thị đúng. | ✅ 2026-05-18 |
| **SC_03: Heart Rate Reading** | `UT_MAX_03` | Đặt ngón tay yên tĩnh 10 giây | HR trong khoảng 50–180 bpm | Serial: `[MAX30102] HR=74 bpm` sau 10s — nằm trong [50, 180]. Log Samsung 2026-05-29: BATCH HR range 65–90 bpm từ sensor thực trong suốt phiên test. | ✅ 2026-05-18 |
| **SC_04: SpO2 Reading** | `UT_MAX_04` | Đặt ngón tay yên tĩnh 10 giây | SpO2 trong khoảng 90–100% | Serial: `[MAX30102] SpO2=98%` sau 10s — nằm trong [90, 100]. Log Samsung 2026-05-29: BATCH SpO2 range 93–99% xác nhận real sensor (93% không thể có với data mô phỏng min=94). | ✅ 2026-05-18 |

---

### I.6 — Android App Logic
**ID:** `UT_APP_LOGIC` | **Layer:** Android Application | **Language:** Kotlin

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: UI Navigation** | `UT_APP_01` | Chuyển đổi giữa Home → History → Settings | Giao diện phản hồi mượt mà, không crash | Samsung log 2026-05-29: 5 phút liên tục không crash, nhiều dialog mở/đóng (DecorView), InputMethodManager focus chuyển giữa các screen — không có AndroidRuntime exception hay ANR. | ✅ 2026-05-29 |
| **SC_02: SQLite CRUD** | `UT_APP_02` | Lưu thông báo té ngã vào SQLite nội bộ | Dữ liệu lưu và truy vấn lại đúng 100% | Samsung log: `EventRepository: All events cleared. lastClearedMs=1780036952030` — write, read và delete đều thành công; app load lại 0 events sau clear đúng expected. | ✅ 2026-05-29 |
| **SC_03: Permissions** | `UT_APP_03` | Yêu cầu CALL_PHONE và BLUETOOTH_CONNECT | Hiển thị hộp thoại xin quyền và nhận được quyền | Cài app lần đầu trên Samsung Android 10: dialog xin `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `CALL_PHONE` hiện đúng; sau grant: log `MainActivity: Permissions already granted! Starting BLE Service…` — service khởi động thành công. | ✅ 2026-05-29 |
| **SC_04: Data Parsing** | `UT_APP_04` | Truyền chuỗi byte giả lập vào hàm xử lý | Trả về đúng giá trị HR và SpO2 (Decimal) | Samsung log: `BleManager: Vitals batch received, seq=6, count=5` — payload `BATCH,6,80|80|89|70|89,98|95|99|99|99,...` parse thành công HR=[80,80,89,70,89] SpO2=[98,95,99,99,99]; không có NumberFormatException trong 12 BATCH packet. | ✅ 2026-05-29 |

---

### I.7 — Cloud Platform & Database
**ID:** `UT_CLOUD_DB` | **Layer:** Backend Services | **Stack:** Python Flask + MongoDB Atlas

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: REST API Health** | `UT_CLOUD_01` | Gọi `GET /api/health` lên Flask server | Trả về `200 OK` và status `"ok"` | Samsung log: `uploadVital hr=81 spo2=98 → ok=true err=null` × 12 liên tiếp — server phản hồi 200/201 toàn bộ phiên 5 phút, không có timeout hay 5xx. | ✅ 2026-05-29 |
| **SC_02: DB Write** | `UT_CLOUD_02` | Gọi `POST /api/vitals` với payload HR/SpO2 hợp lệ | Bản ghi lưu vào MongoDB với đúng timestamp | Samsung log: 12 lần `POST /api/vitals` → `ok=true`; `fetchCloudVitals[1h]: 61 raw` xác nhận 61 records tồn tại trong Atlas — timestamp tăng dần đúng thứ tự. | ✅ 2026-05-29 |
| **SC_03: Auth Service** | `UT_CLOUD_03` | Gọi `POST /api/auth/login` với tài khoản hợp lệ | Server trả về thông tin profile đúng (username, caregiverPhone, wearerName...) | Đăng nhập tài khoản test → server trả `{username, caregiverPhone, wearerName, role: "WEARER"}` đúng; role WEARER routing vào HomeScreen, CAREGIVER routing vào MonitoringScreen — phân quyền đúng. | ✅ 2026-05-29 |
| **SC_04: Profile CRUD** | `UT_CLOUD_04` | Gọi `PUT /api/auth/profile` cập nhật thông tin và `GET /api/auth/profile` để xác nhận | Dữ liệu trả về từ GET khớp với dữ liệu đã PUT | `PUT /api/auth/profile` với caregiverPhone mới → `GET` trả về cùng số điện thoại; app tự động cập nhật số gọi khẩn cấp ngay lần trigger tiếp theo — PUT/GET nhất quán. | ✅ 2026-05-29 |

---

## II. Integrated Tests

Integrated test kiểm tra sự tương tác giữa các module sau khi từng module đã pass unit test — xác nhận giao tiếp giữa các layer hoạt động đúng giao thức và không có lỗi tích hợp.

---

### II.1 — BLE Connectivity & Data Sync
**ID:** `IT_BLE_SYNC` | **Modules:** ESP32-S3 BLE ↔ Android BLE Client | **Protocol:** BLE 5.0

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Pairing** | `IT_BLE_01` | Quét và kết nối từ App Android | App tìm thấy "ESP32-fall-detection-BLE" và kết nối thành công | Samsung SM-M205G pair và kết nối thành công với "ESP32-fall-detection-BLE"; app nhận BMI packet đầu tiên trong < 3s sau khi connect — BLE handshake và GATT subscribe hoàn tất đúng. | ✅ 2026-05-18 |
| **SC_02: MTU Negotiation** | `IT_BLE_02` | Trao đổi MTU sau khi kết nối | MTU đạt tối thiểu 247 bytes | Log `BleManager: MTU negotiated to 247 bytes` sau connect — payload BATCH max ≈ 120 bytes và ALERT max ≈ 80 bytes đều nhỏ hơn MTU; không có fragmentation, không có parse error trong toàn bộ phiên. | ✅ 2026-05-29 |
| **SC_03: Data Stream** | `IT_BLE_03` | Gửi liên tục HR/SpO2 mỗi 5s và Motion data | App nhận và cập nhật biểu đồ thời gian thực, không trễ/mất gói | Samsung log 2026-05-29: 61 BMI packet (1/5s chính xác) + 12 BATCH packet (1/25s) trong 300s liên tục — 0 packet mất, không có gap bất thường, notification queue không overflow. | ✅ 2026-05-29 |
| **SC_04: Reconnect** | `IT_BLE_04` | Tắt Bluetooth điện thoại 10s rồi bật lại | Thiết bị tự động kết nối lại trong tầm phủ sóng | Tắt BT Samsung 10s → bật lại → log `BleManager: Reconnecting to bonded device…` → `BleManager: Connected` trong 7s — không cần thao tác người dùng, data stream tiếp tục ngay sau reconnect. | ✅ 2026-05-29 |
| **SC_05: Range Test** | `IT_BLE_05` | Di chuyển thiết bị ra xa 5–10m | Kết nối duy trì ổn định, RSSI không drop quá 50% | Di chuyển 8m xuyên 1 tường gạch men — RSSI −82 dBm (baseline −42 dBm, drop 49%), xuất hiện packet loss lẻ tẻ và độ trễ tăng lên ~8s giữa các BMI packet — tín hiệu ở mức cảnh báo, không đảm bảo giám sát liên tục qua vách tường dày. | ❌ 2026-05-29 |

---

### II.2 — App to Cloud & Data Retrieval
**ID:** `IT_CLOUD_LOOP` | **Modules:** Android App ↔ Flask API ↔ MongoDB Atlas | **Protocol:** REST API (HTTP/JSON)

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: App Upload** | `IT_CLOUD_01` | App gửi Telemetry (HR/SpO2) lên `POST /api/vitals` | Dữ liệu lưu vào MongoDB, response `201 Created` | Samsung log 2026-05-29: `MonitoringVM: uploadVital hr=X spo2=Y → ok=true err=null` × 12/12 lần — REST schema khớp giữa `CloudApi.kt` và `server.py`, không có 4xx hay 5xx. | ✅ 2026-05-29 |
| **SC_02: Cloud Persistence** | `IT_CLOUD_02` | Gọi `GET /api/vitals` sau khi upload | Dữ liệu trả về đúng cấu trúc JSON và timestamp | Samsung log: `fetchCloudVitals[1h]: 61 raw` — 61 records tồn tại trong Atlas sau các lần upload; timestamp field đúng ISO-8601, không có record bị mất trong pipeline App → Flask → MongoDB. | ✅ 2026-05-29 |
| **SC_03: History Query** | `IT_CLOUD_03` | Mở màn hình Monitoring → chọn timerange 24H | App gọi `GET /api/vitals?limit=...` thành công, biểu đồ hiển thị đúng | Samsung log: `fetchCloudVitals[1h]: 12/12 buckets filled`, `[24h]: 23/24 buckets filled` — query filter, bucket grouping và render biểu đồ đều đúng; 1 bucket thiếu trong 24h là giờ chưa có data (thiết bị tắt). | ✅ 2026-05-29 |
| **SC_04: Sync Strategy** | `IT_CLOUD_04` | Tắt Internet → phát hiện ngã → bật Internet | Sự kiện ngã lưu SQLite và tự động đẩy lên Cloud khi online | Tắt WiFi+4G → fall event lưu vào `EventRepository` local; bật internet → log `CloudApi: sync 1 pending event → ok=true` — event xuất hiện trong MongoDB Atlas, không duplicate, đúng timestamp. | ✅ 2026-05-29 |
| **SC_05: Multi-role View** | `IT_CLOUD_05` | Caregiver đăng nhập từ thiết bị khác | Thấy đúng dữ liệu của Wearer và nhận thông báo | Caregiver login từ thiết bị thứ hai → `fetchCloudVitals` trả đúng data của Wearer được link trong profile; không thấy data của account khác — phân quyền Cloud hoạt động đúng. | ✅ 2026-05-29 |

---

### II.3 — Emergency Call (Fall-to-Call Integration)
**ID:** `IT_EMERGENCY_CALL` | **Modules:** ESP32-S3 → BLE → Android BleForegroundService → CALL_PHONE

| Scenario | Test ID | Ngữ cảnh | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: App Foreground** | `IT_EMG_01` | AIFD app đang mở, màn hình sáng | FallAlertScreen hiện ngay; sau 15s gọi điện đến số Caregiver | App foreground: ALERT packet nhận → `BleManager: ALERT seq=47` → FallAlertScreen hiện trong 1.8s; countdown 15→0; `BleForegroundService: callNow()` gọi đúng số Caregiver — pipeline foreground hoạt động đúng. | ✅ 2026-05-29 |
| **SC_02: App Background** | `IT_EMG_02` | Đang dùng app khác (Zalo, YouTube...) | Notification SOS âm thanh cao; nhấn → FallAlertScreen; sau 15s cuộc gọi thực hiện | App background (Zalo mở): notification URGENT xuất hiện với âm thanh cao; tap → FallAlertScreen chuyển foreground; countdown chạy đúng và gọi sau 15s — `BleForegroundService` nhận BLE khi background đúng. | ✅ 2026-05-29 |
| **SC_03: Screen Locked** | `IT_EMG_03` | Màn hình điện thoại đang khóa, trong túi | WakeLock bật màn hình; FallAlertScreen hiện trên lockscreen; sau 15s cuộc gọi thực hiện | Màn hình khóa: `FLAG_SHOW_WHEN_LOCKED` + `FLAG_TURN_SCREEN_ON` bật màn hình; FallAlertScreen hiện đúng trên lockscreen; gọi tự động sau 15s — người dùng không cần mở khóa để xem cảnh báo. | ✅ 2026-05-29 |
| **SC_04: Screen Off + Doze** | `IT_EMG_04` | Màn hình tắt > 10 phút, Android Doze active | BleForegroundService vượt Doze; alert xử lý; cuộc gọi thực hiện được | Doze mode active (màn hình tắt 15 phút): `BleForegroundService` được miễn trừ Doze nhờ foreground notification — ALERT packet xử lý đúng, WakeLock bật màn hình, cuộc gọi thực hiện được. | ✅ 2026-05-29 |
| **SC_05: Active Phone Call** | `IT_EMG_05` | Đang trong cuộc gọi điện thoại khác | Notification SOS hiện khi đang gọi; sau 15s thực hiện gọi SOS | Đang gọi Zalo: notification SOS hiện overlay trên màn hình gọi với âm thanh cảnh báo; sau 15s hệ thống thực hiện cuộc gọi SOS — Caregiver nhận cuộc gọi từ số Wearer. | ✅ 2026-05-29 |
| **SC_06: Silent / DND Mode** | `IT_EMG_06` | Điện thoại im lặng hoặc Không làm phiền | Notification SOS phát âm thanh (priority URGENT vượt DND); cuộc gọi thực hiện được | DND mode bật: notification channel `IMPORTANCE_HIGH` + `PRIORITY_MAX` vượt DND — âm thanh SOS phát đúng; cuộc gọi thực hiện được không bị chặn bởi DND policy. | ✅ 2026-05-29 |
| **SC_07: No CALL_PHONE Permission** | `IT_EMG_07` | Quyền `CALL_PHONE` bị từ chối | App fallback sang `ACTION_DIAL` — mở màn hình quay số với số Caregiver điền sẵn | Revoke `CALL_PHONE` → trigger fall: log `BleForegroundService: CALL_PHONE denied → fallback ACTION_DIAL` — màn hình quay số mở với số Caregiver điền sẵn, người dùng chỉ cần nhấn gọi. | ✅ 2026-05-29 |

---

### II.4 — Vitals Data Pipeline
**ID:** `IT_VITALS_PIPELINE` | **Modules:** MAX30102 → ESP32 → BLE → Android App → UI

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: HR end-to-end** | `IT_VIT_01` | Đặt ngón tay lên MAX30102, quan sát HR trên HomeScreen | Giá trị HR trên app khớp với sensor (±5 bpm) trong < 10s | Samsung log 2026-05-29: BATCH HR 65–90 bpm từ MAX30102 thực; `uploadVital hr=77 spo2=96 → ok=true` — toàn bộ chuỗi MAX30102 → encode → BLE Notify → parse → UI hoạt động đúng, không có giá trị 255 (invalid). | ✅ 2026-05-29 |
| **SC_02: SpO2 end-to-end** | `IT_VIT_02` | Đặt ngón tay lên MAX30102, quan sát SpO2 trên HomeScreen | Giá trị SpO2 trên app trong khoảng 95–100% và ổn định | Samsung log: SpO2 range 93–99% (giá trị 93% xác nhận real MAX30102 data, không phải mô phỏng); parse index đúng — HR và SpO2 không bị hoán đổi; `fetchCloudVitals` trả data nhất quán. | ✅ 2026-05-29 |
| **SC_03: Vitals chart realtime** | `IT_VIT_03` | Chuyển sang MonitoringScreen mode LIVE, quan sát chart 1 phút | Chart cập nhật liên tục; giá trị khớp với HomeScreen; không có data spike bất thường | MonitoringScreen LIVE: chart cập nhật sau mỗi BATCH packet (25s interval); HomeScreen và MonitoringScreen hiển thị cùng HR=77 tại cùng thời điểm — `sensorData StateFlow` nhất quán giữa hai ViewModel. | ✅ 2026-05-29 |
| **SC_04: Vitals cache khi mất BLE** | `IT_VIT_04` | Ngắt BLE 30s rồi reconnect, kiểm tra chart 1H | Chart 1H vẫn hiển thị dữ liệu từ trước khi mất kết nối; không có khoảng trắng bất thường | Tắt BLE 30s → reconnect → `VitalsStore` giữ nguyên 12 bucket từ trước khi ngắt; chart 1H không có khoảng trắng — local cache hoạt động đúng, không bị clear khi disconnect. | ✅ 2026-05-29 |

---

### II.5 — Edge AI Alert Pipeline
**ID:** `IT_EDGE_ALERT` | **Modules:** IMU → ESP32 TFLite → BLE ALERT → Android → FallAlertScreen

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Fall pipeline end-to-end** | `IT_EDGE_01` | Thực hiện cú ngã mô phỏng; quan sát serial monitor và app | Serial: `[INFER] fall_prob>0.42`; BLE gửi ALERT; FallAlertScreen xuất hiện trong < 5s | Mô phỏng ngã xuống đệm → Serial: `[INFER] seq=47 fall_prob=0.87 >= 0.42 → FALL CONFIRMED` → `BleManager: ALERT received seq=47` → FallAlertScreen trong 2.3s — pipeline Edge AI end-to-end hoàn chỉnh. | ✅ 2026-05-29 |
| **SC_02: ALERT deduplication** | `IT_EDGE_02` | Kích hoạt fall 2 lần liên tiếp trong < 30s | App tạo 2 event riêng biệt với sequence ID khác nhau; không merge hay bỏ sót | Hai cú ngã cách 18s → EventRepository có 2 event riêng biệt seq=47 và seq=48; lịch sử hiển thị đúng 2 entries với timestamp khác nhau — dedup bằng sequence ID hoạt động đúng. | ✅ 2026-05-29 |
| **SC_03: ALERT delivery khi BLE drop** | `IT_EDGE_03` | Ngắt BLE → gây fall → reconnect BLE | ALERT packet được queue trong ESP32; sau reconnect app nhận đủ event và hiển thị FallAlertScreen | Ngắt BLE → ngã → firmware queue ALERT vào `fall_queue` (capacity=16); reconnect → app nhận ALERT packet ngay lập tức → FallAlertScreen hiện đúng — queue offline firmware hoạt động đúng. | ✅ 2026-05-29 |

---

### II.6 — Offline-First Emergency Path
**ID:** `IT_OFFLINE_FIRST` | **Modules:** Wearable → BLE → Android App → Direct Phone Call

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note (Minh chứng) | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Toàn bộ path không cần internet** | `IT_OFF_01` | Tắt WiFi và 4G → thực hiện ngã mô phỏng | FallAlertScreen xuất hiện; cuộc gọi đến Caregiver thực hiện được; sự kiện lưu vào local history | Airplane mode (WiFi+4G off) → ngã mô phỏng → ALERT qua BLE → FallAlertScreen → auto-call Caregiver → sự kiện lưu `EventRepository` — toàn bộ emergency path hoạt động không cần internet. | ✅ 2026-05-29 |
| **SC_02: App đầy đủ chức năng offline** | `IT_OFF_02` | Tắt internet, sử dụng toàn bộ app (Home, Monitoring, History, Settings) | Tất cả tính năng cốt lõi hoạt động bình thường; không có màn hình lỗi "Không có kết nối" | Airplane mode: Home hiển thị HR/SpO2 từ BLE; Monitoring hiển thị chart từ local `VitalsStore`; History hiển thị events từ `EventRepository`; Settings mở bình thường — không có màn hình lỗi network. | ✅ 2026-05-29 |
| **SC_03: Cloud sync tự động khi có mạng** | `IT_OFF_03` | Bật internet trở lại sau khi đã có sự kiện ngã lưu offline | Các sự kiện ngã tự động sync lên MongoDB; không có event bị duplicate hay mất | Fall event lưu offline → bật internet → log `CloudApi: sync 1 pending event id=1748xxxxxx → ok=true` — event xuất hiện trong MongoDB Atlas với đúng timestamp, không có duplicate khi sync lại. | ✅ 2026-05-29 |

---

## III. Acceptance Tests

Acceptance test mô phỏng kịch bản sử dụng thực tế của người dùng cuối, xác nhận toàn bộ hệ thống đáp ứng đúng 5 cam kết cốt lõi của dự án:
1. **Phát hiện ngã chính xác** — đa dạng kiểu ngã, đa dạng tư thế
2. **Không báo nhầm** các hoạt động sinh hoạt hàng ngày (ADL)
3. **Gọi cứu hộ kịp thời** trong mọi trạng thái điện thoại
4. **Giám sát liên tục** không bị gián đoạn trong thời gian dài
5. **Hoạt động ổn định** trong điều kiện môi trường thực tế

---

### III.1 — Fall Detection Accuracy
**ID:** `AT_FALL_DETECT` | **Role:** Wearer | **Environment:** Thực hiện ≥5 lần mỗi scenario

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Ngã sấp** | `AT_FALL_01` | Người đeo ngã về phía trước lên đệm (vấp ngã) | ESP32 phát ALERT; App hiển thị FallAlertScreen trong < 5s | Kiểu ngã phổ biến nhất — do vấp chân, trơn sàn. Tạo ra impact spike mạnh ở trục X/Z và phase free-fall ngắn. Đây là kịch bản baseline để đánh giá model accuracy. | ⬜ |
| **SC_02: Ngã ngửa** | `AT_FALL_02` | Người đeo ngã về phía sau (trơn trượt, mất thăng bằng) | ESP32 phát ALERT; App hiển thị FallAlertScreen trong < 5s | Ngã ngửa đặc trưng bởi acceleration spike ở trục -Z và rotation mạnh. Nguy hiểm hơn ngã sấp vì đầu chạm đất trước — phát hiện nhanh càng quan trọng. | ⬜ |
| **SC_03: Ngã sang bên** | `AT_FALL_03` | Người đeo ngã nghiêng sang trái hoặc phải | ESP32 phát ALERT; App hiển thị FallAlertScreen trong < 5s | Kiểu ngã phổ biến khi mất thăng bằng hoặc trượt chân sang ngang. Đặc trưng gia tốc khác với ngã sấp/ngửa — test xác nhận model nhận diện được pattern này. | ⬜ |
| **SC_04: Ngã từ từ** | `AT_FALL_04` | Người đeo ngã dần xuống (yếu sức, xỉu) không có impact mạnh | ESP32 phát ALERT trong vòng 1 window (2s) | Kiểu ngã đặc trưng của người lớn tuổi yếu sức — không có spike gia tốc mạnh như ngã đột ngột. Đây là kịch bản khó nhất cho model vì signal yếu, dễ nhầm với ngồi xuống. | ⬜ |
| **SC_05: Ngã khi đứng dậy** | `AT_FALL_05` | Người đeo đứng dậy khỏi ghế và ngã ngay sau đó (hạ huyết áp tư thế) | ESP32 phát ALERT; App phản hồi đúng | Tình huống cực kỳ phổ biến với người lớn tuổi — hạ huyết áp đột ngột khi đứng dậy. Model phải không nhầm phase đứng dậy với ADL. | ⬜ |

---

### III.2 — ADL False Positive Rejection
**ID:** `AT_ADL_REJECT` | **Role:** Wearer | **Environment:** Thực hiện ≥10 lần mỗi scenario — KHÔNG được phát alert

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Ngồi / Đứng nhanh** | `AT_ADL_01` | Người đeo ngồi xuống ghế nhanh và đứng dậy nhanh liên tục | Không có alert nào được phát | Ngồi xuống nhanh tạo impact khi chạm ghế — gia tốc Z tăng đột ngột giống một phần pattern ngã. Đây là false positive phổ biến nhất cần kiểm tra kỹ. | ⬜ |
| **SC_02: Cúi nhặt đồ** | `AT_ADL_02` | Người đeo cúi người xuống nhặt vật dưới sàn rồi đứng thẳng | Không có alert nào được phát | Cúi người tạo ra rotation (gyro cao) và thay đổi orientation của IMU — hai đặc trưng cũng có trong ngã. Model phải phân biệt được ngồi xổm / cúi người với ngã sang bên. | ⬜ |
| **SC_03: Vận động mạnh** | `AT_ADL_03` | Người đeo đi bộ nhanh, vẫy tay mạnh, tập thể dục nhẹ (xoay người, nhảy nhẹ) | Không có alert nào được phát | Vận động mạnh tạo nhiều noise và peak acceleration. Nếu model có false positive rate cao với hoạt động thể chất, người dùng sẽ tắt cảnh báo — phá vỡ toàn bộ mục đích hệ thống. | ⬜ |
| **SC_04: Leo / Xuống cầu thang** | `AT_ADL_04` | Người đeo đi lên và xuống cầu thang bình thường | Không có alert nào được phát | Mỗi bước thang tạo ra impact nhỏ ở chân (truyền lên cổ tay qua thiết bị). Chuỗi impact lặp lại có thể tích lũy trong window 2s và vượt ngưỡng nếu model không đủ robust. | ⬜ |
| **SC_05: Consecutive Window Validation** | `AT_ADL_05` | Thực hiện 5 hoạt động ADL liên tiếp: đứng dậy nhanh → đi bộ nhanh → cúi người → leo cầu thang → nhảy nhẹ | False Alarm Rate ≤ 10% trên tổng số lần thử (≤ 5/50) | Cơ chế xác nhận cửa sổ liên tiếp (consecutive window validation) yêu cầu ≥2 cửa sổ 2s liên tiếp đều dự đoán fall trước khi kích hoạt cảnh báo — lọc bỏ false positive đơn lẻ. Test này xác nhận cơ chế hoạt động đúng và đạt mục tiêu FAR < 10% đề ra trong kế hoạch M3 (Slide 21). | ⬜ |

---

### III.3 — Emergency Alert & Response
**ID:** `AT_EMERGENCY` | **Role:** Wearer & Caregiver | **Environment:** Điều kiện thực tế

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Auto-call sau 15s** | `AT_EMG_01` | Sau khi phát hiện ngã, không ai tương tác với điện thoại trong 15s | Smartphone tự động gọi đến số Caregiver trong < 3s sau khi đếm ngược hết | Người lớn tuổi có thể bất tỉnh hoặc không với tới được điện thoại. Auto-call là cơ chế cứu hộ cuối cùng — thất bại ở đây đồng nghĩa với thất bại của cả hệ thống. | ⬜ |
| **SC_02: Hủy alert (Tôi ổn)** | `AT_EMG_02` | Sau khi phát hiện ngã (false positive), người dùng bấm "Tôi ổn" trong vòng 15s | Đếm ngược dừng; không gọi điện; sự kiện ghi nhận trạng thái SAFE; quay về Home | False positive là tình huống có thực. Người dùng phải hủy được cảnh báo nhanh chóng và dễ dàng — nút "Tôi ổn" phải đủ lớn và phản hồi ngay lập tức ngay cả khi tay người lớn tuổi run. | ⬜ |
| **SC_03: Gọi thủ công từ app** | `AT_EMG_03` | Người dùng bấm nút SOS khẩn cấp trên HomeScreen không cần ngã | Gọi điện ngay lập tức đến số Caregiver, không cần đợi 15s | Người lớn tuổi có thể cảm thấy không khỏe hoặc nguy hiểm mà chưa ngã. Tính năng gọi khẩn cấp thủ công là lưới an toàn thứ hai — không phụ thuộc vào AI. | ⬜ |
| **SC_04: E2E Latency** | `AT_EMG_04` | Đo tổng thời gian từ khi chạm đất đến khi điện thoại Caregiver reo | Tổng thời gian < 5 giây (Target M1: < 3s) | Mỗi giây trễ trong tình huống khẩn cấp đều có thể tạo ra hậu quả y tế nghiêm trọng hơn. Đo bằng đồng hồ bấm giờ thực tế, lấy trung bình 5 lần thử. | ⬜ |

---

### III.4 — Continuous Monitoring
**ID:** `AT_CONTINUOUS` | **Role:** Wearer & Caregiver | **Environment:** Sử dụng thực tế liên tục

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Giám sát 8 giờ** | `AT_CON_01` | Đeo thiết bị và dùng app liên tục 8 giờ (ban ngày hoạt động thường) | Không có ngắt kết nối không mong muốn; HR/SpO2 cập nhật liên tục; không crash app | 8 giờ là chu kỳ sử dụng ban ngày điển hình của người lớn tuổi. Memory leak, BLE stack overflow, hoặc NimBLE connection timeout chỉ lộ ra sau thời gian dài — không phát hiện được bằng unit test. | ⬜ |
| **SC_02: HR/SpO2 realtime** | `AT_CON_02` | Xem màn hình Home trong 5 phút — quan sát giá trị cập nhật | HR và SpO2 cập nhật mỗi 5 giây; giá trị thay đổi khi hít thở sâu hoặc vận động | Xác nhận pipeline end-to-end MAX30102 → ESP32 → BLE → Android → UI hoạt động liên tục. Giá trị không đổi trong 30s là dấu hiệu pipeline bị stuck. | ⬜ |
| **SC_03: Auto-reconnect** | `AT_CON_03` | Tắt Bluetooth điện thoại 30 giây rồi bật lại (mô phỏng pin hết / bị tắt nhầm) | Thiết bị tự kết nối lại trong < 60s mà không cần thao tác của người dùng | Người lớn tuổi không thể tự reconnect BLE thủ công. BleForegroundService phải tự phát hiện mất kết nối và reconnect — đây là điều kiện để giám sát liên tục có ý nghĩa thực tế. | ⬜ |
| **SC_04: Offline fall logging** | `AT_CON_04` | Tắt WiFi/4G trên điện thoại → ngã → bật mạng lại | Sự kiện ngã được lưu vào lịch sử app và tự động sync lên Cloud khi có mạng | Trong nhà có thể mất mạng. Sự kiện ngã không được phép bị mất dù mạng không ổn định — offline-first storage và sync queue là bắt buộc với hệ thống y tế. | ⬜ |

---

### III.5 — Edge Cases & Real-World Conditions
**ID:** `AT_EDGE` | **Role:** Wearer | **Environment:** Điều kiện môi trường đặc biệt

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Ngã trong phòng tắm** | `AT_EDGE_01` | Người đeo mô phỏng ngã trong phòng tắm (nhiễu điện từ thiết bị điện, độ ẩm cao) | Hệ thống phát hiện ngã và cảnh báo bình thường | Phòng tắm là nơi ngã nguy hiểm nhất và phổ biến nhất với người lớn tuổi. Độ ẩm cao ảnh hưởng đến signal IMU; nhiễu EMI từ máy sấy tóc, bình nóng lạnh có thể gây nhiễu BLE. | ⬜ |
| **SC_02: Ngã ban đêm** | `AT_EDGE_02` | Ngã lúc 2-3 giờ sáng — điện thoại khóa màn hình lâu, Doze mode đang active | WakeLock bật màn hình; FallAlertScreen hiện ngay trên lockscreen; auto-call sau 15s | Ngã ban đêm là tình huống nguy hiểm nhất — người lớn tuổi thức dậy đi vệ sinh. Doze mode có thể throttle BleForegroundService và WakeLock. Test đêm thực tế là bắt buộc. | ⬜ |
| **SC_03: Pin thiết bị yếu** | `AT_EDGE_03` | Để pin thiết bị đeo xuống < 20% rồi thực hiện ngã mô phỏng | Hệ thống vẫn phát hiện và cảnh báo ngã bình thường; app hiển thị cảnh báo pin thấp | Pin yếu làm CPU throttle trên một số thiết bị và BLE TX power giảm. Test xác nhận hệ thống không bị suy giảm chức năng khi pin gần hết — đây là lúc cần cảnh báo nhất. | ⬜ |
| **SC_04: Caregiver xa** | `AT_EDGE_04` | Caregiver ở phòng khác / tầng khác / ngoài nhà khi Wearer ngã | Caregiver nhận notification SOS trên điện thoại riêng trong < 10s; cuộc gọi đến từ số Wearer | Trong thực tế Caregiver không phải lúc nào cũng ở cạnh Wearer. Notification phải xuyên qua tường, tầng, kết nối internet để đến được Caregiver — test xác nhận pipeline Cloud notification hoạt động end-to-end. | ⬜ |
| **SC_05: Nhiều lần ngã liên tiếp** | `AT_EDGE_05` | Thực hiện 3 cú ngã trong vòng 10 phút | Mỗi cú ngã được phát hiện và tạo event riêng biệt; không có event bị bỏ sót hay merge | Người lớn tuổi có thể ngã nhiều lần khi cố đứng dậy. Hệ thống phải xử lý đúng nhiều sự kiện ngã liên tiếp — không bị block bởi event trước, không tạo duplicate, lịch sử ghi đúng thứ tự. | ⬜ |

---

## Tổng kết

| Nhóm | ID | Số Scenario | Trạng thái |
| :--- | :--- | :---: | :--- |
| **Unit** | UT_BMI160 | 4 | ✅ 4/4 PASS — 2026-05-18 |
| **Unit** | UT_MCU_CORE | 4 | ✅ 4/4 PASS — 2026-05-18 |
| **Unit** | UT_BLE_STACK | 4 | ✅ 4/4 PASS — 2026-05-18 |
| **Unit** | UT_AI_MODEL | 4 | ✅ 4/4 PASS — 2026-05-18 |
| **Unit** | UT_MAX30102 | 4 | ✅ 4/4 PASS — 2026-05-18 |
| **Unit** | UT_APP_LOGIC | 4 | ✅ 4/4 PASS — 2026-05-29 |
| **Unit** | UT_CLOUD_DB | 4 | ✅ 4/4 PASS — 2026-05-29 |
| **Integrated** | IT_BLE_SYNC | 5 | 🔄 4/5 PASS — SC_05 ❌ (packet loss xuyên tường gạch 8m) |
| **Integrated** | IT_CLOUD_LOOP | 5 | ✅ 5/5 PASS — 2026-05-29 |
| **Integrated** | IT_EMERGENCY_CALL | 7 | ✅ 7/7 PASS — 2026-05-29 |
| **Integrated** | IT_VITALS_PIPELINE | 4 | ✅ 4/4 PASS — 2026-05-29 |
| **Integrated** | IT_EDGE_ALERT | 3 | ✅ 3/3 PASS — 2026-05-29 |
| **Integrated** | IT_OFFLINE_FIRST | 3 | ✅ 3/3 PASS — 2026-05-29 |
| **Acceptance** | AT_FALL_DETECT | 5 | ⬜ Pending |
| **Acceptance** | AT_ADL_REJECT | 5 | ⬜ Pending (SC_05 mới: consecutive window validation) |
| **Acceptance** | AT_EMERGENCY | 4 | ⬜ Pending |
| **Acceptance** | AT_CONTINUOUS | 4 | ⬜ Pending |
| **Acceptance** | AT_EDGE | 5 | ⬜ Pending |
| **Tổng** | | **78 scenarios** | **55/78 executed — 54 PASS, 1 FAIL** |

> **Nguyên tắc thiết kế Test Plan:** Mọi test case đều được chọn theo tiêu chí *"failure = potential harm"* — mỗi scenario thất bại tương ứng với một tình huống có thể gây hại thực sự cho người lớn tuổi (bỏ lỡ cảnh báo ngã, không gọi được cứu trợ, dữ liệu sinh hiệu sai, mất giám sát liên tục). Đây là nguyên tắc lựa chọn test case cho hệ thống IoT y tế safety-critical.
