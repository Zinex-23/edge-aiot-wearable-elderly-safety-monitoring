# ESP32-S3 Edge Tutorial: BMI160 + MAX30102 + BLE

Tài liệu này ghi lại cách hiểu code hiện tại trong `S3_BLE/` và driver `firmware/S3_BLE/src/max30102_sensor.cpp`. Mục tiêu là đủ chi tiết để sau này viết lại firmware lấy được:

- Gia tốc 3 trục từ BMI160: `ax`, `ay`, `az`
- Con quay 3 trục từ BMI160: `gx`, `gy`, `gz`
- Nhịp tim từ MAX30102: `HR`
- Oxy máu từ MAX30102: `SpO2`
- Gửi dữ liệu qua BLE theo format hiện có

## 1. Tổng quan repo liên quan

Các file cần đọc khi làm firmware edge:

```text
S3_BLE/
  platformio.ini
  src/main.cpp
  BLE_PROTOCOL.md
  DATA_FLOW.md
  DATA_STRUCTURE.md
  tools/ble_client.py

firmware/S3_BLE/
  include/max30102_sensor.h
  src/max30102_sensor.cpp
  MAX30102_INTEGRATION_GUIDE.md
```

Ý nghĩa từng phần:

- `S3_BLE/src/main.cpp`: firmware chính đang chạy trên ESP32-S3. File này đã có BMI160, BLE, queue dữ liệu, batching HR/SpO2, task lấy mẫu, task inference fall detection.
- `S3_BLE/platformio.ini`: cấu hình PlatformIO và thư viện. Hiện có TensorFlow Lite Micro và NimBLE. Khi tích hợp MAX30102 thật phải thêm thư viện SparkFun MAX3010x.
- `firmware/S3_BLE/include/max30102_sensor.h`: API public cho module MAX30102.
- `firmware/S3_BLE/src/max30102_sensor.cpp`: implementation đọc MAX30102, chạy thuật toán SparkFun để tính HR/SpO2, lọc nhiễu, trả về giá trị ổn định.
- `S3_BLE/tools/ble_client.py`: client Python dùng Bleak để connect BLE, subscribe notify, gửi `READY`, in packet `ALERT` và `BATCH`.

Trạng thái hiện tại của code:

- BMI160 đã được đọc thật trong `S3_BLE/src/main.cpp`.
- MAX30102 chưa được tích hợp trực tiếp vào `S3_BLE/src/main.cpp`.
- Hàm `readVitalsSample()` trong `S3_BLE/src/main.cpp` hiện vẫn tạo dữ liệu giả bằng `random()`.
- Driver MAX30102 thật đã có sẵn ở `firmware/S3_BLE/`, cần copy/tích hợp vào project `S3_BLE/`.

## 2. Sơ đồ gắn chân phần cứng

Code hiện tại dùng một bus I2C chung cho cả BMI160 và MAX30102:

```cpp
static const int I2C_SDA_PIN = 8;
static const int I2C_SCL_PIN = 9;
static const int BUTTON_PIN = 10;
static const int LED_PIN = 48;
```

### 2.1. Bảng đấu dây ESP32-S3 với BMI160 và MAX30102

| ESP32-S3 | BMI160 | MAX30102 | Ghi chú |
|---|---|---|---|
| `3V3` | `VCC` hoặc `VIN` | `VCC` hoặc `VIN` | Ưu tiên cấp 3.3V để an toàn logic I2C |
| `GND` | `GND` | `GND` | Bắt buộc chung mass |
| `GPIO8` | `SDA` | `SDA` | Bus I2C chung |
| `GPIO9` | `SCL` | `SCL` | Bus I2C chung |
| Không dùng | `INT1/INT2` | `INT` | Code hiện tại không dùng interrupt |
| `GPIO10` | Nút nhấn một đầu | Không dùng | Nút kéo xuống GND, code dùng `INPUT_PULLUP` |

Nếu board BMI160 có các chân `CS`, `CSB`, `SDO`, `SA0`:

- `CS` hoặc `CSB`: kéo lên `3V3` để chọn chế độ I2C nếu module yêu cầu.
- `SDO` hoặc `SA0`: chọn địa chỉ I2C.
  - Nối `GND` để BMI160 dùng địa chỉ `0x68`.
  - Nối `3V3` để BMI160 dùng địa chỉ `0x69`.
- Code hiện tại tự dò cả `0x68` và `0x69`, nên dùng địa chỉ nào cũng được.

MAX30102 thường dùng địa chỉ I2C cố định:

- `0x57`

Khi chạy `scanI2C()`, Serial Monitor nên thấy:

```text
I2C device found at address 0x57
I2C device found at address 0x68
```

hoặc:

```text
I2C device found at address 0x57
I2C device found at address 0x69
```

