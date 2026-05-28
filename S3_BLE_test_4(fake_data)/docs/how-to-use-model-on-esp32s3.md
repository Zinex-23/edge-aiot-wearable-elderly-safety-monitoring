# How To Use Model On ESP32-S3 With PlatformIO

## Mục tiêu

Tài liệu này hướng dẫn từng bước cách nhúng model fall detection đã huấn luyện vào `ESP32-S3 Super Mini` bằng `PlatformIO IDE` trong `VS Code`.

Model sẽ dùng:

1. `fall_detection_model.h`
2. TensorFlow Lite Micro
3. Dữ liệu IMU 6 kênh:
   - `ax`
   - `ay`
   - `az`
   - `gx`
   - `gy`
   - `gz`

## File cần dùng

Lấy các file sau từ thư mục model đã xuất:

1. `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/models/fall_detection_model.h`
2. `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/docs/esp32_deployment_notes.md`
3. `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/results/metrics_summary.txt`

Model nhúng trực tiếp lên firmware là:

- `fall_detection_model.h`

Không dùng trực tiếp:

- `best_model.keras`
- `fall_detection_model.tflite`

Lý do:

1. `.keras` chỉ dùng để train/evaluate trên máy tính
2. `.tflite` là file model trung gian
3. `.h` mới là dạng thuận tiện để biên dịch vào firmware C/C++

## Thông số model cần nhớ

### Input tensor

- Shape: `1 x 100 x 6`
- Mỗi lần suy luận cần `100` mẫu
- Mỗi mẫu có `6` đặc trưng

Thứ tự đặc trưng:

1. `ax`
2. `ay`
3. `az`
4. `gx`
5. `gy`
6. `gz`

### Tần số lấy mẫu

- `50 Hz`

### Ý nghĩa window

- `100 samples = 2 giây dữ liệu`

### Đơn vị dữ liệu đầu vào

Bạn phải đưa dữ liệu vào đúng đơn vị mà model đã học:

1. `ax, ay, az` tính theo `g`
2. `gx, gy, gz` tính theo `deg/s`

Nếu IMU của bạn trả ra:

1. `m/s^2` cho accelerometer
   - đổi sang `g` bằng cách chia `9.80665`
2. `rad/s` cho gyroscope
   - đổi sang `deg/s` bằng cách nhân `57.2957795`

### Quantization input

Model hiện là `int8`.

Thông số lượng tử hóa input:

1. `scale = 6.11098051071167`
2. `zero_point = 19`

Công thức:

```cpp
int8_t q = (int8_t)round(value / 6.11098051071167f + 19.0f);
```

Sau đó clamp trong khoảng:

```cpp
[-128, 127]
```

## Threshold stage nên chạy trước CNN

Đây là pipeline hybrid, nên không nên gọi CNN liên tục.

Threshold đang dùng:

1. `threshold_a = 1.8`
2. `threshold_g = 50.0`

Logic:

```text
candidate = (max_acc_mag > 1.8) OR (max_gyro_mag > 50.0)
```

Trong đó:

```text
A = sqrt(ax^2 + ay^2 + az^2)
G = sqrt(gx^2 + gy^2 + gz^2)
```

Nếu `candidate = false`:

- bỏ qua suy luận CNN

Nếu `candidate = true`:

- chạy TensorFlow Lite Micro

Điều này giúp:

1. giảm số lần inference
2. giảm tải CPU
3. giảm tiêu thụ điện năng

## Bước 1: Cài VS Code và PlatformIO

Nếu chưa có:

1. Cài `Visual Studio Code`
2. Mở `Extensions`
3. Tìm `PlatformIO IDE`
4. Cài extension này

Sau khi cài xong:

1. restart VS Code

## Bước 2: Tạo project PlatformIO mới

Trong VS Code:

1. mở `PlatformIO Home`
2. chọn `New Project`
3. nhập tên project, ví dụ:
   - `esp32s3_fall_detection`
4. chọn board phù hợp với ESP32-S3 Super Mini

Nếu chưa chắc board nào đúng, bắt đầu với một board ESP32-S3 phổ biến như:

1. `esp32-s3-devkitc-1`

Framework nên chọn:

1. `Arduino`

Sau đó nhấn `Finish`

## Bước 3: Cấu hình `platformio.ini`

Mở file `platformio.ini` và chỉnh tương tự:

```ini
[env:esp32-s3-devkitc-1]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
monitor_speed = 115200
board_build.flash_mode = qio
board_build.partitions = default_8MB.csv
build_flags =
  -DCORE_DEBUG_LEVEL=0
```

Lưu ý:

1. Nếu board thực tế của bạn có profile khác, thay `board = ...` cho đúng
2. Nếu board chỉ có 4MB flash, dùng partition phù hợp 4MB
3. Nếu build báo thiếu flash/RAM, cần tối giản thư viện và tensor arena

## Bước 4: Thêm thư viện TensorFlow Lite Micro

Có 2 cách:

