# Ánh Xạ Kiến Trúc Mô Hình Vào Mã Nguồn (Code Mapping)

Tài liệu này giúp bạn đối chiếu giữa **Lý thuyết** (các lớp mạng) và **Thực tế** (dòng code) trong file `train.py`.

Mô hình được xây dựng trong hàm `build_model` (Dòng 71 - 92).

---

### 1. Input Layer (Lớp đầu vào)
- **Lý thuyết**: Nhận dữ liệu thô (100 mẫu, 6 trục).
- **Mã nguồn (Dòng 74)**:
  ```python
  inputs = tf.keras.Input(shape=(100, 6), name="imu_window")
  ```
- **Giải thích**: `shape=(100, 6)` chính là thông số định nghĩa 2 giây dữ liệu (100 mẫu) và 6 kênh cảm biến.

### 2. Normalization Layer (Lớp chuẩn hóa)
- **Lý thuyết**: Đưa dữ liệu về cùng thang đo.
- **Mã nguồn (Dòng 72-73, 75)**:
  ```python
  norm = tf.keras.layers.Normalization(axis=-1, name="balanced_norm")
  norm.adapt(train_x.reshape(-1, train_x.shape[-1]))
  x = norm(inputs)
  ```
- **Giải thích**: `norm.adapt` dùng để tính toán trung bình và độ lệch chuẩn của tập train, sau đó `norm(inputs)` áp dụng công thức chuẩn hóa lên dữ liệu đầu vào.

### 3. Conv1D - Lớp Tích chập 1 (16 filters)
- **Lý thuyết**: Trích xuất đặc trưng cục bộ (kính lúp).
- **Mã nguồn (Dòng 76)**:
  ```python
  x = tf.keras.layers.Conv1D(16, 3, activation="relu", padding="same")(x)
  ```
- **Giải thích**: `16` là số bộ lọc, `3` là kích thước kính lúp (kernel size), `relu` giúp loại bỏ các giá trị âm không cần thiết.

### 4. MaxPooling1D (Giảm mẫu)
- **Lý thuyết**: Giữ tín hiệu mạnh nhất, giảm nhiễu.
- **Mã nguồn (Dòng 77)**:
  ```python
  x = tf.keras.layers.MaxPooling1D(2)(x)
  ```
- **Giải thích**: `2` có nghĩa là gom 2 điểm dữ liệu lại và chỉ lấy 1 điểm lớn nhất, giúp giảm khối lượng tính toán đi một nửa.

### 5. Conv1D - Lớp Tích chập 2 (32 filters)
- **Lý thuyết**: Trích xuất đặc trưng cấp cao.
- **Mã nguồn (Dòng 78)**:
  ```python
  x = tf.keras.layers.Conv1D(32, 3, activation="relu", padding="same")(x)
  ```
- **Giải thích**: Tiếp tục trích xuất 32 đặc trưng phức tạp hơn từ dữ liệu đã qua xử lý sơ bộ.

### 6. GlobalAveragePooling1D (Nén toàn cục)
- **Lý thuyết**: Tóm tắt dữ liệu thành bộ đặc trưng duy nhất.
- **Mã nguồn (Dòng 79)**:
  ```python
  x = tf.keras.layers.GlobalAveragePooling1D()(x)
  ```
- **Giải thích**: Đây là bước "nén" cực mạnh, chuyển từ dạng chuỗi thời gian thành một vector đặc trưng phẳng, giúp mô hình rất nhẹ.

### 7. Dense - Lớp ẩn (32 units)
- **Lý thuyết**: Suy luận logic.
- **Mã nguồn (Dòng 80)**:
  ```python
  x = tf.keras.layers.Dense(32, activation="relu")(x)
  ```
- **Giải thích**: Kết nối các đặc trưng lại để đưa ra các suy đoán trung gian trước khi quyết định cuối cùng.

### 8. Output Dense (Lớp đầu ra)
- **Lý thuyết**: Xác suất cuối cùng (Sigmoid).
- **Mã nguồn (Dòng 81)**:
  ```python
  outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="fall_prob")(x)
  ```
- **Giải thích**: `activation="sigmoid"` đảm bảo đầu ra luôn nằm trong khoảng 0 đến 1 (xác suất té ngã).

---

### Tóm tắt luồng dữ liệu (Data Flow)
`Input` -> `Chuẩn hóa` -> `Lọc đặc trưng 1` -> `Nén 1` -> `Lọc đặc trưng 2` -> `Nén toàn cục` -> `Suy luận` -> `Xác suất té ngã`
