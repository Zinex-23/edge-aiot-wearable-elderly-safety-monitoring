# ☁️ Integrated Test: App to Cloud & Data Retrieval

> **ID:** IT_CLOUD_LOOP | **Modules:** Android App + ThingsBoard + MongoDB | **Protocol:** MQTT / REST API

## 1. Description
Kiểm tra luồng dữ liệu hai chiều: Từ ứng dụng gửi lên Đám mây (Đồng bộ) và từ Đám mây truy vấn về ứng dụng (Xem lịch sử).

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: App Upload** | App Android gửi dữ liệu Telemetry (HR/SpO2) qua MQTT | Dashdoard ThingsBoard cập nhật giá trị đúng theo thời gian thực | [ ] |
| **SC_02: Cloud Persistence**| Kiểm tra dữ liệu trong MongoDB sau khi gửi từ App | Dữ liệu được lưu trữ bền vững với đúng cấu hình JSON | [ ] |
| **SC_03: History Query** | Mở màn hình "History" trên App và chọn khoảng thời gian | App gọi REST API thành công và hiển thị đúng biểu đồ quá khứ | [ ] |
| **SC_04: Sync Strategy** | Tắt Internet -> Phát hiện té ngã -> Bật lại Internet | Sự kiện té ngã được lưu trong SQLite và tự động đẩy lên Cloud khi online | [ ] |
| **SC_05: Multi-role View** | Caregiver đăng nhập từ thiết bị khác | Thấy được đúng dữ liệu của Wearer và nhận thông báo cảnh báo | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Đảm bảo Token của thiết bị trên ThingsBoard là chính xác và không bị hết hạn (Expired).
