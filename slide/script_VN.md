# Kịch Bản Thuyết Trình — Báo Cáo M2 (Tiếng Việt)
**CaraFall: Hệ Thống Wearable Edge AIoT Thông Minh Giám Sát An Toàn Người Già**

---

## Slide 1 — Trang bìa (~20s)

Kính chào thầy cô và hội đồng. Em tên là Trần Phước Diễn, cùng với thành viên nhóm là Phạm Văn Tiến, nhóm em xin được trình bày báo cáo M2 Capstone về đề tài: Thiết kế và triển khai hệ thống wearable Edge AIoT thông minh phục vụ giám sát an toàn người cao tuổi theo thời gian thực. Đề tài được thực hiện dưới sự hướng dẫn của TS. Nguyễn Thị Anh Thư và ThS. Nguyễn Đức Phước.

---

## Slide 2 — Mục lục (~20s)

Bài trình bày của nhóm em gồm 5 phần chính: Phần 1 tóm tắt lại mục tiêu dự án; Phần 2 trình bày kiến trúc hệ thống và phương pháp đề xuất; Phần 3 phân công nhiệm vụ cá nhân; Phần 4 là các kết quả đã đạt được; và Phần 5 là kế hoạch công việc còn lại đến milestone cuối.

---

## Slide 3 — Đặt vấn đề & Động lực (~45s)

Tại sao đề tài này quan trọng? Theo WHO, té ngã là nguyên nhân thứ hai gây tử vong do tai nạn không chủ ý trên toàn thế giới. Người cao tuổi từ 60 tuổi trở lên chiếm tỷ lệ tử vong do té ngã cao nhất. Điều đặc biệt quan trọng là khái niệm "thời gian vàng" — nếu cứu hộ được thực hiện trong vài phút đầu sau cú ngã, tỷ lệ sống sót tăng lên đáng kể. Riêng tại Việt Nam, dân số đang già hóa nhanh, dự kiến đến năm 2038 sẽ có 20% dân số là người cao tuổi theo số liệu UNFPA. Đây chính là bối cảnh thúc đẩy nhóm em phát triển một giải pháp phát hiện té ngã tự động, đáng tin cậy và không phụ thuộc vào kết nối mạng.

---

## Slide 4 — Tổng quan kiến trúc hệ thống (Sơ đồ) (~30s)

Hệ thống được thiết kế theo kiến trúc 5 tầng: Tầng Perception thu thập dữ liệu cảm biến; Tầng Edge Processing xử lý AI trực tiếp trên vi điều khiển; Tầng Communication sử dụng BLE 5.0; Tầng Application là ứng dụng Android; và Tầng Cloud lưu trữ dữ liệu dài hạn. Điểm mấu chốt là AI được xử lý hoàn toàn tại thiết bị — không cần internet để phát hiện té ngã.

---

## Slide 5 — Tổng quan kiến trúc hệ thống (Chi tiết module) (~45s)

Hệ thống gồm 3 module chính. Thứ nhất, Module Thu thập dữ liệu — cảm biến IMU BMI160 cung cấp dữ liệu gia tốc và con quay hồi chuyển 6 trục ở 50 Hz, cảm biến MAX30102 đo nhịp tim và SpO2. Thứ hai, Module Xử lý tại Edge — vi điều khiển ESP32-S3 chạy mô hình TinyCNN trực tiếp trên chip, không phụ thuộc cloud. Thứ ba, Module Giao tiếp và Cảnh báo — BLE 5.0 kết nối thiết bị với ứng dụng Android, ứng dụng tự động thực hiện cuộc gọi khẩn cấp khi phát hiện té ngã.

---

## Slide 6 — Phương pháp đề xuất: Luồng dữ liệu (~60s)

