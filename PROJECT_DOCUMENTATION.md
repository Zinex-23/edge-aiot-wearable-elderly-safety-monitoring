# 🛡️ Hệ Thống Giám Sát An Toàn Người Già (CaraFall) - Edge AI & IoT

Chào mừng bạn đến với tài liệu tổng quan dự án **CaraFall**. Đây là một giải pháp giám sát sức khỏe và cảnh báo té ngã thông minh dành cho người cao tuổi, được thiết kế với triết lý **"Offline-First"** để đảm bảo an toàn tuyệt đối ngay cả khi không có kết nối Internet.

---

## 🌟 Tổng Quan Dự Án (Project Overview)

Dự án tập trung vào việc giải quyết vấn đề an toàn cho người già thông qua một thiết bị đeo (wearable) có khả năng:
1.  **Phát hiện té ngã (Fall Detection)** sử dụng mô hình trí tuệ nhân tạo (Edge AI) chạy trực tiếp trên thiết bị.
2.  **Theo dõi chỉ số sinh tồn**: Nhịp tim (HR) và nồng độ Oxy trong máu (SpO2).
3.  **Cảnh báo khẩn cấp**: Tự động thực hiện cuộc gọi và gửi thông báo đến người thân qua Bluetooth Low Energy (BLE) mà không cần WiFi.
4.  **Lưu trữ đám mây**: Đồng bộ dữ liệu lịch sử lên ThingsBoard để theo dõi xu hướng sức khỏe lâu dài.

---

## 🏗️ Kiến Trúc Hệ Thống (System Architecture)

Hệ thống được chia thành 3 tầng chính:

### 1. Edge Layer (Thiết bị đeo)
- **Phần cứng**: Sử dụng vi điều khiển **ESP32-S3** mạnh mẽ.
- **Cảm biến**: 
  - Cảm biến IMU (Gia tốc & Con quay hồi chuyển) để thu thập dữ liệu chuyển động.
  - Cảm biến **MAX30102** để đo HR và SpO2.
- **Xử lý AI**: Mô hình **TinyCNN** được nén và chạy trực tiếp trên MCU để phát hiện té ngã theo thời gian thực với độ trễ cực thấp (< 2s).

### 2. Local Gateway (Ứng dụng Android)
- **Kết nối**: Liên lạc với thiết bị đeo qua **BLE 5.0**.
- **Chức năng chính**:
  - Hiển thị dữ liệu sức khỏe thời gian thực.
  - **Cảnh báo ưu tiên**: Ngay khi nhận tín hiệu té ngã, ứng dụng sẽ thực hiện cuộc gọi khẩn cấp (Direct Call) đến số điện thoại đã cài đặt.
  - **Cache dữ liệu**: Lưu trữ tạm thời khi điện thoại ngoại tuyến.

### 3. Cloud Layer (Quản lý & Lịch sử)
- **Platform**: **ThingsBoard** được sử dụng làm Dashboard giám sát trung tâm.
- **Database**: **MongoDB** lưu trữ lịch sử dữ liệu lâu dài.
- **Web Dashboard**: Cho phép người thân/bác sĩ xem lại lịch sử sức khỏe từ xa qua trình duyệt.

---

## 🧠 Mô Hình Edge AI (TinyCNN)

Dự án sử dụng một mô hình mạng nơ-ron tích chập (CNN) được tối ưu hóa đặc biệt cho thiết bị nhúng.

| Thông số | Giá trị |
| :--- | :--- |
| **Kiến trúc** | TinyCNN (Conv1D + Global Average Pooling) |
| **Tổng tham số** | ~2,974 params |
| **Kích thước mô hình** | ~10.7 KB (TFLite Quantized) |
| **Độ nhạy (Recall)** | **98.36%** |
| **Độ chính xác (Accuracy)** | ≥ 95% |

---

## 📚 Dữ Liệu & Huấn Luyện (Data & Training)

- **Dataset**: Sử dụng bộ dữ liệu **MobiFall Dataset v2.0**, bao gồm nhiều kịch bản té ngã và hoạt động thường ngày (ADL).
- **Tiền xử lý**: Dữ liệu IMU được chuẩn hóa và cắt thành các cửa sổ thời gian (Sliding Window) để đưa vào mô hình.
- **Huấn luyện**: 
  - Tối ưu hóa trên tập dữ liệu cân bằng.
  - Sử dụng các kỹ thuật như **Quantization-Aware Training** để đảm bảo mô hình hoạt động chính xác sau khi chuyển đổi sang định dạng TFLite cho MCU.

---

## 📁 Cấu Trúc Thư Mục (Project Structure)

```text
.
├── AI/                     # Tài liệu và scripts liên quan đến AI/Machine Learning
├── android_studio_AIFD/    # Mã nguồn ứng dụng Android (Kotlin & Jetpack Compose)
├── S3_Combine/             # Mã nguồn firmware chính cho ESP32-S3
├── S3_BLE_TEST_BUTTON/     # Các module test tính năng BLE và Button
├── System_Architecture/    # Sơ đồ và tài liệu phân tích hệ thống
├── thingsboard_app/        # Cấu hình và mã nguồn cho Dashboard ThingsBoard
├── train_model_FallDetection/ # Scripts huấn luyện mô hình phát hiện té ngã
├── REPORT/                 # Các báo cáo kỹ thuật (PDF/DOCX)
└── README.md               # Hướng dẫn nhanh
```

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

- **Firmware**: C++, ESP-IDF / Arduino framework, TensorFlow Lite for Microcontrollers.
- **Mobile**: Kotlin, Jetpack Compose, Android BLE API.
- **Backend/IoT**: ThingsBoard, MongoDB, Node.js.
- **Machine Learning**: Python, TensorFlow/Keras, Scikit-learn.

---

## 🚀 Hướng Dẫn Cài Đặt (Quick Start)

1.  **Firmware**: Mở thư mục `S3_Combine` bằng PlatformIO hoặc Arduino IDE, nạp code vào ESP32-S3.
2.  **Android App**: Mở `android_studio_AIFD` bằng Android Studio và cài đặt lên điện thoại.
3.  **Kết nối**: Bật Bluetooth trên điện thoại, mở app và quét thiết bị "CaraFall".

---

## 📌 Triết Lý Thiết Kế: "Cảnh báo là tức thời (Offline), Dữ liệu là lâu dài (Online)"
Đây là điểm mạnh lớn nhất của dự án, loại bỏ hoàn toàn rủi ro mất kết nối mạng - yếu tố sống còn của các hệ thống an toàn y tế.

---
*Tài liệu này được tự động cập nhật để phản ánh trạng thái mới nhất của dự án.*
