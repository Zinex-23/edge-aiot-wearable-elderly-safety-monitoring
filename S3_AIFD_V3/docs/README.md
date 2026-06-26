# S3_AIFD_V3 — Docs

## Tổng quan

Firmware V3 kế thừa toàn bộ V1 (BMI160 + TFLite V84 + BLE + LED FSM) và bổ sung:
- WiFi + Firebase RTDB streaming realtime
- Khi Firebase `/status` = `"fall"` → nhảy thẳng vào `STILL_TIMING` (bỏ qua FALL_WATCH)
- Nhấn nút SAFE → ghi `"non-fall"` lên Firebase + BLE SAFE

## Firebase RTDB

- URL: `https://hospicare-91930-default-rtdb.asia-southeast1.firebasedatabase.app/`
- Path: `/status`
- Giá trị: `"fall"` hoặc `"non-fall"`
