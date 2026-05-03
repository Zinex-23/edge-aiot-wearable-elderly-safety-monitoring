# Pinout ESP32-S3 Super Mini cho BMI160 và MAX30102

Firmware hiện tại dùng chung một bus I2C:

```text
SDA = GPIO8
SCL = GPIO9
I2C speed = 100 kHz
Serial Monitor = 115200 baud
```

## Bảng nối dây

| ESP32-S3 Super Mini | BMI160 | MAX30102 | Ghi chú |
|---|---|---|---|
| `3V3` | `VCC` hoặc `VIN` | `VCC` hoặc `VIN` | Ưu tiên cấp 3.3V cho logic I2C |
| `GND` | `GND` | `GND` | Bắt buộc nối chung mass |
| `GPIO8` | `SDA` | `SDA` | Bus I2C chung |
| `GPIO9` | `SCL` | `SCL` | Bus I2C chung |
| Không nối | `INT1/INT2` | `INT` | Firmware đang đọc polling, không dùng interrupt |

## BMI160

Nếu module BMI160 có chân `CS`, `CSB`, `SDO`, hoặc `SA0`:

| Chân BMI160 | Cách nối để dùng I2C |
|---|---|
| `CS` hoặc `CSB` | Kéo lên `3V3` nếu module yêu cầu chọn chế độ I2C |
| `SDO` hoặc `SA0` | Nối `GND` để dùng địa chỉ `0x68`, hoặc nối `3V3` để dùng `0x69` |

Firmware tự động thử cả hai địa chỉ `0x68` và `0x69`.

## MAX30102

MAX30102 thường dùng địa chỉ I2C cố định:

```text
0x57
```

Để có HR/SpO2 hợp lệ, đặt ngón tay che ổn định lên mặt cảm biến. Khi chưa có ngón tay hoặc tín hiệu chưa ổn định, firmware sẽ in:

```text
HR=255 bpm SpO2=255% finger=no vitals_valid=no
```

`255` là giá trị invalid, không phải giá trị đo thật.

## Địa chỉ I2C mong đợi

Khi mở Serial Monitor, lúc boot nên thấy một trong hai bộ địa chỉ:

```text
I2C device found at address 0x57
I2C device found at address 0x68
```

hoặc:

```text
I2C device found at address 0x57
I2C device found at address 0x69
```

## Lưu ý nguồn và dây nối

- Không cấp 5V trực tiếp vào cảm biến nếu module không có regulator hoặc level shifter.
- Dây `SDA` và `SCL` nên ngắn, đặc biệt với MAX30102 vì tín hiệu PPG dễ nhiễu.
- Nhiều module đã có điện trở pull-up I2C. Nếu bus không ổn định, thêm pull-up `4.7k` đến `10k` từ `SDA` và `SCL` lên `3V3`.
- Nếu Serial Monitor không hiện log sau khi nạp, kiểm tra board có bật USB CDC không. File `platformio.ini` đã đặt `ARDUINO_USB_CDC_ON_BOOT=1`.
