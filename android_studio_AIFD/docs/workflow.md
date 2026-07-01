# 🔄 Quy Trình Vận Hành Ứng Dụng (Software Workflow)

Tài liệu này mô tả chi tiết các bước xử lý nội bộ của mã nguồn ứng dụng Android AIFD.

---

## 1. Khởi Chạy & Cấu Hình (Launch Flow)

1. **MainActivity**: Đọc các cài đặt đã lưu (`theme`, `language`, `role`) từ bộ nhớ.
2. **Preference Provider**: Thiết lập ngôn ngữ và giao diện (Dark/Light) cho toàn bộ cây thư mục UI.
3. **Session Check**:
   - Nếu chưa đăng nhập -> Chuyển hướng tới `LoginScreen`.
   - Nếu chưa chọn vai trò -> Chuyển hướng tới `RoleSelectionScreen`.

---

## 2. Luồng Điều Hướng Chính (Main Navigation)

Sau khi khởi chạy thành công, `AppNavigation` sẽ thiết lập một `Scaffold` chứa:
- **Top Bar**: Tiêu đề động theo từng màn hình.
- **Bottom Bar**: Cho phép chuyển đổi nhanh giữa các module:
  - **Home**: Tổng quan sức khỏe và cảnh báo.
  - **Monitoring**: Biểu đồ nhịp tim/SpO2 trực tiếp.
  - **History**: Nhật ký các lần té ngã.
  - **Settings**: Quản lý cá nhân và thiết bị.

---

## 3. Quy Trình Kết Nối Phần Cứng (BLE Workflow)

Đây là luồng quan trọng nhất để ứng dụng "giao tiếp" được với thiết bị đeo:
1. **Scanning**: `DeviceViewModel` yêu cầu `BleManager` quét các thiết bị xung quanh.
2. **Connecting**: Người dùng chọn thiết bị -> `BleManager` thực hiện kết nối GATT.
3. **Observing**: Sau khi kết nối, ứng dụng "lắng nghe" dữ liệu thông qua các `SharedFlow/StateFlow`.
4. **Processing**: Dữ liệu thô từ BLE được parse thành đối tượng `SensorData` để UI hiển thị.

---

## 4. Xử Lý Cảnh Báo Té Ngã (Alert Handling)

Khi phần cứng (ESP32) phát hiện té ngã, luồng xử lý trong mã nguồn như sau:
1. **Trigger**: `AlertViewModel` nhận tín hiệu ngắt từ BLE hoặc mô phỏng.
2. **Notification**: Ứng dụng tự động chuyển hướng người dùng tới màn hình `FallAlertScreen` (màn hình có ưu tiên cao nhất).
3. **Action**: 
   - Nếu người dùng nhấn "I'm Safe" -> Reset trạng thái alert.
   - Nếu người dùng nhấn "Call for Help" -> Kích hoạt cuộc gọi khẩn cấp (Emergency Call).
4. **Persistence**: Thông tin vụ việc được lưu lại vào danh sách `FallEvent` để xem lại trong trang Lịch sử.

---
> [!TIP]
> Toàn bộ logic được thiết kế theo hướng **Event-Driven**, giúp ứng dụng phản ứng tức thì với các sự cố bất ngờ của người lớn tuổi.
