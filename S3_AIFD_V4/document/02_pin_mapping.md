# 02 — Bảng nối chân ngoại vi ↔ MCU

**Ngày cập nhật:** 2026-05-15
**MCU:** ESP32-S3-DevKitM-1 (chip ESP32-S3, USB-OTG qua GPIO 19/20)
**File code áp dụng:** [`src/main.cpp`](../src/main.cpp)

---

## 1. Bảng tổng hợp

| # | Ngoại vi          | Chân ngoại vi   | GPIO MCU | Chế độ pin       | Ghi chú                                              |
| - | ----------------- | --------------- | -------- | ---------------- | ---------------------------------------------------- |
| 1 | LED xanh          | Anode (+)       | GPIO 4   | OUTPUT           | Nối tiếp điện trở 220 Ω → GND                        |
| 2 | LED vàng          | Anode (+)       | GPIO 5   | OUTPUT           | Nối tiếp điện trở 220 Ω → GND                        |
| 3 | LED đỏ            | Anode (+)       | GPIO 6   | OUTPUT           | Nối tiếp điện trở 220 Ω → GND                        |
| 4 | Buzzer 5V (2300 Hz) | Cực dương (+) | GPIO 7   | OUTPUT (tone)    | Cực âm (−) → GND. Drive bằng `tone(7, 2300)`         |
| 5 | Nút nhấn          | 1 chân          | GPIO 10  | INPUT_PULLUP     | Chân còn lại → GND. Không cần điện trở pull-up ngoài |
| 6 | BMI160 IMU        | SDA             | GPIO 8   | I2C SDA          | I2C @ 100 kHz. Module thường có pull-up sẵn 10 kΩ    |
| 7 | BMI160 IMU        | SCL             | GPIO 9   | I2C SCL          | I2C @ 100 kHz                                        |
| 8 | BMI160 IMU        | VCC             | 3V3      | nguồn            | Cấp 3.3V cho module (KHÔNG dùng 5V trừ khi module có LDO) |
| 9 | BMI160 IMU        | GND             | GND      | mass             | Mass chung                                           |
| 10| BMI160 IMU        | SDO             | GND      | địa chỉ I2C      | Nối GND → addr 0x68 (mặc định). Để hở/pull-up → 0x69 |

> Tất cả ngoại vi dùng chung mass (**GND**) với MCU. Nguồn cấp 5V cho buzzer có thể lấy từ chân **5V/VBUS** của DevKitM-1 (khi cấp qua USB).
> BMI160 dùng 3V3 (không phải 5V) — module GY-BMI160 phổ biến trên thị trường VN đa số có LDO chấp nhận 3.3–5V, nhưng để an toàn dùng 3V3.

---

## 2. Bảng nguồn

| Chân nguồn MCU | Mức điện áp | Cấp cho                       |
| -------------- | ----------- | ----------------------------- |
| 3V3            | 3.3 V       | BMI160 VCC                    |
| 5V (VBUS)      | 5.0 V       | Buzzer 5V (qua GPIO 7 switch) |
| GND            | 0 V         | Mass chung cho mọi ngoại vi   |

---

## 3. Sơ đồ kết nối chi tiết (ASCII)

```
  NGUỒN
  ┌──────┐
  │ 3V3  ├──────────────────────────────────────────── [3V3 rail] ──────────────────┐
  │      │                                                                           │
  │ 5V   ├──────────────────────────────────────────── [5V rail]  ─────────┐        │
  │      │                                                                  │        │
  │ GND  ├──────────────────────────────────────────── [GND rail] ─┐       │        │
  │      │                                                          │       │        │
  │  ESP32-S3-DevKitM-1                                             │       │        │
  │                    │                                            │       │        │
  │  ┌─────────────────┴──────────────────────────┐                │       │        │
  │  │                                            │                │       │        │
  │  │  GPIO 4 ───────────────────[R 220Ω]───┬───│── Anode  (+) │>│ LED XANH       │
  │  │                                        └───│── Cathode (−) ──────── GND ─────┤
  │  │                                            │                                  │
  │  │  GPIO 5 ───────────────────[R 220Ω]───┬───│── Anode  (+) │>│ LED VÀNG       │
  │  │                                        └───│── Cathode (−) ──────── GND ─────┤
  │  │                                            │                                  │
  │  │  GPIO 6 ───────────────────[R 220Ω]───┬───│── Anode  (+) │>│ LED ĐỎ         │
  │  │                                        └───│── Cathode (−) ──────── GND ─────┤
  │  │                                            │                                  │
  │  │  GPIO 7 ────────────────────────────── (+) BUZZER 5V (−) ──── GND ───────────┤
  │  │             (5V cho buzzer lấy từ 5V rail nếu cần)                            │
  │  │                                            │                                  │
  │  │  GPIO 10 ──────────────────────────┬── [NÚT] ── GND ──────────────────────── ┤
  │  │  (INPUT_PULLUP ~45kΩ nội bộ)       │                                          │
  │  │                                    │ (tuỳ chọn: tụ 100nF từ chân nút → GND)  │
  │  │                                            │                                  │
  │  │  GPIO 8 (SDA) ─────────────────── SDA ─── ┤                                  │
  │  │  GPIO 9 (SCL) ─────────────────── SCL ─── ┤  ┌──────────────┐               │
  │  │  3V3  ─────────────────────────── VCC ─── ┤  │  BMI160 IMU  │ ──── 3V3 ──── ┘
  │  │  GND  ─────────────────────────── GND ─── ┤  └──────────────┘
  │  │  GND  ─────────────────────────── SDO ────┘   (addr 0x68)
  │  │
  │  └────────────────────────────────────────────┘
  └──────┘
```

