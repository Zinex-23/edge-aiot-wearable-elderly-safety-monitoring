# 🦷 Unit Test: BLE Connection Stack (Edge Side)

> **ID:** UT_BLE_STACK | **Component:** ESP32-S3 BLE Service | **Mode:** Peripheral

## 1. Description
Kiểm tra các thành phần của Blueooth Low Energy trên thiết bị để đảm bảo khả năng quảng bá (Advertising) và quản lý dịch vụ (Services).

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: Advertising** | Khởi chạy chế độ Advertising của ESP32 | Các thiết bị khác tìm thấy tên "AIFD Wearable" | [ ] |
| **SC_02: Service Init** | Khởi tạo Service UUID và Characteristic UUID | Các UUID xuất hiện đầy đủ trong bảng cấu hình GATT | [ ] |
| **SC_03: Data Notification**| Gửi dữ liệu biến động qua cơ chế Notify | Client (App) nhận được bản tin mà không cần thực hiện Read | [ ] |
| **SC_04: Passkey** | Thực hiện ghép nối yêu cầu Passkey (nếu có) | Hệ thống xác thực thành công mã pin đúng | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Kiểm tra TX Power để tối ưu khoảng cách kết nối và tiêu thụ điện.
