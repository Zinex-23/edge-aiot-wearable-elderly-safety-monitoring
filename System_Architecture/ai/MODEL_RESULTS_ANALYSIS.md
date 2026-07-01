# 📊 Phân tích Kết quả Mô hình AI & Lựa chọn Ngưỡng (Threshold)

Tài liệu này giải thích chi tiết các chỉ số đạt được và lý do kỹ thuật đằng sau việc lựa chọn ngưỡng quyết định cho mô hình phát hiện té ngã.

## 1. Kết quả Hiệu năng Tổng thể

Dựa trên dữ liệu huấn luyện và kiểm thử với kiến trúc TinyCNN, mô hình đạt được các chỉ số sau:

| Chỉ số (Metric) | Kết quả (Value) | Mô tả |
| :--- | :--- | :--- |
| **Recall (Độ nhạy)** | **98.36%** | Khả năng phát hiện đúng các cú ngã thật |
| **Accuracy (Độ chính xác)**| **90.80%** | Tỷ lệ dự đoán đúng trên toàn bộ tập dữ liệu |
| **Precision** | **85.41%** | Tỷ lệ thực sự ngã trong các dự báo "Fall" |
| **F1-Score** | **91.43%** | Chỉ số cân bằng giữa Precision và Recall |

## 2. Phân tích Ngưỡng Quyết định (Threshold Analysis)

Ngưỡng mặc định của hầu hết các mô hình phân loại là **0.50**. Tuy nhiên, đối với bài toán an toàn sức khỏe người già, chúng ta đã điều chỉnh ngưỡng xuống **0.40**.

### Tại sao chọn ngưỡng 0.40?

Lý do xuất phát từ việc đối chiếu với **Đặc tả yêu cầu (Specifications)** ban đầu:

1.  **Ưu tiên An toàn Tuyệt đối (Safety First)**:
    *   **Yêu cầu**: "Mục tiêu là không được bỏ lỡ bất kỳ cú ngã nào".
    *   **Phân tích**: Trong y tế, lỗi **False Negative** (Người già ngã nhưng hệ thống không báo) cực kỳ nguy hiểm, có thể dẫn đến tử vong. Lỗi **False Positive** (Người già không ngã nhưng App báo) chỉ gây ra một chút phiền toái nhỏ.
    *   **Kết luận**: Hạ ngưỡng xuống 0.40 giúp tăng Recall từ ~92% lên **98.36%**, đảm bảo xác xuất bỏ sót là cực thấp (< 2%).

2.  **Cân bằng với Độ trễ (Latency < 2s)**:
    *   Ngưỡng 0.40 cho phép mô hình phản ứng nhanh hơn với các tín hiệu "chớm" có dấu hiệu té ngã, giúp rút ngắn thời gian ra quyết định so với việc chờ tín hiệu đạt mức cực kỳ chắc chắn (>0.50).

3.  **Đặc tính của dữ liệu IMU trên cổ tay**:
    *   Dữ liệu từ cổ tay thường có nhiều nhiễu do các hoạt động sinh hoạt (ADL). Ngưỡng 0.40 được tìm ra thông qua việc quét (Threshold Sweeping) để đạt được điểm tối ưu giữa việc giữ Recall cao nhất trong khi vẫn duy trì Accuracy tổng thể trên 90% (Thỏa mãn yêu cầu M1).

## 3. Ma trận Nhầm lẫn (Confusion Matrix)

![Improved Confusion Matrix](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/ai/results/images/confusion_matrix.png)

*   **Nhận xét**: Chỉ có **4 trường hợp** ngã bị bỏ sót (False Negatives) trong tổng số hàng trăm mẫu thử nghiệm. Đây là con số cực kỳ ấn tượng cho một mô hình chạy trên thiết bị nhúng (Edge AI).

---
*Kết luận: Ngưỡng 0.40 là lựa chọn chiến lược để đánh đổi một chút độ chính xác tổng thể lấy sự an toàn tối đa cho người già.*
