# 📱 Android Application Specifications

Chi tiết tính năng và yêu cầu kỹ thuật của ứng dụng giám sát trên Smartphone.

## 1. Yêu cầu Hệ thống

| Đặc tính | Thông số | Ghi chú |
| :--- | :--- | :--- |
| **Nền tảng** | Android 10 (API 29) trở lên | Hỗ trợ quản lý quyền BLE/Calling mới |
| **Ngôn ngữ** | Kotlin | Đảm bảo hiệu năng và an toàn mã nguồn |
| **Quyền truy cập** | Bluetooth, Location, Call Phone | Cần thiết cho tính năng khẩn cấp |

## 2. Tính năng Cốt lõi (Critical Features)

| Feature | Description | Quantitative |
| :--- | :--- | :--- |
| **Vital signs display** | Show HR, SpO2 | Refresh rate ≥ 0.2 Hz |
| **Motion data** | Display accel, gyro | Sampling synced with device |
| **Status display** | FALL / NON-FALL | Update delay < 500 ms |
| **Visualization** | Charts / indicators | Smooth rendering (no lag) |

## 3. Giao diện (UI/UX)

- **Màn hình Login**: Đăng nhập/Đăng ký tài khoản người dùng/người thân.
- **Màn hình Home**: Hiển thị trạng thái kết nối, nhịp tim và SpO2 thời gian thực.
- **Màn hình Health History**: Xem lại biểu đồ sinh tồn và các sự kiện theo thời gian.
- **Màn hình Alerts**: Danh sách các cảnh báo té ngã đã xảy ra kèm vị trí.
- **Màn hình Profile**: Cài đặt thông tin cá nhân và số điện thoại gọi khẩn cấp.
- **Cảnh báo khẩn cấp (Alert Overlay)**: Hiển thị đè lên các ứng dụng khác khi có té ngã.

## 4. Hình ảnh thực tế (App Screenshots)

Dưới đây là giao diện thực tế của ứng dụng AIFD:

| Dashboard & Role | Health Monitoring |
| :---: | :---: |
| ![Home](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/home.png) | ![Health HR](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/health_hr.png) |
| *Hình 1: Màn hình Home & Vitals* | *Hình 2: Biểu đồ Nhịp tim (HR)* |

| History & Events | Settings & Profile |
| :---: | :---: |
| ![History](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/history.png) | ![Settings](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/settings.png) |
| *Hình 3: Lịch sử cảnh báo* | *Hình 4: Cài đặt hệ thống* |

| Login Screen | Role Selection |
| :---: | :---: |
| ![Login](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/login.png) | ![Role](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/app/results/images/role_selection.png) |
| *Hình 5: Đăng nhập* | *Hình 6: Lựa chọn vai trò* |