### 2.2. Lưu ý nguồn và I2C

- Không cấp 5V trực tiếp vào cảm biến nếu module không có regulator hoặc level shifter.
- Dùng chung `GND` giữa ESP32-S3, BMI160, MAX30102.
- Dây SDA/SCL nên ngắn, đặc biệt khi MAX30102 đọc tín hiệu PPG dễ nhiễu.
- Nhiều module đã có điện trở kéo lên I2C. Nếu bus không ổn định, thêm pull-up khoảng `4.7k` đến `10k` lên `3V3`.
- Code đặt I2C ở `100 kHz` để cả BMI160 và MAX30102 cùng chạy ổn định trên một bus:

```cpp
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
Wire.setClock(100000);
Wire.setTimeOut(20);
```

## 3. Cấu trúc chính của `S3_BLE/src/main.cpp`

File `main.cpp` hiện được chia thành các nhóm lớn.

### 3.1. Khai báo pin, BLE, BMI160 register

Các pin:

```cpp
static const int I2C_SDA_PIN = 8;
static const int I2C_SCL_PIN = 9;
static const int BUTTON_PIN = 10;
static const int LED_PIN = 48;
```

Các UUID BLE:

```cpp
static const char *BLE_DEVICE_NAME = "ESP32-fall-detection-BLE";
static const char *BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char *BLE_STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8";
static const char *BLE_VITALS_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1";
static const char *BLE_CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03";
```

Các register quan trọng của BMI160:

```cpp
static const uint8_t BMI160_ADDR_LOW = 0x68;
static const uint8_t BMI160_ADDR_HIGH = 0x69;
static const uint8_t BMI160_CHIP_ID = 0xD1;

static const uint8_t REG_CHIP_ID = 0x00;
static const uint8_t REG_GYR_DATA = 0x0C;
static const uint8_t REG_ACC_DATA = 0x12;
static const uint8_t REG_ACC_CONF = 0x40;
static const uint8_t REG_ACC_RANGE = 0x41;
static const uint8_t REG_GYR_CONF = 0x42;
static const uint8_t REG_GYR_RANGE = 0x43;
static const uint8_t REG_CMD = 0x7E;
```

Scale đang dùng:

```cpp
static const float ACC_LSB_PER_G = 16384.0f;
static const float GYR_LSB_PER_DPS = 16.4f;
```

Điều này tương ứng với:

- Accelerometer range: `+/-2g`
- Gyroscope range: `+/-2000 dps`

### 3.2. Cấu trúc dữ liệu IMU

BMI160 được đưa về struct:

```cpp
struct ImuSample {
  float ax = 0.0f;
  float ay = 0.0f;
  float az = 0.0f;
  float gx = 0.0f;
  float gy = 0.0f;
  float gz = 0.0f;
  uint32_t tsMs = 0;
};
```

Ý nghĩa:

- `ax`, `ay`, `az`: gia tốc theo đơn vị `g`.
- `gx`, `gy`, `gz`: vận tốc góc theo đơn vị `degree/second`.
- `tsMs`: timestamp nội bộ theo `millis()`.

Code giữ một cửa sổ trượt:

```cpp
static const int kWindowSize = 100;
static const int kFeatureCount = 6;
static const int kInferenceStride = 50;

ImuSample imuWindow[kWindowSize];
int windowHead = 0;
int windowCount = 0;
int samplesSinceInference = 0;
```

Với sample rate `50 Hz`:

- `100` mẫu tương đương khoảng `2 giây`.
- Inference stride `50` nghĩa là sau mỗi `1 giây` sẽ thử chạy inference một lần nếu cửa sổ đã đủ mẫu.
- Mỗi sample có `6` feature: `ax, ay, az, gx, gy, gz`.

### 3.3. Cấu trúc dữ liệu vitals

Vitals được gom theo batch:

```cpp
static const uint32_t VITALS_SAMPLE_PERIOD_MS = 5000;
static const uint32_t VITALS_DISPATCH_PERIOD_MS = 25000;
static const uint8_t VITALS_BATCH_SIZE = 5;
static const uint8_t INVALID_VITAL_VALUE = 255;
```

Ý nghĩa:

- Cứ `5 giây` lấy một mẫu HR/SpO2.
- Cứ `25 giây` gửi một batch.
- Mỗi batch có `5` mẫu.
- Giá trị `255` nghĩa là invalid hoặc chưa có dữ liệu hợp lệ.

Struct một mẫu vitals:

```cpp
struct VitalSample {
  uint8_t heartRate = INVALID_VITAL_VALUE;
  uint8_t spo2 = INVALID_VITAL_VALUE;
  uint32_t timestampSec = 0;
};
```

Struct một batch:

