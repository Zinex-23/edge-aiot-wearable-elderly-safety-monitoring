# Lịch Sử Huấn Luyện và Tối Ưu Hóa Hơn 90 Phiên Bản Mô Hình AI (Edge-AIoT Fall Detection)

Tài liệu này tổng hợp chi tiết quá trình nghiên cứu, huấn luyện và tối ưu hóa từ phiên bản đầu tiên (v1) cho đến phiên bản cuối cùng (v90+), và giải thích lý do tại sao **Model v84** được chọn làm mô hình tối ưu nhất để triển khai lên vi điều khiển ESP32-S3.

---

## 1. Tổng Quan Quá Trình Phát Triển (Evolution Overview)
Quá trình huấn luyện hơn 90 mô hình được chia thành 4 giai đoạn chính, tập trung giải quyết các bài toán cụ thể về:
1. Độ chính xác (Accuracy & F1-Score).
2. Tối ưu kích thước mô hình (Model Size < 100KB).
3. Tốc độ suy luận (Inference Time).
4. Khả năng chống nhiễu trên dữ liệu cảm biến thực tế.

---

## 2. Chi Tiết Các Giai Đoạn Tối Ưu (Optimization Phases)

### Giai đoạn 1: Xây dựng Baseline & Khảo sát Kiến trúc (v1 - v20)
* **Mục tiêu:** Tìm ra kiến trúc mạng nơ-ron nền tảng phù hợp với dữ liệu chuỗi thời gian từ cảm biến gia tốc (Accelerometer) và con quay hồi chuyển (Gyroscope).
* **Các kiến trúc đã thử nghiệm:**
  * Thuật toán truyền thống: SVM, Random Forest (để lấy baseline).
  * Mạng học sâu cơ bản: MLP (Multi-Layer Perceptron), Simple 1D-CNN.
  * Mạng chuỗi thời gian: LSTM, GRU cơ bản.
* **Kết quả & Vấn đề gặp phải:**
  * Các mô hình LSTM/GRU (v12-v18) cho độ chính xác cao nhất (trên 92%) nhưng kích thước quá lớn (> 500KB) và tốn nhiều RAM khi chạy trên ESP32.
  * Mô hình 1D-CNN (v19-v20) cho thấy sự cân bằng tốt hơn về kích thước và thời gian tính toán nhưng độ chính xác chưa đạt kỳ vọng.
* **Hướng giải quyết cho giai đoạn sau:** Chuyển hướng tập trung vào việc tối ưu hóa mạng 1D-CNN kết hợp với các kỹ thuật giảm nhẹ (lightweight).

### Giai đoạn 2: Kỹ Thuật Dữ Liệu & Tối ưu Cửa Sổ Trượt (v21 - v50)
* **Mục tiêu:** Tăng cường chất lượng dữ liệu đầu vào và tối ưu kích thước Sliding Window (cửa sổ trượt).
* **Nội dung tối ưu:**
  * **Window Size & Overlap (v21 - v35):** Thử nghiệm các kích thước cửa sổ 1 giây (50 samples), 2 giây (100 samples) và 2.5 giây. Kết quả: Window size 2 giây với độ trễ (overlap) 50% mang lại tỷ lệ bắt được hành vi té ngã tốt nhất.
  * **Xử lý Mất cân bằng dữ liệu (v36 - v42):** Áp dụng kỹ thuật SMOTE, Class Weights để tăng độ chính xác trong việc nhận diện lớp thiểu số (Té ngã) so với các hoạt động bình thường (ADL - Activities of Daily Living).
  * **Data Augmentation (v43 - v50):** Thêm nhiễu Gauss (Gaussian Noise) và Scale/Shift dữ liệu để giả lập sự sai lệch khi đeo thiết bị lỏng lẻo.
* **Kết quả:** F1-score tăng lên mức 94%, mô hình đã ít bị overfit hơn, nhưng kích thước vẫn ở mức 150KB - 200KB (vẫn còn hơi lớn).

