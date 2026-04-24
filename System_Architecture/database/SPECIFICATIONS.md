# ☁️ Database & Cloud Specifications

Chi tiết về hạ tầng lưu trữ và quản lý tập trung trên Đám mây.

## 1. Nền tảng IoT (ThingsBoard)

| Đặc tính | Giải pháp | Ghi chú |
| :--- | :--- | :--- |
| **Giao thức** | MQTT (TCP/SSL) | Bảo mật và tiết kiệm băng thông |
| **Quản lý thiết bị** | Device Profiles / Assets | Phân cấp theo hộ gia đình/cá nhân |
| **Telemetry** | HR, SpO2, Accelerometer | Dữ liệu đo xa dùng để vẽ biểu đồ lịch sử |
| **Attributes** | Status (Fall/Non-fall) | Trạng thái tức thời của thiết bị |

## 2. Cơ sở dữ liệu (MongoDB)

| Đặc tính | Thông số | Mục đích |
| :--- | :--- | :--- |
| **Loại DB** | NoSQL (Document-based) | Linh hoạt trong việc lưu trữ JSON telemetry |
| **Lưu trữ lịch sử** | Không giới hạn (Retention Policy) | Phục vụ phân tích xu hướng lâu dài |
| **Data Integrity** | Write Acknowledgement | Đảm bảo dữ liệu sức khỏe không bị mất khi lưu |

## 3. Web Dashboard

- **Giao diện Admin**: Quản lý hàng trăm thiết bị cùng lúc.
- **Biểu đồ quá khứ (Historical Data)**: Cho phép chọn khoảng thời gian (ngày/tuần/tháng) để xem lại diễn biến nhịp tim và nồng độ oxy.
- **Báo cáo**: Xuất tệp PDF/Excel báo cáo tình trạng an toàn định kỳ cho người thân.