```cpp
struct VitalsBatchPacket {
  uint32_t sequence = 0;
  uint8_t heartRate[VITALS_BATCH_SIZE];
  uint8_t spo2[VITALS_BATCH_SIZE];
  uint32_t timestampSec[VITALS_BATCH_SIZE];
};
```

Code hiện tại có queue RAM:

- `vitalsQueue`: lưu các batch HR/SpO2 khi chưa có BLE client.
- `fallQueue`: lưu alert ngã khi chưa có BLE client.

Nếu queue đầy, code bỏ packet cũ nhất để tránh tràn RAM.

## 4. BMI160: flow đọc accelerometer và gyroscope

### 4.1. Dò địa chỉ và chip id

Hàm `detectBMI160()` thử đọc `REG_CHIP_ID` ở `0x68`, sau đó `0x69`.

Logic:

```text
set bmi160Addr = 0x68
read REG_CHIP_ID
if chipId == 0xD1 -> OK

set bmi160Addr = 0x69
read REG_CHIP_ID
if chipId == 0xD1 -> OK

else -> fail
```

Nếu wiring đúng, log sẽ có dạng:

```text
Detecting BMI160...
  Address 0x68: Got ID 0xD1 (Expected 0xD1)
BMI160 initialization SUCCESS
```

### 4.2. Khởi tạo BMI160

Hàm `initBMI160()` làm các bước:

```cpp
if (!detectBMI160()) return false;

writeReg(REG_CMD, 0x11);  // accelerometer normal mode
delay(10);

writeReg(REG_CMD, 0x15);  // gyroscope normal mode
delay(80);

writeReg(REG_ACC_CONF, 0x28);
writeReg(REG_ACC_RANGE, 0x03);

writeReg(REG_GYR_CONF, 0x28);
writeReg(REG_GYR_RANGE, 0x00);
```

Cấu hình range đang khớp với scale:

- `REG_ACC_RANGE = 0x03` -> accelerometer `+/-2g` -> `16384 LSB/g`.
- `REG_GYR_RANGE = 0x00` -> gyroscope `+/-2000 dps` -> `16.4 LSB/dps`.

### 4.3. Đọc raw data

Accelerometer data bắt đầu ở register `0x12`:

```cpp
bool readAccelRaw(int16_t &axRaw, int16_t &ayRaw, int16_t &azRaw) {
  uint8_t d[6];
  if (!readRegs(REG_ACC_DATA, d, 6)) return false;
  axRaw = toInt16(d[0], d[1]);
  ayRaw = toInt16(d[2], d[3]);
  azRaw = toInt16(d[4], d[5]);
  return true;
}
```

Gyroscope data bắt đầu ở register `0x0C`:

```cpp
bool readGyroRaw(int16_t &gxRaw, int16_t &gyRaw, int16_t &gzRaw) {
  uint8_t d[6];
  if (!readRegs(REG_GYR_DATA, d, 6)) return false;
  gxRaw = toInt16(d[0], d[1]);
  gyRaw = toInt16(d[2], d[3]);
  gzRaw = toInt16(d[4], d[5]);
  return true;
}
```

BMI160 trả dữ liệu little-endian:

```cpp
int16_t toInt16(uint8_t lsb, uint8_t msb) {
  return (int16_t)((msb << 8) | lsb);
}
```

### 4.4. Convert về đơn vị thật

Hàm `readImuSample()` đọc raw rồi convert:

```cpp
sample.ax = axRaw / ACC_LSB_PER_G;
sample.ay = ayRaw / ACC_LSB_PER_G;
sample.az = azRaw / ACC_LSB_PER_G;
sample.gx = gxRaw / GYR_LSB_PER_DPS;
sample.gy = gyRaw / GYR_LSB_PER_DPS;
sample.gz = gzRaw / GYR_LSB_PER_DPS;
sample.tsMs = millis();
```

Kết quả cuối cùng:

- `ax`, `ay`, `az`: float, đơn vị `g`.
- `gx`, `gy`, `gz`: float, đơn vị `dps`.

## 5. MAX30102: cấu trúc driver hiện có

Driver nằm ở:

```text
firmware/S3_BLE/include/max30102_sensor.h
firmware/S3_BLE/src/max30102_sensor.cpp
```

### 5.1. API public trong `max30102_sensor.h`

Struct trả kết quả:

```cpp
struct VitalsReading {
  uint8_t heartRate;       // bpm, 255 = invalid
  uint8_t spo2;            // %, 255 = invalid
  bool fingerDetected;     // true nếu có ngón tay trên sensor
  bool valid;              // true nếu cả HR và SpO2 hợp lệ
  unsigned long timestamp; // millis()
};
```

Các hàm public:

```cpp
bool max30102_init();
void max30102_update();
VitalsReading max30102_getLatestVitals();
bool max30102_isReady();
bool max30102_isFingerDetected();
```

