# Tài Liệu Chuẩn Bị Phỏng Vấn: Dự Án CaraFall (Elderly Safety Wearable System)

Tài liệu này tổng hợp các luận điểm (talking points) quan trọng, liên kết trực tiếp giữa các đầu mục công việc bạn đảm nhiệm với kiến trúc hệ thống và mã nguồn thực tế. Hãy sử dụng những thông tin này để tự tin trả lời các câu hỏi chuyên sâu từ nhà tuyển dụng.

---

## 1. Triết Lý Thiết Kế & Kiến Trúc Hệ Thống

**Câu hỏi dự kiến:** *"Hãy giới thiệu tổng quan về dự án và tại sao bạn lại chọn kiến trúc phần cứng/phần mềm như vậy?"*

**Luận điểm trả lời:**
* **Triết lý Offline-First (Ưu tiên ngoại tuyến):** Điểm yếu chí mạng của nhiều hệ thống IoT y tế là phụ thuộc vào mạng Internet (WiFi/4G). Dự án này thiết kế để phát hiện té ngã và cảnh báo ngay lập tức qua BLE đến điện thoại (Gateway) mà không cần WiFi. Điều này đảm bảo an toàn tuyệt đối trong mọi hoàn cảnh.
* **Kiến trúc ESP32-S3 & FreeRTOS Dual-Core:** Vi điều khiển ESP32-S3 được chọn vì khả năng xử lý tính toán tốt (phù hợp cho AI). Việc ứng dụng **FreeRTOS đa luồng (2 nhân)** là điểm sáng kỹ thuật quan trọng nhất:
  * **Core 0 (Độ ưu tiên cao):** Chuyên trách tác vụ thu thập dữ liệu cảm biến thời gian thực (`taskSampling`).
  * **Core 1:** Chuyên xử lý tác vụ nặng là chạy suy luận mô hình AI (`taskInference`), tránh làm nghẽn (blocking) luồng đọc cảm biến.

---

## 2. Luồng Dữ Liệu: Cảm Biến -> Phát Hiện Ngã -> Cảnh Báo

**Câu hỏi dự kiến:** *"Hệ thống xử lý luồng dữ liệu như thế nào kể từ lúc người dùng bị ngã cho đến khi phát ra cảnh báo?"*

**Luận điểm trả lời (Trình bày theo các bước logic trong code):**

1. **Thu thập dữ liệu (Core 0):** Cảm biến BMI160 liên tục đọc gia tốc và góc quay (I2C) với tần số 50Hz (mỗi 20ms).
2. **Đồng bộ hóa an toàn:** Dữ liệu được đẩy vào một bộ đệm vòng (Ring Buffer). Do hai nhân chạy song song (đọc và ghi), tôi đã sử dụng **Mutex (`gImuMutex`)** để khóa vùng nhớ, ngăn chặn lỗi tranh chấp dữ liệu (data corruption).
3. **Các Cổng Logic Lọc (Gates):** Để tiết kiệm pin, AI không chạy liên tục. Dữ liệu phải vượt qua các ngưỡng `ACTIVITY_ACC_THRESHOLD` và `CANDIDATE_ACC_THRESHOLD`. Chỉ khi có chuyển động đủ mạnh (nghi ngờ ngã), cửa sổ AI mới được mở ra trong 5 giây.
4. **Suy luận AI (Core 1):** Dữ liệu vượt qua Cổng sẽ được lượng tử hóa (quantize) và đưa vào mô hình TinyCNN (TensorFlow Lite Micro) để tính toán xác suất ngã.
5. **Cỗ máy trạng thái giảm cảnh báo giả (State Machine):** Đây là logic rất thực tế. Nếu AI báo ngã, hệ thống sẽ chưa báo động ngay. Nó chuyển sang trạng thái `FDS_FALL_WATCH` và `FDS_STILL_TIMING` để theo dõi sự bất động. Nếu người dùng có thể tự đứng dậy và đi lại (chuyển động mạnh), báo động bị hủy. Điều này giảm thiểu tối đa báo động giả (False Positive).
6. **Cảnh báo khẩn cấp:** Nếu xác nhận ngã thực sự, biến `gFallAlertActive` được kích hoạt. Hệ thống chớp LED Đỏ, hú Còi, và lập tức gửi gói tin BLE (`ALERT, fall, ...`) qua NimBLE đến ứng dụng Android. Android sẽ tự động gọi trực tiếp (Direct Call) cho người thân.

