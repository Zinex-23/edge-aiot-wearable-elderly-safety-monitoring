# Phân Tích Chi Tiết Mô Hình AI Phát Hiện Té Ngã (Edge AI)

Báo cáo này tập trung vào phân tích cấu trúc mô hình TinyCNN và quy trình huấn luyện cho dự án giám sát an toàn người già qua thiết bị đeo.

## 1. Kiến Trúc Mô Hình (Model Architecture)
Mô hình được thiết kế theo dạng **TinyCNN**, tối ưu cho việc chạy trên vi điều khiển như ESP32-S3 với kích thước sau khi nén chỉ khoảng **10.7 KB**.

### Giải thích chi tiết luồng xử lý của từng lớp:

1.  **Input Layer `(100, 6)`**:
    - **Nhiệm vụ**: Nhận dữ liệu thô từ cảm biến IMU.
    - **Chi tiết**: Dữ liệu là một "cửa sổ" thời gian dài 2 giây, chứa 100 điểm dữ liệu mẫu. Mỗi điểm mẫu có 6 thông số: `ax, ay, az` (gia tốc) và `gx, gy, gz` (tốc độ góc). Đây là "nguyên liệu thô" để mô hình bắt đầu phân tích hành vi.

2.  **Normalization Layer (Chuẩn hóa)**:
    - **Nhiệm vụ**: Đưa dữ liệu về cùng một thang đo (thường là trung bình bằng 0 và độ lệch chuẩn bằng 1).
    - **Chi tiết**: Vì các trục cảm biến có thể có tầm giá trị khác nhau (ví dụ: gia tốc có thể lớn, nhưng tốc độ góc lại nhỏ), lớp này giúp mô hình không bị "thiên vị" bởi các con số lớn, giúp quá trình học ổn định và chính xác hơn.

3.  **Conv1D - Lớp Tích chập 1 chiều (16 filters, kernel 3)**:
    - **Nhiệm vụ**: Trích xuất các đặc trưng cục bộ theo thời gian.
    - **Chi tiết**: Lớp này giống như một "kính lúp" trượt dọc theo 2 giây dữ liệu. Nó tìm kiếm các mẫu tín hiệu đặc trưng của việc té ngã, chẳng hạn như sự thay đổi cực mạnh và đột ngột của gia tốc trọng trường khi va chạm. Với 16 bộ lọc, nó có thể tìm kiếm 16 kiểu mẫu (pattern) khác nhau cùng lúc.

4.  **MaxPooling1D (giảm mẫu)**:
    - **Nhiệm vụ**: Giữ lại những tín hiệu mạnh nhất và loại bỏ nhiễu.
    - **Chi tiết**: Nó chia dữ liệu thành các đoạn nhỏ và chỉ giữ lại giá trị lớn nhất trong mỗi đoạn. Việc này giúp mô hình "bền bỉ" hơn với các sai lệch nhỏ về thời gian (ví dụ: cú ngã xảy ra sớm hay muộn một chút thì kết quả vẫn nhận diện đúng). Đồng thời, nó giúp giảm một nửa khối lượng tính toán, rất quan trọng cho chip ESP32.

5.  **Conv1D (32 filters, kernel 3)**:
    - **Nhiệm vụ**: Trích xuất các đặc trưng cấp cao.
    - **Chi tiết**: Sau khi dữ liệu đã được thu gọn ở lớp trước, lớp này tiếp tục phân tích sâu hơn để kết hợp các mẫu tín hiệu lại với nhau (ví dụ: kết hợp sự thay đổi gia tốc X với sự xoay của trục Gyro Y) để nhận diện các hành vi phức tạp hơn.

6.  **GlobalAveragePooling1D (Nén toàn cục)**:
    - **Nhiệm vụ**: tóm tắt toàn bộ 2 giây dữ liệu thành một bộ đặc trưng duy nhất.
    - **Chi tiết**: Thay vì giữ lại hàng chục điểm dữ liệu theo thời gian, lớp này tính trung bình cộng của mỗi filter từ lớp trước. Điều này biến một mảng dữ liệu dài thành một danh sách các "đặc tính" rút gọn. Đây là "bí quyết" giúp mô hình cực kỳ nhẹ (Tiny) nhưng vẫn giữ được thông tin quan trọng nhất.

7.  **Dense - Lớp ẩn (32 units)**:
    - **Nhiệm vụ**: "Suy luận" dựa trên các đặc trưng đã trích xuất.
    - **Chi tiết**: Đây là nơi mô hình thực hiện các phép tính logic phức tạp để tự hỏi: "Với các đặc tính này, xác suất có phải là một cú ngã hay không?". Nó kết nối các thông tin rời rạc lại thành một bức tranh tổng thể.

8.  **Output Dense - Lớp đầu ra (1 unit, Sigmoid)**:
    - **Nhiệm vụ**: Đưa ra con số quyết định cuối cùng.
    - **Chi tiết**: Hàm **Sigmoid** nén kết quả về khoảng từ **0.0 (không té)** đến **1.0 (chắc chắn té)**. Con số này sau đó sẽ được so sánh với ngưỡng **0.40** để kích hoạt cảnh báo.

---

## 2. Quy Trình Huấn Luyện (Training Process)

### Chuẩn bị dữ liệu:
-   **Nguồn**: Sử dụng tập dữ liệu `HR_IMU`.
-   **Cửa sổ hóa (Windowing)**: Mỗi cửa sổ dài 2 giây (100 mẫu ở tần số 50Hz).
-   **Bước nhảy (Stride)**: 50 mẫu (1 giây), tạo ra độ chồng lấp (overlap) 50% để không bỏ sót các sự kiện quan trọng.
-   **Cân bằng dữ liệu (Data Balancing)**: Sử dụng phương pháp **Undersampling**. Vì số ngày hoạt động bình thường (non-fall) nhiều hơn nhiều so với lúc té ngã (fall), hệ thống đã lấy mẫu ngẫu nhiên tập `non-fall` để khớp với số lượng tập `fall` (tỷ lệ 1:1).

### Cấu hình Train:
-   **Optimizer**: Adam (learning rate: 0.001).
-   **Loss Function**: Binary Crossentropy (phù hợp cho phân loại 2 lớp).
-   **Epochs**: Tối đa 60 vòng lặp.
-   **Early Stopping**: Dừng sớm nếu hàm mất mát (loss) trên tập kiểm thử (validation) không còn giảm sau 10 epoch để tránh quá khớp (overfitting).

---

## 3. Thông Số Và Hiệu Năng
-   **Threshold (Ngưỡng quyết định)**: Được chọn là **0.40** (thay vì 0.50 mặc định) để tăng độ nhạy (Recall).
-   **Recall (Độ phủ)**: Đạt **98.36%** - Nghĩa là gần như mọi trường hợp té ngã đều được phát hiện (rất quan trọng trong y tế).
-   **Accuracy (Độ chính xác)**: **90.80%**.
-   **False Alarm Rate**: **16.73%** (Cảnh báo sai có xảy ra nhưng đã được đánh đổi để lấy Recall cao).

---

## 4. Triển Khai Trên ESP32-S3 (Deployment)
Mô hình được chuyển đổi sang định dạng **TFLite INT8 Quantization**.
-   **Dữ liệu đầu vào**: Phải đảm bảo đúng thứ tự kênh: `ax, ay, az, gx, gy, gz`.
-   **Tần số lấy mẫu**: Cần duy trì ở **50Hz** để đồng bộ với cấu hình huấn luyện.
-   **Kích thước Header**: File `.h` được xuất ra để nhúng trực tiếp vào mã nguồn C++ của ESP32.