Cách dùng đúng:

1. Gọi `Wire.begin(...)` trong `setup()` trước.
2. Gọi `max30102_init()` sau `Wire.begin(...)`.
3. Gọi `max30102_update()` thường xuyên trong loop hoặc task lấy mẫu.
4. Khi cần lấy HR/SpO2, gọi `max30102_getLatestVitals()`.

### 5.2. Config của MAX30102

Các hằng số trong header:

```cpp
#define MAX30102_UPDATE_INTERVAL_MS    200
#define MAX30102_FINGER_THRESHOLD      50000
#define MAX30102_HR_MAX_JUMP           15
#define MAX30102_SPO2_MAX_JUMP         3
#define MAX30102_HR_MIN                40
#define MAX30102_HR_MAX                180
#define MAX30102_SPO2_MIN              90
#define MAX30102_SPO2_MAX              100
#define MAX30102_BUFFER_SIZE           100
```

Ý nghĩa:

- `MAX30102_UPDATE_INTERVAL_MS = 200`: driver tự giới hạn update khoảng `5 Hz`.
- `MAX30102_FINGER_THRESHOLD = 50000`: nếu IR thấp hơn ngưỡng này thì coi như chưa đặt ngón tay.
- `MAX30102_BUFFER_SIZE = 100`: thuật toán SparkFun cần buffer 100 mẫu IR và Red.
- HR hợp lệ nằm trong `40..180 bpm`.
- SpO2 hợp lệ nằm trong `90..100%`.
- Nếu HR nhảy quá `15 bpm` so với giá trị ổn định trước đó thì bỏ qua.
- Nếu SpO2 nhảy quá `3%` so với giá trị ổn định trước đó thì bỏ qua.

### 5.3. Khởi tạo MAX30102

Trong `max30102_init()`:

```cpp
particleSensor.begin(Wire, I2C_SPEED_STANDARD)
```

Điểm quan trọng:

- Driver dùng chung object `Wire` với BMI160.
- `Wire.begin()` phải được gọi trước ở firmware chính.
- `I2C_SPEED_STANDARD` tương ứng `100 kHz`, khớp với bus I2C của `main.cpp`.

Sau khi tìm thấy sensor:

```cpp
particleSensor.setup(60, 4, 2, 200, 411, 16384);
particleSensor.setPulseAmplitudeGreen(0);
```

Tham số `setup()`:

| Tham số | Giá trị | Ý nghĩa |
|---|---:|---|
| `ledBrightness` | `60` | LED Red/IR mức vừa phải |
| `sampleAverage` | `4` | Sensor tự average 4 mẫu |
| `ledMode` | `2` | Red + IR, dùng cho SpO2 |
| `sampleRate` | `200` | 200 sample/second |
| `pulseWidth` | `411` | pulse width 411 us, độ phân giải cao |
| `adcRange` | `16384` | ADC range |

Driver tắt LED xanh:

```cpp
particleSensor.setPulseAmplitudeGreen(0);
```

Vì HR/SpO2 chỉ cần Red và IR.

### 5.4. Buffer khởi động

Sau khi setup, driver fill buffer ban đầu:

```cpp
for (int i = 0; i < MAX30102_BUFFER_SIZE; i++) {
  while (!particleSensor.available()) {
    particleSensor.check();
  }
  redBuffer[i] = particleSensor.getRed();
  irBuffer[i] = particleSensor.getIR();
  particleSensor.nextSample();
}
```

Điểm cần nhớ:

- Đoạn này blocking khoảng vài giây.
- Mục đích là có đủ 100 mẫu đầu tiên để thuật toán SparkFun tính HR/SpO2.
- Sau giai đoạn này `sensorReady = true`.

### 5.5. Update non-blocking

Hàm `max30102_update()`:

1. Thoát ngay nếu sensor chưa ready.
2. Chỉ chạy nếu đã qua `MAX30102_UPDATE_INTERVAL_MS`.
3. Kiểm tra FIFO có sample mới chưa bằng `particleSensor.available()` và `particleSensor.check()`.
4. Ghi sample mới vào circular buffer:

```cpp
redBuffer[bufferHead] = particleSensor.getRed();
irBuffer[bufferHead] = particleSensor.getIR();
particleSensor.nextSample();
```

5. Dùng giá trị IR mới nhất để detect ngón tay:

```cpp
currentFingerDetected = (irValue >= MAX30102_FINGER_THRESHOLD);
```

6. Nếu không có ngón tay:

```cpp
lastStableHR = 0;
lastStableSpO2 = 0;
return;
```

7. Nếu có ngón tay, linearize circular buffer rồi chạy thuật toán:

