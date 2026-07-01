# ACCEPTANCE TEST — Field Test Sheet
## AI Fall Detection Wearable (AIFD) — ESP32-S3

> **Mục đích:** Kiểm tra nghiệm thu thực tế. In tờ này, mang ra hiện trường, điền tay.
> **Firmware:** `S3_AIFD_V1` | **App:** AIFD Android
> **Ngày test:** ________________ | **Người test:** ________________ | **Địa điểm:** ________________

---

### Trạng thái LED thiết bị (tham khảo khi test)

| Màu & Kiểu | Ý nghĩa |
|---|---|
| 🔵 Xanh dương nhấp nháy chậm (500ms) | Đang khởi động |
| 🟡 Vàng nhấp nháy chậm (500ms) | Chưa kết nối điện thoại |
| 🟢 Xanh lá sáng liên tục | Đã kết nối BLE |
| 🟡 Vàng nhấp nháy nhanh (250ms) | Mất kết nối / Lỗi cảm biến |
| 🔴 Đỏ nhấp nháy chậm (500ms) | Đang theo dõi ngã (chờ nằm im) |
| 🔴 Đỏ nhấp nháy nhanh (250ms) + **CÒI** | **Xác nhận ngã — đang báo động** |

---

## III.1 — Kiểm tra phát hiện ngã (AT_FALL_DETECT)

> **Yêu cầu trước khi test:** Thiết bị đeo ở cổ tay. LED xanh lá (đã kết nối app). Thực hiện **≥ 5 lần** mỗi kịch bản. Dùng đệm mềm để an toàn.

| Test ID | Kịch bản | Cách thực hiện | Phản ứng thiết bị ✓ | Phản ứng App ✓ | Pass | Fail | Ghi chú |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| `AT_FALL_01` | **Ngã sấp** | Ngã về phía trước xuống đệm, giả lập vấp ngã. Nằm yên sau khi ngã ≥ 5s. | 1. LED chuyển → 🔴 chậm (~1s sau ngã) 2. Sau 5–15s nằm yên: LED → 🔴 nhanh + còi kêu | FallAlertScreen xuất hiện trong < 5s. Countdown 15s hiện trên màn hình. | ☐ | ☐ | |
| `AT_FALL_02` | **Ngã ngửa** | Ngã về phía sau (mô phỏng trơn trượt). Nằm yên sau khi ngã ≥ 5s. | 1. LED chuyển → 🔴 chậm (~1s sau ngã) 2. Sau 5–15s nằm yên: LED → 🔴 nhanh + còi kêu | FallAlertScreen xuất hiện trong < 5s. Countdown 15s hiện trên màn hình. | ☐ | ☐ | |
| `AT_FALL_03` | **Ngã sang bên** | Ngã nghiêng sang trái hoặc phải. Nằm yên sau khi ngã ≥ 5s. | 1. LED chuyển → 🔴 chậm (~1s sau ngã) 2. Sau 5–15s nằm yên: LED → 🔴 nhanh + còi kêu | FallAlertScreen xuất hiện trong < 5s. Countdown 15s hiện trên màn hình. | ☐ | ☐ | |
| `AT_FALL_04` | **Ngã từ từ** | Ngã dần xuống chậm (giả lập xỉu / yếu sức), không có cú đập mạnh. Nằm yên ≥ 5s. | 1. LED chuyển → 🔴 chậm (có thể trễ hơn 1–2s so với ngã mạnh) 2. Sau 5–15s nằm yên: LED → 🔴 nhanh + còi kêu | FallAlertScreen xuất hiện trong < 5s kể từ khi còi kêu. | ☐ | ☐ | |
| `AT_FALL_05` | **Ngã sau khi đứng dậy** | Đứng dậy từ ghế rồi ngã ngay sau đó (hạ huyết áp tư thế). Nằm yên ≥ 5s. | 1. LED chuyển → 🔴 chậm (~1–2s sau ngã) 2. Sau 5–15s nằm yên: LED → 🔴 nhanh + còi kêu | FallAlertScreen xuất hiện trong < 5s kể từ khi còi kêu. | ☐ | ☐ | |