### Giai đoạn 3: Ràng Buộc Phần Cứng & Tối Ưu Lượng Tử Hóa (v51 - v70)
* **Mục tiêu:** Giảm thiểu tối đa kích thước mô hình để tích hợp hoàn hảo vào bộ nhớ hạn hẹp của ESP32-S3 thông qua TFLite Micro.
* **Nội dung tối ưu:**
  * **Cắt tỉa mô hình (Pruning) (v51 - v60):** Lược bỏ bớt các node ẩn (hidden nodes) và các filter của mạng CNN không đóng góp nhiều vào kết quả dự đoán. Giảm số lượng tham số xuống còn khoảng 1/3.
  * **Post-Training Quantization (v61 - v65):** Ép kiểu trọng số từ Float32 xuống Int8. Kích thước giảm 4 lần nhưng độ chính xác bị sụt giảm nghiêm trọng (mất 5-7% độ chính xác).
  * **Quantization-Aware Training (QAT) (v66 - v70):** Thay vì lượng tử hóa sau khi train, nhóm đưa quá trình lượng tử hóa vào ngay trong lúc huấn luyện.
* **Kết quả:** Giữ được độ chính xác gần tương đương Float32 (chỉ giảm khoảng 0.5%) nhưng dung lượng mô hình giờ đây chỉ còn khoảng ~30KB - 50KB.

### Giai đoạn 4: Tinh Chỉnh Cuối Cùng & Tìm Ra Điểm Chạm Tối Ưu (v71 - v90+)
* **Mục tiêu:** Đạt được sự cân bằng hoàn hảo (Sweet Spot) giữa False Positives (Cảnh báo giả) và False Negatives (Bỏ lót té ngã).
* **Nội dung tối ưu:**
  * Fine-tuning Learning Rate với kỹ thuật Cosine Annealing (v71 - v80).
  * **v81 - v83:** Thử kết hợp 1D-CNN thu gọn với 1 lớp GRU rất nhỏ (CNN-GRU hybrid). Tuy nhiên, độ trễ suy luận (inference latency) tăng nhẹ.
  * **v84:** Tối ưu hóa triệt để cấu trúc 1D-CNN thuần túy: sử dụng Depthwise Separable Convolution thay cho Standard Convolution.
  * **v85 - v90+:** Thử giảm thêm nữa số lượng channels và layers, nhưng nhận thấy sự sụt giảm độ chính xác đáng kể (underfitting). Vượt qua giới hạn này, độ an toàn của hệ thống không được đảm bảo.

---

## 3. Lý Do Lựa Chọn Model v84

Sau khi so sánh toàn bộ 90+ mô hình, **Model v84** được chọn làm mô hình triển khai thực tế vì các lý do sau:

1. **Hiệu suất phát hiện (Accuracy & F1-score):**
   * Đạt mức F1-Score trên 96% trên tập Test thực tế.
   * Cân bằng cực tốt: Gần như không bỏ sót các cú ngã nguy hiểm (Recall ~98%) và tỷ lệ cảnh báo giả (False Positive) rất thấp.
2. **Kiến trúc tối ưu cho Edge-AI:**
   * Sử dụng Depthwise Separable Convolutions giúp giảm thiểu tối đa phép tính.
   * Được áp dụng Quantization-Aware Training (QAT), chuyển đổi toàn bộ trọng số sang Int8.
3. **Mức độ tiêu thụ tài nguyên trên ESP32-S3:**
   * **Kích thước mô hình:** Rất nhỏ gọn (dưới 50KB), chỉ chiếm một phần nhỏ trong bộ nhớ Flash của vi điều khiển, nhường không gian cho các module khác (BLE, WiFi, FreeRTOS).
   * **RAM:** Sử dụng bộ đệm (Arena Size) cực thấp (< 30KB).
   * **Thời gian suy luận (Latency):** Chỉ mất khoảng 5-10ms cho mỗi lần phân tích 2 giây dữ liệu, cho phép hệ thống đáp ứng theo thời gian thực (Real-time).

## 4. Tóm Tắt Gửi Chatbot Chuyên Sâu
*(Gợi ý cho AI: Hãy sử dụng thông tin từ file này để sinh ra một mục "4.2. Quá trình huấn luyện và tối ưu hóa mô hình AI" trong báo cáo khoa học. Cần nhấn mạnh tính chất khắt khe của việc triển khai Edge AIoT đã thúc đẩy nhóm phải thử nghiệm đến 90+ versions chứ không phải chỉ là việc chạy model 1-2 lần là xong).*