---

## 3. Vai Trò Của Bạn (Project Leader) - Chứng minh bằng Code

**Câu hỏi dự kiến:** *"Trong slide bạn ghi là người thiết kế firmware, tích hợp AI và làm giao thức BLE. Bạn đã đối mặt với những khó khăn kỹ thuật gì và giải quyết ra sao?"*

**Luận điểm trả lời theo từng thành tựu:**

* ✅ **Designed embedded firmware architecture:** 
  * *"Tôi đã thiết kế kiến trúc phân chia tác vụ song song trên FreeRTOS. Quản lý việc truyền dữ liệu giữa các Task bằng Ring Buffer kết hợp Mutex, đảm bảo không bị thất thoát khung hình cảm biến khi AI đang chạy."*
* ✅ **Implemented BMI160 IMU driver & I2C:** 
  * *"Thay vì phụ thuộc vào thư viện bên thứ 3 cồng kềnh, tôi đã viết trực tiếp các hàm giao tiếp I2C (`readReg`, `writeReg`) với BMI160. Tôi tự cấu hình thanh ghi dải đo và tính toán tỷ lệ chuyển đổi LSB sang đơn vị vật lý (`g`, `dps`)."*
* ✅ **Integrated TensorFlow Lite Micro model:** 
  * *"Tôi đã tối ưu hóa mô hình TinyCNN xuống chuẩn int8, dung lượng chỉ còn ~10.7 KB để vừa vặn với SRAM của MCU. Tôi đã viết logic khởi tạo `MicroInterpreter`, cấp phát tĩnh `tensorArena` (60KB), và xử lý quá trình lượng tử hóa (quantize) input/output."*
* ✅ **Built BLE alert protocol & state machine:** 
  * *"Tôi chọn `NimBLE` stack vì nó tối ưu RAM hơn stack BLE chuẩn của ESP-IDF. Tôi thiết kế một giao thức string nhẹ (dễ parse trên Android) gồm các lệnh `ALERT`, `SAFE`, `BATCH`. Đồng thời tích hợp cơ chế bắt tay `READY` đảm bảo kết nối tin cậy."*
* ✅ **Implemented LED, buzzer & button logic:** 
  * *"Tôi thiết kế một State Machine riêng cho LED để dễ dàng debug trực quan các luồng xử lý bằng mắt. Nút bấm vật lý được viết hàm chống nhiễu (Debounce) cẩn thận, cho phép đa tính năng: Nhấn khi bình thường thì gửi báo khẩn cấp (SOS), nhấn khi đang hú còi thì gửi lệnh `SAFE` báo an toàn."*

---

## 💡 Mẹo nhỏ ghi điểm thêm:
1. **Kiến trúc linh hoạt (Modularity):** Nhấn mạnh rằng code được thiết kế dạng module. Ví dụ: Dữ liệu nhịp tim và SpO2 hiện đang được mô phỏng sẵn (Simulated) để test giao thức BLE. Khi lắp cảm biến MAX30102 thật vào, chỉ cần sửa đúng 2 hàm đọc cảm biến mà không ảnh hưởng gì đến luồng hệ thống hay giao thức truyền.
2. **Quản lý RAM chặt chẽ:** Đề cập đến việc sử dụng mảng tĩnh (Static Arrays) và cấp phát bộ nhớ cố định (như `tensorArena`) ngay từ đầu để tránh lỗi phân mảnh bộ nhớ rò rỉ (memory leak) gây crash thiết bị khi hoạt động 24/7.