**Kết quả nhóm AT_FALL_DETECT:** _____ / 5 PASS

---

## III.2 — Kiểm tra không báo nhầm ADL (AT_ADL_REJECT)

> **Yêu cầu:** Thiết bị đeo ở cổ tay. LED xanh lá (đã kết nối). Thực hiện **≥ 10 lần** mỗi kịch bản.
> **Tiêu chí thành công:** LED vẫn giữ nguyên 🟢 xanh lá liên tục. Không có còi. App không hiện FallAlertScreen.

| Test ID | Kịch bản | Cách thực hiện | Phản ứng thiết bị ✓ (không được thay đổi) | Phản ứng App ✓ (không được thay đổi) | Pass | Fail | Ghi chú |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| `AT_ADL_01` | **Ngồi / Đứng nhanh** | Ngồi xuống ghế nhanh và đứng dậy nhanh liên tục 10 lần. | LED giữ nguyên 🟢 xanh lá liên tục. Không có còi. | Không có FallAlertScreen. Màn hình Home bình thường. | ☐ | ☐ | |
| `AT_ADL_02` | **Cúi nhặt đồ** | Cúi người xuống nhặt vật dưới sàn rồi đứng thẳng, lặp lại 10 lần. | LED giữ nguyên 🟢 xanh lá liên tục. Không có còi. | Không có FallAlertScreen. Màn hình Home bình thường. | ☐ | ☐ | |
| `AT_ADL_03` | **Vận động mạnh** | Đi bộ nhanh, vẫy tay mạnh, xoay người, nhảy nhẹ trong 2 phút liên tục. | LED giữ nguyên 🟢 xanh lá liên tục. Không có còi. | Không có FallAlertScreen. Màn hình Home bình thường. | ☐ | ☐ | |
| `AT_ADL_04` | **Leo / Xuống cầu thang** | Đi lên và xuống 1 tầng cầu thang 5 lần liên tiếp. | LED giữ nguyên 🟢 xanh lá liên tục. Không có còi. | Không có FallAlertScreen. Màn hình Home bình thường. | ☐ | ☐ | |
| `AT_ADL_05` | **Chuỗi 5 ADL liên tiếp** | Thực hiện liên tiếp không nghỉ: đứng dậy nhanh → đi bộ nhanh → cúi người → leo cầu thang → nhảy nhẹ. Lặp lại 10 lần. | LED giữ nguyên 🟢 xanh lá liên tục. Không có còi. Nếu có LED 🔴 chậm thoáng qua nhưng không ra còi → vẫn PASS. | Không có FallAlertScreen. FAR (False Alarm Rate) ≤ 10% (≤ 5/50 lần thử). | ☐ | ☐ | FAR thực tế: ___/50 |

**Kết quả nhóm AT_ADL_REJECT:** _____ / 5 PASS

---

## III.3 — Kiểm tra cảnh báo khẩn cấp (AT_EMERGENCY)

> **Yêu cầu:** Cần 2 người (Wearer + Caregiver) hoặc 2 điện thoại. Số Caregiver đã được cấu hình trong app Settings.

