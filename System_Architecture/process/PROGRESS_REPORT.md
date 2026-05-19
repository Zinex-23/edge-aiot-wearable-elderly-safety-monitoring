# 📈 Báo cáo Tiến độ theo Quy trình Kỹ thuật (Engineering Progress)

Tài liệu này theo dõi tiến độ dự án dựa trên mô hình **Engineering Design Process (EDP)**.

![Engineering Design Process](file:///home/dsoft1/CAPSTONE/Code/System_Architecture/process/engineering_design_process.png)
*Hình 1: Mô hình quy trình thiết kế kỹ thuật của dự án.*

---

## 📊 Bảng Đánh giá Tiến độ (Mapping & Status)

| Stage | Status | Chi tiết công việc đã hoàn thành |
| :--- | :---: | :--- |
| **Problem Identification** | ✅ Done | Xác định vấn đề té ngã và giải pháp an toàn thời gian thực. |
| **Research** | ✅ Done | Nghiên cứu cảm biến (BMI160/MAX30102) và mô hình TinyCNN. |
| **Requirements Specification**| ✅ Done | Hoàn thiện bộ Specs cho Edge, MCU, AI, BLE, App, Database. |
| **Concept Generation** | ✅ Done | Thiết kế kiến trúc Offline-First ưu tiên kết nối BLE. |
| **Design** | ✅ Done | Hoàn thiện thiết kế UI/UX (6 màn hình), sơ đồ khối hệ thống. |
| **Prototype and Construct** | 🚧 90% | App + firmware hoạt động thật trên thiết bị. Cloud backend deploy trên Render. |
| **System Integration** | ✅ 95% | **End-to-end hoàn chỉnh**: ESP32 → BLE → Android → Render → MongoDB Atlas. Auth, vitals upload, history fetch đều hoạt động. |
| **System Test** | 🚧 65% | Test thực tế trên Samsung Galaxy M20 (Android 10). 8 bug fix trong ngày 2026-05-20. |
| **Delivery and Acceptance** | ⏳ 0% | Giai đoạn nghiệm thu và bảo vệ đồ án (Sắp tới). |
| **Maintenance and Upgrade** | ⏳ 0% | Kế hoạch tối ưu hóa sau khi hoàn thành dự án. |

---

## 📝 Tóm tắt thực hiện Tuần này

### 2026-05-20 — Cloud Integration Day
Ngày quan trọng nhất của giai đoạn System Integration. Toàn bộ stack hoạt động end-to-end lần đầu:

1. **Cloud Backend**: Deploy Flask server lên Render, thêm đầy đủ API auth + vitals + fall_events
2. **Android**: Tích hợp OkHttp, xây dựng CloudApi, auth với MongoDB, upload/fetch vitals
3. **Bug Fix**: 8 bug được phát hiện và fix, bao gồm crash trên Android 10, timestamp 1970, chart overflow
4. **Data Validation**: Xóa 415 document dữ liệu bẩn (timestamp epoch), xác thực pipeline upload/fetch

Chi tiết: xem [`2026-05-20.md`](2026-05-20.md)

---

### 2026-05-19 — BLE Sync & Fall Detection Day
Hoàn thành đồng bộ protocol Edge ↔ Android và tinh chỉnh pipeline phát hiện té ngã:

1. **Critical Bug Fix**: NimBLE `setValue()` gửi pointer thay vì string → fix toàn bộ BLE transmission
2. **Fall Detection Pipeline 7 tầng**: Thiết kế + tinh chỉnh ngưỡng, AI Window 6s, sliding stillness timer
3. **BLE Protocol hoàn chỉnh**: 4 packet types (ALERT/SAFE/BATCH/BMI), READY handshake
4. **Android BLE Sync**: `BlePacketParser` mới, 15 unit tests PASS, fix AlertScreen duplicate countdown
5. **Documentation**: `05_fall_detection_pipeline.md`, `SYNC_COMPLETION_REPORT.md`, `user_flow.md`

Chi tiết: xem [`2026-05-19.md`](2026-05-19.md)

---

### Trước 2026-05-19
1. **Chốt Đặc tả (Spec)**: Đồng bộ hóa toàn bộ thông số kỹ thuật dựa trên báo cáo M1.
2. **Triển khai Phần mềm (Software Deployment)**:
   - Deploy thành công mô hình AI (Recall 98.51%) lên môi trường nhúng.
   - Deploy ứng dụng Android AIFD với 6 màn hình chức năng chính.
3. **Hoạch định Kiểm thử (Test Planning)**: Xây dựng xong bộ kịch bản kiểm thử 3 lớp.

## 📅 Kế hoạch tiếp theo
- Test fall detection end-to-end trên thiết bị thật
- Kiểm tra offline mode (cache khi mất mạng)
- Tích lũy đủ 24h data để validate chart 24h
- Tiến tới **Delivery and Acceptance**

---
*Tài liệu được cập nhật dựa trên quy trình chuẩn kỹ thuật.*
