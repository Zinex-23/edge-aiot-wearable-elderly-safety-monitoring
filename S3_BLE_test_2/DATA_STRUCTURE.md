# Cấu trúc dữ liệu truyền BLE (ESP32-S3 -> Client)

Tài liệu này chi tiết hóa các định dạng gói tin được truyền từ thiết bị ESP32-S3 đến Client (ứng dụng Android hoặc Python script) thông qua giao thức BLE.

## 1. Thông tin dịch vụ (Service & Characteristics)

Tất cả dữ liệu được truyền qua một Service duy nhất:
- **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`

Các Đặc tính (Characteristics):
- **Cảnh báo ngã (Status)**: `beb5483e-36e1-4688-b7f5-ea07361b26a8` (Notify)
- **Dữ liệu sinh hiệu (Vitals)**: `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` (Notify)
- **Điều khiển (Control)**: `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` (Read/Write)

---

## 2. Gói tin Cảnh báo (ALERT)

Gói tin này chỉ được gửi khi thiết bị phát hiện sự kiện ngã (fall).

### Định dạng
```text
ALERT,<sequence>,<timestamp_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
```

### Các trường dữ liệu
- `ALERT`: Nhãn nhận diện gói tin.
- `sequence`: Số thứ tự gói tin (tăng dần).
- `timestamp_sec`: Thời điểm phát hiện (Unix timestamp UTC).
- `fall`: Nhãn sự kiện.
- `status_code`: Hiện tại mặc định là `1`.
- `fall_prob`: Xác suất ngã (0.000 - 1.000).
- `non_fall_prob`: Xác suất không ngã (0.000 - 1.000).

### Ví dụ
`ALERT,15,1776730125,fall,1,0.895,0.105`

---

## 3. Gói tin Sinh hiệu theo Batch (BATCH)

Dữ liệu nhịp tim (HR) và nồng độ oxy (SpO2) được gom lại và gửi mỗi 25 giây một lần (chứa 5 mẫu, mỗi mẫu cách nhau 5 giây).

### Định dạng
```text
BATCH,<sequence>,<hr_list>,<spo2_list>,<ts_list>
```

### Các trường dữ liệu
- `BATCH`: Nhãn nhận diện gói tin.
- `sequence`: Số thứ tự batch (tăng dần).
- `hr_list`: Danh sách 5 giá trị nhịp tim, cách nhau bởi dấu `|`.
- `spo2_list`: Danh sách 5 giá trị SpO2, cách nhau bởi dấu `|`.
- `ts_list`: Danh sách 5 mốc thời gian (Unix timestamp UTC) tương ứng, cách nhau bởi dấu `|`.

### Ví dụ
`BATCH,12,72|75|73|76|74,98|97|98|98|97,1776730100|1776730105|1776730110|1776730115|1776730120`

> [!NOTE]
> Giá trị `255` trong `hr_list` hoặc `spo2_list` có nghĩa là dữ liệu không hợp lệ hoặc chưa có cảm biến.

---

## 4. Giao thức Bắt tay (READY Handshake)

Khi Client kết nối, ESP32 sẽ không gửi ngay dữ liệu trong hàng đợi (backlog) cho đến khi nhận được lệnh `READY`.

1. **Client connect** và **Subscribe** vào các Notify characteristics.
2. **Client Write** chuỗi `READY` vào Đặc tính Điều khiển (Control).
3. **ESP32** sẽ đẩy (flush) toàn bộ dữ liệu cũ trong hàng đợi ra theo thứ tự: Các gói `ALERT` trước, sau đó đến các gói `BATCH`.

| Lệnh | Mô tả | ESP32 Phản hồi (ACK) |
| :--- | :--- | :--- |
| `READY` | Thông báo client đã sẵn sàng nhận notify | `ACK:READY` |
| `PING` | Kiểm tra kết nối | `ACK:PING` |
