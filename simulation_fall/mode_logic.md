# Logic Sinh Dữ Liệu và Suy Luận AI (Toggle Switch)

Dưới đây là sơ đồ luồng logic hoạt động khi bạn bật/tắt công tắc ở Frontend, giải thích cách Dữ Liệu sinh ra -> Đẩy vào Model -> Ra Output:

## 1. Sinh Dữ Liệu ngầm (Background Data Gen)
Hệ thống tạo ra một luồng dữ liệu giả lập IMU độc lập, chạy liên tục ở tốc độ `50Hz` (50 dòng/giây):

*   **Trạng thái Công tắc (OFF)**: `is_fall_mode = False`
    *   Hệ thống liên tục sinh ra **Dữ liệu bình thường (Non-fall Data)**:
        *   Gia tốc `acc_z` giao động yên bình quanh mốc `1.0 G` (Chỉ số trọng lượng cơ thể).
        *   Gia tốc x, y và Tốc độ góc (Gyro) siêu nhỏ nhắn quanh mốc `0`.
    *   Dữ liệu này được gán ngầm Ground Truth là `non_fall`.

*   **Trạng thái Công tắc (ON)**: `is_fall_mode = True`
    *   Hệ thống liên tục sinh ra **Dữ liệu loạn biến (Fall Data)** mô tả trạng thái bất thường:
        *   Gia tốc z, x, y quật lên quật xuống từ `-5G` đến `6G` liên tục.
        *   Vận tốc góc xoay điên đảo `> 250 độ/giây`.
    *   Dữ liệu này được gán ngầm Ground Truth là `fall`.

## 2. Model Xử Lý (Inference)
Chứa ở hàm `mock_model.predict(window)`:
*   Mỗi khi kho dữ liệu gom đủ **100 mẫu (tương đương với 2 giây thời gian)**, toàn bộ `window` 100 dòng này sẽ bị quẳng thẳng vào hàm AI dự đoán.
*   Model **hoàn toàn KHÔNG BIẾT công tắc trên màn hình đang bật hay tắt**. Nhiệm vụ duy nhất của model là nhìn vào bảng 100 số liệu IMU này.
    *   Nếu nó thấy gia tốc văng mạnh, nó định lượng và chốt Output là `fall`.
    *   Nó sẽ so Output này với cái Ground Truth lén gửi kèm ban đầu. Nếu `Output == Ground Truth`, nó đánh giá là AI nhận diện **ĐÚNG (CORRECT)**, ngược lại là sai.

--- 
**KẾT LUẬN về việc "Bật chế độ té ngã nhưng dữ liệu không biến đổi"**
Như đã giải thích, quá trình này do file `simulation.py` điều khiển ngầm. Tuy nhiên hệ thống terminal của bạn đang cho thấy tiến trình python cũ đã chạy liên tục tận `41m30s`. Bạn chưa hề ấn Ctrl+C để tắt luồng python cũ đi để khởi động lại bản mới nhất (có API Công Tắc). Do đó front-end gửi tín hiệu bật công tắc thì Backend cũ không thể tiếp nhận và thay đổi tần số sinh dữ liệu được!
