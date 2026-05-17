# TEST PLAN OVERVIEW — AIFD Wearable Safety System

> **Project:** AI Fall Detection — Intelligent Edge AIoT Wearable for Real-Time Elderly Safety Monitoring
> **Revision:** 2026-05-18
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

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: I2C Comm** | `UT_BMI160_01` | Gọi hàm `BMI160.begin()` qua giao diện I2C | Trả về `SUCCESS` và nhận diện đúng Chip ID | BMI160 là nguồn dữ liệu thô duy nhất cho toàn bộ pipeline phát hiện ngã. Nếu giao tiếp I2C lỗi ngay từ đầu (sai địa chỉ, bus treo), mọi tính năng cốt lõi sẽ không hoạt động — test này xác nhận lớp nền phần cứng khả dụng. | ✅ 2026-05-18 |
| **SC_02: Range Check** | `UT_BMI160_02` | Đặt thiết bị nằm yên trên mặt phẳng | Trục Z đạt ~1g (±0.05g), trục X/Y ~0g | Hiệu chỉnh (calibration) sai sẽ làm mô hình AI nhận đầu vào lệch so với dữ liệu huấn luyện, dẫn đến false positive hoặc bỏ sót ngã. Test này xác nhận cảm biến đọc đúng trọng lực tĩnh trước khi đưa vào inference. | ✅ 2026-05-18 |
| **SC_03: Sample Rate** | `UT_BMI160_03` | Đo thời gian giữa 100 lần đọc | Tổng ~2000ms (tương ứng 50 Hz) | Mô hình TinyML được huấn luyện trên chuỗi thời gian 50 Hz (100 mẫu = 2 giây). Nếu tần số thực thấp hơn (40 Hz), cửa sổ dữ liệu bị "kéo giãn" — mô hình nhận dữ liệu sai phân phối so với lúc huấn luyện, giảm độ chính xác. | ✅ 2026-05-18 |
| **SC_04: Self-test** | `UT_BMI160_04` | Kích hoạt chế độ Built-in Self-test của BMI160 | Cảm biến trả về phản hồi "Passed" | BMI160 có cơ chế tự kiểm tra nội bộ (MEMS). Dùng self-test để phát hiện sớm cảm biến hỏng hoặc bị lỗi do va đập trong quá trình lắp ráp thiết bị đeo, tránh đưa ra thị trường thiết bị defective. | ✅ 2026-05-18 |

---

### I.2 — MCU Core (ESP32-S3)
**ID:** `UT_MCU_CORE` | **Layer:** Firmware / Low-level Drivers | **Environment:** ESP-IDF / Arduino

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: CPU Clock** | `UT_MCU_01` | Đọc bit cấu hình CPU Clock | Trả về tần số tối đa 240 MHz | TFLite Micro Inference và BLE stack chạy đồng thời — cần CPU 240 MHz để xử lý xong trong <50 ms. Nếu clock bị throttle (80/160 MHz), latency inference vượt giới hạn thời gian thực và thiếu băng thông xử lý cho BLE song song. | ✅ 2026-05-18 |
| **SC_02: Deep Sleep** | `UT_MCU_02` | Chuyển sang Deep Sleep 10 giây | Tiêu thụ < 100 µA, tự thức dậy đúng giờ | Thiết bị đeo phải hoạt động cả ngày từ pin nhỏ. Deep Sleep giữa các chu kỳ đo (~5 giây) giúp kéo dài pin. Test xác nhận tiêu thụ đạt mức thiết kế và wake-up đáng tin cậy — nếu không thức dậy được, dữ liệu bị gián đoạn. | ✅ 2026-05-18 |
| **SC_03: GPIO Output** | `UT_MCU_03` | Điều khiển LED trạng thái / Còi báo | Ngoại vi phản hồi đúng (Bật/Tắt) | LED và còi là kênh phản hồi trực tiếp duy nhất trên phần cứng (không qua điện thoại). Khi BLE mất kết nối hoặc phát hiện ngã, LED/còi cảnh báo người xung quanh — GPIO lỗi làm mất kênh cảnh báo vật lý này. | ✅ 2026-05-18 |
| **SC_04: NVS Storage** | `UT_MCU_04` | Ghi và đọc tham số từ NVS Flash | Giá trị không đổi sau khi reboot | NVS lưu cấu hình thiết bị (BLE address, ngưỡng cảnh báo). Nếu NVS bị mất sau reboot (do sector lỗi hoặc write fail), thiết bị phải cấu hình lại từ đầu mỗi lần khởi động — ảnh hưởng trực tiếp đến tính ổn định dài hạn. | ✅ 2026-05-18 |

