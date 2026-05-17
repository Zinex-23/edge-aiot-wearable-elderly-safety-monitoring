# S3_BLE — Document Index

Tài liệu workflow & tính năng đã code trong folder `S3_BLE`. Mỗi file được đánh số theo thứ tự thời gian để dễ truy lại.

| #  | Tài liệu                                                                          | Ngày        | Tóm tắt                                                                 |
| -- | --------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------- |
| 01 | [LED + Button + Buzzer State Machine](01_led_button_buzzer_state_machine.md)      | 2026-05-15  | State machine 5 trạng thái với debouncing nút nhấn, buzzer 2300 Hz.     |
| 02 | [Bảng nối chân ngoại vi ↔ MCU](02_pin_mapping.md)                                 | 2026-05-15  | Pin mapping ESP32-S3 ↔ 3 LED + buzzer + nút nhấn + BMI160 I2C.          |
| 03 | [BMI160 + AI Fall Detection](03_bmi160_fall_detection.md)                         | 2026-05-16  | 5 lớp lọc: candidate, model V50, impact, stillness, duration 5s.        |
| 04 | [Lịch sử thí nghiệm](04_experiment_history.md)                                    | 2026-05-16  | 10 thí nghiệm điều chỉnh tham số, bài học rút ra, tham số hiện tại.    |

---

## Quy ước

- File code chính: [`src/main.cpp`](../src/main.cpp)
- Cấu hình build: [`platformio.ini`](../platformio.ini)
- Khi thêm tính năng mới → tạo doc mới `NN_ten-tinh-nang.md` và thêm dòng vào bảng phía trên.
