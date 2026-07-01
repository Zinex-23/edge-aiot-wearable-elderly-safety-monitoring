# Q&A — Câu Hỏi Hội Đồng & Gợi Ý Trả Lời
**Báo Cáo M2 — CaraFall Wearable Safety Monitoring System**

---

## PHẦN AI & MODEL

---

### Q1: Tại sao chọn TinyCNN thay vì các mô hình ML cổ điển như SVM, Random Forest?

**Trả lời:**
Các mô hình ML cổ điển như SVM hay RF yêu cầu bước trích xuất đặc trưng thủ công — CareFall [1] trích xuất tới 88 đặc trưng thống kê. Bước này tốn tài nguyên tính toán và khó triển khai trên MCU. TinyCNN học trực tiếp từ dữ liệu IMU thô — tensor (100, 6) — không cần feature engineering. Quan trọng hơn, TinyCNN học được các **pattern thời gian** (temporal patterns) trong chuỗi dữ liệu mà các mô hình ML cổ điển dùng vector đặc trưng không nắm bắt được. Sau khi lượng tử hóa INT8, mô hình chỉ còn 10,96 KB — phù hợp hoàn toàn với giới hạn flash của ESP32-S3.

---

### Q2: Tại sao không dùng LSTM hay Transformer thay vì CNN?

**Trả lời:**
LSTM và Transformer cho kết quả tốt trên chuỗi dài nhưng có chi phí tính toán và bộ nhớ cao hơn nhiều so với CNN 1D — không phù hợp với MCU có 512 KB SRAM. Với cửa sổ 2 giây (100 mẫu), Conv1D đã đủ để nắm bắt các pattern chuyển động đặc trưng của té ngã. Đây là sự đánh đổi có chủ đích giữa độ chính xác và khả năng triển khai trên thiết bị nhúng.

---

### Q3: Các thông số huấn luyện (optimizer, batch size, epochs) được chọn như thế nào?

**Trả lời:**
Tất cả đều được xác định qua grid search thực nghiệm:
- **Adam lr=1e-3**: Thử 1e-2 thì loss dao động mạnh, không hội tụ; 1e-4 thì quá chậm và accuracy thấp. 1e-3 là điểm cân bằng tốt nhất.
- **Batch size 32**: Thử 16 thì gradient nhiễu quá, 64 dễ rơi vào sharp minima khó tổng quát hóa. 32 cho validation performance tốt nhất.
- **60 Epochs + patience 10**: Learning curve cho thấy model hội tụ ở epoch 35–45. Đặt max 60 với Early Stopping tránh overfitting.
- **Checkpoint lowest val loss**: Đảm bảo lấy model ở trạng thái tổng quát hóa tốt nhất, không phải epoch cuối.

---

### Q4: Binary Cross-Entropy được chọn vì sao?

**Trả lời:**
Đây là hàm mất mát tiêu chuẩn cho bài toán phân loại nhị phân (2 lớp: fall / non-fall) kết hợp với Sigmoid ở output layer. BCE đo lường sự khác biệt giữa xác suất dự đoán và nhãn thực tế, đồng thời phạt nặng những dự đoán sai lệch lớn. Nó tối ưu hóa theo nguyên lý Maximum Likelihood Estimation — phù hợp với bản chất của bài toán.

---

### Q5: Tại sao kích thước mô hình là 10,96 KB?

**Trả lời:**
Con số này gồm 2 phần:
- **Dữ liệu tham số** (2.974 params sau INT8): Weights (INT8) = 2.880 bytes + Biases (INT32) = 324 bytes + Normalization (Float32) = 52 bytes → **3.256 bytes**
- **Overhead FlatBuffer TFLite**: Metadata lớp, operator codes, bảng quantization map → **7.711 bytes**
- **Tổng**: 3.256 + 7.711 = **10.967 bytes ≈ 10,96 KB**

---

### Q6: Tại sao chọn threshold 0,50 thay vì 0,40 hay 0,30?

**Trả lời:**
Dựa trên phân tích biểu đồ threshold tuning (Figure 5 trong slide): Recall duy trì ổn định trên 98% trong dải 0,30–0,70 — tức là giảm threshold thêm không cải thiện Recall nhưng làm tăng đột biến False Alarm Rate. Ngưỡng 0,50 là điểm mà False Alarm Rate bắt đầu giảm đáng kể trong khi Recall vẫn ở mức cao. Đây là điểm cân bằng tối ưu giữa độ nhạy và tỷ lệ cảnh báo nhầm.