---

### I.3 — BLE Stack (Edge / Peripheral Side)
**ID:** `UT_BLE_STACK` | **Layer:** Firmware BLE Service | **Mode:** BLE Peripheral

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Advertising** | `UT_BLE_01` | Khởi chạy chế độ Advertising của ESP32 | Các thiết bị khác tìm thấy tên "AIFD Wearable" | Nếu thiết bị không quảng bá đúng tên/UUID, ứng dụng Android không thể tìm thấy khi scan — người dùng không thể ghép đôi ban đầu. Đây là điểm entry đầu tiên của toàn bộ kết nối hệ thống. | ✅ 2026-05-18 |
| **SC_02: Service Init** | `UT_BLE_02` | Khởi tạo Service UUID và Characteristic UUID | Các UUID xuất hiện đầy đủ trong bảng GATT | Android app subscribe cụ thể các UUID (VITALS `7b809f11`, ALERT `beb5483e`, CONTROL `f9b2c417`). Nếu UUID thiếu hoặc sai, app không subscribe được notification → không nhận dữ liệu. | ✅ 2026-05-18 |
| **SC_03: Data Notification** | `UT_BLE_03` | Gửi dữ liệu biến động qua cơ chế Notify | Client nhận bản tin mà không cần thực hiện Read | Toàn bộ pipeline sinh hiệu và cảnh báo ngã dựa vào BLE Notify (push). Nếu Notify không hoạt động và phải dùng Read (poll), latency tăng mạnh và tốn bandwidth — không đảm bảo phát hiện ngã thời gian thực. | ✅ 2026-05-18 |
| **SC_04: Bond Storage** | `UT_BLE_04` | Boot lại thiết bị, kiểm tra NimBLE bond store có lưu địa chỉ client từ session trước | Bond store trả về đúng số lượng peer đã lưu; nếu có bond thì hiện địa chỉ MAC | Thiết bị đeo reboot liên tục (hết pin, reset). Người lớn tuổi không thể pair lại thủ công mỗi lần — bond storage NVS đảm bảo firmware nhớ điện thoại đã ghép và tự reconnect khi boot, không cần thao tác của người dùng. | ✅ 2026-05-18 |

---

