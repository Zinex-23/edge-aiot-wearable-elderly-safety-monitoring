# 📱 Unit Test: Android App Modules

> **ID:** UT_APP_LOGIC | **Component:** Android Application | **Language:** Kotlin

## 1. Description
Kiểm tra các thành phần phần mềm của ứng dụng Android một cách độc lập để đảm bảo logic xử lý đúng.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: UI Navigation** | Chuyển đổi giữa các màn hình Home -> History -> Settings | Giao diện phản hồi mượt mà, không bị crash ứng dụng | [ ] |
| **SC_02: SQLite CRUD** | Lưu một thông báo té ngã vào cơ sở dữ liệu SQLite nội bộ | Dữ liệu được lưu và truy vấn lại đúng 100% | [ ] |
| **SC_03: Permissions** | Yêu cầu quyền CALL_PHONE và BLUETOOTH_CONNECT | Hệ thống hiển thị hộp thoại xin quyền và nhận được quyền | [ ] |
| **SC_04: Data Parsing** | Truyền một chuỗi byte giả lập (Simulated Packet) vào hàm xử lý | Hàm trả về đúng giá trị nhịp tim và SpO2 (Decimal) | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Kiểm tra khả năng tương thích trên các phiên bản Android khác nhau (API 29-34).
