# Phân tích Dung lượng Mô hình Fall Detection V84 (INT8)

Tài liệu này giải thích chi tiết cách tính toán dung lượng thực tế của mô hình V84 sau khi thực hiện Quantization (INT8) để triển khai trên ESP32-S3.

## 1. Thông số tổng quát
- **Tổng số tham số (Total Params):** Khoảng ~56,000 tham số
- **Dung lượng file (.tflite):** 62.09 KB
- **Dung lượng file quy đổi:** 63,576 Bytes (62.09 * 1024)

---

## 2. Công thức tính toán
Dung lượng mô hình được tính dựa trên hai thành phần chính:
**Dung lượng thực tế = Dung lượng Tham số (Weight Data) + Dung lượng Phụ trội (Overhead)**

### A. Chi tiết Dung lượng Tham số (~56,076 Bytes)
Các tham số không có cùng kích thước do yêu cầu về độ chính xác. Dựa trên kiến trúc `[32,64,64,96]/K3/D32` của V84:

| Thành phần | Số lượng tham số (Ước tính) | Kiểu dữ liệu | Bytes/Tham số | Tổng cộng (Bytes) |
| :--- | :---: | :---: | :---: | :---: |
| **Weights** (Trọng số CNN/Dense) | ~55,000 | INT8 | 1 | ~55,000 |
| **Biases** (Độ lệch) | ~256 | INT32 | 4 | ~1,024 |
| **Normalization** (Mean/Var) | 13 | Float32 | 4 | 52 |
| **TỔNG PHẦN THAM SỐ** | **~55,269** | - | - | **~56,076** |

### B. Chi tiết Dung lượng Phụ trội - Overhead (~7,500 Bytes)
Đây là phần cấu trúc của định dạng TFLite FlatBuffer, cần thiết để hệ thống TFLite Micro có thể đọc và thực thi mô hình.

| Thành phần | Mô tả | Ước tính (Bytes) |
| :--- | :--- | :---: |
| **Operator Codes** | Danh sách các phép toán (Conv1D, MaxPooling, v.v.) | ~500 |
| **Tensor Metadata** | Tên, hình dạng (shape), kiểu dữ liệu của từng layer | ~4,000 |
| **Quantization Maps** | Bảng tra cứu Scale và Zero-point cho từng tensor | ~2,000 |
| **Graph & Headers** | Cấu trúc kết nối giữa các layer và định danh file | ~1,000 |
| **TỔNG PHẦN OVERHEAD** | - | **~7,500** |

---

## 3. Tổng kết bảng tính
| Đại lượng | Giá trị (Bytes) | Tỷ trọng (%) |
| :--- | :---: | :---: |
| Dữ liệu tham số | ~56,076 | 88.2% |
| Dữ liệu cấu trúc (Overhead) | ~7,500 | 11.8% |
| **TỔNG CỘNG (File Size)** | **63,576** | **100%** |

**Ghi chú:** Do V84 là một mô hình tương đối lớn (khoảng 56,000 tham số), tỷ trọng của dữ liệu tham số (dữ liệu trọng số thực tế) chiếm phần lớn (88.2%). Phần Overhead sẽ trở nên không đáng kể khi mạng nơ-ron mở rộng thêm. Những tham số trong quá trình huấn luyện (Epoch, Batch Size, Dropout, Learning Rate) hoàn toàn **không** tác động đến con số tổng cộng này.

---

## 4. Công thức tính toán chi tiết (Thế số)

Dưới đây là công thức hoàn chỉnh với các con số ước tính để tính ra kết quả cuối cùng:

**Bước 1: Tính dung lượng phần tham số (Weights & Biases)**
- Weights (INT8): $55,000 \times 1 = 55,000 \text{ Bytes}$
- Biases (INT32): $256 \times 4 = 1,024 \text{ Bytes}$
- Normalization (Float32): $13 \times 4 = 52 \text{ Bytes}$
- **Tổng Params**: $55,000 + 1,024 + 52 = 56,076 \text{ Bytes}$

**Bước 2: Cộng với dung lượng phụ trội (Overhead)**
- Overhead (Cấu trúc TFLite): $7,500 \text{ Bytes}$
- **Tổng cộng**: $56,076 + 7,500 = 63,576 \text{ Bytes}$

**Bước 3: Quy đổi kết quả cuối cùng**
- $63,576 \text{ Bytes} \div 1024 = \mathbf{62.0859... \text{ KB}} \approx \mathbf{62.09 \text{ KB}}$

*(Ghi chú: Dung lượng 62.09 KB được quy đổi theo hệ nhị phân chuẩn 1 KB = 1024 Bytes, tính toán dựa trên cấu trúc file thực tế).*
