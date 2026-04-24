# 🏆 Acceptance Test: Fall Detection & Emergency Call

> **ID:** AT_FALL_SOS | **User Role:** Wearer & Caregiver | **Environment:** Real-world usage

## 1. Description
Kiểm tra kịch bản quan trọng nhất của hệ thống: Phát hiện té ngã thật và thực hiện cuộc gọi khẩn cấp tự động.

## 2. Test Scenarios

| Scenario | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **SC_01: Sudden Fall** | Người đeo thực hiện cú ngã mô phỏng lên đệm (té ngửa/té sấp) | ESP32-S3 phát tín hiệu Fall Detected; App Android báo động đỏ | [ ] |
| **SC_02: Auto-Call** | Sau khi phát hiện ngã (SC_01) | Smartphone tự động thực hiện cuộc gọi SOS đến số Caregiver trong < 3s | [ ] |
| **SC_03: ADL Rejection** | Người đeo thực hiện các hành động: Ngồi xuống nhanh, đi bộ, vẫy tay | Mô hình AI KHÔNG báo động (không có False Positive) | [ ] |
| **SC_04: End-to-End Latency**| Đo tổng thời gian từ khi chạm đất đến khi điện thoại care reo | Tổng thời gian < 5 giây (Target M1: < 2s Processing) | [ ] |
| **SC_05: Cloud Sync** | Khi Smartphone có mạng, kiểm tra lịch sử trên Cloud | Sự kiện té ngã được ghi nhận đúng giờ, đúng vị trí trên Dashboard | [ ] |

## 3. Conclusion
*   **Result**: [Pending]
*   **Notes**: Thực hiện ít nhất 10 lần thử nghiệm cho SC_01 và SC_03 để tính toán tỷ lệ chính xác cuối cùng.