| Test ID | Kịch bản | Cách thực hiện | Phản ứng thiết bị ✓ | Phản ứng App ✓ | Pass | Fail | Ghi chú |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| `AT_EMG_01` | **Auto-call sau 15s** | Trigger ngã (hoặc nhấn nút trên thiết bị). Sau khi FallAlertScreen xuất hiện, **không chạm vào điện thoại**. Chờ 15s. | LED 🔴 nhanh + còi kêu suốt trong quá trình đếm ngược. Còi tắt sau khi gọi xong. | FallAlertScreen countdown 15→0. Điện thoại Caregiver **đổ chuông** trong vòng 3s sau khi đếm ngược hết. | ☐ | ☐ | Đo thời gian từ 0 đến chuông Caregiver: _____s |
| `AT_EMG_02` | **Hủy alert (Tôi ổn)** | Trigger ngã. Khi FallAlertScreen xuất hiện, nhấn nút **"Tôi ổn"** hoặc nhấn nút vật lý trên thiết bị trong vòng 15s. | LED 🔴 nhanh + còi → **tắt còi ngay**, LED quay về 🟢 xanh lá. | Countdown dừng lại. Màn hình quay về Home. Điện thoại Caregiver **không đổ chuông**. | ☐ | ☐ | |
| `AT_EMG_03` | **Gọi thủ công (SOS)** | Không cần ngã. Nhấn nút SOS trên HomeScreen của app. | LED chuyển → 🔴 nhanh + còi kêu ngay. | Gọi điện **ngay lập tức** đến số Caregiver (không đợi 15s). | ☐ | ☐ | |
| `AT_EMG_04` | **Đo độ trễ E2E** | Thực hiện ngã mô phỏng. Bấm đồng hồ từ lúc chạm đất đến khi điện thoại Caregiver đổ chuông. Lặp 5 lần. | LED 🔴 nhanh + còi trong vòng < 20s sau ngã. | Điện thoại Caregiver đổ chuông. **Tổng thời gian < 25s** (bao gồm 15s countdown + gọi). | ☐ | ☐ | Lần 1: ___s  Lần 2: ___s  Lần 3: ___s  Lần 4: ___s  Lần 5: ___s  TB: ___s |

**Kết quả nhóm AT_EMERGENCY:** _____ / 4 PASS

---

## III.4 — Kiểm tra giám sát liên tục (AT_CONTINUOUS)

> **Yêu cầu:** Điện thoại và thiết bị hoạt động liên tục. Ghi nhận thời gian bắt đầu.

| Test ID | Kịch bản | Cách thực hiện | Phản ứng thiết bị ✓ | Phản ứng App ✓ | Pass | Fail | Ghi chú |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| `AT_CON_01` | **Giám sát 8 giờ** | Đeo thiết bị và để app chạy liên tục 8 giờ. Hoạt động sinh hoạt bình thường. Kiểm tra định kỳ mỗi 30 phút. | LED 🟢 xanh lá liên tục suốt 8 giờ. Không tự chuyển sang 🟡 vàng (mất kết nối). | App không crash. HR/SpO2 cập nhật mỗi 25s. Không có FallAlertScreen tự xuất hiện. | ☐ | ☐ | Bắt đầu: ___:___ Kết thúc: ___:___ Số lần mất kết nối: ___ |
| `AT_CON_02` | **HR/SpO2 realtime** | Đặt ngón tay lên cảm biến MAX30102. Quan sát màn hình Home trong 5 phút. | LED 🟢 xanh lá. Không thay đổi. | HR và SpO2 cập nhật mỗi 25s. Giá trị thay đổi khi hít thở sâu. Không có giá trị "--" (255) kéo dài. | ☐ | ☐ | HR range: ___–___ SpO2 range: ___–___ |
| `AT_CON_03` | **Auto-reconnect** | Tắt Bluetooth điện thoại. Đợi 30 giây. Bật Bluetooth lại. Bấm đồng hồ. | LED: 🟢 → 🟡 nhanh (3s) → 🟡 chậm (đang tìm) → 🟢 (kết nối lại). | App tự kết nối lại. Data stream tiếp tục. **Thời gian reconnect < 60s.** | ☐ | ☐ | Thời gian reconnect: _____s |
| `AT_CON_04` | **Offline fall logging** | Tắt WiFi + 4G. Trigger ngã (nhấn nút thiết bị). Bật WiFi lại sau 2 phút. | LED 🔴 nhanh + còi → tắt sau khi nhấn nút SAFE. | Sự kiện ngã xuất hiện trong History app (offline). Sau khi bật WiFi: event tự sync lên Cloud. Kiểm tra web portal / API để xác nhận. | ☐ | ☐ | |

**Kết quả nhóm AT_CONTINUOUS:** _____ / 4 PASS

---

## III.5 — Kiểm tra điều kiện đặc biệt (AT_EDGE)

> **Yêu cầu:** Chuẩn bị đệm mềm. Một số kịch bản cần 2 người.

