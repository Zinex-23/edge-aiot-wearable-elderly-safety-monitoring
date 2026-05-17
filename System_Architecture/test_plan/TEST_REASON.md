# Test Reasoning — AIFD Wearable Safety System

> **Project:** AI Fall Detection — Intelligent Edge AIoT Wearable for Real-Time Elderly Safety Monitoring
> **Date:** 2026-05-18
> **Purpose:** Giải thích lý do tồn tại của từng nhóm test — trả lời câu hỏi *"Tại sao nhóm test này cần thiết?"* ở cấp độ module, không phải scenario.

---

## Bảng tóm tắt nhanh

| Nhóm | ID | Scenarios | Trạng thái | Lý do |
| :--- | :--- | :---: | :---: | :--- |
| **Unit** | UT_BMI160 | 4 | ✅ 4/4 | Kiểm tra cảm biến chuyển động (IMU) |
| **Unit** | UT_MCU_CORE | 4 | ✅ 4/4 | Kiểm tra nền tảng vi điều khiển |
| **Unit** | UT_BLE_STACK | 4 | ✅ 4/4 | Kiểm tra kết nối không dây BLE |
| **Unit** | UT_AI_MODEL | 4 | ✅ 4/4 | Kiểm tra mô hình AI phát hiện ngã |
| **Unit** | UT_MAX30102 | 4 | ✅ 4/4 | Kiểm tra cảm biến nhịp tim và SpO2 |
| **Unit** | UT_APP_LOGIC | 4 | ⏳ Pending | Kiểm tra logic ứng dụng Android |
| **Unit** | UT_CLOUD_DB | 4 | ⏳ Pending | Kiểm tra lưu trữ và phân phối dữ liệu trên Cloud |
| **Integrated** | IT_BLE_SYNC | 5 | ⏳ Pending | Kiểm tra giao tiếp BLE giữa thiết bị đeo và điện thoại |
| **Integrated** | IT_CLOUD_LOOP | 5 | ⏳ Pending | Kiểm tra luồng dữ liệu từ app lên Cloud và truy vấn ngược lại |
| **Integrated** | IT_EMERGENCY_CALL | 7 | ⏳ Pending | Kiểm tra cuộc gọi khẩn cấp trong các hoàn cảnh sử dụng thực tế |
| **Integrated** | IT_VITALS_PIPELINE | 4 | ⏳ Pending | Kiểm tra luồng dữ liệu sinh hiệu từ cảm biến đến màn hình app |
| **Integrated** | IT_EDGE_ALERT | 3 | ⏳ Pending | Kiểm tra pipeline từ AI phát hiện ngã đến cảnh báo trên app |
| **Integrated** | IT_OFFLINE_FIRST | 3 | ⏳ Pending | Kiểm tra đường khẩn cấp chính không cần internet |
| **Acceptance** | AT_FALL_DETECT | 5 | ⏳ Pending | Xác nhận phát hiện đúng các kiểu ngã thực tế (sấp, ngửa, bên, từ từ, khi đứng dậy) |
| **Acceptance** | AT_ADL_REJECT | 4 | ⏳ Pending | Xác nhận không báo nhầm khi sinh hoạt bình thường (ngồi, cúi, vận động, leo thang) |
| **Acceptance** | AT_EMERGENCY | 4 | ⏳ Pending | Xác nhận quy trình cảnh báo và gọi cứu hộ hoạt động đúng end-to-end |
| **Acceptance** | AT_CONTINUOUS | 4 | ⏳ Pending | Xác nhận hệ thống giám sát liên tục ổn định trong 8 giờ sử dụng thực tế |
| **Acceptance** | AT_EDGE | 5 | ⏳ Pending | Xác nhận hệ thống hoạt động trong điều kiện khắc nghiệt (phòng tắm, ban đêm, pin yếu, ngã liên tiếp) |
| **Tổng** | | **65** | **20/65** | |

---

## Nguyên tắc chọn test case

> Mọi test case đều được thiết kế theo tiêu chí **"failure = potential harm"** — mỗi scenario thất bại tương ứng với một tình huống có thể gây hại thực sự cho người lớn tuổi: bỏ lỡ cảnh báo ngã, không gọi được cứu trợ, hiển thị sai dữ liệu y tế, mất giám sát liên tục. Đây là tiêu chí lựa chọn test case cho hệ thống IoT y tế safety-critical.

---

## Bảng tổng kết & Lý do

