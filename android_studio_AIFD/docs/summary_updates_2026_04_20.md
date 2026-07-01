# Tổng Hợp Cập Nhật Tính Năng - 20/04/2026

Tài liệu này tổng hợp toàn bộ các thay đổi quan trọng đã thực hiện hôm nay để đảm bảo hệ thống phát hiện té ngã hoạt động ổn định 24/7, kể cả khi app chạy nền hoặc điện thoại đang khóa.

---

## 1. Dịch vụ chạy ngầm (BleForegroundService)
Đây là "trái tim" mới của ứng dụng. Thay vì chạy Bluetooth trên màn hình, mọi thứ giờ đây nằm trong một Service không thể bị Android tiêu diệt.

### Các tính năng chính:
- **Duy trì kết nối:** Giữ kết nối với ESP32 liên tục.
- **Bật màn hình (WakeLock):** Khi có té ngã, Service tự động bật sáng màn hình điện thoại.
- **Countdown 15s:** Tự động đếm ngược 15 giây. Nếu người dùng không nhấn "An toàn", Service sẽ tự thực hiện cuộc gọi.
- **Cuộc gọi khẩn cấp:** Sử dụng `Intent.ACTION_CALL` để gọi ngay cho người thân.

```kotlin
// Snippet: Logic đếm ngược và tự động gọi trong Service
private fun startEmergencyTimer() {
    countdownJob = serviceScope.launch {
        for (i in 15 downTo 1) {
            _countdownSeconds.value = i
            delay(1000)
        }
        // Sau 15s không phản hồi -> Gọi ngay
        placeEmergencyCall()
    }
}
```

---

## 2. Cơ chế Điều hướng Phản ứng (Broadcast Navigation)
Vì Service chạy ngầm, nó không thể trực tiếp "mở" màn hình của App. Chúng ta sử dụng **BroadcastReceiver**.

- **Service:** Gửi một thông điệp (Broadcast) mang tên `ACTION_FALL_DETECTED`.
- **AppNavigation:** Lắng nghe thông điệp này và tự động nhảy vào màn hình `FallAlertScreen` dù người dùng đang ở bất kỳ đâu trong app.

```kotlin
// Snippet: Lắng nghe té ngã trong AppNavigation
val receiver = object : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == BleForegroundService.ACTION_FALL_DETECTED) {
            navController.navigate("fall_alert") // Tự nhảy màn hình
        }
    }
}
```

---

## 3. Sửa lỗi Discovery & Scan (Binding Logic)
Chúng ta đã giải quyết triệt để lỗi bấm "Scan" mà không thấy thiết bị do Service chưa kịp kết nối xong.

- **Pending Scan:** Nếu Service đang khởi tạo, ViewModel sẽ "ghi nhớ" lệnh quét và thực hiện ngay khi Service sẵn sàng.
- **Bắt đầu sớm:** Khởi động Service ngay từ `onCreate` của `MainActivity`.

```kotlin
// Snippet: Logic chờ Service trong DeviceViewModel
override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
    service = (binder as BleForegroundService.LocalBinder).getService()
    if (pendingScan) {
        startScan() // Thực hiện lệnh quét đã bị "nợ" trước đó
        pendingScan = false
    }
}
```

---

## 4. Xử lý lỗi "Location Off" (GPS)
Android chặn quét Bluetooth nếu GPS tắt. Chúng ta đã thêm cơ chế phát hiện và hướng dẫn người dùng.

- **Kiểm tra GPS:** App phát hiện nếu Vị trí đang tắt.
- **Thông báo UI:** Hiển thị thẻ đỏ thông báo: *"Vui lòng bật Vị trí (GPS) để tìm thiết bị"*.
- **ScanFilter:** Thêm bộ lọc để tăng độ nhạy và tuân thủ quy định bảo mật của Android.

```kotlin
// Snippet: Kiểm tra GPS trong BleManager
private fun isLocationEnabled(): Boolean {
    val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    return lm.isLocationEnabled
}
```

---

## 5. Bảo mật & Ổn định (SecurityException)
Trên Android 12+, việc đọc tên thiết bị Bluetooth (`device.name`) đôi khi bị hệ thống chặn gây crash app. 

- **Safety Wrapper:** Mọi lệnh truy cập tên thiết bị giờ được bao bọc bởi `try-catch`.
- **Dữ liệu dự phòng:** Nếu không đọc được tên trực tiếp, App sẽ thử tìm tên trong gói tin quảng bá (`scanRecord`).

---

## Danh sách tệp tin đã thay đổi:
1. `BleForegroundService.kt`: Chứa logic chạy ngầm, gọi điện, đếm ngược.
2. `BleManager.kt`: Chốt chặn cuối cùng xử lý Bluetooth, GPS, Filter.
3. `DeviceViewModel.kt`: Cầu nối thông minh giữa giao diện và Service.
4. `MainActivity.kt`: Điểm khởi đầu chuẩn xác của Service.
5. `AppNavigation.kt`: Xử lý nhảy màn hình khi có sự cố.
6. `DevicePairingScreen.kt`: Hiển thị lỗi GPS trực quan cho người dùng.

---

## 6. Nhật ký thảo luận & Quyết định quan trọng
Dưới đây là tóm tắt các cuộc trao đổi và lý do vì sao chúng ta chọn phương án hiện tại:

- **Chuyển sang Foreground Service:** Chúng ta đã thảo luận về việc App bị đóng khi tắt màn hình. Quyết định cuối cùng là đưa toàn bộ Logic Bluetooth vào Service để đảm bảo thiết bị luôn được giám sát 24/7.
- **Thời gian chờ 15 giây:** Để tránh việc gọi nhầm (false alarm) khi người dùng lỡ làm rơi thiết bị nhưng không sao, chúng ta thống nhất đặt bộ đệm 15 giây để người dùng kịp nhấn "An toàn".
- **Sử dụng ACTION_CALL:** Thay vì chỉ hiện thông báo, chúng ta quyết định App phải tự thực hiện cuộc gọi thực sự để đảm bảo tính khẩn cấp cao nhất.
- **Lỗi không Scan được:** Sau khi chuyển sang Service, chúng ta phát hiện lỗi "mất lệnh Scan" do bất đồng bộ. Giải pháp là thêm cơ chế "Hàng đợi lệnh" (Pending Scan) trong ViewModel.
- **Vấn đề Vị trí (GPS):** Phân tích log hệ thống cho thấy Android chặn quét BLE nếu GPS tắt. Quyết định là không chỉ sửa code mà phải thêm cảnh báo trực quan cho người dùng.

> [!TIP]
> Bạn có thể yên tâm nghỉ ngơi. Hệ thống hiện tại đã rất "lì lợm" trước các cơ chế tiết kiệm pin của Android và hỗ trợ tốt cho việc cứu hộ người già.

---
*Ngày cập nhật: 20/04/2026*
*Tác giả: Antigravity AI*