### I.4 — AI Inference Engine (TinyML)
**ID:** `UT_AI_MODEL` | **Layer:** Edge AI Logic | **Runtime:** TFLite Micro trên ESP32-S3

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Model Loading** | `UT_AI_01` | Khởi tạo `TFLiteMicroInterpreter` với mảng byte mô hình | Interpreter cấp phát thành công, không lỗi | ESP32-S3 có RAM hạn chế (~512KB SRAM). Nếu tensor arena size cấu hình sai, `AllocateTensors()` thất bại ngay khi khởi động — toàn bộ tính năng phát hiện ngã bị vô hiệu hóa. Test này xác nhận mô hình fit vào bộ nhớ thiết bị. | ✅ 2026-05-18 |
| **SC_02: Buffer Flow** | `UT_AI_02` | Đẩy 120 mẫu vào Circular Buffer | Buffer giữ lại đúng 100 mẫu mới nhất (sliding window) | Mô hình nhận đầu vào là cửa sổ 100 mẫu liên tiếp (2 giây @ 50 Hz). Circular buffer phải ghi đè đúng mẫu cũ nhất — nếu logic overwrite sai, cửa sổ bị lệch thời gian và mô hình nhận dữ liệu ngẫu nhiên, dẫn đến false detection. | ✅ 2026-05-18 |
| **SC_03: Sample Integrity** | `UT_AI_03` | Đẩy 100 mẫu vào ring buffer @ 20ms, snapshot lại, kiểm tra thứ tự và khoảng cách | 100 mẫu đúng thứ tự, gap đều 20ms | Với kiến trúc FreeRTOS dual-task (taskSampling Core 0 / taskInference Core 1), inference không còn block sampling. Test này xác nhận ring buffer luôn giữ đúng 100 mẫu cách đều 20ms — điều kiện đầu vào bắt buộc của model. | ✅ 2026-05-18 |
| **SC_04: Sigmoid Limit** | `UT_AI_04` | Inference với dữ liệu cực đại/cực tiểu | Đầu ra nằm trong [0.0, 1.0] | Đầu ra sigmoid là xác suất ngã (fallProb). Nếu do lỗi quantization đầu ra vượt [0, 1], logic so sánh ngưỡng trên ESP32 (`fallProb >= threshold`) cho kết quả không xác định — thiết bị có thể báo động sai liên tục hoặc không bao giờ báo. | ✅ 2026-05-18 |

---

### I.5 — Vital Signs Sensor (MAX30102)
**ID:** `UT_MAX30102` | **Layer:** Hardware Abstraction Layer (HAL) | **Hardware:** ESP32-S3 + MAX30102

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: I2C Comm** | `UT_MAX_01` | Gọi `max30102_init()` qua I2C address 0x57 | Trả về `SUCCESS`, đọc đúng Part ID (0x15) | MAX30102 là cảm biến SpO2/HR duy nhất trong hệ thống. Nếu I2C lỗi, toàn bộ dữ liệu sinh hiệu gửi về app sẽ là giá trị invalid (255) — Caregiver không theo dõi được sức khỏe người đeo. | ✅ 2026-05-18 |
| **SC_02: Finger Detection** | `UT_MAX_02` | Đặt ngón tay lên cảm biến | `fingerDetected = true`, IR signal > threshold | MAX30102 dùng LED IR để phát hiện ngón tay. Nếu không detect được finger, sensor báo HR=255/SpO2=255 ngay cả khi đang đeo đúng cách — app hiển thị sai và Caregiver lo lắng không cần thiết. | ✅ 2026-05-18 |
| **SC_03: Heart Rate Reading** | `UT_MAX_03` | Đặt ngón tay yên tĩnh 10 giây | HR trong khoảng 50–180 bpm | Nhịp tim là chỉ số y tế quan trọng nhất để phát hiện bất thường (nhịp tim quá cao/thấp). Giá trị ngoài phạm vi sinh lý [50, 180] cho thấy thuật toán đo sai hoặc cảm biến bị nhiễu — không thể dùng để theo dõi sức khỏe. | ✅ 2026-05-18 |
| **SC_04: SpO2 Reading** | `UT_MAX_04` | Đặt ngón tay yên tĩnh 10 giây | SpO2 trong khoảng 90–100% | SpO2 < 90% là dấu hiệu nguy hiểm cần cấp cứu ngay. Nếu cảm biến đo sai (báo SpO2 = 70% khi thực tế 98%), Caregiver có thể phản ứng quá mức; ngược lại nếu báo 98% khi thực tế thấp, bỏ lỡ tình huống nguy hiểm. | ✅ 2026-05-18 |

---

