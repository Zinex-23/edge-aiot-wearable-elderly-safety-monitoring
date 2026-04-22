# Cấu trúc Màn hình và Luồng Điều hướng Ứng dụng AIFD

Tài liệu này mô tả chi tiết các màn hình trong ứng dụng, nội dung, ý nghĩa của chúng và cách người dùng di chuyển giữa các màn hình.

## 🗺️ Luồng Điều hướng Chính

Ứng dụng sử dụng **Jetpack Compose Navigation** với các luồng chính sau:

1.  **Luồng Xác thực**: `Login` ↔ `Register` → `Role Selection`.
2.  **Luồng Chính (Bottom Nav)**: `Home` ↔ `Monitoring` ↔ `History` ↔ `Settings`.
3.  **Luồng Khẩn cấp**: Tự động chuyển đến `Fall Alert` từ bất kỳ đâu khi phát hiện ngã.
4.  **Luồng Quản lý Thiết bị**: `Home/Settings` → `Device Pairing` → `Device Detail`.

---

## 📱 Chi tiết các Màn hình

### 1. Nhóm Đăng ký & Đăng nhập
*   **Màn hình Đăng nhập (LoginScreen)**:
    *   **Nội dung**: Ô nhập tên đăng nhập, mật khẩu.
    *   **Ý nghĩa**: Xác thực người dùng và bắt đầu phiên làm việc.
*   **Màn hình Đăng ký (RegisterScreen)**:
    *   **Nội dung**: Form nhập thông tin cá nhân (Tên, tuổi, số điện thoại người thân).
    *   **Ý nghĩa**: Khởi tạo hồ sơ người dùng, đặc biệt là lưu số điện thoại cứu hộ.

### 2. Màn hình Chọn Vai trò (RoleSelectionScreen)
*   **Nội dung**: Hai lựa chọn lớn: **Người đeo (Wearer)** và **Người chăm sóc (Caregiver)**.
*   **Ý nghĩa**: Quyết định quyền hạn và giao diện. Người đeo có quyền quản lý thiết bị BLE, người chăm sóc chỉ xem dữ liệu.

### 3. Trang chủ (HomeScreen) - Dashboard
*   **Nội dung**: 
    *   Biểu ngữ chào hỏi (Greeting).
    *   Trạng thái kết nối thiết bị (Connected/Disconnected).
    *   Các thẻ tóm tắt (StatCards): Nhịp tim, Oxy trong máu, Số bước chân.
    *   Nút gọi khẩn cấp (dành cho người đeo).
*   **Ý nghĩa**: Cung cấp cái nhìn tổng quát nhất về tình trạng sức khỏe và kết nối hiện tại.

### 4. Theo dõi Chi tiết (MonitoringScreen)
*   **Nội dung**: 
    *   Các tab: Nhịp tim (Heart Rate), Oxy máu (SpO2), Bước chân (Steps).
    *   Đồ thị đường (Line Chart) cho dữ liệu thời gian thực.
    *   Thông số: Trung bình, Thấp nhất, Cao nhất.
*   **Ý nghĩa**: Phân tích sâu hơn các chỉ số sức khỏe theo thời gian (Live, 1h, 24h).

### 5. Lịch sử Sự kiện (HistoryScreen)
*   **Nội dung**: Danh sách các sự kiện té ngã hoặc cảnh báo đã xảy ra kèm thời gian và trạng thái xử lý.
*   **Ý nghĩa**: Lưu trữ nhật ký an toàn để người thân hoặc bác sĩ có thể theo dõi lại.

### 6. Cài đặt (SettingsScreen)
*   **Nội dung**: 
    *   Thông tin tài khoản.
    *   Cài đặt ngôn ngữ (Tiếng Anh/Tiếng Việt).
    *   Chế độ giao diện (Sáng/Tối).
    *   Quản lý thiết bị BLE.
*   **Ý nghĩa**: Nơi tùy chỉnh ứng dụng và quản lý các kết nối phần cứng.

### 7. Cảnh báo Té ngã (FallAlertScreen) - Quan trọng nhất
*   **Nội dung**: 
    *   Thông báo đỏ rực: "Phát hiện té ngã!".
    *   Đồng hồ đếm ngược 15 giây.
    *   Hai nút lớn: **"Tôi an toàn"** (Hủy) và **"Gọi ngay"**.
*   **Ý nghĩa**: Giao diện can thiệp khẩn cấp. Nếu người dùng không phản hồi, ứng dụng sẽ thực hiện quyền ưu tiên cao nhất là gọi điện cứu hộ.

### 8. Ghép đôi Thiết bị (DevicePairingScreen)
*   **Nội dung**: Danh sách các thiết bị BLE "ESP32" đang ở gần.
*   **Ý nghĩa**: Thiết lập liên kết Bluetooth giữa điện thoại và thiết bị đeo.

---

## 📈 Ý nghĩa các Chỉ số Sức khỏe

*   **Nhịp tim (Heart Rate)**: Đơn vị bpm. Biểu thị trạng thái tim mạch.
    *   *Bình thường*: 60-100 bpm.
    *   *Bất thường*: Cảnh báo nếu quá cao hoặc quá thấp khi không vận động.
*   **Nồng độ Oxy (SpO2)**: Đơn vị %.
    *   *Bình thường*: 95-100%. Nếu dưới 92% là mức báo động cần chú ý y tế.
*   **Số bước chân (Steps)**: Theo dõi hoạt động thể chất hàng ngày.
    *   Mục tiêu mặc định: 10,000 bước.

---

## 🛠️ Quy tắc Di chuyển (Navigation Rules)

-   **Nút Back**: Luôn quay lại màn hình trước đó, trừ màn hình `FallAlert` (phải xử lý xong mới được thoát).
-   **Bottom Navigation**: Chuyển đổi nhanh giữa 4 khu vực chính (Home, Health, History, Settings).
-   **Tự động chuyển trang**: Xảy ra khi:
    -   Đăng nhập thành công → Sang trang chính.
    -   Thiết bị đeo báo ngã → Chuyển ngay sang trang Cảnh báo (bất kể đang ở đâu).