> **Lưu ý quan trọng**: Firmware hiện tại đang dùng threshold 0,40. Ngưỡng 0,50 trong báo cáo là kết quả phân tích tối ưu và sẽ được cập nhật trong giai đoạn integration.

---

### Q7: False Alarm Rate 16,73% còn khá cao, nhóm sẽ xử lý thế nào?

**Trả lời:**
Đây là điểm yếu nhóm thẳng thắn thừa nhận — hiện chưa đạt target ≤ 10%. Giải pháp đã lên kế hoạch cho giai đoạn cuối là **"Consecutive Window Validation"**: thay vì cảnh báo ngay khi 1 window dự đoán là fall, hệ thống yêu cầu **N cửa sổ liên tiếp** (ví dụ N=2 hoặc N=3) đều cho kết quả fall trước khi kích hoạt alert. Vì té ngã thật tạo ra chuỗi chuyển động kéo dài, còn false positive thường là hiện tượng đơn lẻ đột biến. Cơ chế này không làm tăng độ trễ đáng kể vì mỗi window chỉ 2 giây.

---

### Q8: Tại sao Recall (98,36%) lại được ưu tiên hơn Accuracy (90,80%)?

**Trả lời:**
Trong hệ thống an toàn sinh mạng, hai loại lỗi có chi phí rất khác nhau:
- **Bỏ sót té ngã** (False Negative): người già ngã không được cứu → hậu quả có thể tử vong.
- **Cảnh báo nhầm** (False Positive): gọi điện thừa → gây phiền nhưng không nguy hiểm.

Chi phí của False Negative vượt xa chi phí của False Positive. Vì vậy tối ưu hóa Recall là ưu tiên số một. Accuracy 90,80% bị kéo xuống bởi 41 false positives — vấn đề sẽ được xử lý bằng consecutive window validation, không ảnh hưởng đến khả năng phát hiện té ngã thật.

---

## PHẦN DỮ LIỆU & TIỀN XỬ LÝ

---

### Q9: Nhóm lọc/cắt bớt dữ liệu non-fall như thế nào? Tại sao loại bỏ đi mà không giữ hết?

**Trả lời:**
Dataset HR-IMU có mất cân bằng nghiêm trọng: 1.628 fall vs 5.468 non-fall (~1:3,4). Giữ nguyên sẽ làm model lệch — học cách đoán non-fall cho an toàn thay vì học phân biệt. Nhóm thực hiện undersampling dựa trên **2 cơ sở**:

**1. Temporal Redundancy (Dư thừa thời gian):** Sliding window với bước dịch nhỏ tạo ra các cửa sổ liên tiếp chồng lấp nhau — window[i] và window[i+1] chia sẻ 99/100 mẫu. Các hoạt động kéo dài như ngồi yên, đứng, đi bộ đều đặn tạo ra hàng trăm window gần như bản sao nhau, không mang thông tin mới — đây là nguyên nhân chính tạo ra 5.468 non-fall windows.

**2. Low Information Content (Thông tin thấp):** Window có độ lệch chuẩn (std) thấp — trạng thái gần tĩnh — không có giá trị phân biệt với lớp fall. Giữ lại chúng chỉ làm loãng tín hiệu đặc trưng.

Sau khi loại bỏ các window dư thừa và thông tin thấp, nhóm lấy mẫu ngẫu nhiên từ pool chất lượng còn lại để đạt tỷ lệ 1:1 với fall. Kết quả: 3.256 windows cân bằng, model học được ranh giới quyết định rõ ràng hơn.

---

### Q10: Tại sao chọn cửa sổ 2 giây (100 mẫu @ 50Hz)?

**Trả lời:**
2 giây là khoảng thời gian vừa đủ để nắm bắt hoàn chỉnh một cú té ngã — gồm 3 phase: **impact** (va chạm mạnh, ~0,5s), **free-fall** (rơi, ~0,5s), **recovery** (chạm đất, ~1s). Ngắn hơn có thể bỏ sót một phase, dài hơn tăng độ trễ phát hiện. CareFall dùng 60 giây — quá dài cho cảnh báo khẩn cấp. 2 giây cho phép phát hiện gần như tức thời và phù hợp với tần số mẫu 50Hz của BMI160.

---

### Q11: Tại sao dùng dataset HR-IMU thay vì tự thu thập dữ liệu?

**Trả lời:**
Thu thập dữ liệu té ngã thực tế với người cao tuổi là bất khả thi về mặt đạo đức và an toàn. HR-IMU là dataset được công bố trong paper IEEE Access 2020, có 21 đối tượng thực nghiệm, 6 kịch bản té ngã khác nhau (ngã trước, ngã sau, ngã ngang...) và 9 loại hoạt động thường ngày. Đây là dataset tiêu chuẩn được cộng đồng nghiên cứu công nhận, đặt tại cổ tay — phù hợp với thiết kế wristband của nhóm.