### I.6 — Android App Logic
**ID:** `UT_APP_LOGIC` | **Layer:** Android Application | **Language:** Kotlin

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: UI Navigation** | `UT_APP_01` | Chuyển đổi giữa Home → History → Settings | Giao diện phản hồi mượt mà, không crash | Người lớn tuổi là đối tượng sử dụng chính — mọi crash hay navigation bất ngờ (back stack sai route) gây mất tin tưởng và có thể bỏ lỡ cảnh báo ngã. Kiểm tra trên Android API 29–34 vì vòng đời thiết bị thực tế dài. | ⬜ |
| **SC_02: SQLite CRUD** | `UT_APP_02` | Lưu thông báo té ngã vào SQLite nội bộ | Dữ liệu lưu và truy vấn lại đúng 100% | Lịch sử sự kiện ngã được lưu offline-first để đảm bảo không mất dữ liệu khi không có mạng. CRUD sai (duplicate key, wrong timestamp) làm Caregiver xem lịch sử không chính xác — ảnh hưởng đến quyết định y tế. | ⬜ |
| **SC_03: Permissions** | `UT_APP_03` | Yêu cầu CALL_PHONE và BLUETOOTH_CONNECT | Hiển thị hộp thoại xin quyền và nhận được quyền | Android 12+ yêu cầu `BLUETOOTH_CONNECT` riêng biệt (thay vì `BLUETOOTH` cũ). Thiếu một trong hai quyền này làm tính năng cốt lõi thất bại hoàn toàn: không scan BLE được hoặc không gọi điện khẩn cấp được. | ⬜ |
| **SC_04: Data Parsing** | `UT_APP_04` | Truyền chuỗi byte giả lập vào hàm xử lý | Trả về đúng giá trị HR và SpO2 (Decimal) | Payload BLE có định dạng cụ thể: `BATCH,seq,heartRate,spO2,timestamp` và `ALERT,seq,ts,fall,1,fallProb,nonFallProb`. Parse sai (wrong index, wrong split) cho giá trị sai hoặc crash `NumberFormatException`. | ⬜ |

---

### I.7 — Cloud Platform & Database
**ID:** `UT_CLOUD_DB` | **Layer:** Backend Services | **Stack:** ThingsBoard + MongoDB

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Rule Engine** | `UT_CLOUD_01` | Gửi gói tin "Fall Detected" giả lập lên ThingsBoard | Rule Engine kích hoạt Alarm thành công | ThingsBoard Rule Chain là cơ chế khuếch đại cảnh báo lên Cloud — nếu Rule Engine không trigger, Caregiver trên thiết bị khác không nhận được push notification từ Cloud khi Wearer ngã. | ⬜ |
| **SC_02: DB Write** | `UT_CLOUD_02` | Ghi bản ghi Telemetry vào MongoDB | Bản ghi xuất hiện đúng nhãn thời gian | Timestamp sai sẽ làm lịch sử sinh hiệu bị hiển thị sai thứ tự trên Dashboard — bác sĩ hoặc người chăm sóc đọc biểu đồ không chính xác, ảnh hưởng đến phân tích sức khỏe dài hạn. | ⬜ |
| **SC_03: Auth Service** | `UT_CLOUD_03` | Đăng nhập với tài khoản hợp lệ | Hệ thống trả về JWT Token và quyền truy cập đúng | JWT Token sai role (Wearer vs Caregiver) sẽ cấp sai quyền truy cập dữ liệu — vi phạm bảo mật: Caregiver A có thể xem dữ liệu của Wearer B. | ⬜ |
| **SC_04: Retention** | `UT_CLOUD_04` | Thiết lập chính sách xóa dữ liệu cũ sau 30 ngày | Dữ liệu cũ hơn 30 ngày tự động dọn dẹp | Không có retention policy, MongoDB tích lũy vô hạn dữ liệu telemetry. Sau vài tháng storage sẽ đầy và toàn bộ ghi dữ liệu bị từ chối — hệ thống ngừng hoạt động silently. | ⬜ |

---

## II. Integrated Tests

Integrated test kiểm tra sự tương tác giữa các module sau khi từng module đã pass unit test — xác nhận giao tiếp giữa các layer hoạt động đúng giao thức và không có lỗi tích hợp.