| Nhóm | ID | Scenarios | Trạng thái | Lý do nhóm test này tồn tại |
| :--- | :--- | :---: | :---: | :--- |
| **Unit** | UT_BMI160 | 4 | ✅ 4/4 | BMI160 là **nguồn dữ liệu duy nhất** cho AI fall detection. Nếu cảm biến lỗi (sai địa chỉ I2C, sai tần số, sai calibration), mọi tính năng phía trên đều sụp đổ hoàn toàn. Test nhóm này đảm bảo lớp nền phần cứng ổn định trước khi tích hợp AI. |
| **Unit** | UT_MCU_CORE | 4 | ✅ 4/4 | ESP32-S3 là nền tảng chạy toàn bộ firmware. CPU clock, power management, GPIO, NVS là **điều kiện tiên quyết**: thiếu 240MHz thì AI không đủ băng thông; thiếu NVS thì thiết bị không nhớ cấu hình khi reboot; thiếu GPIO thì mất kênh cảnh báo vật lý duy nhất khi BLE mất kết nối. |
| **Unit** | UT_BLE_STACK | 4 | ✅ 4/4 | BLE là kênh giao tiếp duy nhất giữa thiết bị đeo và điện thoại. Advertising sai → không ghép đôi được; UUID sai → app không subscribe được; NOTIFY sai → không nhận alert ngã; Bond storage thiếu → người lớn tuổi phải pair lại thủ công mỗi lần reboot. |
| **Unit** | UT_AI_MODEL | 4 | ✅ 4/4 | AI inference là **giá trị cốt lõi** của đồ án. Test xác nhận model nạp vào 60KB arena thành công, FreeRTOS ring buffer giữ đúng 100 mẫu @ 20ms, output sigmoid trong [0,1]. Bất kỳ lỗi nào ở đây làm fall detection không chạy hoặc cho kết quả sai. |
| **Unit** | UT_MAX30102 | 4 | ✅ 4/4 | MAX30102 cung cấp HR và SpO2 — hai chỉ số sinh hiệu quan trọng nhất để Caregiver theo dõi sức khỏe từ xa. Nếu cảm biến đo sai hoặc không nhận diện được ngón tay, toàn bộ dữ liệu vitals gửi về app là 255 (invalid) — mất đi hoàn toàn chức năng giám sát sức khỏe liên tục. |
| **Unit** | UT_APP_LOGIC | 4 | ⏳ Pending | Android app là giao diện người dùng cuối. Crash UI, parse sai payload BLE, thiếu permission CALL_PHONE/BLUETOOTH_CONNECT là những lỗi người dùng thấy ngay lập tức. Test nhóm này đảm bảo lớp phần mềm Android hoạt động độc lập trước khi tích hợp với hardware thật. |
| **Unit** | UT_CLOUD_DB | 4 | ⏳ Pending | ThingsBoard + MongoDB là lớp lưu trữ và phân phối thông báo cho Caregiver từ xa. Rule Engine không trigger → Caregiver không nhận alert từ xa; DB timestamp sai → lịch sử y tế không đáng tin; Auth sai role → vi phạm privacy dữ liệu y tế. |
| **Integrated** | IT_BLE_SYNC | 5 | ⏳ Pending | Unit test xác nhận từng phía hoạt động đúng riêng lẻ — nhưng **không phát hiện protocol mismatch** giữa ESP32 và Android trên hardware thật. MTU negotiation thất bại, reconnect race condition, range drop 10m — chỉ xuất hiện khi hai thiết bị thực sự giao tiếp. |
| **Integrated** | IT_CLOUD_LOOP | 5 | ⏳ Pending | Unit test backend và app đã pass — nhưng **dữ liệu có thể mất ở bất kỳ bước nào** trong pipeline App → MQTT → ThingsBoard → MongoDB → REST → App. Offline-sync, multi-role, JSON schema mismatch chỉ lộ ra khi test toàn bộ vòng lặp. |
| **Integrated** | IT_EMERGENCY_CALL | 7 | ⏳ Pending | Cuộc gọi khẩn cấp đến người thân phải hoạt động **trong mọi trạng thái thực tế của điện thoại** — không chỉ khi app đang mở. 7 ngữ cảnh (foreground, background, màn hình khóa, Doze mode, đang gọi điện khác, chế độ im lặng, thiếu permission) bao phủ toàn bộ tình huống sinh hoạt của người lớn tuổi và Caregiver. |
| **Integrated** | IT_VITALS_PIPELINE | 4 | ⏳ Pending | Unit test đã xác nhận MAX30102 đọc đúng và BLE notify hoạt động riêng lẻ — integrated test xác nhận dữ liệu đi đúng từ cảm biến qua toàn bộ chuỗi đến màn hình app mà không bị sai lệch, bị đổi chỗ, hoặc mất khi BLE ngắt tạm. |
| **Integrated** | IT_EDGE_ALERT | 3 | ⏳ Pending | Unit test AI model đã pass — integrated test xác nhận khi AI phát hiện ngã trên ESP32, ALERT packet truyền qua BLE và app xử lý đúng: không mất event khi BLE drop, không tạo duplicate khi nhiều alert liên tiếp. |
| **Integrated** | IT_OFFLINE_FIRST | 3 | ⏳ Pending | Theo kiến trúc hệ thống, đường khẩn cấp chính hoàn toàn offline (Wearable → BLE → App → Direct Call). Test xác nhận cam kết này: hệ thống phải bảo vệ được người dùng kể cả khi không có internet, và tự sync lên Cloud khi có cơ hội. |
| **Acceptance** | AT_FALL_DETECT | 5 | ⏳ Pending | Kiểm tra độ chính xác phát hiện ngã với 5 kiểu ngã thực tế — đây là cam kết kỹ thuật chính của đồ án |
| **Acceptance** | AT_ADL_REJECT | 4 | ⏳ Pending | Kiểm tra tỷ lệ false positive với sinh hoạt hàng ngày — false positive cao khiến người dùng tắt cảnh báo, phá vỡ toàn bộ hệ thống |
| **Acceptance** | AT_EMERGENCY | 4 | ⏳ Pending | Xác nhận cuộc gọi cứu hộ và quy trình alert hoạt động đúng end-to-end trong thực tế |
| **Acceptance** | AT_CONTINUOUS | 4 | ⏳ Pending | Xác nhận hệ thống không bị suy giảm hay gián đoạn sau 8 giờ sử dụng liên tục |
| **Acceptance** | AT_EDGE | 5 | ⏳ Pending | **Bằng chứng thực tế** hệ thống hoạt động trong điều kiện khắc nghiệt nhất — phòng tắm, ban đêm, pin yếu, ngã liên tiếp |
| **Tổng** | | **65** | **20/65** | |