---

## PHẦN HỆ THỐNG & THIẾT KẾ

---

### Q12: Nếu không có mạng lẫn sóng SIM thì có báo cho người thân được không?

**Trả lời:**
Đây là giới hạn thực tế của hệ thống hiện tại. Khi không có cả internet lẫn sóng cellular, luồng gọi điện khẩn cấp sẽ không thực hiện được. Tuy nhiên, hệ thống vẫn hoạt động ở mức cục bộ:
- **ESP32-S3** vẫn phát hiện té ngã và gửi alert qua BLE đến điện thoại (không cần mạng).
- **Điện thoại** hiển thị cảnh báo và có thể phát âm thanh/đèn để thu hút người xung quanh.
- **Thiết bị đeo** có thể tích hợp còi/LED để tạo tín hiệu cầu cứu tại chỗ.

**Hướng phát triển:** Nếu có WiFi nhưng không có sóng, WiFi Calling vẫn gọi được trên một số nhà mạng. Về dài hạn, có thể tích hợp module LoRa vào ESP32-S3 để liên lạc khoảng cách xa (~km) không cần cellular. Tuy nhiên các hướng này nằm ngoài phạm vi đề tài hiện tại vốn tập trung vào kiến trúc BLE + Edge AI.

---

### Q13: Tại sao không xử lý AI trên điện thoại thay vì trên ESP32?

**Trả lời:**
Ba lý do chính:
1. **Độ trễ BLE**: Truyền liên tục 6 trục × 50Hz qua BLE tốn băng thông và thêm độ trễ không xác định. Xử lý tại nguồn (on-device) cho phép kết quả trong <100ms.
2. **Độ tin cậy**: Nếu BLE mất kết nối, điện thoại không nhận được dữ liệu để xử lý — hệ thống tê liệt. Xử lý trên ESP32 đảm bảo phát hiện té ngã ngay cả khi điện thoại mất kết nối.
3. **Triết lý Offline-First**: AI trên MCU = tự chủ hoàn toàn, không phụ thuộc bất kỳ thiết bị hay kết nối nào khác.

---

### Q14: ESP32-S3 có đủ tài nguyên để chạy TFLite Micro không?

**Trả lời:**
Có. ESP32-S3 có 512KB SRAM và hỗ trợ TFLite Micro natively. Mô hình của nhóm chỉ cần 10,96 KB flash cho model weights và tensor arena (buffer trung gian khi inference) được cấp phát 60 KB trong firmware. Còn lại tài nguyên dành cho BLE stack, sensor drivers và các tác vụ nền. Nhóm đã verify thông qua `AllocateTensors()` thành công trên hardware thực tế.

---

### Q15: Tại sao chọn BLE 5.0 thay vì WiFi để giao tiếp?

**Trả lời:**
BLE 5.0 tiêu thụ điện năng thấp hơn WiFi từ 10–100 lần — cực quan trọng với thiết bị đeo dùng pin nhỏ. Phạm vi 10–30m là đủ cho môi trường trong nhà, nơi người cao tuổi thường sinh hoạt. BLE cũng cho phép kết nối nhanh và duy trì kết nối liên tục mà không cần router. WiFi sẽ cần cơ sở hạ tầng (router) và tiêu thụ pin nhiều hơn — không phù hợp với wearable 24/7.

---

### Q16: Tại sao cần PCB tùy chỉnh thay vì dùng module dev board?

**Trả lời:**
Dev board (như ESP32-S3 Super Mini) rất tiện cho prototype nhưng kích thước lớn (khoảng 20×18mm) và không thể tích hợp tất cả linh kiện vào form factor wristband. PCB tùy chỉnh 32×40mm cho phép: tích hợp BMI160 + MAX30102 + ESP32-S3 + mạch quản lý pin LiPo + USB-C trên 1 board duy nhất, tối ưu routing I2C để giảm EMI cho tín hiệu PPG, và thiết kế ground plane 2 lớp cho ổn định tín hiệu. Đây là bước cần thiết để chuyển từ prototype sang sản phẩm đeo được thực tế.

---

### Q17: INT8 Quantization là gì và tại sao dùng nó?

