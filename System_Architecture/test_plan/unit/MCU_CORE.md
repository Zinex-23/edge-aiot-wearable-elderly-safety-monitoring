# ⚙️ Unit Test: MCU Core & Low-level Drivers

> **ID:** UT_MCU_CORE | **Component:** ESP32-S3 | **Environment:** ESP-IDF / Arduino

## 1. Description
Kiểm tra các chức năng lõi của vi điều khiển ESP32-S3 để đảm bảo phần cứng nền tảng hoạt động ổn định.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: CPU Clock** | Đọc bit cấu hình CPU Clock | Trả về tần số tối đa 240 MHz | [ ] |
| **SC_02: Deep Sleep** | Chuyển sang chế độ Deep Sleep trong 10s | Thiết bị tiêu thụ dòng < 100uA và tự thức dậy | [ ] |
| **SC_03: GPIO Output** | Điều khiển LED trạng thái/Còi báo | Linh kiện ngoại vi phản hồi đúng (Bật/Tắt) | [ ] |
| **SC_04: NVS Storage** | Ghi và đọc một tham số từ bộ nhớ NVS Flash | Giá trị không đổi sau khi khởi động lại (Reboot) | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Đảm bảo bộ cấp nguồn ổn định khi CPU hoạt động ở mức 240MHz.
