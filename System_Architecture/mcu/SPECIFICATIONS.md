# ⚡ MCU & Connectivity Specifications

Chi tiết phần cứng điều khiển trung tâm và giao thức kết nối không dây.

## 1. Vi điều khiển (ESP32-S3)

| Đặc tính | Thông số | Ghi chú |
| :--- | :--- | :--- |
| **MCU** | **ESP32-S3 Mini** | Lựa chọn tối ưu cho thiết bị đeo |
| **CPU** | Xtensa® Dual-core 240 MHz | Hỗ trợ tập lệnh AI tăng tốc |
| **Xung nhịp** | 240 MHz | Đảm bảo tính thời gian thực |
| **Dòng hoạt động** | **~100–120 mA (WiFi)** | Cần tối ưu để đạt mục tiêu > 6 ngày |

## 2. Bluetooth Low Energy (BLE 5.0)

| Đặc tính | Đề xuất (Specification) | Vai trò |
| :--- | :--- | :--- |
| **Kỹ thuật** | BLE 5.0 (Long Range/High Throughput) | Kết nối không mạng đến Smartphone |
| **MTU Size** | 247 Bytes | Truyền dữ liệu IMU+Vital nén trong 1 gói |
| **Conn. Interval** | 20ms - 45ms | Đảm bảo truyền dữ liệu vận động liên tục |
| **Advertising** | 100ms | Đảm bảo App Android tìm thấy thiết bị nhanh |
| **Security** | LE Secure Connections | Bảo mật dữ liệu sức khỏe người dùng |

## 3. Quản lý Kết nối

- **Fallback Wi-Fi**: Tự động bật Wi-Fi để đồng bộ Cloud khi có tín hiệu.
- **Offline Buffer**: Lưu trữ tới 100 sự kiện khẩn cấp nếu mất kết nối BLE tạm thời.
