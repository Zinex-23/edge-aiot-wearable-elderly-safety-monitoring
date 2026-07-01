# ☁️ Unit Test: Cloud Platform & Database Services

> **ID:** UT_CLOUD_DB | **Component:** ThingsBoard & MongoDB | **Role:** Backend Services

## 1. Description
Kiểm tra các thành phần logic trên Cloud để đảm bảo xử lý dữ liệu và lưu trữ đúng quy trình.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: Rule Engine** | Gửi một gói tin "Fall Detected" giả lập lên ThingsBoard | Rule Engine kích hoạt thông báo (Alarm) thành công | [ ] |
| **SC_02: DB Write** | Ghi một bản ghi Telemetry vào MongoDB | Bản ghi xuất hiện trong Collection với đúng nhãn thời gian (Timestamp) | [ ] |
| **SC_03: Auth Service** | Thực hiện đăng nhập với tài khoản hợp lệ | Hệ thống trả về JWT Token và quyền truy cập đúng | [ ] |
| **SC_04: Retention** | Thiết lập chính sách xóa dữ liệu cũ (ví dụ sau 30 ngày) | Các dữ liệu cũ hơn 30 ngày tự động được dọn dẹp | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Kiểm tra độ trễ (Latency) của Rule Engine khi xử lý các tín hiệu cảnh báo.
