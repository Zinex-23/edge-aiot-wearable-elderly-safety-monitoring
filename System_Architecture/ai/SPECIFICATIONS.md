# 🧠 AI Model Specifications (TinyCNN)

Tài liệu này chi tiết về kiến trúc, quá trình huấn luyện và tối ưu hóa của mô hình trí tuệ nhân tạo phát hiện té ngã.

## 1. Kiến trúc Mô hình (Model Architecture)

Mô hình là mạng nơ-ron tích chập 1 chiều (1D-CNN) được tối ưu hóa cho tài nguyên thấp.

| Layer | Type | Output Shape | Param # |
| :--- | :--- | :--- | :--- |
| **Input** | imu_window | (None, 100, 6) | 0 |
| **Normalization**| balanced_norm | (None, 100, 6) | 13 |
| **Conv1D** | 16 filters, k3 | (None, 100, 16) | 304 |
| **MaxPooling1D** | pool size 2 | (None, 50, 16) | 0 |
| **Conv1D** | 32 filters, k3 | (None, 50, 32) | 1,568 |
| **GlobalAveragePool**| GAP Layer | (None, 32) | 0 |
| **Dense** | Hidden Layer | (None, 32) | 1,056 |
| **Output** | fall_prob (Sigmoid) | (None, 1) | 33 |

## 2. Thông số Huấn luyện (Training Parameters)

| Đặc tính | Giá trị | Ghi chú |
| :--- | :--- | :--- |
| **Optimizer** | Adam | Tốc độ học (lr) = 0.001 |
| **Loss Function** | Binary Crossentropy| Phân loại nhị phân (Fall/Non-fall) |
| **Epochs** | 60 | Kèm Early Stopping (patience=10) |
| **Batch Size** | 32 | Phù hợp với kích thước dataset |
| **Dataset Balance** | Undersampling | Cân bằng tỷ lệ Fall:Non-fall (1:1) |

## 3. Tối ưu hóa & Triển khai (TinyML)

| Kỹ thuật | Chi tiết | Lợi ích |
| :--- | :--- | :--- |
| **Quantization** | **Post-training INT8** | Giảm kích thước và tăng tốc trên MCU |
| **Input Feature** | ax, ay, az, gx, gy, gz | 6 kênh tín hiệu IMU đồng bộ |
| **Preprocessing** | Z-score Normalization | Ổn định tín hiệu đầu vào cho AI |
| **Decision Threshold**| **0.40** | Tối ưu hóa để đạt Recall 98.36% |

## 4. Dataset (Dữ liệu huấn luyện)

Dữ liệu được kết hợp từ nhiều nguồn tập trung vào vị trí đeo ở cổ tay (Wrist-based) để tăng độ chính xác:
- **Nguồn**: HR_IMU Dataset (Fall & ADL sequences).
- **Tổng số cửa sổ**: 3,256 (sau khi đã cân bằng).
- **Tần số lấy mẫu**: 50 Hz.
- **Thời lượng mỗi cửa sổ**: 2.0 giây (100 mẫu).

## 5. Hình ảnh kết quả (Results Visualization)

Dưới đây là các biểu đồ minh chứng cho hiệu năng của mô hình (đã được tối ưu độ tương phản cho Slide):

![Confusion Matrix](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/ai/results/images/confusion_matrix.png)
*Hình 1: Ma trận nhầm lẫn (Confusion Matrix) với độ tương phản cao.*

![ROC Curve](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/ai/results/images/roc_curve.png)
*Hình 2: Đường cong ROC (AUC = 0.9712).*

![Training History](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/ai/results/images/training_accuracy.png)
*Hình 3: Quá trình hội tụ của Độ chính xác (Accuracy).*

![Precision-Recall](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/ai/results/images/precision_recall_curve.png)
*Hình 4: Đường cong Precision-Recall.*
