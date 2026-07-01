Dưới đây là mẫu **README** để miêu tả cách bố trí dữ liệu cho dự án của bạn. Bạn có thể sử dụng và chỉnh sửa theo yêu cầu của mình.

### **README - Bố trí Dữ liệu**

````markdown
# Dự án Giám sát Sức khỏe Người Cao Tuổi (Elderly Health Monitoring)

## Mục tiêu

Mục tiêu của dự án là xây dựng một hệ thống giám sát sức khỏe cho người cao tuổi thông qua cảm biến đeo trên người. Dữ liệu từ cảm biến được gửi lên MongoDB Atlas để phân tích và cảnh báo người dùng về các vấn đề sức khỏe như nhịp tim cao, SpO2 thấp, v.v.

## Cấu trúc Dữ liệu trong MongoDB

Dữ liệu sẽ được lưu trữ trong một **MongoDB Atlas cluster**. Cấu trúc dữ liệu được chia thành các **document** trong các **collection** riêng biệt, mỗi collection phục vụ một mục đích khác nhau.

### **1. Cấu trúc Collection `sensor_readings_new`**

Dữ liệu được lưu trữ trong collection **`sensor_readings_new`** với các trường sau:

```json
{
  "_id": ObjectId("..."),
  "device_id": "wristband_001",
  "user_id": "elder_001",
  "timestamp": "2026-03-19T16:00:00Z",
  "heart_rate": [
    {"timestamp": "2026-03-19T16:00:00Z", "value": 80},
    {"timestamp": "2026-03-19T16:00:10Z", "value": 87},
    ...
  ],
  "spo2": [
    {"timestamp": "2026-03-19T16:00:00Z", "value": 96},
    {"timestamp": "2026-03-19T16:00:10Z", "value": 95},
    ...
  ],
  "battery": 80
}
````

* **`_id`**: Được MongoDB tự động tạo ra khi insert dữ liệu.
* **`device_id`**: Mã thiết bị cảm biến (ví dụ: "wristband_001").
* **`user_id`**: Mã người dùng (ví dụ: "elder_001").
* **`timestamp`**: Thời gian gửi dữ liệu, dạng UTC.
* **`heart_rate`**: Mảng chứa các giá trị nhịp tim, mỗi giá trị đi kèm với **timestamp** riêng.
* **`spo2`**: Mảng chứa các giá trị SpO2, mỗi giá trị đi kèm với **timestamp** riêng.
* **`battery`**: Mức pin của thiết bị cảm biến.

### **2. Cấu trúc Collection `alerts`**

Dữ liệu cảnh báo được lưu trong collection **`alerts`**, chứa thông tin cảnh báo khi các chỉ số như nhịp tim hoặc SpO2 vượt ngưỡng:

```json
{
  "_id": ObjectId("..."),
  "device_id": "wristband_001",
  "user_id": "elder_001",
  "timestamp": "2026-03-19T16:00:10Z",
  "type": "low_spo2",
  "message": "SpO2 thấp nguy hiểm"
}
```

* **`_id`**: Được MongoDB tự động tạo ra khi insert dữ liệu.
* **`device_id`**: Mã thiết bị cảm biến (ví dụ: "wristband_001").
* **`user_id`**: Mã người dùng (ví dụ: "elder_001").
* **`timestamp`**: Thời gian cảnh báo được gửi, dạng UTC.
* **`type`**: Loại cảnh báo (ví dụ: "low_spo2", "high_heart_rate").
* **`message`**: Nội dung của cảnh báo (ví dụ: "SpO2 thấp nguy hiểm").

### **3. Tạo Dữ liệu**

Dữ liệu được tạo ra mô phỏng các giá trị nhịp tim (**heart_rate**), SpO2 (**spo2**), và mức pin (**battery**) mỗi **10 giây** trong khoảng thời gian **10 phút** (tương đương với 60 giá trị cho mỗi cảm biến).

* **Heart Rate**: Mảng chứa 60 giá trị, mỗi giá trị là nhịp tim được đo trong khoảng từ **60 đến 120**.
* **SpO2**: Mảng chứa 60 giá trị, mỗi giá trị là mức SpO2 được đo trong khoảng từ **92 đến 100**.
* **Battery**: Mức pin của thiết bị được tạo ngẫu nhiên trong khoảng từ **20% đến 100%**.

### **4. Cập nhật với Timestamp**

Mỗi giá trị trong mảng **heart_rate** và **spo2** sẽ đi kèm với **timestamp** tương ứng (cách nhau 10 giây).

Ví dụ:

```json
{
  "heart_rate": [
    {"timestamp": "2026-03-19T16:00:00Z", "value": 80},
    {"timestamp": "2026-03-19T16:00:10Z", "value": 87},
    ...
  ],
  "spo2": [
    {"timestamp": "2026-03-19T16:00:00Z", "value": 96},
    {"timestamp": "2026-03-19T16:00:10Z", "value": 95},
    ...
  ]
}
```

### **5. Quy trình Gửi Dữ liệu**

1. **Mỗi 10 giây**, hệ thống sẽ gửi một gói dữ liệu chứa các giá trị mới cho **heart_rate** và **spo2** cùng với **timestamp**.
2. Dữ liệu sẽ được **insert vào collection `sensor_readings_new`**.
3. Nếu có giá trị bất thường (như nhịp tim quá cao hoặc SpO2 quá thấp), một **cảnh báo** sẽ được gửi vào collection `alerts`.

---

## Cách Vẽ Biểu Đồ

Với cấu trúc này, bạn có thể dễ dàng **vẽ biểu đồ** trên **web** với trục X là **timestamp** và trục Y là **giá trị heart_rate hoặc spo2**. Các công cụ như **Plotly**, **D3.js**, hoặc **Matplotlib** có thể sử dụng dữ liệu này để tạo ra biểu đồ thời gian.

### Ví dụ sử dụng Plotly (Python):

```python
import plotly.express as px
import pandas as pd

# Giả sử dữ liệu đã được lấy từ MongoDB và chuyển thành DataFrame
df = pd.DataFrame({
    "timestamp": ["2026-03-19T16:00:00Z", "2026-03-19T16:00:10Z", ...],
    "heart_rate": [80, 87, ...]
})

# Vẽ biểu đồ
fig = px.line(df, x='timestamp', y='heart_rate', title='Nhịp Tim Theo Thời Gian')
fig.show()
```

---

### **Tổng Kết**

Dữ liệu trong dự án này được tổ chức để dễ dàng truy vấn và vẽ biểu đồ theo **timestamp**, giúp bạn theo dõi các thay đổi của cảm biến theo thời gian. Với cách tổ chức này, bạn có thể dễ dàng mở rộng và sử dụng dữ liệu cho các phân tích và cảnh báo trong tương lai.

---

Chúc bạn thành công với dự án! Nếu cần thêm thông tin hoặc hỗ trợ, đừng ngần ngại yêu cầu.