---

### II.1 — BLE Connectivity & Data Sync
**ID:** `IT_BLE_SYNC` | **Modules:** ESP32-S3 BLE ↔ Android BLE Client | **Protocol:** BLE 5.0

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Pairing** | `IT_BLE_01` | Quét và kết nối từ App Android | App tìm thấy "AIFD Wearable" và kết nối thành công | Unit test đã xác nhận ESP32 advertising đúng và app parse đúng — integrated test xác nhận hai phía giao tiếp được với nhau trên thiết bị thật, không bị lỗi do firmware version mismatch hay Android BLE stack khác nhau giữa các hãng máy. | ✅ 2026-05-18 |
| **SC_02: MTU Negotiation** | `IT_BLE_02` | Trao đổi MTU sau khi kết nối | MTU đạt tối thiểu 247 bytes | Payload BATCH và ALERT có thể dài hơn MTU mặc định (23 bytes). Nếu MTU negotiation thất bại hoặc đạt giá trị thấp, gói tin bị cắt ngắn (fragmentation sai) → data corrupt → parse lỗi và crash `NumberFormatException`. | ⬜ |
| **SC_03: Data Stream** | `IT_BLE_03` | Gửi liên tục HR/SpO2 mỗi 5s và Motion data | App nhận và cập nhật biểu đồ thời gian thực, không trễ/mất gói | Đây là "stress test" của kênh BLE — kiểm tra xem notification queue có bị overflow khi firmware gửi dữ liệu liên tục không, và Android BLE callback có được gọi đúng thread không (UI không block). | ⬜ |
| **SC_04: Reconnect** | `IT_BLE_04` | Tắt Bluetooth điện thoại 10s rồi bật lại | Thiết bị tự động kết nối lại trong tầm phủ sóng | Người lớn tuổi có thể vô tình tắt Bluetooth hoặc pin điện thoại hết rồi sạc lại. Reconnect tự động (exponential backoff) là bắt buộc để không cần người dùng can thiệp thủ công — giám sát phải liên tục. | ⬜ |
| **SC_05: Range Test** | `IT_BLE_05` | Di chuyển thiết bị ra xa 5–10m | Kết nối duy trì ổn định, RSSI không drop quá 50% | Thiết bị đeo trên cổ tay, điện thoại để túi hoặc trên bàn — khoảng cách 5–10m là tình huống sinh hoạt thực tế. Nếu kết nối drop ở khoảng cách này, hệ thống không đảm bảo giám sát liên tục trong nhà. | ⬜ |

---

### II.2 — App to Cloud & Data Retrieval
**ID:** `IT_CLOUD_LOOP` | **Modules:** Android App ↔ ThingsBoard ↔ MongoDB | **Protocol:** MQTT / REST API

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: App Upload** | `IT_CLOUD_01` | App gửi Telemetry (HR/SpO2) qua MQTT | Dashboard ThingsBoard cập nhật theo thời gian thực | Xác nhận giao thức MQTT (QoS, topic name, JSON schema) được cả App và ThingsBoard hiểu đúng — sai một field tên là Rule Engine không kích hoạt được cảnh báo. | ⬜ |
| **SC_02: Cloud Persistence** | `IT_CLOUD_02` | Kiểm tra dữ liệu trong MongoDB sau khi gửi | Dữ liệu lưu đúng cấu trúc JSON và timestamp | Integrated test xác nhận pipeline App → MQTT Broker → ThingsBoard → MongoDB không bị mất dữ liệu ở bước nào — unit test chỉ test từng thành phần riêng lẻ, không phát hiện được mất dữ liệu giữa các bước. | ⬜ |
| **SC_03: History Query** | `IT_CLOUD_03` | Mở màn hình History, chọn khoảng thời gian | App gọi REST API thành công, hiển thị đúng biểu đồ | REST API schema (endpoint, query params, response JSON) phải khớp giữa App và backend. Nếu field name sai (ví dụ `heartRate` vs `heart_rate`), biểu đồ lịch sử không render được dù dữ liệu tồn tại trong DB. | ⬜ |
| **SC_04: Sync Strategy** | `IT_CLOUD_04` | Tắt Internet → phát hiện ngã → bật Internet | Sự kiện ngã lưu SQLite và tự động đẩy lên Cloud khi online | Offline-first là yêu cầu với thiết bị y tế — mạng không ổn định không được phép làm mất sự kiện ngã. Test này xác nhận cơ chế sync queue hoạt động đúng: không duplicate khi upload lại và không mất sự kiện khi offline kéo dài. | ⬜ |
| **SC_05: Multi-role View** | `IT_CLOUD_05` | Caregiver đăng nhập từ thiết bị khác | Thấy đúng dữ liệu của Wearer và nhận thông báo | Xác nhận phân quyền Cloud hoạt động đúng: Caregiver A chỉ thấy dữ liệu Wearer được link với tài khoản A, không thấy dữ liệu của người khác — đây là yêu cầu privacy cơ bản của hệ thống y tế. | ⬜ |

