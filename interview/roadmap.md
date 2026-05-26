# Lộ Trình Học Embedded (Từ Cơ Bản Đến Dự Án CaraFall)

Bảng kỹ năng C mà bạn đang theo học là **cực kỳ chuẩn xác** và là "kim chỉ nam" cho dân lập trình Embedded. Để giúp bạn có động lực, tôi sẽ chỉ ra chính xác những kiến thức trong bảng đó đã được dùng ở đâu trong file `main.cpp` của bạn, sau đó vẽ ra lộ trình tiếp theo để bạn làm chủ toàn bộ dự án này.

---

## GIAI ĐOẠN 1: Làm chủ Ngôn ngữ C (Áp dụng ngay vào dự án của bạn)

Hãy tiếp tục học theo bảng của bạn, nhưng mỗi khi học xong 1 phần, hãy mở file `main.cpp` ra để đối chiếu:

### 1. Pointer (Con trỏ) & Array/String
*   **Học gì:** Hiểu sự khác biệt giữa truyền giá trị và truyền địa chỉ (`&`). Hiểu mảng thực chất là con trỏ. Chuỗi C (C-string) kết thúc bằng `\0`.
*   **Dùng ở đâu trong code:**
    *   Hàm `readRegs(uint8_t reg, uint8_t *buf, size_t len)`: Truyền con trỏ `buf` vào để hàm tự động ghi dữ liệu cảm biến vào mảng mà không cần `return` (rất tiết kiệm RAM).
    *   Gửi BLE: `gCharAlert->setValue((uint8_t*)payload, strlen(payload))`. Ép kiểu chuỗi ký tự thành mảng byte để gửi đi.

### 2. Struct & Enum
*   **Học gì:** Cách gom nhóm dữ liệu (Struct) và định nghĩa các trạng thái (Enum).
*   **Dùng ở đâu trong code:**
    *   **Struct:** `struct ImuSample { float ax... float gx... uint32_t tsMs }`. Thay vì tạo 7 mảng rời rạc, bạn gom nó thành 1 gói duy nhất.
    *   **Enum:** `enum LedState { LED_IDLE, LED_MOVING... }` và `enum FallDetectState`. Đây chính là cốt lõi của **State Machine** (Cỗ máy trạng thái) mà bạn dùng để chống báo động giả.

### 3. Memory Management (Quản lý bộ nhớ) & Static/Volatile/Const
*   **Học gì:** Sự nguy hiểm của `malloc/free` (Heap) trong MCU. Ý nghĩa của `static` (biến giữ nguyên giá trị), `volatile` (báo cho compiler không tối ưu biến này vì nó có thể thay đổi bất ngờ bởi phần cứng/ngắt).
*   **Dùng ở đâu trong code:**
    *   **Static Memory:** `uint8_t tensorArena[kTensorArenaSize]`. Phân bổ tĩnh 60KB cho AI thay vì dùng `malloc` để tránh Memory Leak.
    *   **Volatile:** `static volatile bool gFallAlertActive = false;`. Biến này bị thay đổi đột ngột bởi luồng TFLite hoặc Nút bấm, nên phải có `volatile` để chương trình luôn đọc giá trị mới nhất từ RAM.

### 4. Bitwise (Thao tác bit)
*   **Học gì:** Dịch bit `<<`, `>>`, OR `|`, AND `&`.
*   **Dùng ở đâu trong code:**
    *   Hàm ghép byte I2C: `(int16_t)((msb << 8) | lsb)`. Cảm biến gửi gia tốc dưới dạng 2 byte rời rạc (High và Low). Dịch trái byte High 8 bit rồi ghép (OR) với byte Low để ra số 16 bit hoàn chỉnh.

---

## GIAI ĐOẠN 2: Lập trình Ngoại vi Cơ bản (Peripheral / Bare-metal)

Sau khi vững C, hãy học cách điều khiển phần cứng của vi điều khiển (dùng Arduino Framework hoặc ESP-IDF cơ bản):

1.  **GPIO (General Purpose Input/Output):** 
    *   Học cách chớp LED (`digitalWrite`), đọc nút bấm (`digitalRead`).
    *   **Nâng cao:** Kỹ thuật **Debounce** (Chống dội phím) bằng phần mềm (dùng `millis()`). Code của bạn có hàm `handleButton()` xử lý debounce rất chuẩn!
2.  **Giao thức I2C (Inter-Integrated Circuit):**
    *   Học nguyên lý: Master-Slave, địa chỉ thiết bị, chân SDA (Data) và SCL (Clock).
    *   Đọc datasheet của một cảm biến bất kỳ (như BMI160) để biết cách ghi vào thanh ghi `REG_CMD` và đọc thanh ghi `REG_ACC_DATA`.

---

## GIAI ĐOẠN 3: Lập trình Hệ điều hành Thời gian thực (FreeRTOS)

Đây là bước ngoặt từ một "tay mơ" thành một kỹ sư Embedded thực thụ.

1.  **Task (Luồng/Tiến trình):** 
    *   Hiểu cách OS chia sẻ thời gian CPU (Time Slicing).
    *   Thực hành hàm `xTaskCreatePinnedToCore`. Hiểu về Priority (Độ ưu tiên).
2.  **Đồng bộ hóa (Synchronization):**
    *   **Mutex & Semaphore:** Học cách giải quyết bài toán Race Condition khi nhiều Task cùng truy cập 1 biến (như cách bạn dùng `gImuMutex` cho Ring Buffer).
3.  **Giao tiếp giữa các Task (Inter-Task Communication):**
    *   **Task Notifications:** Kỹ thuật đánh thức Task khác (`xTaskNotifyGive` và `ulTaskNotifyTake` trong code của bạn). Rất nhẹ và nhanh.
    *   **Queues (Hàng đợi):** Mặc dù dự án này bạn dùng Ring Buffer + Mutex tự viết, nhưng Queue của FreeRTOS cũng là một khái niệm bắt buộc phải học.

---

## GIAI ĐOẠN 4: Công Nghệ Nâng Cao (AI & Connectivity)

Giai đoạn này đòi hỏi bạn đọc hiểu tài liệu tiếng Anh và mã nguồn mở nhiều hơn:

1.  **Bluetooth Low Energy (BLE):**
    *   Hiểu khái niệm GAP (Quảng bá - Advertising) và GATT (Kết nối).
    *   Tìm hiểu cấu trúc cây: Server -> Service (UUID) -> Characteristic (Read/Write/Notify).
    *   Thực hành dùng thư viện NimBLE thay vì thư viện BLE mặc định.
2.  **Edge AI (TinyML / TensorFlow Lite Micro):**
    *   Hiểu khái niệm "Quantization" (Lượng tử hóa). Tại sao MCU không thích số thập phân (float) mà thích số nguyên (int8).
    *   Thực hành convert mô hình Python (`.tflite`) thành mảng C (C-array).
    *   Tìm hiểu cách khởi tạo `MicroInterpreter` và cấp phát `Tensor Arena`.

**Lời khuyên:** Đừng cố học mọi thứ cùng lúc. Hãy code từng module nhỏ: Hôm nay chỉ chớp LED -> Ngày mai chỉ đọc I2C in ra Serial -> Tuần sau thử nhét I2C vào Task FreeRTOS... Cứ thế bạn sẽ ráp được dự án lớn này!
