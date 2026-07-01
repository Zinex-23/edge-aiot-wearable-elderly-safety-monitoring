# 🛡️ Edge & AI Specifications

Tài liệu này chi tiết các thông số kỹ thuật của lớp xử lý biên và mô hình trí tuệ nhân tạo.

## 1. Thông số Cảm biến (Sensors)

| Cảm biến | Loại | Thông số / Tần số | Mục đích |
| :--- | :--- | :--- | :--- |
| **BMI160** | IMU 6-Axis | ±16g, ±2000 dps / 50 Hz | Phát hiện va chạm và thay đổi tư thế |
| **MAX30102** | HR & SpO2 | 1 sample / 5s | Giám sát nhịp tim và nồng độ oxy |

## 2. Thông số Mô hình AI (TinyCNN)

| Chỉ số | Thông số kỹ thuật (Mục tiêu M1) | Ghi chú |
| :--- | :--- | :--- |
| **Độ chính xác té ngã** | **≥ 95%** | Mục tiêu tối thiểu trên tập test |
| **Sai số Nhịp tim (HR)**| **±2 BPM** | Theo benchmark kỹ thuật |
| **Sai số SpO2** | **±3%** | Đạt chuẩn giám sát sức khỏe |
| **Độ nhạy (Recall)** | 98.36% | Kết quả huấn luyện hiện tại |
| **Kích thước file .h** | ~10.7 KB | Tối ưu hóa cho ESP32-S3 Mini |

## 3. Logic Xử lý Biên

- **Cửa sổ trượt (Sliding Window)**: 100 mẫu (2 giây), dịch chuyển 100 mẫu — **KHÔNG có overlap** (`kInferenceStride = 100`; mỗi cửa sổ 2 s liền kề, suy luận 1 lần / 2 s).
- **Tiền xử lý**: Chuẩn hóa Z-score (Mean/Std) thích ứng ngay trên chip.
- **Thời gian suy luận**: < 20ms thực hiện trên ESP32-S3.