---

### II.3 — Emergency Call (Fall-to-Call Integration)
**ID:** `IT_EMERGENCY_CALL` | **Modules:** ESP32-S3 → BLE → Android BleForegroundService → CALL_PHONE

| Scenario | Test ID | Ngữ cảnh | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: App Foreground** | `IT_EMG_01` | AIFD app đang mở, màn hình sáng | FallAlertScreen hiện ngay; sau 15s gọi điện đến số Caregiver | Kịch bản lý tưởng nhất — app foreground, không có rào cản OS. Nếu fail ở đây, lỗi nằm ở logic xử lý ALERT packet hoặc timer countdown. | ⬜ |
| **SC_02: App Background** | `IT_EMG_02` | Đang dùng app khác (Zalo, YouTube...) | Notification SOS âm thanh cao; nhấn → FallAlertScreen; sau 15s cuộc gọi thực hiện | BleForegroundService đảm bảo app nhận BLE notification khi background. Android có thể giới hạn activity launch từ background — test xác nhận WakeLock và full-screen intent hoạt động đúng. | ⬜ |
| **SC_03: Screen Locked** | `IT_EMG_03` | Màn hình điện thoại đang khóa, trong túi | WakeLock bật màn hình; FallAlertScreen hiện trên lockscreen; sau 15s cuộc gọi thực hiện | Người lớn tuổi thường để điện thoại khóa màn hình. Nếu alert không hiện trên lockscreen, cuộc gọi auto xảy ra "trong im lặng" — Wearer không thể cancel kịp thời. | ⬜ |
| **SC_04: Screen Off + Doze** | `IT_EMG_04` | Màn hình tắt > 10 phút, Android Doze active | BleForegroundService vượt Doze; alert xử lý; cuộc gọi thực hiện được | Android Doze mode (API 23+) throttle background apps. BleForegroundService được miễn trừ Doze nhờ foreground notification — test xác nhận exemption hoạt động đúng trên thiết bị thật. | ⬜ |
| **SC_05: Active Phone Call** | `IT_EMG_05` | Đang trong cuộc gọi điện thoại khác | Notification SOS hiện khi đang gọi; sau 15s thực hiện gọi SOS | Caregiver có thể đang gọi điện khi Wearer ngã. Notification phải nổi bật đủ để Caregiver nhận ra. Behavior khi đang có cuộc gọi khác cần document rõ (interrupt vs miss). | ⬜ |
| **SC_06: Silent / DND Mode** | `IT_EMG_06` | Điện thoại im lặng hoặc Không làm phiền | Notification SOS phát âm thanh (priority URGENT vượt DND); cuộc gọi thực hiện được | DND mode chặn thông báo thông thường. Android cho phép URGENT priority vượt DND — test xác nhận channel priority được cấu hình đúng. | ⬜ |
| **SC_07: No CALL_PHONE Permission** | `IT_EMG_07` | Quyền `CALL_PHONE` bị từ chối | App fallback sang `ACTION_DIAL` — mở màn hình quay số với số Caregiver điền sẵn | `ACTION_CALL` yêu cầu `CALL_PHONE` permission. Nếu không có fallback, tính năng auto-call im lặng thất bại mà không báo lỗi. `ACTION_DIAL` là fallback an toàn — không cần permission, luôn hoạt động. | ⬜ |