| Test ID | Kịch bản | Cách thực hiện | Phản ứng thiết bị ✓ | Phản ứng App ✓ | Pass | Fail | Ghi chú |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| `AT_EDGE_01` | **Ngã trong phòng tắm** | Mang thiết bị vào phòng tắm (độ ẩm cao). Mô phỏng ngã xuống đệm, nằm yên ≥ 5s. | LED 🔴 chậm → 🔴 nhanh + còi, giống test bình thường. Không có hiện tượng nhiễu loạn LED. | FallAlertScreen trong < 5s. | ☐ | ☐ | |
| `AT_EDGE_02` | **Ngã ban đêm** | Thực hiện lúc 22:00 trở đi. Khoá màn hình điện thoại ≥ 10 phút trước. Trigger ngã. | LED 🔴 nhanh + còi kêu (giống ban ngày). | Màn hình điện thoại **tự bật**. FallAlertScreen hiện **trên lockscreen** mà không cần mở khoá. | ☐ | ☐ | Thời gian test: ___:___ |
| `AT_EDGE_03` | **Pin thiết bị thấp** | Để pin thiết bị xuống < 20% (nếu có đo pin). Mô phỏng ngã, nằm yên ≥ 5s. | LED 🔴 chậm → 🔴 nhanh + còi, phản ứng bình thường. | FallAlertScreen trong < 5s. Không có delay bất thường so với pin đầy. | ☐ | ☐ | Pin tại thời điểm test: ____% |
| `AT_EDGE_04` | **Caregiver ở xa** | Caregiver ở phòng khác hoặc ngoài nhà (có internet). Trigger ngã từ phía Wearer. | LED 🔴 nhanh + còi sau khi ngã. | Điện thoại Caregiver nhận notification SOS **trong < 10s**. Điện thoại Caregiver đổ chuông sau countdown. | ☐ | ☐ | Khoảng cách Wearer–Caregiver: _____ |
| `AT_EDGE_05` | **Nhiều lần ngã liên tiếp** | Trigger ngã lần 1 → nhấn SAFE → trigger ngã lần 2 → nhấn SAFE → trigger ngã lần 3 → nhấn SAFE. Các lần cách nhau ~2 phút. | Mỗi lần: LED 🔴 nhanh + còi. Sau SAFE: LED về 🟢 xanh lá ngay. Chu kỳ lặp lại đúng 3 lần. | History app ghi **đúng 3 sự kiện** riêng biệt với timestamp khác nhau. Không có event bị mất hay trùng lặp. | ☐ | ☐ | |

**Kết quả nhóm AT_EDGE:** _____ / 5 PASS

---

## Tổng kết nghiệm thu

| Nhóm | Số kịch bản | PASS | FAIL | Chưa test | Đạt |
|:---|:---:|:---:|:---:|:---:|:---:|
| AT_FALL_DETECT — Phát hiện ngã | 5 | | | | ☐ |
| AT_ADL_REJECT — Không báo nhầm | 5 | | | | ☐ |
| AT_EMERGENCY — Cảnh báo khẩn cấp | 4 | | | | ☐ |
| AT_CONTINUOUS — Giám sát liên tục | 4 | | | | ☐ |
| AT_EDGE — Điều kiện đặc biệt | 5 | | | | ☐ |
| **Tổng** | **23** | | | | |

**Tỷ lệ PASS:** _____ / 23 = _____%

**Hệ thống đạt yêu cầu nghiệm thu:** ☐ **CÓ** &nbsp;&nbsp;&nbsp;&nbsp; ☐ **CHƯA** (cần xử lý FAIL trước khi triển khai)

---

**Xác nhận:**

| Vai trò | Họ tên | Chữ ký | Ngày |
|---|---|---|---|
| Người thực hiện test | | | |
| Người giám sát | | | |

---

*Firmware: S3_AIFD_V1 — Pipeline: BMI160 → TFLite V84 → FALL_WATCH → STILL_TIMING (5s) → ALARM*
*BLE: NimBLE no-bond, Service UUID 4fafc201, MTU 247*
