# 🧠 Unit Test: TinyML Inference Engine

> **ID:** UT_AI_MODEL | **Module:** Edge AI Logic | **Runtime:** TFLite Micro on ESP32-S3

## 1. Description
Kiểm tra khả năng nạp mô hình, quản lý bộ nhớ đệm (Circular Buffer) và thời gian xử lý cửa sổ dữ liệu.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: Model Loading**| Khởi tạo `TFLiteMicroInterpreter` với mảng byte mô hình | Interpreter cấp phát thành công bộ nhớ và không lỗi | [ ] |
| **SC_02: Buffer Flow** | Đẩy 120 mẫu dữ liệu giả lập vào Circular Buffer | Buffer giữ lại đúng 100 mẫu mới nhất (sliding window) | [ ] |
| **SC_03: Latency Check** | Đo thời gian hàm `interpreter.Invoke()` cho 1 mẫu | Thời gian xử lý < 50ms (để đảm bảo thời gian thực) | [ ] |
| **SC_04: Sigmoid Limit** | Thực hiện inference với dữ liệu cực đại/cực tiểu | Đầu ra nằm trong khoảng [0.0, 1.0] | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Kiểm tra tensor arena size để tránh tràn stack memory trên ESP32.