---

### II.4 — Vitals Data Pipeline
**ID:** `IT_VITALS_PIPELINE` | **Modules:** MAX30102 → ESP32 → BLE → Android App → UI

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: HR end-to-end** | `IT_VIT_01` | Đặt ngón tay lên MAX30102, quan sát HR trên HomeScreen | Giá trị HR trên app khớp với sensor (±5 bpm) trong < 10s | Test xác nhận toàn bộ chuỗi MAX30102 → ESP32 encode BATCH → BLE Notify → Android parse → UI update. Nếu bất kỳ bước nào lỗi, app hiển thị 255 (invalid) hoặc giá trị sai. | ⬜ |
| **SC_02: SpO2 end-to-end** | `IT_VIT_02` | Đặt ngón tay lên MAX30102, quan sát SpO2 trên HomeScreen | Giá trị SpO2 trên app trong khoảng 95–100% và ổn định | BATCH packet chứa cả HR và SpO2 — parse sai index sẽ làm hai giá trị bị hoán đổi cho nhau, gây hiểu lầm nghiêm trọng về tình trạng sức khỏe. | ⬜ |
| **SC_03: Vitals chart realtime** | `IT_VIT_03` | Chuyển sang MonitoringScreen mode LIVE, quan sát chart 1 phút | Chart cập nhật liên tục; giá trị khớp với HomeScreen; không có data spike bất thường | Xác nhận MonitoringViewModel và HomeViewModel nhận cùng nguồn dữ liệu (sensorData StateFlow) — hai màn hình không được hiển thị giá trị khác nhau tại cùng thời điểm. | ⬜ |
| **SC_04: Vitals cache khi mất BLE** | `IT_VIT_04` | Ngắt BLE 30s rồi reconnect, kiểm tra chart 1H | Chart 1H vẫn hiển thị dữ liệu từ trước khi mất kết nối; không có khoảng trắng bất thường | Local Cache (VitalsStore) lưu bucket dữ liệu trong bộ nhớ app. Dữ liệu không bị xóa khi BLE ngắt tạm thời — đây là tính năng offline-first của lớp lưu trữ local. | ⬜ |

---

### II.5 — Edge AI Alert Pipeline
**ID:** `IT_EDGE_ALERT` | **Modules:** IMU → ESP32 TFLite → BLE ALERT → Android → FallAlertScreen

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Fall pipeline end-to-end** | `IT_EDGE_01` | Thực hiện cú ngã mô phỏng; quan sát serial monitor và app | Serial: `[INFER] fall_prob>0.42`; BLE gửi ALERT; FallAlertScreen xuất hiện trong < 5s | Test toàn bộ chuỗi Edge AI: IMU → FreeRTOS taskSampling → taskInference → fall detected → BLE ALERT notify → Android parse → UI alert. Đây là pipeline cốt lõi của dự án. | ⬜ |
| **SC_02: ALERT deduplication** | `IT_EDGE_02` | Kích hoạt fall 2 lần liên tiếp trong < 30s | App tạo 2 event riêng biệt với sequence ID khác nhau; không merge hay bỏ sót | ESP32 gán sequence number tăng dần cho mỗi ALERT packet. Android app phải dedup bằng sequence ID — nếu thiếu dedup, cùng 1 cú ngã có thể tạo nhiều event trùng trong lịch sử. | ⬜ |
| **SC_03: ALERT delivery khi BLE drop** | `IT_EDGE_03` | Ngắt BLE → gây fall → reconnect BLE | ALERT packet được queue trong ESP32; sau reconnect app nhận đủ event và hiển thị FallAlertScreen | Ngã đúng lúc BLE vừa mất kết nối là scenario nguy hiểm nhất. Queue offline của firmware (FALL_QUEUE_CAPACITY=16) đảm bảo ALERT không bị mất. | ⬜ |

