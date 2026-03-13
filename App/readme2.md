# Elderly Health Monitor - README sử dụng source

## 1. Tổng quan
Đây là ứng dụng Flutter đa nền tảng (Android/iOS/Web/Linux) để hiển thị dashboard theo dõi sức khỏe người lớn tuổi từ dữ liệu thiết bị đeo.

Hiện tại dự án đang dùng **mock data** nội bộ (`lib/data/mock_health_data.dart`) qua service giả lập (`HealthMonitorService`) để mô phỏng dữ liệu realtime.

## 2. Công nghệ chính
- Flutter + Dart (SDK trong `pubspec.yaml`: `^3.11.1`)
- Quản lý state: `provider`
- Vẽ biểu đồ: `fl_chart`
- Format thời gian: `intl`

## 3. Chạy dự án
Từ thư mục `App`:

```bash
flutter pub get
flutter run
```

Một số lệnh hữu ích:

```bash
flutter run -d chrome      # chạy web
flutter run -d android     # chạy Android (nếu đã có emulator/device)
flutter test               # chạy test widget
```

## 4. Cấu trúc code chính

```text
App/
  lib/
    main.dart                  # Entry point
    app.dart                   # Khởi tạo MaterialApp + MultiProvider

    data/
      mock_health_data.dart    # Dữ liệu mẫu cho toàn bộ dashboard

    models/                    # Data model + enum nghiệp vụ
      dashboard_snapshot.dart
      elderly_profile.dart
      health_alert.dart
      health_metric_point.dart
      activity_hour.dart
      health_enums.dart

    services/
      health_monitor_service.dart  # Service fetch dữ liệu (đang trả mock)

    providers/
      health_provider.dart      # Load/refresh dashboard state
      theme_provider.dart       # Light/Dark mode

    screens/
      main_shell.dart           # Bottom navigation + loading/error state
      home_dashboard_screen.dart
      health_screen.dart
      activity_screen.dart
      alerts_screen.dart
      emergency_screen.dart
      profile_screen.dart
      metrics/
        resting_heart_rate_screen.dart
        hrv_screen.dart
        spo2_screen.dart

    widgets/                    # UI components tái sử dụng
      premium_card.dart
      metric_card.dart
      metric_line_chart.dart
      activity_bar_chart.dart
      progress_ring.dart
      screen_header.dart
      status_chip.dart
      ...

    theme/
      app_theme.dart
      app_colors.dart
      app_text_styles.dart
      app_spacing.dart
      status_palette.dart

  test/
    widget_test.dart
```

## 5. Luồng dữ liệu và điều hướng
1. `main.dart` chạy `ElderlyHealthMonitorApp`.
2. `app.dart` khởi tạo 2 provider:
   - `HealthProvider(service: HealthMonitorService())..loadDashboard()`
   - `ThemeProvider()`
3. `MainShell` nhận state từ `HealthProvider`:
   - Đang load: hiện `_LoadingView`
   - Lỗi: hiện `_ErrorView` + nút Retry
   - Có dữ liệu: render 5 tab (`Home`, `Health`, `Activity`, `Alerts`, `Profile`)
4. Các màn hình con dùng chung `DashboardSnapshot` để hiển thị metric, alert, chart.

## 6. Chức năng theo màn hình
- `Home`: dashboard tổng hợp, refresh dữ liệu, mở nhanh chi tiết metric và cảnh báo khẩn.
- `Health`: tổng quan sức khỏe + truy cập 3 màn hình metric chuyên sâu.
- `Activity`: bước chân, active minutes, calories, distance, biểu đồ theo giờ.
- `Alerts`: danh sách cảnh báo; cảnh báo `isEmergency=true` mở `EmergencyScreen`.
- `Profile`: thông tin hồ sơ, bệnh sử, trạng thái wearable, đổi Light/Dark mode.

## 7. Cách thay mock data bằng dữ liệu thật
Điểm thay đổi chính:
1. Sửa `lib/services/health_monitor_service.dart` để gọi API/Bluetooth/local DB thật.
2. Chuyển response về `DashboardSnapshot` (hoặc map qua DTO trước).
3. Giữ nguyên `HealthProvider` và UI nếu contract model không đổi.

Gợi ý triển khai:
- Tách `HealthMonitorService` thành interface + implementation (`Mock` / `Api`).
- Thêm xử lý timeout/retry chi tiết trong `loadDashboard`.
- Có thể thêm persistence cache cho trạng thái offline.

## 8. Kiểm thử và lưu ý
- Test hiện có: `test/widget_test.dart` kiểm tra dashboard render sau khi load.
- Trong môi trường mình chạy, lệnh `flutter` chưa có sẵn (`flutter: command not found`), nên chưa xác nhận build/test thực tế tại máy này.
- Android package mặc định hiện là `com.example.elderly_health_monitor`; nên đổi trước khi phát hành.

