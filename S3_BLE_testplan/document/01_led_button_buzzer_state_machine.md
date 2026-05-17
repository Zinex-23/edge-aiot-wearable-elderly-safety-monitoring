# 01 — LED + Button + Buzzer State Machine

**Ngày tạo:** 2026-05-15
**File code:** [`src/main.cpp`](../src/main.cpp)
**Mục đích:** Triển khai logic ban đầu cho 3 LED (xanh / vàng / đỏ), 1 nút nhấn và 1 loa buzzer trên ESP32-S3. Mỗi lần nhấn nút sẽ chuyển sang trạng thái kế tiếp theo vòng lặp.

---

## 1. Sơ đồ chân (mặc định)

| Thành phần   | GPIO | Chế độ         | Ghi chú                                |
| ------------ | ---- | -------------- | -------------------------------------- |
| LED xanh     | 4    | OUTPUT         | HIGH = sáng (LED nối anode lên 3V3 thì đảo lại) |
| LED vàng     | 5    | OUTPUT         | HIGH = sáng                             |
| LED đỏ       | 6    | OUTPUT         | HIGH = sáng                             |
| Buzzer       | 7    | OUTPUT (tone)  | Driver bằng `tone()` ở 2300 Hz          |
| Nút nhấn     | 10   | INPUT_PULLUP   | Nhấn = LOW (cạnh xuống). Nối nút giữa GPIO 10 và GND. |

> Các GPIO trên đều an toàn trên ESP32-S3-DevKitM-1 (không phải strapping/USB pin). Có thể đổi pin trong khối `PIN CONFIG` ở đầu `src/main.cpp`.

---

## 2. Sơ đồ đấu nối

```
ESP32-S3
  GPIO 4  ──[R 220Ω]──|>|── GND      (LED xanh)
  GPIO 5  ──[R 220Ω]──|>|── GND      (LED vàng)
  GPIO 6  ──[R 220Ω]──|>|── GND      (LED đỏ)
  GPIO 7  ──────────── (+) Buzzer 5V (−) ── GND
  GPIO 10 ──┬── Nút nhấn ── GND
            └── (PULLUP nội bộ — không cần điện trở ngoài)
```

Lưu ý buzzer: theo datasheet người dùng cung cấp (Loa Buzzer 5V, 2300 Hz ± 500 Hz, <25 mA) ESP32 có thể drive trực tiếp. Nếu thực tế đo dòng >20 mA hoặc loa kêu yếu thì nên dùng transistor NPN (2N2222 / S8050) làm switch:

```
GPIO 7 ──[R 1kΩ]── Base
                   Emitter ── GND
                   Collector ── (−) Buzzer, (+) Buzzer ── 5V
```

---

## 3. State machine

5 trạng thái, vòng tròn: nhấn nút → trạng thái kế tiếp.

| # | Tên trạng thái     | LED xanh | LED vàng | LED đỏ | Buzzer       |
| - | ------------------ | :------: | :------: | :----: | :----------: |
| 0 | `STATE_ALL_ON`     | ON       | ON       | ON     | OFF          |
| 1 | `STATE_GREEN`      | ON       | OFF      | OFF    | OFF          |
| 2 | `STATE_YELLOW`     | OFF      | ON       | OFF    | OFF          |
| 3 | `STATE_RED`        | OFF      | OFF      | ON     | OFF          |
| 4 | `STATE_BLINK_BUZZ` | Nhấp nháy 300 ms | Nhấp nháy | Nhấp nháy | ON (2300 Hz) |

Sau trạng thái 4, nhấn nút sẽ quay về trạng thái 0 (`STATE_ALL_ON`), sau đó là 1, 2, 3, 4, 0 ... lặp lại.

> **Lưu ý:** Trong yêu cầu ban đầu có câu "nhấn thêm nữa thì quay lại trạng thái có mỗi đèn vàng sáng rồi tiếp tục". Hiện đang triển khai theo vòng lặp tự nhiên (`0 → 1 → 2 → 3 → 4 → 0 → 1 → 2 ...`). Nếu thực sự muốn skip green sau khi quay về `ALL_ON` thì báo lại để chỉnh.

---

## 4. Chống nhiễu nút nhấn (debounce)

Dùng kỹ thuật **time-based debouncing** ở phần mềm — đơn giản, không tốn tài nguyên, không cần thư viện:

1. Đọc giá trị nút mỗi vòng `loop()`.
2. Khi giá trị thay đổi so với lần đọc trước → reset timer (`btnLastChange = millis()`).
3. Chỉ chấp nhận trạng thái mới khi giá trị ổn định **liên tục ≥ `DEBOUNCE_MS` (30 ms)**.
4. Chỉ trigger chuyển state ở **cạnh xuống** (HIGH → LOW) — tức lúc người dùng vừa bấm xuống, không phải lúc thả ra.

```cpp
static const unsigned long DEBOUNCE_MS = 30;
```

Có thể tăng giá trị này lên 50 ms nếu nút cơ học cũ/rẻ tiền vẫn còn bounce. Tốt nhất nên kết hợp thêm:

- **Tụ lọc cứng:** 100 nF từ chân nút xuống GND giúp lọc nhiễu RF/EMI tốt hơn.
- **Pull-up:** đã dùng `INPUT_PULLUP` nội bộ (~45 kΩ). Nếu môi trường nhiễu nặng có thể thay bằng pull-up ngoài 10 kΩ.

---

## 5. Buzzer: active vs passive

Ảnh người dùng cung cấp là **Loa Buzzer 5V, 2300 Hz ± 500 Hz**. Có hai khả năng:

| Loại            | Nhận biết                                | Cách drive trong code                              |
| --------------- | ---------------------------------------- | -------------------------------------------------- |
| **Passive**     | Phải drive bằng tín hiệu vuông để phát ra âm | `tone(PIN_BUZZER, 2300)` / `noTone(PIN_BUZZER)`     |
| **Active**      | Cấp điện áp DC là tự kêu (có IC dao động bên trong) | `digitalWrite(PIN_BUZZER, HIGH/LOW)`                |

Hiện code đang dùng `tone()` (lựa chọn an toàn — passive). Nếu loa là active mà nghe có tiếng rè/lạ, sửa 2 hàm trong `main.cpp`:

```cpp
static void buzzerOn()  { digitalWrite(PIN_BUZZER, HIGH); }
static void buzzerOff() { digitalWrite(PIN_BUZZER, LOW);  }
```

---

## 6. Tham số cấu hình nhanh

Tất cả nằm ở đầu `src/main.cpp`:

```cpp
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_BUZZER     = 7;
static const int PIN_BUTTON     = 10;

static const unsigned int  BUZZER_FREQ_HZ     = 2300;  // tần số cộng hưởng buzzer
static const unsigned long DEBOUNCE_MS        = 30;    // ngưỡng chống dội nút
static const unsigned long BLINK_INTERVAL_MS  = 300;   // chu kỳ nhấp nháy ở state 4
```

---

## 7. Build & nạp

```bash
cd S3_BLE
pio run -t upload
pio device monitor   # nếu muốn xem log Serial
```

`platformio.ini` đã có sẵn target `esp32-s3-devkitm-1` và `monitor_speed=115200`.