```cpp
maxim_heart_rate_and_oxygen_saturation(
  linearIR,
  MAX30102_BUFFER_SIZE,
  linearRed,
  &algoSpo2,
  &algoValidSpo2,
  &algoHeartRate,
  &algoValidHeartRate
);
```

8. Lọc nhiễu:

- HR chỉ nhận nếu thuật toán báo valid, nằm trong range, và không nhảy quá `15 bpm`.
- SpO2 chỉ nhận nếu thuật toán báo valid, nằm trong range, và không nhảy quá `3%`.

### 5.6. Lấy kết quả mới nhất

Hàm `max30102_getLatestVitals()` trả:

- `heartRate = 255`, `spo2 = 255`, `valid = false` nếu sensor chưa ready hoặc không có ngón tay.
- Nếu có giá trị stable hợp lệ, trả HR và SpO2 dạng `uint8_t`.

Do đó khi tích hợp vào hệ thống BLE hiện tại, có thể map trực tiếp:

```cpp
VitalsReading reading = max30102_getLatestVitals();
sample.heartRate = reading.heartRate;
sample.spo2 = reading.spo2;
```

Không cần đổi format BLE, vì code BLE đã dùng `255` làm invalid value.

## 6. Cách tích hợp MAX30102 vào project `S3_BLE`

### 6.1. Thêm library vào `platformio.ini`

Trong `S3_BLE/platformio.ini`, thêm SparkFun MAX3010x:

```ini
lib_deps =
    tanakamasayuki/TensorFlowLite_ESP32@^1.0.0
    h2zero/NimBLE-Arduino@^1.4.2
    sparkfun/SparkFun MAX3010x Pulse and Proximity Sensor Library@^1.1.2
```

### 6.2. Copy driver MAX30102 vào `S3_BLE`

Copy:

```text
firmware/S3_BLE/include/max30102_sensor.h -> S3_BLE/include/max30102_sensor.h
firmware/S3_BLE/src/max30102_sensor.cpp   -> S3_BLE/src/max30102_sensor.cpp
```

Sau khi copy, project `S3_BLE` sẽ build được `#include "max30102_sensor.h"`.

### 6.3. Include header trong `main.cpp`

Ở đầu `S3_BLE/src/main.cpp`, thêm:

```cpp
#include "max30102_sensor.h"
```

Vị trí hợp lý là sau:

```cpp
#include <Wire.h>
```

### 6.4. Thêm state cho MAX30102

Sau nhóm BMI160 state:

```cpp
uint8_t bmi160Addr = BMI160_ADDR_LOW;
bool bmiOk = false;
uint32_t lastSampleMs = 0;
```

thêm:

```cpp
bool max30102Ok = false;
```

### 6.5. Thay `readVitalsSample()` từ random sang sensor thật

Hiện tại:

```cpp
bool readVitalsSample(VitalSample &sample) {
  sample.timestampSec = currentUnixTimeSecUtc();
  sample.heartRate = (uint8_t)random(68, 96);
  sample.spo2 = (uint8_t)random(94, 100);
  return true;
}
```

Thay bằng:

```cpp
bool readVitalsSample(VitalSample &sample) {
  sample.timestampSec = currentUnixTimeSecUtc();

  if (!max30102Ok) {
    sample.heartRate = INVALID_VITAL_VALUE;
    sample.spo2 = INVALID_VITAL_VALUE;
    return true;
  }

  VitalsReading reading = max30102_getLatestVitals();
  sample.heartRate = reading.heartRate;
  sample.spo2 = reading.spo2;
  return true;
}
```

Lý do vẫn `return true` khi MAX30102 lỗi:

- Batch system vẫn chạy.
- BLE client vẫn nhận được packet đúng format.
- HR/SpO2 là `255`, client hiểu là invalid.

### 6.6. Init MAX30102 trong `setup()`

Trong `setup()`, sau khi `Wire.begin(...)`, `scanI2C()`, và init BMI160, thêm:

```cpp
max30102Ok = max30102_init();
if (max30102Ok) {
  Serial.println("MAX30102 initialization SUCCESS");
} else {
  Serial.println("MAX30102 initialization FAILED - vitals will be invalid");
}
```

Vị trí đề xuất:

```cpp
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
Wire.setClock(100000);
Wire.setTimeOut(20);
delay(100);

scanI2C();

bmiOk = initBMI160();
if (bmiOk) {
  Serial.println("BMI160 initialization SUCCESS");
} else {
  Serial.println("BMI160 initialization FAILED - check wiring and power");
}

max30102Ok = max30102_init();
if (max30102Ok) {
  Serial.println("MAX30102 initialization SUCCESS");
} else {
  Serial.println("MAX30102 initialization FAILED - vitals will be invalid");
}

initBle();
```

