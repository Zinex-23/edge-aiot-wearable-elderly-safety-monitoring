# Phân tích Dung lượng Mô hình Fall Detection (INT8)

Tài liệu này giải thích chi tiết cách tính toán dung lượng thực tế của mô hình sau khi thực hiện Quantization (INT8) để triển khai trên ESP32-S3.

## 1. Thông số tổng quát
- **Tổng số tham số (Total Params):** 2,974 tham số
- **Dung lượng file (.tflite):** 10.71 KB
- **Dung lượng file quy đổi:** 10,967 Bytes (10.71 * 1024)

---

## 2. Công thức tính toán
Dung lượng mô hình được tính dựa trên hai thành phần chính:
**Dung lượng thực tế = Dung lượng Tham số (Weight Data) + Dung lượng Phụ trội (Overhead)**

### A. Chi tiết Dung lượng Tham số (3,256 Bytes)
Các tham số không có cùng kích thước do yêu cầu về độ chính xác:

| Thành phần | Số lượng tham số | Kiểu dữ liệu | Bytes/Tham số | Tổng cộng (Bytes) |
| :--- | :---: | :---: | :---: | :---: |
| **Weights** (Trọng số CNN/Dense) | 2,880 | INT8 | 1 | 2,880 |
| **Biases** (Độ lệch) | 81 | INT32 | 4 | 324 |
| **Normalization** (Mean/Var) | 13 | Float32 | 4 | 52 |
| **TỔNG PHẦN THAM SỐ** | **2,974** | - | - | **3,256** |

### B. Chi tiết Dung lượng Phụ trội - Overhead (7,711 Bytes)
Đây là phần cấu trúc của định dạng TFLite FlatBuffer, cần thiết để hệ thống TFLite Micro có thể đọc và thực thi mô hình.

| Thành phần | Mô tả | Ước tính (Bytes) |
| :--- | :--- | :---: |
| **Operator Codes** | Danh sách các phép toán (Conv1D, MaxPooling, v.v.) | ~500 |
| **Tensor Metadata** | Tên, hình dạng (shape), kiểu dữ liệu của từng layer | ~4,000 |
| **Quantization Maps** | Bảng tra cứu Scale và Zero-point cho từng tensor | ~2,000 |
| **Graph & Headers** | Cấu trúc kết nối giữa các layer và định danh file | ~1,211 |
| **TỔNG PHẦN OVERHEAD** | - | **7,711** |

---

## 3. Tổng kết bảng tính
| Đại lượng | Giá trị (Bytes) | Tỷ trọng (%) |
| :--- | :---: | :---: |
| Dữ liệu tham số | 3,256 | 29.7% |
| Dữ liệu cấu trúc (Overhead) | 7,711 | 70.3% |
| **TỔNG CỘNG (File Size)** | **10,967** | **100%** |

**Ghi chú:** Với các mô hình siêu nhỏ (Tiny models), phần Overhead luôn chiếm tỷ trọng cao. Khi mô hình mở rộng về số lượng tham số, tỷ trọng của Overhead sẽ giảm dần so với dữ liệu trọng số thực tế.
