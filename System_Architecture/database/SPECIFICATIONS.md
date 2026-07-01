# ☁️ Database & Cloud Specifications

Chi tiết về hạ tầng lưu trữ và quản lý tập trung trên Đám mây.

## 1. Nền tảng Cloud (Flask REST API + MongoDB)

> **Lưu ý:** Hệ thống **KHÔNG dùng ThingsBoard**. Backend là **API REST tự xây bằng Python Flask** (deploy trên Render), giao tiếp HTTP/JSON với app Android và lưu trực tiếp vào **MongoDB Atlas**.

| Đặc tính | Giải pháp | Ghi chú |
| :--- | :--- | :--- |
| **Giao thức** | HTTP/JSON (REST) | App ↔ Flask qua OkHttp; không dùng MQTT |
| **API Server** | Python Flask (gunicorn), deploy Render | Endpoint `/api/vitals`, `/api/fall_event`, `/api/auth/*` |
| **Telemetry** | HR, SpO2, Fall events | Lưu vào collection `vitals`, `fall_events` |
| **Push notification** | Firebase Cloud Messaging (FCM) | Caregiver nhận cảnh báo từ xa |
| **Trạng thái** | Fall/Non-fall (qua `fall_events`) | Sự kiện ngã + xác nhận (acknowledge) |

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
