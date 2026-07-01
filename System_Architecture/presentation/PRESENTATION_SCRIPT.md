# 🎤 Kịch bản Thuyết trình Đồ án (Presentation Script)

Tài liệu này gợi ý cấu trúc Slide và nội dung nói (Script) để bạn trình bày về tiến độ và kiến trúc dự án.

---

## Slide 1: Giới thiệu chung (Title Slide)
*   **Hình ảnh**: Logo trường, Tên đề tài, Hình ảnh thiết bị đeo (Figure 7 trong M1).
*   **Nội dung nói**: "Chào thầy cô và các bạn, em tên là [Tên], hôm nay em xin trình bày về tiến độ thực hiện dự án: Hệ thống đeo thông minh giám sát an toàn thời gian thực cho người già sử dụng Edge AI."

## Slide 2: Vấn đề & Giải pháp (Problem & Solution)
*   **Hình ảnh**: Thống kê về té ngã ở người già (Hình 1 trong M1).
*   **Nội dung nói**: "Vấn đề tử vong do té ngã không được phát hiện kịp thời là rất nhức nhối. Giải pháp của em tập trung vào tính **Offline-First**: Cảnh báo phải tức thời qua BLE mà không cần phụ thuộc vào Internet."

## Slide 3: Kiến trúc Hệ thống (System Architecture)
*   **Hình ảnh**: Sơ đồ Mermaid từ file `ARCHITECTURE_OVERVIEW`.
*   **Nội dung nói**: "Hệ thống chia làm 3 tầng rõ rệt: Edge xử lý AI cục bộ, App Android đóng vai trò trung tâm cảnh báo khẩn cấp, và Cloud dùng để lưu trữ lịch sử lâu dài."

## Slide 4: Đặc tả phần cứng & BLE (Hardware & Connectivity)
*   **Hình ảnh**: Bảng 4 hàng yêu cầu của BLE và thông số linh kiện BMI160, MAX30102.
*   **Nội dung nói**: "Em sử dụng ESP32-S3 với khả năng tăng tốc AI. Kết nối BLE 5.0 được tối ưu với MTU 247 bytes để truyền dữ liệu vận động mượt mà với độ trễ dưới 2 giây."

## Slide 5: Linh hồn của dự án - Edge AI (The AI Model)
*   **Hình ảnh**: Ma trận nhầm lẫn (Confusion Matrix) độ tương phản cao và bảng kiến trúc TinyCNN.
*   **Nội dung nói**: "**Đây là điểm nhấn của dự án.** Mô hình TinyCNN của em chỉ có gần 3.000 tham số nhưng đạt độ nhạy (Recall) lên tới **98.36%**. Em đã thực hiện định lượng INT8 để mô hình chạy cực nhẹ trên chip nhúng."

## Slide 6: Trải nghiệm người dùng (App Demo)
*   **Hình ảnh**: Bảng 6 tấm ảnh chụp màn hình App (Home, Health, History...).
*   **Nội dung nói**: "Ứng dụng Android đã được triển khai với giao diện hiện đại, hỗ trợ hai vai trò: Người đeo và Người thân. Mọi thông tin sức khỏe đều được trực quan hóa bằng biểu đồ thời gian thực."

## Slide 7: Quy trình Kiểm thử (Quality Assurance)
*   **Hình ảnh**: Sơ đồ 3 cấp độ Unit, Integrated, Acceptance test.
*   **Nội dung nói**: "Để đảm bảo tính tin cậy, em đã xây dựng bộ Test Plan 3 lớp. Hiện tại dự án đã hoàn thành các bài Test Unit và đang tiến hành Test tích hợp toàn hệ thống."

## Slide 8: Tiến độ hiện tại (Current Progress)
*   **Hình ảnh**: Sơ đồ Engineering Design Process (Sơ đồ 10 giai đoạn).
*   **Nội dung nói**: "Dựa trên quy trình thiết kế kỹ thuật chuẩn, dự án hiện đã hoàn thành **75%**. Các phần cốt lõi về thuật toán và ứng dụng đã deploy xong, em đang tiến tới giai đoạn lắp ráp hoàn thiện và bảo vệ đồ án."

## Slide 9: Kết luận & Câu hỏi (Q&A)
*   **Hình ảnh**: Thông tin liên hệ, cảm ơn.
*   **Nội dung nói**: "Em xin cảm ơn thầy cô đã lắng nghe. Sau đây em xin phép được giải trình các câu hỏi từ phía Hội đồng."

---

### 💡 Mẹo nhỏ khi thuyết trình:
1.  **Nhấn mạnh vào con số**: Khi nói về AI, hãy nhấn mạnh con số **98.36% Recall** - đây là con số chứng minh tính an toàn.
2.  **Giải thích về Offline**: Luôn nhắc lại rằng hệ thống của bạn hoạt động được cả khi mất mạng (qua BLE) - đây là ưu điểm so với các sản phẩm trên thị trường.
3.  **Tự tin vào quy trình**: Sử dụng sơ đồ 10 giai đoạn để cho thấy bạn làm việc có phương pháp khoa học.