### 6.7. Gọi `max30102_update()` trong task lấy mẫu

`samplingTask()` hiện chạy mỗi `20 ms` vì sample rate BMI160 là `50 Hz`.

Thêm `max30102_update()` vào vòng lặp. Driver tự giới hạn update mỗi `200 ms`, nên gọi thường xuyên là ổn:

```cpp
void samplingTask(void *pvParameters) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xFrequency = pdMS_TO_TICKS(SAMPLE_PERIOD_MS);
  ImuSample sample;

  Serial.println("Sampling task STARTED");
  for (;;) {
    vTaskDelayUntil(&xLastWakeTime, xFrequency);

    if (!acquisitionEnabled) continue;

    if (max30102Ok) {
      max30102_update();
    }

    if (!bmiOk) continue;

    if (readImuSample(sample)) {
      portENTER_CRITICAL(&imuMux);
      pushSample(sample);
      portEXIT_CRITICAL(&imuMux);

      maybeSampleVitals();
      maybeDispatchVitalsBatch();

      if (samplesSinceInference >= kInferenceStride && windowCount >= kWindowSize) {
        if (inferenceTaskHandle != NULL) {
          xTaskNotifyGive(inferenceTaskHandle);
        }
      }
    }
  }
}
```

Lưu ý: đặt `max30102_update()` trước `if (!bmiOk) continue;` giúp MAX30102 vẫn được update nếu BMI160 lỗi. Nếu yêu cầu hệ thống bắt buộc cả hai sensor cùng OK mới chạy, có thể giữ logic phụ thuộc `bmiOk`, nhưng cách tách riêng như trên dễ debug hơn.

## 7. Flow hoạt động đầy đủ sau khi tích hợp

### 7.1. Flow trong `setup()`

```text
ESP32-S3 boot
  -> Serial.begin(115200)
  -> init button GPIO10 input pull-up
  -> init LED GPIO48
  -> Wire.begin(SDA=8, SCL=9, 100kHz)
  -> scanI2C()
       expect MAX30102 at 0x57
       expect BMI160 at 0x68 or 0x69
  -> initBMI160()
       read chip id 0xD1
       set accel normal mode
       set gyro normal mode
       set accel +/-2g
       set gyro +/-2000 dps
  -> max30102_init()
       begin SparkFun MAX3010x on Wire
       setup Red + IR mode
       fill 100-sample buffer
  -> initBle()
       create BLE service
       create status notify char
       create vitals notify char
       create control read/write char
       start advertising
  -> initModel()
       load TFLite model
       allocate tensors
  -> resetVitalsState()
  -> create samplingTask on core 1
  -> create inferenceTask on core 0
```

### 7.2. Flow trong `samplingTask`

```text
Every 20 ms:
  if acquisition disabled:
      skip

  max30102_update()
      internally runs only every 200 ms
      updates Red/IR circular buffer
      detects finger
      computes and filters HR/SpO2

  readImuSample()
      read axRaw, ayRaw, azRaw
      read gxRaw, gyRaw, gzRaw
      convert to ax, ay, az in g
      convert to gx, gy, gz in dps
      push into 100-sample imuWindow

  maybeSampleVitals()
      every 5 seconds:
        read latest HR/SpO2 from MAX30102
        push into vitalsHistory

  maybeDispatchVitalsBatch()
      every 25 seconds:
        build BATCH with 5 samples
        send BLE if connected
        else queue to RAM

  if enough IMU samples for inference:
      notify inferenceTask
```

### 7.3. Flow trong `inferenceTask`

```text
Wait until samplingTask notifies
  -> check IMU window has 100 samples
  -> calculate max acceleration magnitude
  -> calculate max gyro magnitude
  -> if window is not candidate:
       fallProb = 0
       do not send alert
  -> else:
       quantize 100 x 6 input features
       run TFLite Micro
       dequantize output
       if fallProb >= 0.40:
          create ALERT packet
          send BLE if connected
          else queue to RAM
```

Candidate threshold hiện tại:

```cpp
static const float FALL_DECISION_THRESHOLD = 0.40f;
static const float CANDIDATE_ACC_THRESHOLD = 1.5f;
static const float CANDIDATE_GYRO_THRESHOLD = 50.0f;
```

### 7.4. Flow BLE

Firmware tạo một BLE service:

```text
Service UUID:
4fafc201-1fb5-459e-8fcc-c5c9c331914b
```

Characteristics:

| Dữ liệu | UUID | Property |
|---|---|---|
| Fall alert | `beb5483e-36e1-4688-b7f5-ea07361b26a8` | Read, Notify |
| Vitals batch | `7b809f11-63f0-4dca-8e4d-2b4e8384e7c1` | Read, Notify |
| Control | `f9b2c417-1d15-4ad4-9b52-b94aa0f76b03` | Read, Write |

