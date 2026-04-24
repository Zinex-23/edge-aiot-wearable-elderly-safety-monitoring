# 📡 Integrated Test: BLE Connectivity & Data Sync

> **ID:** IT_BLE_SYNC | **Modules:** ESP32-S3 BLE + Android App BLE | **Protocol:** BLE 5.0

## 1. Description
Kiểm tra sự tương tác và truyền dẫn dữ liệu không dây giữa thiết bị đeo và ứng dụng điện thoại.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: Pairing** | Thực hiện quét và kết nối từ App Android | App tìm thấy tên thiết bị "AIFD Wearable" và kết nối thành công | [ ] |
| **SC_02: MTU Negotiation**| Thực hiện trao đổi MTU sau khi kết nối | MTU đạt tối thiểu 247 bytes để truyền gói dữ liệu lớn | [ ] |
| **SC_03: Data Stream** | Gửi liên tục dữ liệu HR/SpO2 mỗi 5s và Motion data | App nhận và cập nhật biểu đồ thời gian thực không bị trễ/mất gói | [ ] |
| **SC_04: Reconnect** | Tắt Bluetooth trên điện thoại 10s rồi bật lại | Thiết bị tự động kết nối lại khi trong tầm phủ sóng | [ ] |
| **SC_05: Range Test** | Di chuyển thiết bị ra xa khỏi smartphone 5-10m | Kết nối duy trì ổn định không bị drop quá 50% RSSI | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Kiểm tra quyền truy cập vị trí (Location) trên Android 12+ để đảm bảo BLE scan hoạt động.
