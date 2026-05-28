# Data Flow

Tài liệu này mô tả luồng dữ liệu hiện tại của firmware ESP32 trong project `S3_BLE`.

## 1. Mục tiêu thiết kế

Luồng mới được thiết kế để:

- giảm tần suất truyền BLE để tiết kiệm pin
- chỉ gửi cảnh báo ngay khi thực sự phát hiện `fall`
- gom dữ liệu HR/SpO2 thành batch thay vì gửi liên tục
- vẫn không mất dữ liệu ngắn hạn khi thiết bị nhận BLE chưa kết nối

## 2. Các loại dữ liệu

Firmware hiện xử lý 2 nhóm dữ liệu chính:

1. `Fall detection`
- nguồn: dữ liệu IMU từ BMI160
- dùng cho model phát hiện ngã
- chỉ tạo gói BLE khi kết quả là `fall`

2. `Vitals batch`
- nguồn hiện tại: dữ liệu HR và SpO2 giả lập ngẫu nhiên để test đường truyền
- về sau có thể thay bằng cảm biến thật
- được gom và gửi theo chu kỳ

## 3. Chu kỳ lấy mẫu và gửi dữ liệu

### 3.1. Fall detection

- IMU được lấy mẫu ở tần số `50 Hz`
- model chạy theo cửa sổ `100` mẫu
- khi `fallProb >= 0.40` thì coi là `fall`
- chỉ lúc đó mới tạo gói `ALERT`
- nếu là `non-fall` thì không gửi BLE alert

### 3.2. Vitals

- cứ mỗi `5 giây` lấy `1` mẫu HR/SpO2
- cứ mỗi `25 giây` tạo `1 batch`
- mỗi batch chứa đúng `5` mẫu:
  - `HR[5]`
  - `SpO2[5]`
  - `timestamp[5]`

Lý do batch có `5` mẫu:

- chu kỳ lấy mẫu là `5s`
- chu kỳ gửi là `25s`
- nên trong một chu kỳ gửi đầy đủ sẽ có `5` điểm dữ liệu

## 4. Timestamp

Timestamp trong payload hiện tại là:

- Unix timestamp theo giây
- múi giờ `UTC+0`

Điều này áp dụng cho:

- từng điểm dữ liệu trong `BATCH`
- thời điểm tạo `ALERT`

## 5. BLE payload

## 5.1. Alert packet

Chỉ gửi khi phát hiện `fall`.

Format:

```text
ALERT,<sequence>,<timestamp_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
```

Ví dụ:

```text
ALERT,7,1776730125,fall,1,0.812,0.188
```

Ý nghĩa:

- `sequence`: số thứ tự gói alert
- `timestamp_sec`: thời điểm phát hiện fall
- `fall`: nhãn sự kiện
- `status_code`: hiện tại là `1`
- `fall_prob`: xác suất ngã
- `non_fall_prob`: xác suất không ngã

## 5.2. Vitals batch packet

Format:

```text
BATCH,<sequence>,hr0|hr1|hr2|hr3|hr4,spo20|spo21|spo22|spo23|spo24,ts0|ts1|ts2|ts3|ts4
```

Ví dụ:

```text
BATCH,12,72|75|73|76|74,98|97|98|98|97,1776730100|1776730105|1776730110|1776730115|1776730120
```

Ý nghĩa:

- `sequence`: số thứ tự batch
- `hr*`: 5 mẫu heart rate
- `spo2*`: 5 mẫu SpO2
- `ts*`: timestamp UTC giây tương ứng với từng mẫu

## 6. Queue khi chưa có BLE client

Nếu tại thời điểm cần gửi mà chưa có thiết bị BLE nhận:

- firmware không bỏ dữ liệu ngay
- dữ liệu sẽ được lưu trong queue RAM nội bộ

Hiện có 2 queue riêng:

1. `fallQueue`
- lưu các gói `ALERT`

2. `vitalsQueue`
- lưu các gói `BATCH`

## 7. Khi client kết nối lại

Khi BLE client kết nối:

- firmware chưa flush ngay
- firmware chờ client subscribe notify xong
- sau đó client phải ghi lệnh `READY` vào BLE control characteristic
- chỉ khi nhận `READY`, firmware mới bắt đầu flush backlog

Thứ tự flush:

1. gửi hết `ALERT`
2. gửi hết `BATCH`

Lý do:

- alert ngã là dữ liệu ưu tiên cao hơn
- tránh tình trạng ESP gửi backlog trước khi client đã `start_notify`

## 7.1. Control handshake

Characteristic điều khiển:

- UUID: `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03`

Luồng chuẩn:

1. client connect tới ESP32
2. client subscribe `status`
3. client subscribe `vitals`
4. client write `READY`
5. ESP32 flush toàn bộ queue đang chờ

Điểm quan trọng:

- nếu không có `READY`, backlog sẽ chưa được flush
- việc này làm reconnect ổn định hơn so với flush ngay tại thời điểm `connect`

## 8. Các giới hạn hiện tại

### 8.1. HR/SpO2 đang là dữ liệu giả lập

Hiện tại firmware đang tạo:

- HR ngẫu nhiên trong khoảng hợp lý
- SpO2 ngẫu nhiên trong khoảng hợp lý

Mục đích:

- kiểm tra đường truyền BLE
- kiểm tra queue
- kiểm tra client parsing

Khi có cảm biến thật, chỉ cần thay logic lấy mẫu trong firmware, không cần đổi format truyền dữ liệu.

### 8.2. Queue có giới hạn

Queue RAM không phải vô hạn.

Nếu mất kết nối quá lâu:

- queue có thể đầy
- dữ liệu cũ nhất sẽ bị ghi đè

Điều này giúp tránh tràn RAM.

### 8.3. Chưa có ACK ở tầng ứng dụng

Hiện tại:

- firmware gửi notify BLE
- nếu client mất kết nối đúng lúc đang nhận thì vẫn có khả năng mất gói

Nói cách khác:

- đã có queue để giảm mất dữ liệu khi client offline
- nhưng chưa phải giao thức guaranteed delivery tuyệt đối

## 9. Luồng dữ liệu tổng quát

```text
BMI160 IMU -> lấy mẫu 50Hz -> model fall detection -> nếu fall -> tạo ALERT -> gửi BLE hoặc đưa vào fallQueue

HR/SpO2 source -> lấy mẫu mỗi 5s -> lưu vào bộ nhớ batch tạm -> đủ 25s -> tạo BATCH 5 điểm -> gửi BLE hoặc đưa vào vitalsQueue

BLE client kết nối -> subscribe notify -> gửi READY -> flush fallQueue trước -> flush vitalsQueue sau
```

## 10. Tóm tắt ngắn

- IMU dùng để phát hiện ngã
- chỉ `fall` mới sinh alert BLE
- HR/SpO2 lấy mẫu mỗi `5s`
- mỗi `25s` gửi `1 batch` gồm `5` điểm
- nếu chưa có client BLE thì dữ liệu được giữ trong queue RAM
- khi có client, phải subscribe xong rồi gửi `READY`
- sau `READY`, firmware mới đẩy toàn bộ backlog ra theo thứ tự ưu tiên `ALERT` rồi `BATCH`
