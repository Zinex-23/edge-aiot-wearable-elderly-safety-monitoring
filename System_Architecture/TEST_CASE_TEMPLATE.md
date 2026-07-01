# 🛠️ Test Case: [Tên Bài Kiểm Thử]

> **ID:** TC_[xxx] | **Trạng thái:** 🟢 Sẵn sàng | **Người thực hiện:** [Tên]

## 1. Mô tả (Description)
*   **Mục tiêu**: [Ví dụ: Đảm bảo thiết bị gọi điện ngay sau khi phát hiện té ngã]
*   **Loại test**: [Black-box / Integration]
*   **Hardware**: ESP32-S3 Mini + Smartphone

## 2. Chuẩn bị (Pre-requisites)
1.  Thiết bị đeo đã kết nối BLE với Smartphone qua App AIFD.
2.  Smartphone có quyền truy cập ứng dụng gọi điện và danh bạ.
3.  Hệ thống đang ở trạng thái hoạt động bình thường (Healthy).

## 3. Các bước thực hiện (Test Steps)

| Bước | Hành động (Action) | Kết quả mong đợi (Expected Result) | Kết quả thực tế | Check |
| :--- | :--- | :--- | :--- | :---: |
| 1 | Thực hiện mô phỏng cú ngã (ví dụ: thả rơi vào đệm) | AI trên chip nhận diện đúng cú ngã | | [ ] |
| 2 | Theo dõi thông báo trên App Android | App hiển thị cảnh báo "Fall Detected" trong < 2s | | [ ] |
| 3 | Theo dõi hành động của Smartphone | Smartphone tự động thực hiện cuộc gọi SOS theo cấu hình | | [ ] |
| 4 | | | | [ ] |

## 4. Kết luận (Conclusion)
*   **Kết quả cuối cùng**: [Pass / Fail]
*   **Ghi chú lỗi (Bugs/Issues)**: [Danh sách nếu có]
*   **Đề xuất**: [Cải thiện ngưỡng nhạy AI, giảm trễ...]

---