---

## Tại sao thứ tự Unit → Integrated → Acceptance?

```
Unit Tests (I)
  └─ Từng module hoạt động đúng trong môi trường cô lập
  └─ Nếu Unit fail → không có lý do chạy Integrated (garbage in → garbage out)

Integrated Tests (II)
  └─ Các module giao tiếp đúng với nhau qua giao thức thực tế
  └─ Phát hiện lỗi tích hợp mà Unit không thấy (protocol mismatch, race condition)

Acceptance Tests (III)
  └─ Toàn bộ hệ thống đáp ứng yêu cầu người dùng cuối
  └─ Đây là câu trả lời cho câu hỏi: "Hệ thống có bảo vệ được người lớn tuổi không?"
```

---

## Mapping: Test Group → Rủi ro y tế nếu fail

| Nhóm test | Nếu fail → Rủi ro thực tế |
| :--- | :--- |
| UT_BMI160 | Thiết bị đeo nhưng không thu thập dữ liệu chuyển động — AI không có input → không phát hiện ngã |
| UT_MCU_CORE | Thiết bị reboot mất cấu hình; LED/còi không hoạt động → mất kênh cảnh báo vật lý cuối cùng |
| UT_BLE_STACK | Điện thoại không nhận được dữ liệu hay cảnh báo ngã — toàn bộ kết nối thất bại |
| UT_AI_MODEL | False positive (báo nhầm gây phiền nhiễu) hoặc false negative (bỏ sót ngã thật — nguy hiểm tính mạng) |
| UT_MAX30102 | HR/SpO2 hiển thị 255 (invalid) — Caregiver mất khả năng theo dõi sức khỏe từ xa liên tục |
| UT_APP_LOGIC | App crash đúng lúc người dùng cần nhất; gọi điện không được; không nhận cảnh báo |
| UT_CLOUD_DB | Caregiver từ xa không nhận thông báo; lịch sử y tế sai → quyết định y tế không chính xác |
| IT_BLE_SYNC | Kết nối mất ổn định trong sinh hoạt thực tế → khoảng trống giám sát → ngã không được phát hiện |
| IT_CLOUD_LOOP | Sự kiện ngã không ghi lên Cloud → bác sĩ thiếu dữ liệu; Caregiver xa không hay biết |
| IT_EMERGENCY_CALL | Cuộc gọi cứu hộ không đến được người thân trong tình huống khẩn cấp thực tế |
| AT_FALL_SOS | **Hệ thống không thực hiện được mục đích tồn tại của nó** |
