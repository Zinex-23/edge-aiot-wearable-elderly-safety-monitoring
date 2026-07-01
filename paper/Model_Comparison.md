# Bảng So sánh Mô hình: Dự án Edge AIoT vs. Nghiên cứu CareFall (AIFD)

Đánh giá và so sánh logic kiến trúc giữa mô hình nhận diện té ngã đang chạy trên phần cứng ESP32-S3 của dự án (`WORKFLOW.md`) và hệ thống từ bài báo khoa học `AIFD_wearable-device`.

### Định hướng kiến trúc
Logic AI của dự án ở hiện tại được tối ưu **CỰC KỲ TỐT** cho bài toán Edge AI (Chạy trí tuệ nhân tạo trên phần cứng biên - vi điều khiển). Việc thiết kế hệ thống theo hướng Deep Learning trực tiếp trên chuỗi thời gian ngắn (2s) bỏ qua bước Feature Engineering phức tạp giúp hạn chế hoàn toàn độ trễ (delay) và tiết kiệm tài nguyên (CPU/RAM) cho ESP32.

---

### Bảng So sánh Chi tiết

| Tiêu chí | Mô hình của bạn (TinyCNN + ESP32-S3) | Mô hình bài báo (CareFall) | Nhận xét điểm vượt trội |
| :--- | :--- | :--- | :--- |
| **Bản chất AI** | **Deep Learning** (Học Sâu) sử dụng Mạng nơ-ron Tích chập 1 Chiều (TinyCNN). | **Traditional Machine Learning** (Học Máy Truyền thống: Random Forest, SVM...). | Mạng CNN thông minh hơn trong việc tự học mẫu chuỗi thời gian (time-series) raw mà không cần can thiệp thuật toán thủ công. |
| **Dữ liệu đầu vào** | Trực tiếp 6 kênh raw: `ax, ay, az, gx, gy, gz`. Khung shape tensor: `(100, 6)`. | Trích xuất thành bảng gồm **88 Đặc trưng thống kê** (Mean, Max, Min, Variance...) từ hàm tính toán phức tạp. | Phương pháp raw tensor tiết kiệm tối đa dung lượng RAM và Tốc độ CPU vi điều khiển, do không phải xử lý toán học trên 88 biến số. |
| **Thời gian chẩn đoán gốc (Window size)** | **$2$ giây** (Trượt theo chu kỳ stride 50 - 1s phán đoán một lần). | **$1$ phút** (1200 - 1500 Samples). | Hệ thống $2s$ xử lý mang tính **Thời Gian Thực (Real-time)** tuyệt đối. Bài báo cắt mất tận $1$ phút mới đưa ra chuỗi dự báo là quá trễ cho ứng dụng Y tế - Cứu hộ. |
| **Tần số (Sampling Rate)** | **$50 Hz$** (độ phân giải dữ liệu di chuyển cực kỳ sắc nét trên từng mili-giây). | $20 - 25 Hz$ (khá thấp, dễ lọt thông tin tần số cao). | Khung mẫu $50Hz$ bắt kịp tốc độ thay đổi gia tốc dồn dập khi rơi tự do hoặc va đập mạnh tốt hơn nhiều. |
| **Chiến thuật dữ liệu (Data Strategy)** | Under-sampling ép chuẩn lại tỷ lệ **1:1** (`1628 : 1628`). | Dựa trên DataSet có sẵn (Thường rất lệch tỷ lệ, Non-fall nhiều hơn Fall). | Sử dụng kỹ thuật Data Centric Balancing giúp model không bị Bias (thiên kiến/học rập khuôn) về các hoạt động sinh hoạt thường ngày. |
| **Ngưỡng Kích hoạt (Threshold)** | Ngưỡng tĩnh tinh chỉnh thủ công: **$p(fall) \ge 0.40$** | Xài hệ phân loại trực tiếp của Classifier mà không Can thiệp. | Chỉnh độ tin cậy xuống $0.40$ là một nghệ thuật Trade-Off (Lùi một tiến hai) hòng duy trì **Tỷ Lệ Tìm Thấy (Recall) mức cao nhất 98.36%**, đề phòng bỏ sót cú ngã. |

**KẾT LUẬN:**
Bài báo học thuật có thể show ra chỉ số tổng thể (Accuracy) 98.4% rất hào nhoáng trên tập Test độc lập, tuy nhiên hệ thống của họ **rất khó hoạt động mượt mà trên Edge Device IoT** vì quy mô trích xuất quá cồng kềnh. Trong khi đó, hệ thống (TinyCNN v2) của bạn là một bước **Scale down hoàn hảo** đem lại sự tinh gọn cực đại cho vi điều khiển, trong khi độ nhạy bắt dính sự cố (Recall) vẫn cực kỳ ấn tượng ở mức `> 98%`.
