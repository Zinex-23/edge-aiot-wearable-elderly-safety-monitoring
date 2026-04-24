# 🛠️ Unit Test: BMI160 Sensor Module

> **ID:** UT_BMI160 | **Module:** Hardware Abstraction Layer (HAL) | **Hardware:** ESP32-S3 + BMI160

## 1. Description
Kiểm tra khả năng giao tiếp và tính chính xác của dữ liệu thô (raw data) từ cảm biến gia tốc và con quay hồi chuyển BMI160.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: I2C Comm** | Gọi hàm `BMI160.begin()` qua giao diện I2C | Trả về `SUCCESS` và nhận diện đúng Chip ID | [ ] |
| **SC_02: Range Check** | Đặt thiết bị nằm yên trên mặt phẳng | Trục Z đạt ~1g (±0.05g), trục X/Y ~0g | [ ] |
| **SC_03: Sample Rate** | Đo thời gian giữa 100 lần đọc dữ liệu | Tổng thời gian ~2000ms (tương ứng 50Hz) | [ ] |
| **SC_04: Self-test** | Kích hoạt chế độ Built-in Self-test của BMI160 | Cảm biến trả về phản hồi "Passed" | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Đảm bảo dây bus I2C không quá dài để tránh nhiễu tín hiệu.