Sơ đồ này mô tả toàn bộ luồng hoạt động của hệ thống. Bắt đầu từ người cao tuổi đeo thiết bị, dữ liệu cảm biến — gia tốc, con quay, nhịp tim, SpO2 — được thu thập liên tục và đưa vào ESP32-S3. MCU chạy mô hình Edge AI để phân tích trong thời gian thực với độ trễ thấp. Triết lý thiết kế cốt lõi là **Offline-First**: con đường cảnh báo khẩn cấp chính là Wearable → BLE → Android App → Gọi điện trực tiếp. Toàn bộ con đường này không cần kết nối internet. Khi phát hiện té ngã, ứng dụng lập tức gọi đến người thân đã cài đặt. Song song đó, khi có kết nối mạng, dữ liệu sức khỏe được đồng bộ lên MongoDB để lưu trữ lịch sử. Kiến trúc này đảm bảo cảnh báo an toàn không bao giờ bị trì hoãn bởi sự cố mạng.

---

## Slide 7 — Mô hình thiết kế thực tế: So sánh với CareFall (~60s)

Hệ thống của nhóm được xây dựng dựa trên nền tảng học thuật từ nghiên cứu CareFall của Ruiz-Garcia và cộng sự. Tuy nhiên, nhóm đã xác định những hạn chế khiến CareFall không phù hợp với triển khai nhúng thực tế. Như bảng so sánh cho thấy: CareFall dùng cửa sổ phân tích 60 giây — quá chậm cho cảnh báo khẩn cấp. Nhóm em giảm xuống còn **2 giây** để gần như phát hiện tức thời. CareFall trích xuất 88 đặc trưng thống kê thủ công — tốn tài nguyên tính toán. TinyCNN của nhóm học trực tiếp từ tensor IMU thô (100 × 6), bỏ hoàn toàn bước trích xuất đặc trưng. Mô hình CareFall khoảng 1 MB, trong khi TinyCNN của nhóm chỉ ~50 KB sau lượng tử hóa INT8 — đủ nhỏ để chạy trực tiếp trên ESP32-S3. Nói cách khác, nhóm đã thích nghi hướng đi của CareFall thành một hệ thống triển khai thực tế, nhẹ và hoạt động offline.

---

## Slide 8 — Dataset & Pipeline Huấn luyện: Phân phối dữ liệu (~45s)

Nhóm sử dụng bộ dữ liệu HR-IMU gồm 21 đối tượng thực nghiệm với 19 kịch bản — 6 loại té ngã và 9 hoạt động thường ngày. Bộ dữ liệu gốc có mất cân bằng lớp nghiêm trọng: 1.628 cửa sổ fall so với 5.468 cửa sổ non-fall — tỷ lệ khoảng 1:3,4. Để tránh model bị lệch về phía non-fall, nhóm thực hiện undersampling để cân bằng về tỷ lệ 1:1, thu được 1.628 cửa sổ mỗi lớp và tổng 3.256 mẫu huấn luyện. Sự cân bằng này là yếu tố then chốt để đạt được độ nhạy cao trong bối cảnh an toàn y tế.

---

## Slide 9 — Dataset & Pipeline Huấn luyện: Cấu hình (~45s)

Model được huấn luyện với các siêu tham số được lựa chọn cẩn thận. Nhóm dùng optimizer Adam với learning rate 1e-3 — được chọn sau khi thử 1e-2 bị dao động mạnh và 1e-4 hội tụ quá chậm. Hàm mất mát Binary Cross-Entropy là lựa chọn chuẩn cho phân loại nhị phân kết hợp với Sigmoid ở output. Batch size 32 cho gradient ổn định nhất sau khi thử 16 và 64. Tối đa 60 epoch với Early Stopping patience 10, vì learning curve cho thấy model hội tụ ở epoch 35–45. Và quan trọng là lưu checkpoint có validation loss thấp nhất — không phải epoch cuối — để tránh overfitting.

---

## Slide 10 — Kiến trúc Model: TinyCNN (~60s)

