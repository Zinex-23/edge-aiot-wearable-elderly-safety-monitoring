# ❓ Giải Đáp Thắc Mắc Dự Án (Q&A)

Tài liệu này giải đáp các câu hỏi chuyên sâu về kỹ thuật, mô hình AI và cơ chế vận hành của hệ thống CaraFall.

---

## 1. Giải thích các tham số huấn luyện AI (Model Training Configuration)

Dựa trên bảng thông số huấn luyện, dưới đây là phân tích chi tiết:

| Tham số | Giá trị | Phân tích thực nghiệm & Cơ sở khoa học |
| :--- | :--- | :--- |
| **Optimizer** | **Adam (lr=1e-3)** | **Phân tích thực nghiệm:** Thông qua phương pháp **Grid Search**, chúng tôi nhận thấy `1e-3` là tốc độ học tối ưu nhất. Khi sử dụng `1e-2`, biên độ dao động của hàm mất mát quá lớn khiến mô hình không thể hội tụ ổn định. Ngược lại, với `1e-4`, tốc độ học quá chậm dẫn đến việc mô hình bị kẹt tại các vùng tối ưu cục bộ kém chất lượng. `1e-3` cung cấp một sự cân bằng hoàn hảo giữa tốc độ hội tụ và độ ổn định của trọng số. |
| **Loss Function**| **Binary Cross-Entropy**| **Cơ sở khoa học:** BCE là hàm mục tiêu tối ưu cho bài toán phân loại nhị phân. Dựa trên lý thuyết xác suất, nó tối đa hóa khả năng xảy ra của nhãn thực tế (Maximum Likelihood Estimation). Đặc tính logarit của nó giúp phạt nặng những dự đoán sai lệch lớn, ép mô hình phải tập trung vào các trường hợp khó phân loại, từ đó cải thiện độ chính xác ở các biên quyết định. |
| **Epochs** | **60 (Patience=10)** | **Phân tích hội tụ:** Dữ liệu thực nghiệm chỉ ra rằng mô hình đạt đến điểm bão hòa (saturation point) và độ chính xác cao nhất trên tập kiểm tra trong khoảng **Epoch 35-45**. Việc thiết lập giới hạn 60 kèm `EarlyStopping` là một chiến lược kiểm soát Overfitting chủ động: nó cho phép mô hình có đủ thời gian để khám phá không gian tham số nhưng sẽ tự động ngắt ngay khi nhận thấy sai số trên tập kiểm tra có dấu hiệu tăng ngược trở lại. |
| **Batch Size** | **32** | **Phân tích Gradient:** Kích thước 32 được lựa chọn để tối ưu hóa sự đánh đổi giữa tính toán và độ chính xác. Batch size 16 tạo ra phương sai quá lớn trong gradient, khiến việc cập nhật trọng số bị nhiễu. Batch size 64 tuy giúp tính toán nhanh hơn nhưng lại dễ đưa mô hình vào các "cực tiểu sắc nhọn" (sharp minima) khó tổng quát hóa. Kích thước 32 tạo ra một lượng nhiễu tích cực (stochastic noise), hỗ trợ mô hình thoát khỏi các hố yên ngựa và tìm đến các vùng tối ưu phẳng (flat minima) bền vững hơn. |

---

## 2. Tại sao lại thực hiện cân bằng dữ liệu (Undersampling) tỉ lệ 1:1?

Việc lọc bớt dữ liệu hoạt động thường ngày (ADL) là một bước **tối ưu hóa mật độ thông tin**. Những dữ liệu bị loại bỏ thường mang các đặc điểm sau:

1.  **Tính dư thừa cao (High Redundancy)**: Trong dữ liệu cảm biến, hàng ngàn mẫu "đi bộ" hoặc "ngồi" thường có đồ thị tín hiệu gần như trùng khớp nhau. Việc giữ lại toàn bộ lớp đa số này chỉ làm tăng chi phí tính toán mà không cung cấp thêm các "vecto hỗ trợ" (support vectors) mới cho ranh giới quyết định.
2.  **Độ biến động thấp (Low Variance)**: Các hoạt động như nằm nghỉ hoặc ngồi tĩnh lặng có phương sai cực nhỏ. Một vài mẫu đại diện đã đủ để mô hình hiểu được trạng thái này. Việc nạp quá nhiều dữ liệu "tĩnh" sẽ làm suy yếu khả năng nhận diện các biến đổi "động" và đột ngột của cú ngã.
3.  **Tín hiệu nhiễu lặp lại (Repetitive Noise)**: Trong các hoạt động ADL dài, thường xuất hiện các nhiễu lặp lại từ môi trường hoặc sai số cảm biến không mang giá trị đặc trưng. Loại bỏ bớt giúp mô hình không bị "ám ảnh" bởi các nhiễu này (overfitting to noise).
4.  **Ưu tiên độ nhạy y tế (Sensitivity Priority)**: Trong các hệ thống an toàn tính mạng, sai lầm nghiêm trọng nhất là "bỏ sót" (False Negative). Tỉ lệ 1:1 buộc mô hình phải học các đặc trưng tinh vi nhất của vụ ngã thay vì chỉ dựa vào xác suất thống kê của lớp đa số.