Client phải làm đúng thứ tự:

```text
connect BLE
subscribe fall alert characteristic
subscribe vitals characteristic
write "READY" to control characteristic
ESP32 flush backlog:
  send all ALERT first
  send all BATCH after that
```

Nếu client không gửi `READY`, ESP32 không flush backlog.

## 8. BLE payload format

### 8.1. Fall alert

Format:

```text
ALERT,<sequence>,<timestamp_sec>,fall,<status_code>,<fall_prob>,<non_fall_prob>
```

Ví dụ:

```text
ALERT,12,1776730125,fall,1,0.873,0.127
```

Ý nghĩa:

- `sequence`: số thứ tự alert.
- `timestamp_sec`: timestamp giây.
- `fall`: label cố định cho event ngã.
- `status_code`: hiện tại là `1`.
- `fall_prob`: xác suất ngã.
- `non_fall_prob`: xác suất không ngã.

### 8.2. Vitals batch

Format:

```text
BATCH,<sequence>,<hr0>|<hr1>|<hr2>|<hr3>|<hr4>,<spo20>|<spo21>|<spo22>|<spo23>|<spo24>,<ts0>|<ts1>|<ts2>|<ts3>|<ts4>
```

Ví dụ:

```text
BATCH,31,72|74|75|73|76,98|98|97|98|97,1776730100|1776730105|1776730110|1776730115|1776730120
```

Nếu chưa có dữ liệu hợp lệ từ MAX30102:

```text
BATCH,31,255|255|255|255|255,255|255|255|255|255,1776730100|1776730105|1776730110|1776730115|1776730120
```

Client phải coi `255` là invalid, không phải HR hoặc SpO2 thật.

## 9. Checklist test sau khi viết lại hoặc tích hợp code

### 9.1. Build

```bash
cd S3_BLE
pio run
```

Nếu lỗi thiếu header:

- Kiểm tra đã copy `max30102_sensor.h` vào `S3_BLE/include/`.
- Kiểm tra đã copy `max30102_sensor.cpp` vào `S3_BLE/src/`.

Nếu lỗi thiếu `MAX30105.h` hoặc `spo2_algorithm.h`:

- Kiểm tra `platformio.ini` đã thêm SparkFun MAX3010x library.

### 9.2. Upload và monitor

```bash
cd S3_BLE
pio run -t upload
pio device monitor -b 115200
```

Log mong muốn:

```text
Scanning I2C bus...
I2C device found at address 0x57
I2C device found at address 0x68
Detecting BMI160...
BMI160 initialization SUCCESS
[MAX30102] Sensor FOUND, configuring...
[MAX30102] Ready - initial buffer filled
MAX30102 initialization SUCCESS
BLE advertising started
TFLite Micro ready
Sampling task STARTED
Inference task STARTED
```

### 9.3. Test BMI160

Khi cầm board xoay hoặc lắc nhẹ:

- `ax`, `ay`, `az` phải thay đổi theo hướng trọng lực.
- Khi board nằm yên, tổng magnitude gần `1g`:

```text
sqrt(ax*ax + ay*ay + az*az) ~= 1.0
```

- `gx`, `gy`, `gz` gần `0 dps` khi nằm yên.
- Khi xoay board, gyro phải thay đổi rõ.

Nếu BMI160 fail:

- Kiểm tra `SDA/SCL` có bị đảo không.
- Kiểm tra `CS/CSB` đã ở mode I2C chưa.
- Kiểm tra `SDO/SA0` để chọn `0x68` hoặc `0x69`.
- Kiểm tra nguồn 3.3V và GND.

### 9.4. Test MAX30102

Khi chưa đặt ngón tay:

- `fingerDetected = false`.
- HR/SpO2 trả về `255`.

Khi đặt ngón tay:

- Chờ vài giây để buffer và thuật toán ổn định.
- `fingerDetected = true` nếu IR vượt ngưỡng.
- HR nằm khoảng `40..180`.
- SpO2 nằm khoảng `90..100`.

Nếu luôn ra `255`:

- Đặt ngón tay che đều LED và photodiode.
- Giữ yên tay trong 10-20 giây.
- Tránh ánh sáng mạnh chiếu trực tiếp vào module.
- Kiểm tra module MAX30102 có thật sự ở địa chỉ `0x57` không.
- Nếu IR quá thấp, cân nhắc giảm `MAX30102_FINGER_THRESHOLD`.
- Nếu tín hiệu bão hòa, giảm `ledBrightness` trong `particleSensor.setup(...)`.

### 9.5. Test BLE client

Chạy client:

```bash
cd S3_BLE
python tools/ble_client.py
```

Client sẽ:

1. Scan BLE device tên `ESP32-fall-detection-BLE`.
2. Connect.
3. Subscribe `status` và `vitals`.
4. Gửi `READY`.
5. In payload nhận được.

Packet vitals hợp lệ sẽ có dạng:

```text
BATCH,1,75|76|74|73|75,98|98|97|98|98,...
```

Packet invalid sẽ có HR/SpO2 bằng `255`.

## 10. Các điểm cần chú ý khi viết lại firmware

### 10.1. Không init `Wire` nhiều lần

BMI160 và MAX30102 dùng chung bus I2C. Chỉ nên gọi:

```cpp
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
```

một lần trong `setup()`.

Driver sensor chỉ nhận object `Wire` đã init sẵn. Không để mỗi driver tự gọi `Wire.begin()` với pin khác nhau.

### 10.2. Không để MAX30102 làm nghẽn task lấy mẫu IMU

BMI160 cần lấy mẫu đều `50 Hz` cho model fall detection. Vì vậy:

- `max30102_init()` có thể blocking lúc boot để fill buffer.
- `max30102_update()` trong runtime phải non-blocking.
- Không đặt vòng lặp chờ dữ liệu MAX30102 quá lâu trong `samplingTask`.

### 10.3. Tách lỗi từng sensor

Nên giữ state riêng:

```cpp
bool bmiOk = false;
bool max30102Ok = false;
```

Như vậy:

- BMI160 lỗi thì fall detection không chạy, nhưng BLE và MAX30102 vẫn có thể debug.
- MAX30102 lỗi thì HR/SpO2 là `255`, nhưng fall detection vẫn chạy.
- BLE vẫn hoạt động để báo tình trạng.

### 10.4. Dùng `255` nhất quán cho invalid vitals

Code hiện tại đã thống nhất:

```cpp
static const uint8_t INVALID_VITAL_VALUE = 255;
```

MAX30102 driver cũng trả `255` khi invalid.

Không nên đổi sang `0` vì `0` dễ gây nhầm với dữ liệu chưa init, còn protocol BLE hiện tại đã ghi rõ `255 = invalid`.

### 10.5. Thứ tự ưu tiên dữ liệu BLE

Khi flush queue:

1. Gửi `ALERT` trước.
2. Gửi `BATCH` sau.

Lý do: fall alert quan trọng hơn dữ liệu sinh hiệu định kỳ.

### 10.6. Timestamp hiện tại là timestamp giả lập từ boot

Hàm hiện tại:

```cpp
uint32_t currentUnixTimeSecUtc() {
  return SIMULATED_UNIX_EPOCH_BASE_UTC + (millis() / 1000UL);
}
```

Nó không phải đồng hồ thật. Nó lấy mốc giả:

```cpp
1776729600UL  // 2026-04-21 00:00:00 UTC
```

rồi cộng uptime. Nếu muốn timestamp thật cần thêm cơ chế sync thời gian từ BLE client, RTC, hoặc Wi-Fi/NTP.

## 11. Flow ngắn để nhớ khi code lại

```text
Hardware:
  ESP32-S3 GPIO8/GPIO9 -> I2C bus
  BMI160 -> 0x68 or 0x69
  MAX30102 -> 0x57

Setup:
  Serial
  GPIO
  Wire.begin(8, 9, 100kHz)
  scanI2C
  initBMI160
  initMAX30102
  initBLE
  initModel
  create tasks

Runtime:
  samplingTask every 20 ms
    update MAX30102 non-blocking
    read BMI160 ax ay az gx gy gz
    push IMU window
    every 5 s read latest HR/SpO2
    every 25 s send BATCH
    every 50 IMU samples notify inference

  inferenceTask
    run model on 100 x 6 IMU window
    if fallProb >= 0.40 send ALERT

  loop
    handle button
    flush BLE backlog after READY
```

## 12. File/code cần sửa khi triển khai thật

Danh sách thay đổi tối thiểu:

```text
S3_BLE/platformio.ini
  -> thêm SparkFun MAX3010x library

S3_BLE/include/max30102_sensor.h
  -> copy từ firmware/S3_BLE/include/

S3_BLE/src/max30102_sensor.cpp
  -> copy từ firmware/S3_BLE/src/

S3_BLE/src/main.cpp
  -> include max30102_sensor.h
  -> thêm bool max30102Ok
  -> init max30102 sau Wire.begin
  -> gọi max30102_update trong samplingTask
  -> thay readVitalsSample random bằng max30102_getLatestVitals
```

Sau các bước này, firmware có thể lấy đồng thời:

- `ax`, `ay`, `az`, `gx`, `gy`, `gz` từ BMI160.
- `heartRate`, `spo2`, `fingerDetected`, `valid` từ MAX30102.
- Gửi fall alert và vitals batch qua BLE theo protocol hiện có.