### Cách A: dùng thư viện có sẵn qua PlatformIO

Thử thêm vào `platformio.ini`:

```ini
lib_deps =
  tensorflow/TensorFlowLite_ESP32
```

Nếu registry không resolve ổn, chuyển sang cách B.

### Cách B: chép thư viện local

1. tạo thư mục `lib/`
2. thêm TensorFlow Lite Micro / TensorFlowLite_ESP32 phù hợp vào đó

Trong thực tế, nhiều project ESP32 chạy ổn hơn khi dùng bản thư viện local đã test.

## Bước 5: Copy model header vào project

Copy file:

- `fall_detection_model.h`

vào:

```text
include/fall_detection_model.h
```

Hoặc:

```text
src/fall_detection_model.h
```

Khuyến nghị:

1. đặt trong `include/`

## Bước 6: Tạo file mã nguồn chính

Tạo file:

```text
src/main.cpp
```

Khung tối thiểu:

```cpp
#include <Arduino.h>
#include "fall_detection_model.h"

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/version.h"

namespace {
  const tflite::Model* model = nullptr;
  tflite::MicroInterpreter* interpreter = nullptr;
  TfLiteTensor* input = nullptr;
  TfLiteTensor* output = nullptr;

  constexpr int kWindowSize = 100;
  constexpr int kFeatureCount = 6;
  constexpr int kTensorArenaSize = 60 * 1024;
  uint8_t tensor_arena[kTensorArenaSize];
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  model = tflite::GetModel(fall_detection_model_tflite);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.println("Model schema mismatch");
    while (true) delay(1000);
  }

  static tflite::AllOpsResolver resolver;
  static tflite::MicroInterpreter static_interpreter(
      model, resolver, tensor_arena, kTensorArenaSize);

  interpreter = &static_interpreter;

  TfLiteStatus allocate_status = interpreter->AllocateTensors();
  if (allocate_status != kTfLiteOk) {
    Serial.println("AllocateTensors failed");
    while (true) delay(1000);
  }

  input = interpreter->input(0);
  output = interpreter->output(0);

  Serial.println("TFLite Micro ready");
}

void loop() {
  delay(1000);
}
```

## Bước 7: Kiểm tra tensor input/output

Sau khi `AllocateTensors()`, bạn nên kiểm tra:

1. `input->type`
2. `input->dims`
3. `output->type`

Kỳ vọng:

1. input là `int8`
2. output là `int8`
3. input shape gần như:
   - `[1, 100, 6]`
4. output shape:
   - `[1, 2]`

Bạn có thể in debug:

```cpp
Serial.printf("Input type: %d\n", input->type);
Serial.printf("Output type: %d\n", output->type);
```

## Bước 8: Tạo buffer 100x6

Bạn cần buffer dữ liệu IMU:

```cpp
float imu_window[100][6];
```

Ý nghĩa:

1. 100 time steps
2. 6 features mỗi step

Thứ tự phải đúng:

```text
[ax, ay, az, gx, gy, gz]
```

Ví dụ mỗi lần lấy mẫu:

```cpp
imu_window[idx][0] = ax_g;
imu_window[idx][1] = ay_g;
imu_window[idx][2] = az_g;
imu_window[idx][3] = gx_deg_s;
imu_window[idx][4] = gy_deg_s;
imu_window[idx][5] = gz_deg_s;
```

## Bước 9: Tính threshold trước khi infer

Mỗi khi window đầy 100 mẫu, tính:

```cpp
float maxA = 0.0f;
float maxG = 0.0f;

for (int i = 0; i < 100; ++i) {
  float ax = imu_window[i][0];
  float ay = imu_window[i][1];
  float az = imu_window[i][2];
  float gx = imu_window[i][3];
  float gy = imu_window[i][4];
  float gz = imu_window[i][5];

  float A = sqrtf(ax * ax + ay * ay + az * az);
  float G = sqrtf(gx * gx + gy * gy + gz * gz);

  if (A > maxA) maxA = A;
  if (G > maxG) maxG = G;
}

bool candidate = (maxA > 1.8f) || (maxG > 50.0f);
```

Nếu không phải candidate:

```cpp
return;
```

## Bước 10: Quantize input trước khi gọi model

Input model là `int8`, nên phải đổi từng giá trị float sang int8.

Ví dụ:

```cpp
int8_t quantize_value(float v) {
  const float scale = 6.11098051071167f;
  const int zero_point = 19;
  int q = (int)roundf(v / scale) + zero_point;
  if (q > 127) q = 127;
  if (q < -128) q = -128;
  return (int8_t)q;
}
```

Ghi vào tensor input:

```cpp
for (int t = 0; t < 100; ++t) {
  for (int c = 0; c < 6; ++c) {
    int index = t * 6 + c;
    input->data.int8[index] = quantize_value(imu_window[t][c]);
  }
}
```

## Bước 11: Chạy inference

```cpp
TfLiteStatus invoke_status = interpreter->Invoke();
if (invoke_status != kTfLiteOk) {
  Serial.println("Invoke failed");
  return;
}
```