**Trả lời:**
Quantization là kỹ thuật nén mô hình bằng cách chuyển trọng số từ số thực 32-bit (Float32) xuống số nguyên 8-bit (INT8). Kết quả:
- **Kích thước giảm 4x**: Float32 (4 bytes/param) → INT8 (1 byte/param).
- **Tốc độ tăng 2–4x**: ESP32-S3 có hardware accelerator cho INT8 arithmetic.
- **Tiêu thụ điện giảm**: Phép tính số nguyên hiệu quả hơn số thực.

Nhóm dùng **Post-Training Quantization** — train với Float32 rồi chuyển đổi sang INT8 khi export sang TFLite. Độ chính xác giảm rất ít (<1%) vì model đã được thiết kế nhỏ gọn và dữ liệu IMU có dải giá trị ổn định.

---

### Q18: Hệ thống xử lý false positive như thế nào để tránh làm phiền người dùng?

**Trả lời:**
Hệ thống có cơ chế 15 giây xác nhận — người dùng có thể nhấn "I'm Safe" để hủy nếu là cảnh báo nhầm. Ngoài ra, giai đoạn cuối sẽ thêm consecutive window validation (yêu cầu nhiều cửa sổ liên tiếp đều dương tính trước khi cảnh báo). Firmware cũng đã có candidate threshold — chỉ chạy model khi acc_magnitude > 1,8g hoặc gyro_magnitude > 50 dps, bỏ qua các window hoàn toàn tĩnh để tiết kiệm tài nguyên.

---

### Q19: Nhóm đã test hệ thống thực tế chưa? Kết quả như thế nào?

**Trả lời:**
Ở giai đoạn M2, nhóm đã verify từng module độc lập:
- **AI model**: Đánh giá trên hold-out test set (489 windows, chưa thấy trong training) — Recall 98,36%.
- **Firmware**: Model chạy thành công trên ESP32-S3, `AllocateTensors()` và `Invoke()` hoạt động đúng, BLE notify được kiểm tra.
- **Android app**: Kết nối BLE, nhận dữ liệu VITALS và ALERT, hiển thị real-time, luồng SOS hoạt động.

**Chưa có**: System-level end-to-end testing với toàn bộ luồng từ hardware thực tế → firmware → BLE → app → gọi điện. Đây là mục tiêu của phase Integration (26/05–31/05) và Evaluation (10/06–20/06).

---

### Q20: Dataset HR-IMU thu thập ở cổ tay hay vị trí khác? Có ảnh hưởng đến kết quả không?

**Trả lời:**
HR-IMU thu thập dữ liệu tại **cổ tay trái** — hoàn toàn phù hợp với thiết kế wristband của nhóm. Đây là điểm khác biệt so với nhiều dataset khác thu thập ở thắt lưng hay ngực. Dữ liệu cổ tay phức tạp hơn do chuyển động tay trong sinh hoạt thường ngày (ăn cơm, chải đầu...) có thể gây nhiễu — thách thức này phần nào giải thích False Alarm Rate 16,73% hiện tại. Tuy nhiên đây cũng làm cho mô hình của nhóm thực tế hơn so với các nghiên cứu dùng IMU ở thắt lưng.

---

### Q21: Tại sao không dùng Find My của Apple hay AirTag để báo vị trí khi mất sóng?

**Trả lời:**
Find My là công nghệ **độc quyền của Apple**, không thể tích hợp vào Android app hay ESP32 của bên thứ ba. Cơ chế của Find My yêu cầu hardware được Apple chứng nhận (chip U1 trong AirTag) và protocol độc quyền. Nhóm đang xây dựng trên nền tảng Android + ESP32 — open ecosystem. Hướng tương đương có thể áp dụng là Bluetooth Beacon (iBeacon/Eddystone) kết hợp với mạng lưới người dùng CaraFall, nhưng đây là hướng phát triển dài hạn, không thuộc phạm vi đề tài hiện tại.

---

### Q22: Nhóm có so sánh với các hệ thống thương mại như Apple Watch, Garmin không?

**Trả lời:**
Apple Watch và Garmin có tính năng fall detection nhưng giá cao (từ 5–15 triệu đồng), phụ thuộc vào hệ sinh thái của hãng, và không tối ưu cho người cao tuổi Việt Nam. Hệ thống CaraFall hướng đến chi phí thấp hơn nhiều (ESP32-S3 + PCB custom ~ vài trăm nghìn đồng), hoạt động hoàn toàn offline, và có thể tùy chỉnh theo yêu cầu cụ thể (số liên lạc khẩn cấp, ngưỡng cảnh báo...). Đây là định vị khác biệt so với sản phẩm thương mại.

---

*Tài liệu tổng hợp từ QnA.md gốc và các câu hỏi bổ sung dựa trên nội dung báo cáo M2.*