Sơ đồ này thể hiện kiến trúc từng lớp của TinyCNN. Đầu vào là tensor (100, 6) — 100 mẫu tương đương 2 giây dữ liệu IMU 6 trục ở 50Hz. Lớp Normalization chuẩn hóa đầu vào về cùng thang đo — 13 tham số. Conv1D đầu tiên với 16 filter, kernel size 3 trích xuất các pattern chuyển động cục bộ — 304 tham số. MaxPooling1D giảm chiều thời gian từ 100 xuống 50, giữ lại tín hiệu mạnh nhất và loại nhiễu. Conv1D thứ hai với 32 filter học các pattern cấp cao hơn — 1.568 tham số. Global Average Pooling nén toàn bộ chuỗi thành vector 32 chiều — đây là bước then chốt giúp model đủ nhỏ để triển khai trên MCU. Cuối cùng Dense layer và Sigmoid cho ra xác suất té ngã. Tổng cộng ~2.974 tham số, kích thước 10,96 KB sau lượng tử hóa INT8 — rất nhỏ so với ngưỡng yêu cầu 500 KB.

---

## Slide 11 — Đánh giá Model: Tối ưu Threshold (~60s)

Biểu đồ này thể hiện phân tích quyết định để chọn threshold phân loại. Đường xanh lá là Recall, đường xanh dương là F1-score, đường đỏ là False Alarm Rate. Nhóm quan sát thấy Recall duy trì ổn định trên 98% trong dải threshold 0,30 đến 0,70. False Alarm Rate giảm đáng kể khi threshold tăng. Nhóm chọn **0,50** là điểm cân bằng tối ưu. Tại ngưỡng này, model duy trì Recall gần đỉnh 98,36% trong khi False Alarm Rate bắt đầu giảm rõ rệt. Chọn threshold thấp hơn không cải thiện thêm Recall nhưng làm tăng đột biến cảnh báo nhầm. Chọn cao hơn giảm cảnh báo nhầm nhưng có nguy cơ bỏ sót té ngã thật — điều không thể chấp nhận trong ứng dụng an toàn sinh mạng. Chi phí của một cú ngã bị bỏ sót luôn lớn hơn nhiều so với một cảnh báo nhầm.

---

## Slide 12 — Đánh giá Model: Confusion Matrix (~45s)

Confusion Matrix xác nhận hiệu suất của model trên tập test. Trong 244 trường hợp té ngã thực tế, model phát hiện đúng 240 và chỉ bỏ sót 4 — tỷ lệ bỏ sót 1,64%, nằm trong mục tiêu đặt ra là dưới 2%. Điểm yếu hiện tại nằm ở phía non-fall: 41 trong số 245 trường hợp không té ngã bị báo nhầm là té ngã, tạo ra False Alarm Rate 16,73% — chưa đạt mục tiêu 10%. Nhóm đã lên kế hoạch xử lý vấn đề này ở giai đoạn cuối bằng cơ chế "consecutive window validation" — yêu cầu nhiều cửa sổ liên tiếp đều dự đoán là fall trước khi kích hoạt cảnh báo, qua đó lọc bỏ các false positive đơn lẻ.

---

## Slide 13 — Ứng dụng Mobile: Giao diện chính (~45s)

Ứng dụng Android đóng vai trò là local gateway và giao diện người dùng. Như hình minh họa, ứng dụng gồm: màn hình đăng nhập, màn hình chọn vai trò — Wearer (người đeo) hoặc Caregiver (người chăm sóc), màn hình home hiển thị nhịp tim và SpO2 thời gian thực, và quan trọng nhất là màn hình SOS khẩn cấp. Khi phát hiện té ngã, màn hình này hiện ra với đồng hồ đếm ngược 15 giây. Người dùng có thể nhấn "I'm Safe" để hủy nếu là cảnh báo nhầm, hoặc nhấn "Call for Help" — hoặc không làm gì, ứng dụng sẽ tự động gọi đến người thân sau khi đếm ngược kết thúc. Thiết kế này đảm bảo người dùng còn tỉnh táo có thể hủy cảnh báo nhầm, trong khi người bất tỉnh vẫn được trợ giúp ngay lập tức.

