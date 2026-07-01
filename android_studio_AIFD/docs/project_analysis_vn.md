# Phân tích Chuyên sâu Dự án AIFD (Android)

Tài liệu này trình bày các phân tích kỹ thuật về kiến trúc và cơ chế hoạt động của ứng dụng Android trong hệ thống **Edge-AIoT Wearable Elderly Safety Monitoring**.

## 🏗️ Kiến trúc Hệ thống

Dự án áp dụng mô hình **Kiến trúc Edge-AI phi tập trung**, nơi việc xử lý nặng nhất (suy luận AI) được thực hiện ngay tại thiết bị đeo để giảm thiểu độ trễ và bảo vệ quyền riêng tư.

### 1. Thiết bị đầu cuối (ESP32-S3)
*   **Vai trò**: Thu thập dữ liệu cảm biến và phát hiện té ngã.
*   **Mô hình AI**: Chạy mô hình "TinyCNN" trực tiếp trên chip ESP32-S3.
*   **Kết nối**: Đóng vai trò là BLE GATT Server.

### 2. Ứng dụng Android
*   **BLE Manager (`BleManager.kt`)**: Quản lý kết nối GATT và đăng ký nhận thông báo từ các characteristic (Trạng thái, Gia tốc, Con quay hồi chuyển).
*   **Foreground Service (`BleForegroundService.kt`)**: Thành phần "Người bảo vệ". Chạy liên tục 24/7 dưới dạng foreground service để duy trì liên kết BLE và kích hoạt các giao thức khẩn cấp ngay cả khi ứng dụng bị đóng.
*   **Giao diện (Jetpack Compose)**: Cung cấp chỉ số thời gian thực và cho phép cấu hình thông tin liên hệ khẩn cấp.

---

## 📡 Giao thức BLE & Luồng Dữ liệu

Ứng dụng giao tiếp với ESP32 thông qua một service tùy chỉnh (**4fafc201-1fb5-459e-8fcc-c5c9c331914b**).

| Characteristic | UUID | Định dạng dữ liệu | Mô tả |
| :--- | :--- | :--- | :--- |
| **Status** | `beb5483e...` | `prediction,code,fall_prob,non_fall_prob` | Kết quả dự đoán từ CNN trên ESP32. |
| **Accel** | `7b809f11...` | `ax,ay,az` | Dữ liệu gia tốc thô (Accelerometer). |
| **Gyro** | `f9b2c417...` | `gx,gy,gz` | Dữ liệu vận tốc góc thô (Gyroscope). |

### 🔄 Luồng suy luận (Inference Flow):
1.  ESP32 liên tục giám sát các mẫu chuyển động từ cảm biến IMU.
2.  Mô hình TinyCNN phân loại chuyển động đó có phải là ngã hay không.
3.  Nếu kết quả là té ngã với xác suất $> 0.4$, ESP32 sẽ gửi thông báo (notify) đến characteristic **Status**.
4.  `BleForegroundService` trên Android nhận được thông báo và kích hoạt xử lý.

---

## 🚨 Giao thức Xử lý Khẩn cấp

Khi nhận được gói tin `prediction == "fall"` và `fallProb >= 0.4`:

1.  **Đánh thức hệ thống**: Service yêu cầu `WakeLock` để tự động bật sáng màn hình điện thoại.
2.  **Cảnh báo giao diện**: Gửi broadcast `ACTION_FALL_DETECTED` để yêu cầu UI chuyển hướng ngay sang màn hình `FallAlertScreen`.
3.  **Đếm ngược**: Bắt đầu **đếm ngược 15 giây**.
4.  **Tự động gọi điện**: Nếu người dùng không nhấn "Tôi an toàn" (hủy) trong thời gian đếm ngược, ứng dụng sẽ tự động thực hiện cuộc gọi đến số điện thoại người thân đã đăng ký (mặc định: `0702341350`).

---

## 🛠️ Các Thành phần Cốt lõi

### `BleManager.kt`
-   Sử dụng chiến lược **tự động kết nối** (auto-connect) với các thiết bị ESP32 đã được ghép đôi (pairing) trong cài đặt hệ thống.
-   Xử lý đàm phán MTU (yêu cầu 512 bytes) để truyền tải nhiều dữ liệu hơn và đăng ký tuần tự (sequential) các GATT descriptor.

### `BleForegroundService.kt`
-   Đảm bảo kết nối không bị hệ điều hành Android ngắt khi ứng dụng chạy nền.
-   Sử dụng `START_STICKY` để tự động khởi động lại nếu dịch vụ bị hệ thống giết để giải phóng bộ nhớ.

### `AppNavigation.kt`
-   Trung tâm điều phối luồng màn hình.
-   Sử dụng `BroadcastReceiver` để nhận tín hiệu cảnh báo từ background service và hiển thị màn hình khẩn cấp kịp thời.

---

## 💡 Nhận xét và Đánh giá

*   **Độ tin cậy cao**: Việc sử dụng BLE Bonded device (thiết bị đã ghép đôi) giúp kết nối ổn định hơn nhiều so với việc quét BLE liên tục.
*   **Tối ưu hóa Pin**: Chỉ sử dụng `WakeLock` khi thực sự có cảnh báo khẩn cấp để tiết kiệm năng lượng.
*   **Trải nghiệm mượt mà**: Giao diện được xây dựng bằng công nghệ hiện đại (Jetpack Compose, Material3) giúp phản hồi nhanh và trông rất chuyên nghiệp.