Đọc output:

```cpp
int8_t out0 = output->data.int8[0];
int8_t out1 = output->data.int8[1];
```

Vì output là int8, muốn xem gần đúng score:

```cpp
float output_scale = 0.00390625f;
int output_zero_point = -128;

float score_non_fall = (out0 - output_zero_point) * output_scale;
float score_fall = (out1 - output_zero_point) * output_scale;
```

## Bước 12: Quyết định cảnh báo

Model hiện đã được chọn với decision threshold khá cao trong phase validation.

Thực tế trên ESP32, bạn có thể bắt đầu bằng logic đơn giản:

```cpp
if (score_fall > score_non_fall) {
  // possible fall
}
```

Nếu muốn giống training hơn, có thể áp ngưỡng mạnh hơn cho class fall:

```cpp
if (score_fall > 0.90f) {
  // trigger alert
}
```

Nhưng cần nhớ:

1. output int8 sau quantization không còn là softmax float hoàn hảo
2. nên test thực tế trên thiết bị

## Bước 13: Tích hợp vòng lặp realtime

Pipeline gợi ý:

1. đọc IMU ở `50 Hz`
2. cập nhật rolling buffer
3. mỗi `50 samples` chạy kiểm tra threshold một lần
4. nếu threshold pass thì chạy CNN
5. nếu CNN xác nhận fall thì:
   - buzzer
   - rung
   - BLE notify
   - Wi-Fi / MQTT alert

Pseudo-flow:

```text
read IMU
-> convert units
-> push into 100x6 rolling window
-> every 50 samples:
   -> compute A/G magnitude
   -> threshold stage
   -> if candidate:
      -> quantize input
      -> run TFLite Micro
      -> decide fall/non-fall
      -> send alert
```

## Bước 14: Build project trong PlatformIO

Trong VS Code:

1. mở `PlatformIO`
2. chọn `Build`

Nếu build fail:

1. kiểm tra lại board
2. kiểm tra thư viện TensorFlow Lite Micro
3. tăng `tensor_arena`
4. xem log thiếu symbol / thiếu op

## Bước 15: Upload firmware

1. nối ESP32-S3 bằng USB
2. chọn đúng COM port
3. nhấn `Upload`

Nếu board không vào chế độ flash:

1. giữ `BOOT`
2. nhấn `RESET`
3. thả `RESET`
4. thả `BOOT`

Tùy board clone/super mini, thao tác bootloader có thể khác một chút.

## Bước 16: Mở Serial Monitor để debug

1. mở `Monitor`
2. baud rate `115200`

Nên in:

1. giá trị `maxA`, `maxG`
2. trạng thái `candidate`
3. output model
4. quyết định cuối

Ví dụ:

```cpp
Serial.printf("maxA=%.3f maxG=%.3f candidate=%d\n", maxA, maxG, candidate);
Serial.printf("fall=%.4f non_fall=%.4f\n", score_fall, score_non_fall);
```

## Bước 17: Những lỗi thường gặp

### 1. `AllocateTensors failed`

Nguyên nhân:

1. tensor arena quá nhỏ
2. thiếu op trong resolver

Cách xử lý:

1. tăng `kTensorArenaSize`
2. dùng `AllOpsResolver` trước
3. sau khi chạy ổn, mới tối ưu về `MicroMutableOpResolver`

### 2. Model chạy nhưng kết quả sai nhiều

Nguyên nhân thường là:

1. sai đơn vị cảm biến
2. sai thứ tự cột
3. sai cách quantize
4. dữ liệu lấy không đúng `50 Hz`

### 3. RAM không đủ

Cách xử lý:

1. giữ model hiện tại vì nó đã khá nhỏ
2. giảm debug log
3. tối ưu resolver
4. dùng PSRAM nếu board có

## Bước 18: Tối ưu sau khi chạy ổn

Khi bản đầu tiên đã chạy được:

1. chuyển từ `AllOpsResolver` sang `MicroMutableOpResolver`
2. chỉ đăng ký đúng các op model dùng
3. đo thời gian infer thực tế
4. tinh chỉnh threshold ngoài thực địa

## Khuyến nghị cuối

Để triển khai thực tế, cách an toàn nhất là:

1. dùng `fall_detection_model.h`
2. chạy threshold trước CNN
3. giữ đúng input `100 x 6`
4. giữ đúng đơn vị:
   - accelerometer = `g`
   - gyroscope = `deg/s`
5. debug bằng serial trước khi nối buzzer / MQTT / cloud

## File liên quan trong project hiện tại

1. Model header:
   - `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/models/fall_detection_model.h`
2. Model tflite:
   - `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/models/fall_detection_model.tflite`
3. Ghi chú deployment:
   - `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/docs/esp32_deployment_notes.md`
4. Metrics:
   - `/home/dsoft1/CAPSTONE/dataset/31MAR/edge_ai_training_output/results/metrics_summary.txt`

