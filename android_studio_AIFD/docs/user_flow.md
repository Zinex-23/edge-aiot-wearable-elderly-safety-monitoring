# Sơ đồ hành động hệ thống AIFD
> Song song: **hành vi người dùng** (trái) ↔ **trạng thái hệ thống** (phải)  
> Mũi tên ngang = quan hệ nhân quả giữa hai bên

---

## Sơ đồ 1 — Theo dõi & phát hiện ngã

```mermaid
flowchart LR

    subgraph U1 ["👤  NGƯỜI DÙNG"]
        direction TB
        u1([Đeo thiết bị])
        u2["Đứng yên / nghỉ ngơi"]
        u3["Di chuyển bình thường"]
        u4["Di chuyển đều — 3 chu kỳ"]
        u5["Bị va chạm bất ngờ rất mạnh"]
        u6a["Vẫn cử động mạnh sau đó"]
        u6b["Nằm yên tại chỗ"]
        u7["Nằm im liên tục trên 5 giây"]

        u1 --> u2 --> u3 --> u4 --> u5
        u5 --> u6a
        u5 --> u6b
        u6b --> u7
    end

    subgraph S1 ["⚙️  HỆ THỐNG"]
        direction TB
        s1(["⚫⚫⚫  Khởi động"])
        s2["⚫⚫⚫  LED IDLE\nChờ chuyển động"]
        s3["🟢🟡🔴  LED MOVING\nGhi nhận, tích lũy 3 chu kỳ"]
        s4["🟢⚫⚫  LED ACTIVE\nSẵn sàng phân tích ngã"]
        s5["🟢🟡🔴  LED AI FALL\nAI xác định dấu hiệu ngã"]
        s6a["⚫⚫⚫  Hủy — về IDLE\nNgười vẫn bình thường"]
        s6b["💡💡💡  LED BLINK WATCH\nKiểm tra nằm im — tối đa 10 giây"]
        s7["💡💡💡 🔊  LED ALARM\nXác nhận ngã thật — gửi ALERT → App"]

        s1 --> s2 --> s3 --> s4 --> s5
        s5 --> s6a
        s5 --> s6b
        s6b --> s7
    end

    u1 --> s1
    u5 --> s5
    u6a --> s6a
    u7 --> s7
```

---

## Sơ đồ 2 — Phản hồi khi có báo động

```mermaid
flowchart LR

    subgraph U2 ["👤  NGƯỜI DÙNG"]
        direction TB
        ua(["Nghe còi kêu\nThấy đèn nhấp nháy\nApp hiện cảnh báo"])
        ub1["Nhấn nút trên thiết bị"]
        ub2["Bấm TÔI AN TOÀN trên app"]
        ub3["Bấm GỌI CỨU HỘ trên app"]
        ub4["Không phản hồi trong 15 giây"]
        uc1(["✅ An toàn — hết cảnh báo"])
        uc2(["📞 Thực hiện gọi khẩn cấp"])

        ua --> ub1
        ua --> ub2
        ua --> ub3
        ua --> ub4
        ub1 --> uc1
        ub2 --> uc1
        ub3 --> uc2
        ub4 --> uc2
    end

    subgraph S2 ["⚙️  HỆ THỐNG"]
        direction TB
        sa(["💡💡💡 🔊  LED ALARM đang hoạt động\nBLE đã gửi ALERT — App đếm ngược 15 giây"])
        sb1["Nhận tín hiệu nút từ thiết bị\ngửi SAFE về App"]
        sb2["Nhận lệnh SAFE\ntừ App"]
        sb3["Nhận lệnh GỌI\ntừ App"]
        sb4["Hết 15 giây\nkích hoạt tự động"]
        sc1(["🔇 Tắt còi\n⚫⚫⚫ Đèn về bình thường\nReset hệ thống"])
        sc2(["📞 App gọi\nsố khẩn cấp"])

        sa --> sb1
        sa --> sb2
        sa --> sb3
        sa --> sb4
        sb1 --> sc1
        sb2 --> sc1
        sb3 --> sc2
        sb4 --> sc2
    end

    ua --> sa
    ub1 --> sb1
    ub2 --> sb2
    ub3 --> sb3
    ub4 --> sb4
```

---

## Sơ đồ 3 — Kích hoạt SOS thủ công

```mermaid
flowchart LR

    subgraph U3 ["👤  NGƯỜI DÙNG"]
        direction TB
        ud["Nhấn nút khi hệ thống\nđang ở trạng thái bình thường"]
        ue["Muốn gọi trợ giúp khẩn cấp\nmà không chờ phát hiện tự động"]
        ud --> ue
    end

    subgraph S3 ["⚙️  HỆ THỐNG"]
        direction TB
        sd["Nhận tín hiệu nút\n— không có alarm đang chạy"]
        se(["💡💡💡 🔊  LED ALARM\nGửi ALERT → App ngay lập tức\nApp đếm ngược 15 giây"])
        sd --> se
    end

    ud --> sd
    ue --> se
```

---

## Bảng tương ứng nhanh

| Hành vi người dùng | Đèn trên thiết bị | Trạng thái hệ thống |
|---|:---:|---|
| Đứng yên / nghỉ ngơi | ⚫⚫⚫ | IDLE — chờ chuyển động |
| Di chuyển nhẹ (1–2 chu kỳ) | 🟢🟡🔴 | MOVING — đang tích lũy |
| Di chuyển đều 3 chu kỳ trở lên | 🟢⚫⚫ | ACTIVE — sẵn sàng phân tích |
| Va chạm mạnh bất ngờ | 🟢🟡⚫ → 🟢🟡🔴 | AI đang chạy → xác định dấu hiệu ngã |
| Vẫn cử động mạnh sau va chạm | ⚫⚫⚫ | Hủy — người bình thường |
| Nằm yên — đang kiểm tra | 💡💡💡 | BLINK WATCH — đo thời gian nằm im |
| Nằm im đủ 5 giây | 💡💡💡 🔊 | **ALARM — gửi cảnh báo về App** |
| Nhấn nút khi có còi | ⚫⚫⚫ | Gửi SAFE → App — reset hệ thống |
| Nhấn nút khi bình thường | 💡💡💡 🔊 | **SOS thủ công — gửi ALERT → App** |
