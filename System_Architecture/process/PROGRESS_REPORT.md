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
| **Prototype and Construct** | 🚧 80% | **Đã deploy App và Model AI**. Chờ lắp ráp phần cứng vật lý. |
| **System Integration** | 🚧 70% | Đã thiết kế xong toàn bộ luồng dữ liệu Edge -> App -> Cloud. |
| **System Test** | 🚧 50% | **Đã hoàn thiện bộ Test Plan** (Unit, Integrated, Acceptance). |
| **Delivery and Acceptance** | ⏳ 0% | Giai đoạn nghiệm thu và bảo vệ đồ án (Sắp tới). |
| **Maintenance and Upgrade** | ⏳ 0% | Kế hoạch tối ưu hóa sau khi hoàn thành dự án. |

---

## 📝 Tóm tắt thực hiện Tuần này

Tuần này, dự án đã có bước nhảy vọt từ giai đoạn **Design** sang **Prototype & Integration**:

1.  **Chốt Đặc tả (Spec)**: Đồng bộ hóa toàn bộ thông số kỹ thuật dựa trên báo cáo M1.
2.  **Triển khai Phần mềm (Software Deployment)**:
    *   Deploy thành công mô hình AI (Recall 98.36%) lên môi trường nhúng.
    *   Deploy ứng dụng Android AIFD với 6 màn hình chức năng chính.
3.  **Hoạch định Kiểm thử (Test Planning)**: Xây dựng xong bộ kịch bản kiểm thử 3 lớp để chuẩn bị cho giai đoạn nghiệm thu.

## 📅 Kế hoạch tiếp theo
Tập trung vào việc **System Integration** thực tế trên phần cứng và thực thi các bài test trong **System Test** để tiến tới giai đoạn **Delivery**.

---
*Tài liệu được cập nhật dựa trên quy trình chuẩn kỹ thuật.*