---

### II.6 — Offline-First Emergency Path
**ID:** `IT_OFFLINE_FIRST` | **Modules:** Wearable → BLE → Android App → Direct Phone Call

| Scenario | Test ID | Hành động | Kết quả mong đợi | Note | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SC_01: Toàn bộ path không cần internet** | `IT_OFF_01` | Tắt WiFi và 4G → thực hiện ngã mô phỏng | FallAlertScreen xuất hiện; cuộc gọi đến Caregiver thực hiện được; sự kiện lưu vào local history | Đường khẩn cấp chính là Wearable → BLE → Android App → Direct Phone Call — hoàn toàn offline. Cloud chỉ là secondary. Test xác nhận cam kết kiến trúc này được thực hiện đúng. | ⬜ |
| **SC_02: App đầy đủ chức năng offline** | `IT_OFF_02` | Tắt internet, sử dụng toàn bộ app (Home, Monitoring, History, Settings) | Tất cả tính năng cốt lõi hoạt động bình thường; không có màn hình lỗi "Không có kết nối" | Hệ thống được thiết kế local-first — BLE thay thế cho network. Người lớn tuổi sống ở vùng có mạng kém vẫn phải được bảo vệ đầy đủ. | ⬜ |
| **SC_03: Cloud sync tự động khi có mạng** | `IT_OFF_03` | Bật internet trở lại sau khi đã có sự kiện ngã lưu offline | Các sự kiện ngã tự động sync lên MongoDB; không có event bị duplicate hay mất | Offline-first đồng nghĩa với việc dữ liệu phải được sync khi có cơ hội. Test xác nhận sync queue hoạt động đúng: đúng thứ tự, không trùng, không mất. | ⬜ |

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
| **Unit** | UT_APP_LOGIC | 4 | ⬜ Pending |
| **Unit** | UT_CLOUD_DB | 4 | ⬜ Pending |
| **Integrated** | IT_BLE_SYNC | 5 | 🔄 1/5 (SC_01 ✅ 2026-05-18) |
| **Integrated** | IT_CLOUD_LOOP | 5 | ⬜ Pending |
| **Integrated** | IT_EMERGENCY_CALL | 7 | ⬜ Pending |
| **Integrated** | IT_VITALS_PIPELINE | 4 | ⬜ Pending |
| **Integrated** | IT_EDGE_ALERT | 3 | ⬜ Pending |
| **Integrated** | IT_OFFLINE_FIRST | 3 | ⬜ Pending |
| **Acceptance** | AT_FALL_DETECT | 5 | ⬜ Pending |
| **Acceptance** | AT_ADL_REJECT | 4 | ⬜ Pending |
| **Acceptance** | AT_EMERGENCY | 4 | ⬜ Pending |
| **Acceptance** | AT_CONTINUOUS | 4 | ⬜ Pending |
| **Acceptance** | AT_EDGE | 5 | ⬜ Pending |
| **Tổng** | | **75 scenarios** | **21/75 executed — 21 PASS** |

> **Nguyên tắc thiết kế Test Plan:** Mọi test case đều được chọn theo tiêu chí *"failure = potential harm"* — mỗi scenario thất bại tương ứng với một tình huống có thể gây hại thực sự cho người lớn tuổi (bỏ lỡ cảnh báo ngã, không gọi được cứu trợ, dữ liệu sinh hiệu sai, mất giám sát liên tục). Đây là nguyên tắc lựa chọn test case cho hệ thống IoT y tế safety-critical.