---

## Slide 14 — Ứng dụng Mobile: Theo dõi sức khỏe (~30s)

Tab Health cung cấp theo dõi chi tiết các chỉ số sinh tồn. Người dùng có thể xem xu hướng Nhịp tim và SpO2 theo 3 chế độ: Live, 1 giờ, và 24 giờ, kèm theo giá trị trung bình, thấp nhất và cao nhất. Ứng dụng cũng đưa ra hướng dẫn sức khỏe — ví dụ cảnh báo khi SpO2 dưới 95%. Tab History ghi lại toàn bộ sự kiện bao gồm phát hiện té ngã, mất kết nối thiết bị, pin yếu, cùng trạng thái xử lý.

---

## Slide 15 — Đóng góp cá nhân (~30s)

Đây là bảng phân công nhiệm vụ của nhóm. Các task 1 đến 8 đã hoàn thành đúng tiến độ. Diễn phụ trách pipeline AI — thu thập dataset, thiết kế và huấn luyện model, tối ưu hóa cho edge. Tiến phụ trách phát triển ứng dụng mobile và thiết kế PCB. Task 9 — lắp ráp PCB — đang trong quá trình thực hiện. Các task còn lại bao gồm tích hợp firmware, kiểm thử hệ thống và thiết kế vỏ 3D sẽ được thực hiện trong các giai đoạn tiếp theo.

---

## Slide 16 — Thiết kế PCB: Schematic (~30s)

PCB tùy chỉnh tích hợp toàn bộ các linh kiện trên một board duy nhất. Schematic bao gồm ESP32-S3, cảm biến BMI160, cảm biến MAX30102, mạch quản lý pin và sạc, bộ điều áp LDO 3,3V, cổng USB-C để sạc và nạp firmware, LED RGB hiển thị trạng thái, và đầu nối anten ngoài để tối ưu phạm vi BLE.

---

## Slide 17 — Thiết kế PCB: Layout (~30s)

PCB được thiết kế trong kích thước 32 × 40 mm — đủ nhỏ để tích hợp vào vòng đeo tay. Bản render 3D xác nhận không có xung đột linh kiện. Các nguyên tắc thiết kế quan trọng bao gồm: đặt BMI160 và MAX30102 sát ESP32-S3 để giảm thiểu độ dài đường I2C và nhiễu điện từ EMI, và sử dụng ground plane trên cả hai lớp để đảm bảo chất lượng tín hiệu và tản nhiệt trong quá trình suy luận AI.

---

## Slide 20 — Demo Ứng dụng (~20s)

Tại đây nhóm em xin được thực hiện demo trực tiếp ứng dụng Android, bao gồm kết nối BLE với thiết bị wearable, theo dõi nhịp tim và SpO2 thời gian thực, và luồng cảnh báo khi phát hiện té ngã.

---

## Slide 21 — Kế hoạch tương lai (~30s)

Nhìn về phía trước, các nhiệm vụ còn lại đến milestone cuối bao gồm: hoàn thiện firmware tích hợp driver cảm biến và deploy TFLite model trước 25/05; tích hợp toàn hệ thống firmware + phần cứng + BLE + app trước 31/05; thiết kế vỏ 3D-printed trước 10/06; và kiểm thử, đánh giá hiệu năng toàn hệ thống trước 20/06. Mục tiêu kỹ thuật trọng tâm là giảm False Alarm Rate từ 16,73% xuống dưới 10% thông qua cơ chế xác nhận cửa sổ liên tiếp, trong khi duy trì Recall trên 95%.

---

## Slide 22 — Cảm ơn (~10s)

Trên đây là toàn bộ nội dung báo cáo M2 của nhóm em. Cảm ơn thầy cô và hội đồng đã lắng nghe. Nhóm em sẵn sàng giải đáp các câu hỏi.

---

*Tổng thời gian ước tính: ~12–15 phút*