**Sơ đồ breadboard (mô phỏng thực tế):**

```
  3V3 ──┬──────────────────────────────── VCC BMI160
        │
        ├── (để trống nếu LED 3.3V)
        │
  GND ──┼──────────────────────────────── GND BMI160
        ├──────────────────────────────── SDO BMI160  → addr I2C = 0x68
        ├──────────────────────────────── LED xanh  cathode (−)
        ├──────────────────────────────── LED vàng  cathode (−)
        ├──────────────────────────────── LED đỏ    cathode (−)
        ├──────────────────────────────── Buzzer     cực âm (−)
        └──────────────────────────────── Nút nhấn  chân 2

  GPIO 4 ────[220Ω]──── LED xanh  anode (+)
  GPIO 5 ────[220Ω]──── LED vàng  anode (+)
  GPIO 6 ────[220Ω]──── LED đỏ    anode (+)

  GPIO 7  ─────────────────────────────── Buzzer 5V  cực dương (+)
  (nếu buzzer cần 5V: dùng transistor NPN,
   Base = GPIO 7 qua R 1kΩ, Collector = Buzzer(+), Emitter = GND,
   Buzzer(−) nối 5V/VBUS)

  GPIO 8 (SDA) ─────────────────────────── SDA BMI160
  GPIO 9 (SCL) ─────────────────────────── SCL BMI160

  GPIO 10 ─────────────────────────────── Nút nhấn  chân 1
              (PULLUP nội bộ, không cần R ngoài)
```

**Lưu ý LED:**
- Chân **dài** = Anode (+) → nối GPIO (qua R 220 Ω)
- Chân **ngắn** / phía có vạt phẳng trên thân LED = Cathode (−) → GND

**Lưu ý Buzzer:**
- Nếu là **active buzzer**: GPIO 7 → (+), GND → (−). Dùng `digitalWrite` thay `tone()`.
- Nếu là **passive buzzer** (như trường hợp hiện tại): GPIO 7 drive bằng `tone(7, 2300)`.
- Nếu buzzer yêu cầu nguồn 5V và dòng >20 mA: thêm transistor NPN như ghi chú phía trên.

---

## 4. Ghi chú GPIO ESP32-S3 đã/đang dùng & dự trữ

| GPIO | Trạng thái | Mục đích                                  |
| ---- | ---------- | ----------------------------------------- |
| 0    | strapping  | Boot — **không dùng**                     |
| 3    | strapping  | JTAG select — tránh                       |
| 4    | **dùng**   | LED xanh                                  |
| 5    | **dùng**   | LED vàng                                  |
| 6    | **dùng**   | LED đỏ                                    |
| 7    | **dùng**   | Buzzer                                    |
| 8    | **dùng**   | I2C SDA — BMI160 (có thể chia sẻ thêm cảm biến I2C khác) |
| 9    | **dùng**   | I2C SCL — BMI160                          |
| 10   | **dùng**   | Nút nhấn (INPUT_PULLUP)                   |
| 11–18, 21, 35–42 | trống | I/O thông dụng — dùng được          |
| 19, 20 | USB     | USB D−/D+ — **không dùng cho I/O**        |
| 45, 46 | strapping | Boot mode — tránh nếu có thể            |
| 48   | LED nội    | LED RGB onboard của DevKitM-1             |

---

## 5. Khi thay đổi sơ đồ chân

Sửa khối `PIN CONFIG` ở đầu [`src/main.cpp`](../src/main.cpp):

```cpp
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_BUZZER     = 7;
static const int PIN_BUTTON     = 10;
static const int PIN_I2C_SDA    = 8;
static const int PIN_I2C_SCL    = 9;
```

Cập nhật bảng ở §1 và §4 cho khớp.
