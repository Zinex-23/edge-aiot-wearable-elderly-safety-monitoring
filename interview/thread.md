# Phân Tích Hoạt Động Của 2 Luồng (Threads / Tasks) Trong Hệ Thống

Để tận dụng sức mạnh của chip ESP32-S3 (Dual-Core), kiến trúc phần mềm của bạn được thiết kế với 2 luồng (Task) chạy song song trên 2 nhân (Core) khác nhau. Dưới đây là phân tích chi tiết về cách chúng hoạt động và giao tiếp với nhau.

---

## 1. Luồng 1: Thu Thập Dữ Liệu (`taskSampling`) - Chạy trên Core 0

**Mục đích:** Luồng này đóng vai trò như "Giác quan", có nhiệm vụ duy nhất là đọc dữ liệu liên tục từ cảm biến với chu kỳ thời gian cực kỳ chính xác.

**Đặc điểm cấu hình:**
*   **Vị trí:** Bị "ghim" (pinned) cứng vào **Core 0**.
*   **Độ ưu tiên:** `configMAX_PRIORITIES - 1` (Mức ưu tiên gần như cao nhất trong hệ thống). Đảm bảo việc đọc cảm biến không bao giờ bị trì hoãn bởi các tác vụ khác.

**Cách hoạt động (Vòng lặp vô tận):**
1.  **Chờ đúng thời điểm:** Gọi `vTaskDelayUntil(..., 20ms)`. Luồng sẽ "ngủ" và thức dậy chính xác mỗi 20ms (tương đương tần số 50Hz) để bắt đầu một chu kỳ mới.
2.  **Đọc cảm biến:** Đọc 6 trục (Gia tốc + Góc quay) từ cảm biến BMI160 thông qua I2C.
3.  **Xin khóa Mutex:** Gọi `xSemaphoreTake(gImuMutex)`. Core 0 yêu cầu khóa cửa kho chứa dữ liệu.
4.  **Lưu dữ liệu:** Sau khi có khóa, đẩy dữ liệu vừa đọc vào một mảng vòng (Ring Buffer - `gImuWindow`).
5.  **Trả khóa Mutex:** Gọi `xSemaphoreGive(gImuMutex)` ngay lập tức để Core 1 có thể sử dụng mảng nếu cần.
6.  **Đánh thức Core 1 (Trigger):** Nếu mảng đã nạp đủ 100 mẫu (đủ 1 window), Core 0 sẽ phát tín hiệu bằng lệnh `xTaskNotifyGive(gInferenceTask)` để "hét" lên cho Core 1 biết: *"Dữ liệu đã sẵn sàng, dậy chạy AI đi!"*.

---

## 2. Luồng 2: Xử Lý Trí Tuệ Nhân Tạo (`taskInference`) - Chạy trên Core 1

**Mục đích:** Luồng này đóng vai trò như "Bộ não", chuyên thực hiện các phép toán nhân ma trận nặng nề của mạng Neural để phát hiện té ngã.

**Đặc điểm cấu hình:**
*   **Vị trí:** Bị "ghim" (pinned) cứng vào **Core 1**.
*   **Độ ưu tiên:** `1` (Mức ưu tiên thấp hơn luồng đọc cảm biến).

**Cách hoạt động (Vòng lặp vô tận):**
1.  **Ngủ đông chờ lệnh:** Khởi đầu vòng lặp, Core 1 gọi lệnh `ulTaskNotifyTake(..., portMAX_DELAY)`. Lệnh này ép Core 1 vào trạng thái ngủ sâu (Block state), không tiêu tốn một phần trăm CPU nào cho đến khi nhận được "tiếng hét" (Notification) từ Core 0 ở bước 6 bên trên.
2.  **Thức dậy & Xin khóa Mutex:** Ngay khi nhận tín hiệu, Core 1 tỉnh dậy, gọi `xSemaphoreTake(gImuMutex)` để khóa kho chứa dữ liệu. (Nếu đúng lúc này Core 0 đang nhét dữ liệu vào kho, Core 1 sẽ phải đứng đợi).
3.  **Copy Dữ liệu (Snapshot):** Core 1 sao chép nhanh 100 mẫu từ `gImuWindow` sang một mảng nháp của riêng nó gọi là `gSnapshot`.
4.  **Trả khóa Mutex CẤP TỐC:** Ngay khi copy xong, Core 1 gọi ngay `xSemaphoreGive(gImuMutex)`. 
    👉 *Đây là kỹ thuật lập trình cực kỳ tinh tế: Nhờ trả khóa sớm, Core 0 có thể tiếp tục nhét dữ liệu mới vào mảng gốc mà không bị chặn lại, trong khi Core 1 thong thả xử lý mảng copy (`gSnapshot`).*
5.  **Chạy Thuật Toán Lọc (Gates):** Core 1 duyệt qua mảng `gSnapshot` xem có đỉnh (Peak) chuyển động nào vượt ngưỡng không (`ACTIVITY_ACC_THRESHOLD`). Nếu có chuyển động đáng ngờ, nó mới bật cửa sổ AI.
6.  **Chạy AI (Inference):** 
    *   Ép kiểu (Quantize) dữ liệu từ float sang số nguyên int8.
    *   Gọi hàm TFLite `interpreter->Invoke()` để chạy mạng Neural. Quá trình này tốn nhiều thời gian nhất (vài chục mili-giây). Do chạy ở Core 1 nên nó hoàn toàn không làm gián đoạn việc đọc cảm biến ở Core 0.
    *   Lấy kết quả `fallProb` (Xác suất ngã).
7.  **Quản lý Trạng Thái (State Machine):** Đưa kết quả vào cỗ máy trạng thái (`updateFallStateMachine`). Nếu xác định chắc chắn ngã (và không có cử động sau đó), sẽ kích hoạt biến báo động `gFallAlertActive`.

---

## 3. Tóm Tắt Sự Kết Hợp

Mô hình 2 luồng này áp dụng mẫu thiết kế **Producer - Consumer (Người sản xuất - Người tiêu thụ)**:
*   **Core 0 (Producer):** Mù quáng nhặt rau (đọc I2C) mỗi 20ms, bỏ rau vào rổ (Ring Buffer). Khi rổ đầy thì bấm chuông (`xTaskNotifyGive`).
*   **Core 1 (Consumer):** Đang ngủ, nghe chuông thì dậy. Tranh thủ lấy rổ rau đổ ra thau của mình (`gSnapshot`), trả rổ ngay để Core 0 hái tiếp. Sau đó thong thả mang thau đi nấu ăn (chạy AI) mà không sợ Core 0 hối thúc.
*   **Chiếc Rổ (Mutex):** Để tránh việc Core 1 đang đổ rau ra thau mà Core 0 lại quăng cọng rau mới vào gây văng vãi, cả 2 phải tuân thủ quy tắc khóa rổ bằng Mutex. Ai cầm khóa mới được đụng vào rổ.
