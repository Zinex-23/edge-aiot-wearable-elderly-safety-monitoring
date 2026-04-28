# Kịch Bản Thuyết Trình Đồ Án (Capstone Presentation Script)

**Chủ đề:** So sánh và Đánh giá Mô hình AIFD của Đồ án với Nghiên cứu Học thuật (CareFall)
**Mục tiêu:** Chứng minh cơ sở khoa học và sự vượt trội trong thiết kế hệ thống Nhúng (Embedded/Edge AI) của dự án đồ án.

---

### [Slide: Nhắc đến Cơ sở lý thuyết - Baseline]
*(Hiển thị Tên bài báo "CareFall" và khái niệm Phương pháp Học máy kết hợp 6 trục)*

**🗣️ Lời dẫn:**
> Dạ kính thưa Hội Đồng, 
> Để xây dựng một hệ thống cảnh báo té ngã bằng thiết bị đeo (Wearable Edge AI), nhóm chúng em đã tiến hành đối chiếu với các nghiên cứu uy tín thuộc lĩnh vực này. Nổi bật nhất là công trình nghiên cứu hệ thống **CareFall** mới đây. 
> 
> Nhóm tác giả của bài báo này đã khẳng định được một luận điểm khoa học quan trọng: Việc **hợp nhất dữ liệu cảm biến 6 chiều** – bao gồm 3 trục Gia tốc kế (Accel) và 3 trục Con quay hồi chuyển (Gyro) – kết hợp cùng **Trí tuệ Nhân tạo (AI/ML)** sẽ giúp triệt tiêu đi các rủi ro "Báo Động Giả" vốn là căn bệnh kinh niên của hệ thống đo Ngưỡng gia tốc cơ bản ngày xưa.

---

### [Slide: Phân tích Lỗ hổng và Giới hạn Thực tế]
*(Hiển thị 2 gạch đầu dòng: "Tính toán trích xuất đặc trưng cồng kềnh" và "Độ trễ thời gian 1 Phút")*

**🗣️ Lời dẫn:**
> Tuy nhiên, khi nhìn từ lăng kính của Kỹ thuật hệ thống Nhúng (Embedded Systems), mô hình vĩ mô này để lộ ra những thiết sót chết người ngăn cản chúng đi vào thực tiễn:
> 
> *Thứ nhất*, thuật toán Machine Learning của họ đòi hỏi vi điều khiển phải ngồi **trích xuất tính toán thủ công 88 Đặc trưng Thống kê** cho mỗi một bản ghi. Rất tốn kém tài nguyên tính toán!
>
> *Thứ hai*, nghiêm trọng hơn, thiết kế của bài báo quy định phải gom một Cửa sổ thời gian (Time Window) dài đến **1 phút** mới đưa ra chẩn đoán. Trong y tế cứu hộ, độ trễ 1 phút có thể đã cướp đi tính mạng hoặc thời gian vàng của người cao tuổi.

---

### [Slide: Cấu trúc Giải pháp của Đồ Án]
*(Hiển thị Sơ đồ quy trình: Dữ liệu thô 6 trục -> Tần số 50Hz & Cửa sổ 2s -> Mạng TinyCNN 1D -> Dự đoán)*

**🗣️ Lời dẫn:**
> Để lấp đầy khoảng trống thực tiễn đó, giải pháp của nhóm em ứng dụng trực tiếp triết lý **TinyML (Học Máy Cấp Vi Mô)** để nhúng vào bo mạch ESP32. Chúng em tinh giản hoàn toàn quy trình xử lý cồng kềnh thành một đường ống siêu tốc:
> 
> Chúng em **đẩy thẳng ma trận cảm biến thô (100, 6)** xuyên qua mạng nơ-ron học sâu tích chập 1 chiều **(1D-CNN / TinyCNN)**. Bản thân quy luật CNN sẽ nội suy và chắt lọc tín hiệu mà không cần trích xuất toán học thủ công, giải cứu vi điều khiển khỏi sự quá tải.
> 
> Hơn thế nữa, hệ thống được nhóm đẩy tần số lên mức **50Hz** (siêu mượt) nhưng thu gom Cửa sổ phản ứng lại chỉ còn đúng **2 Giây**. Nhờ vậy, ngay trong khoảnh khắc người bệnh chạm đất, vi điều khiển kích hoạt cơ chế báo cháy khẩn cấp tắp lự theo chuẩn **Thời Gian Thực tuyệt đối (Real-time)**.

---

### [Slide: Kết luận Báo cáo]
*(Hiển thị các chỉ số: Recall: 98.36% / Memory Footprint Mức cực thấp / ESP32-S3 Board)*

**🗣️ Lời dẫn:**
> Kết luận lại, đồ án của em giải quyết được "Sự đánh đổi kép" (Trade-off) khó nhất và kinh điển nhất trong kỹ thuật thiết bị IoT: 
> 
> Đó là **Scale-down** (cắt giảm mạnh mẽ sự cồng kềnh) để nhét vừa phần cứng siêu rẻ, nhưng vẫn giữ được **Độ Nhạy Phản Xạ Cực Đỉnh** (Recall chốt hạ ở mức gần 99%). Giúp chiếc máy trở thành một chiến thần y tế đắc lực, tự chủ hoàn toàn sự sống của mạch vi điều khiển tại biên (Edge Computing). 
> 
> Cảm ơn Hội đồng đã lắng nghe!