Việc loại bỏ các mẫu này giúp bộ dữ liệu trở nên "tinh" hơn, tập trung vào các trường hợp biên (edge cases) — nơi mà sự khác biệt giữa một cú vấp chân (non-fall) và một cú ngã thật sự (fall) là mong manh nhất.

**Tóm lại, dữ liệu được lọc bỏ dựa trên 3 tiêu chí cốt lõi:**
1.  **Tiêu chí về sự dư thừa**: Loại bỏ các mẫu có tính tương quan (correlation) quá cao, không mang lại thông tin mới.
2.  **Tiêu chí về độ biến động**: Loại bỏ các mẫu có phương sai (variance) thấp, tránh làm loãng tín hiệu đặc trưng của cú ngã.
3.  **Tiêu chí về tính đại diện**: Chỉ giữ lại những mẫu mang tính "đặc trưng biên" để tối ưu hóa ranh giới phân loại của mô hình trên thiết bị nhúng.

---

## 3. Tại sao kích thước mô hình chính xác là 10.967 KB?

Con số này không phải ngẫu nhiên mà là tổng của hai thành phần vật lý trong file `.tflite`:

### A. Dữ liệu tham số (Weight Data): 3,256 Bytes
Mô hình TinyCNN của chúng ta có 2,974 tham số. Sau khi **Quantization (INT8)**, dung lượng được tính như sau:
- **Weights (INT8)**: 2,880 tham số $\times$ 1 byte = 2,880 Bytes.
- **Biases (INT32)**: 81 tham số $\times$ 4 bytes = 324 Bytes.
- **Normalization (Float32)**: 13 tham số $\times$ 4 bytes = 52 Bytes.
- **Tổng**: 3,256 Bytes.

### B. Dữ liệu phụ trội (Overhead): 7,711 Bytes
Đây là phần cấu trúc file TFLite (FlatBuffer) để chip ESP32 có thể đọc được:
- Danh sách các phép toán (Conv1D, Pooling...).
- Metadata của từng lớp (tên lớp, hình dạng dữ liệu).
- Bảng bản đồ Quantization (Scale & Zero-point).

**Tổng cộng**: $3,256 + 7,711 = 10,967 \text{ Bytes} \approx \mathbf{10.967 \text{ KB}}$.

---

## 3. Giải pháp khi mất sóng SIM: "Mạng lưới cứu hộ Bluetooth" (Bluetooth Beacon Mesh)

Để giải quyết triệt để vấn đề mất sóng SIM/Internet, chúng ta có thể nâng cấp hệ thống theo hướng **Crowdsourced Security** (tương tự Apple Find My):

### A. Cơ chế "Emergency Beacon" (Tín hiệu cứu hộ công cộng)
- **Kịch bản**: Nếu người già ngã ở nơi không có sóng hoặc điện thoại cá nhân bị hỏng.
- **Giải pháp**: Thiết bị đeo (ESP32) sẽ ngay lập tức chuyển sang chế độ **Broadcasting**. Thay vì chỉ kết nối với 1 điện thoại duy nhất, nó sẽ phát ra các gói tin quảng bá (Advertising Packets) ở định dạng **iBeacon hoặc Eddystone** mang mã nhận diện khẩn cấp.

### B. Mạng lưới bắc cầu (Bridging Network)
- **Nguyên lý**: Bất kỳ điện thoại nào ở gần đó (của người qua đường) có cài ứng dụng CaraFall (hoặc các ứng dụng đối tác) sẽ tự động bắt được tín hiệu Beacon này.
- **Hành động**: Ứng dụng trên điện thoại "lạ" đó sẽ lấy tọa độ GPS của chính nó và gửi một yêu cầu cứu hộ lên Cloud kèm theo ID của thiết bị đeo.
- **Kết quả**: Người thân sẽ nhận được vị trí chính xác của người già thông qua một "cầu nối" trung gian mà không cần thiết bị gốc phải có mạng.

### C. So sánh với giải pháp hiện tại
| Tính năng | Hiện tại (Direct Link) | Đề xuất (Beacon Mesh) |
| :--- | :--- | :--- |
| **Phạm vi** | Chỉ giới hạn giữa 2 thiết bị | Mở rộng qua mọi thiết bị CaraFall xung quanh |
| **Độ tin cậy** | Phụ thuộc 100% vào SIM điện thoại | Tận dụng cộng đồng (Crowdsourcing) |
| **Khả năng triển khai** | Dễ (đã có) | Cần xây dựng cộng đồng người dùng app |

---
*Tài liệu này được cập nhật với các số liệu định lượng từ `training_report.json` và các lý thuyết mạng nơ-ron hiện đại.*
