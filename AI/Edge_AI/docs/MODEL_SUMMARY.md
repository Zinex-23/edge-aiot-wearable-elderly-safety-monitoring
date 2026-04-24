# 🧠 Bảng Tóm Tắt Kiến Trúc Mô Hình (Model Summary)

Dưới đây là bảng chi tiết các lớp (layers) trong mô hình TinyCNN được thiết kế để chạy trên ESP32-S3. Thông tin này được trích xuất trực tiếp từ cấu trúc mã nguồn và rất phù hợp để trình bày trong Slide.

| Layer (type) | Output Shape | Param # |
| :--- | :--- | :--- |
| **imu_window** (Input) | (None, 100, 6) | 0 |
| **balanced_norm** (Normalization) | (None, 100, 6) | 13 |
| **conv1d** (Conv1D) | (None, 100, 16) | 304 |
| **max_pooling1d** (MaxPooling1D) | (None, 50, 16) | 0 |
| **conv1d_1** (Conv1D) | (None, 50, 32) | 1,568 |
| **global_average_pool** (GAP) | (None, 32) | 0 |
| **dense** (Dense) | (None, 32) | 1,056 |
| **fall_prob** (Output/Dense) | (None, 1) | 33 |

### 📊 Thống kê tham số (Parameters Statistics)

- **Tổng số tham số (Total params):** 2,974
- **Tham số có thể huấn luyện (Trainable params):** 2,962
- **Tham số không huấn luyện (Non-trainable params):** 12 (Mean & Variance của lớp Normalization)
- **Kích thước mô hình (TFLite):** ~10.7 KB

---

> [!TIP]
> **Ghi chú cho Slide:** Khi thuyết trình, bạn có thể nhấn mạnh rằng mô hình chỉ có gần **3,000 tham số** nhưng đạt độ nhạy (Recall) lên tới **98.36%**. Đây là minh chứng cho việc tối ưu hóa kiến trúc mạng nơ-ron hiệu quả để hoạt động ổn định trên các **thiết bị có nguồn tài nguyên cực kỳ hạn chế** (Edge AI).
