# 📱 Phân Tích Kiến Trúc Source Code AIFD (Android)

Tài liệu này tập trung vào kiến trúc phần mềm và cách tổ chức mã nguồn của ứng dụng Android AIFD.

---

## 1. Mẫu Thiết Kế (Architecture Pattern)

Ứng dụng tuân thủ chặt chẽ mô hình **MVVM (Model-View-ViewModel)** kết hợp với **Jetpack Compose**:

- **Model (`com.aifd.data`)**: Định nghĩa các cấu trúc dữ liệu cốt lõi như `HealthData`, `FallEvent`, `DeviceInfo`.
- **View (`com.aifd.ui`)**: Sử dụng **Jetpack Compose** hoàn toàn. Giao diện được chia nhỏ thành các `Components` và các `Screens` độc lập, giúp dễ dàng bảo trì và tái sử dụng.
- **ViewModel (`com.aifd.viewmodel`)**: Đóng vai trò là "bộ não" của từng màn hình, quản lý trạng thái (`StateFlow`) và xử lý logic nghiệp vụ.

---

## 2. Các Thành Phần Cốt Lõi

### 🧭 Hệ Thống Điều Hướng (Navigation)
File [AppNavigation.kt](file:///home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring/android_studio_AIFD/app/src/main/java/com/aifd/navigation/AppNavigation.kt) quản lý toàn bộ luồng chuyển cảnh:
- Kiểm tra trạng thái đăng nhập (`isLoggedIn`).
- Lọc quyền truy cập dựa trên vai trò người dùng (`UserRole`: Người đeo hoặc Người giám sát).
- Sử dụng `NavHost` để định nghĩa các route: Home, Monitoring, History, Settings, FallAlert.

### 🔵 Kết Nối Phần Cứng (BLE Management)
Lớp [BleManager.kt](file:///home/zinex/CAPSTONE/AI/edge-aiot-wearable-elderly-safety-monitoring/android_studio_AIFD/app/src/main/java/com/aifd/ble/BleManager.kt) là module trung gian tiếp nhận dữ liệu từ thiết bị đeo:
- Quản lý trạng thái kết nối (Scanning, Connected, Disconnected).
- Định nghĩa các luồng (`Flow`) để đẩy dữ liệu nhịp tim, SpO2 và bước chân lên UI.

### 📊 Quản Lý Trạng Thái (State Management)
Sử dụng `MutableStateFlow` và `update{}` để đảm bảo dữ liệu luôn nhất quán và UI tự động cập nhật khi có thay đổi (Reactive UI). Ví dụ: `MonitoringViewModel` tự động cập nhật biểu đồ sức khỏe mỗi giây.

---

## 3. Quản Lý Tài Nguyên & Cấu Hình

- **Theme**: Hệ thống Dark/Light mode linh hoạt trong thư mục `ui/theme`.
- **Localization**: Hỗ trợ đa ngôn ngữ (Tiếng Anh/Tiếng Việt) thông qua `ProvideAppStrings` giúp ứng dụng thân thiện với mọi đối tượng.
- **Persistence**: Sử dụng `SharedPreferences` trong `MainActivity` để lưu trữ cài đặt người dùng (theme, language, role) bền vững qua các lần khởi động.

---
> [!IMPORTANT]
> Tuy mã nguồn hiện tại đang sử dụng các dữ liệu mẫu (`MockDataProvider`), nhưng cấu trúc đã được thiết kế sẵn sàng để tích hợp dữ liệu thực tế từ cảm biến mà không cần thay đổi kiến trúc UI.
