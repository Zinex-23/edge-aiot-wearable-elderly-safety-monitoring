# 🛡️ CaraFall: Edge AI & IoT Wearable for Elderly Safety

**CaraFall** là một hệ thống giám sát an toàn và sức khỏe toàn diện dành cho người cao tuổi, kết hợp sức mạnh của **Edge AI** và **IoT**. Hệ thống được thiết kế với triết lý **"Offline-First"**, đảm bảo khả năng phát hiện té ngã và thực hiện cảnh báo khẩn cấp ngay lập tức mà không cần phụ thuộc vào kết nối Internet.

---

## 🌟 Triết lý thiết kế: "Cảnh báo là tức thời (Offline), Dữ liệu là lâu dài (Online)"
Điểm khác biệt lớn nhất của CaraFall so với các giải pháp khác là khả năng hoạt động độc lập trong các tình huống khẩn cấp. Việc phát hiện ngã và thực hiện cuộc gọi cứu hộ được thực hiện trực tiếp giữa thiết bị đeo và điện thoại qua Bluetooth (BLE), loại bỏ rủi ro từ việc mất kết nối WiFi hay sự cố đường truyền Cloud.

---

## 🚀 Tính năng nổi bật

- **Edge AI Fall Detection**: Sử dụng mô hình **TinyCNN** chạy trực tiếp trên ESP32-S3. Phát hiện chính xác các cú ngã trong thời gian thực với độ trễ cực thấp.
- **Vital Signs Monitoring**: Theo dõi liên tục nhịp tim (HR) và nồng độ Oxy trong máu (SpO2) qua cảm biến MAX30102.
- **Offline-First Alert System**: Tự động kích hoạt cuộc gọi khẩn cấp (Direct Call) qua ứng dụng Android khi phát hiện té ngã, ngay cả khi không có mạng.
- **Background Guardian**: Ứng dụng Android chạy dưới dạng Foreground Service, đảm bảo kết nối "bất tử" và sẵn sàng báo động ngay cả khi màn hình đang khóa.
- **IoT Integration**: Đồng bộ dữ liệu sức khỏe lên **ThingsBoard Dashboard** để theo dõi xu hướng dài hạn.

---

## 🏗️ Kiến trúc hệ thống (System Architecture)

### 1. Edge Layer (Thiết bị đeo)
- **MCU**: ESP32-S3 (Dual-core, tích hợp tăng tốc AI).
- **IMU**: BMI160 (Gia tốc + Con quay hồi chuyển) lấy mẫu ở 50Hz.
- **Health**: MAX30102 (Đo nhịp tim và SpO2).
- **AI Framework**: TensorFlow Lite for Microcontrollers.

### 2. Local Gateway (Android App)
- **Tech Stack**: Kotlin, Jetpack Compose.
- **Connectivity**: Bluetooth Low Energy (BLE 5.0).
- **Security**: Tự động bật màn hình, bỏ qua khóa màn hình để hiển thị đếm ngược 15 giây trước khi tự động gọi cứu hộ.

### 3. Cloud Layer (Quản lý & Lưu trữ)
- **IoT Platform**: ThingsBoard.
- **Database**: MongoDB.
- **Backend**: Node.js / TypeScript.

---

## 🧠 Hiệu suất mô hình AI (TinyCNN - Balanced V2)

Mô hình hiện đang được sử dụng chính thức là phiên bản **Balanced V2** (HR_IMU data), được tối ưu hóa để giảm thiểu tỷ lệ bỏ sót (Miss Rate) nhằm đảm bảo an toàn tối đa cho người già:

| Metric | Giá trị |
| :--- | :--- |
| **Recall (Độ nhạy)** | **98.36%** |
| **Accuracy (Độ chính xác)** | **90.80%** |
| **Precision** | **85.41%** |
| **F1-score** | **91.43%** |
| **False Alarm Rate (Báo động giả)** | **16.73%** |
| **Miss Rate (Tỷ lệ bỏ sót)** | **1.64%** |
| **Model Size** | **10.71 KB (Int8 Quantized)** |

---

## 📁 Cấu trúc thư mục chi tiết (Project Structure)

```text
.
├── S3_Combine/             # [Chính] Firmware tổng hợp (Sensors + AI + BLE) cho ESP32-S3
├── android_studio_AIFD/    # [Chính] Mã nguồn ứng dụng Android chính (Kotlin & Jetpack Compose)
├── AI/                     # Nghiên cứu ML, các phiên bản mô hình và thực nghiệm (V4-V14)
│   └── Edge_AI/            # Chứa mô hình Balanced V2 đang sử dụng chính thức
├── backend/                # API Server (Node.js/TypeScript) quản lý người dùng & thiết bị
├── thingsboard_app/        # Cấu hình và tích hợp Dashboard ThingsBoard IoT
├── data_processing/        # Các script xử lý, chuẩn hóa và gán nhãn dữ liệu IMU
├── train_model_FallDetection/ # Pipeline huấn luyện mô hình phát hiện té ngã
├── train_model_wrist_Fall_detection_Comprehensive/ # Huấn luyện mô hình đeo cổ tay chuyên sâu
├── System_Architecture/    # Sơ đồ khối, luồng dữ liệu và thiết kế hệ thống
├── S3_BLE/                 # Các module test tính năng Bluetooth Low Energy
├── S3_BLE_TEST_BUTTON/     # Test tích hợp nút bấm khẩn cấp và BLE
├── App/ & App_Kotlin/      # Các phiên bản/module ứng dụng mobile bổ trợ
├── esp32-S3-build/         # Môi trường build và các file thực thi cho ESP32
├── mongodb/                # Cấu hình và dữ liệu cơ sở dữ liệu MongoDB
├── simulation_fall/        # Các kịch bản và dữ liệu mô phỏng té ngã
├── REPORT/                 # Các báo cáo kỹ thuật định kỳ (PDF/DOCX)
├── paper/                  # Tài liệu nghiên cứu và bài báo khoa học liên quan
├── scratch/                # Các script nháp và thử nghiệm nhanh
├── PROJECT_DOCUMENTATION.md # Tài liệu hướng dẫn kỹ thuật chi tiết
├── QnA.md                  # Tổng hợp các câu hỏi thường gặp và giải đáp
├── README.md               # Tài liệu tổng quan (file này)
└── .gitignore              # Cấu hình bỏ qua các file không cần thiết khi git push
```

---

## 🛠️ Hướng dẫn cài đặt nhanh (Quick Start)

1.  **Firmware**:
    - Mở `S3_Combine` bằng VS Code (PlatformIO).
    - Build và nạp (Upload) vào ESP32-S3.
2.  **Android App**:
    - Mở `android_studio_AIFD` bằng Android Studio.
    - Cài đặt lên điện thoại Android (Yêu cầu quyền Bluetooth & Gọi điện).
3.  **Kết nối**:
    - Bật Bluetooth trên điện thoại.
    - Mở app, quét và ghép đôi với thiết bị "ESP32-fall-detection-BLE".

---

## 📄 Giấy phép & Bản quyền
© 2026 CaraFall Project Team - Edge AI & IoT for Social Good.
