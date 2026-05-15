# UI/UX Analysis & Mapping — AIFD Upgrade

**Tạo bởi:** Phân tích từ source code thực tế (clone shallow, đọc file)  
**Mục đích:** Map các pattern UI hay từ 4 repo tham khảo vào dự án AIFD mà KHÔNG phá logic hiện tại.  
**Trạng thái baseline build:** ✅ `./gradlew assembleDebug` đã pass trước khi bắt đầu.  
**Branch làm việc:** `ui-upgrade-syncsense-inspired`  
**Repo SOS bên ngoài (RapidAid-SOS-App):** ❌ KHÔNG clone, KHÔNG tham khảo. FallAlertScreen hiện tại giữ nguyên là chính.

---

## 1. Tổng quan style từng repo

### 1.1 SyncSense_Health_App ⭐ NGUỒN CẢM HỨNG CHÍNH
- **Tech:** Kotlin · Jetpack Compose · Material 3 · Hilt · Firestore
- **Style:** Health/wellness app với floating rounded bottom bar + tách FAB sang phải
- **Điểm mạnh:**
  - **`FloatingSyncSenseBottomBar`** — Pill bar (`RoundedCornerShape(999.dp)`) + FAB tròn riêng biệt phía phải, có shadow ambient/spot
  - **Card layout:** `RoundedCornerShape(24.dp)`, padding 16-18dp, title 17sp Bold (`#1A1A2E`), subtitle 13sp gray (`#6B6B8A`)
  - **Animation:** `animateColorAsState` + `animateDpAsState` cho selected icon size, durationMillis 240ms easing `FastOutSlowInEasing`
  - **Background:** Soft pastel container color (`Color(0x03E99597)` = teal/pink rất nhạt)
  - **Insight cards** (BodySignalsCard, CycleTrendsCard, LifestyleImpactCard, BodyMetabolicCard) — donut chart, line chart, stat grid trong card trắng
- **Điểm yếu / không copy:**
  - Color.kt chỉ là Material3 default (purple) — không phải health palette → KHÔNG copy
  - HomeScreen còn rỗng ("yet to be developed") → chỉ học pattern bottom bar, không học HomeScreen
  - Dùng `painterResource(R.drawable.X)` cho icon → AIFD dùng Material Icons Extended (tốt hơn vì không cần asset)
  - Dependency: Hilt + Firebase Firestore → AIFD KHÔNG dùng, không thêm dependency này

### 1.2 careconnect-mobile
- **Tech:** Kotlin · Jetpack Compose · Material 3 · Firebase (Auth + Firestore)
- **Style:** Role-based care app (Family / Caregiver / Admin / Old Adult)
- **Điểm mạnh:**
  - **Multi-role flow rõ ràng** — Family/Caregiver có dashboard riêng → cảm hứng cho AIFD's Wearer/Caregiver
  - Tách screen theo role: `family/`, `caregiver/`, `admin/` packages
  - Pattern: Dashboard → Patients list → Patient detail → Alerts → Profile
- **Điểm yếu / không copy:**
  - Color.kt cũng chỉ là Material3 default (purple) → không có palette riêng
  - Firebase Auth + Firestore là backend cứng — AIFD dùng SharedPreferences, KHÔNG copy
  - Admin role không liên quan AIFD (chỉ có Wearer/Caregiver)

### 1.3 healthConnectJetpackCompose
- **Tech:** Kotlin · Jetpack Compose · Material 3 · Health Connect SDK
- **Style:** Health metric viewer đơn giản
- **Điểm mạnh:**
  - **`HealthCard`** component — icon + title + latestData + latestDate trong rounded card
  - **`Greetings`** component — pattern greeting card
  - Cách cấu trúc Dashboard tối giản: greeting + grid of metric cards
- **Điểm yếu / không copy:**
  - Style hơi đơn giản (LightGray background, RoundedCornerShape(8.dp)) — AIFD muốn premium hơn → chỉ lấy structure, không lấy style
  - Dùng Health Connect SDK → KHÔNG copy (AIFD dùng BLE trực tiếp)

### 1.4 ComposeCharts ⚠️ KHẢ NĂNG KHÔNG TƯƠNG THÍCH
- **Tech:** Kotlin Multiplatform · Compose
- **Yêu cầu:** Kotlin **2.0.0**
- **AIFD hiện tại:** Kotlin **1.9.20** (Compose Compiler 1.5.5)
- **Quyết định:** ❌ **SKIP dependency này** — version mismatch sẽ gây lỗi build/compile. Rủi ro quá cao cho production.
- **Phương án thay thế:** **Refactor `Charts.kt` hiện tại** thành các component sạch hơn:
  - `AifdChartCard` (wrapper)
  - `AifdLineChart` (Canvas-based, đã có sẵn — chỉ cleanup)
  - `AifdEmptyChartState`
  - Tăng cường defensive code: empty list, all-zero, null, size=1

---

## 2. Mapping cụ thể từng màn hình

| Screen | Hiện trạng | Mapping nâng cấp | Nguồn cảm hứng | Phá logic? |
|--------|-----------|------------------|----------------|------------|
| **LoginScreen** | Form đơn giản, không có card | Bọc form vào card bo 24dp, icon trong TextField, button rõ | SyncSense card style | ❌ Giữ logic hardcoded user, SharedPreferences |
| **RegisterScreen** | Form dài | Chia section "Người đeo" / "Người chăm sóc", spacing tốt hơn | CareConnect role split | ❌ Giữ logic auto-login sau register |
| **RoleSelectionScreen** | Đã có 2 card chọn role | Card lớn hơn, icon to, mô tả rõ về quyền của từng role | CareConnect role flow | ❌ Giữ logic SharedPreferences `user_role` |
| **HomeScreen** ⭐ | Dashboard cơ bản | Greeting card + Device card + 2 health metric card + Steps card + Alert summary | SyncSense card layout + HealthCard pattern | ❌ Giữ HomeViewModel.uiState, BLE pipeline |
| **MonitoringScreen** ⭐ | HR/SpO2 tab + chart | Cleanup chart vào `AifdChartCard`, empty state đẹp, current value card nổi bật | Refactor Charts.kt hiện tại | ❌ Giữ MonitoringViewModel + VitalsStore + sensorData flow |
| **HistoryScreen** | List event | List card M3, icon theo EventType, badge status, empty state | SyncSense card spacing | ❌ Giữ AlertViewModel.fallEvents |
| **SettingsScreen** | Đã có grouped card | Tinh chỉnh: thêm "Danger Zone" section cho Clear Data + Logout, icon row chuẩn hơn | Standard M3 settings | ❌ Giữ tất cả SharedPreferences keys |
| **FallAlertScreen** 🔒 | Đã có UI tốt (countdown ring, pulse animation, red theme) | **CHỈ tinh chỉnh nhẹ nếu cần** — verify navigator mới không che, đảm bảo theme dark/light hoạt động | **KHÔNG tham khảo repo ngoài** | ❌ Giữ 100% logic: countdown, I'm Safe, Call for Help, auto call |
| **DevicePairingScreen** | List device cơ bản | Card list, RSSI badge, loading state | Standard M3 list | ❌ Giữ BLE scan logic, MAC fallback |
| **DeviceDetailScreen** | Detail cơ bản | Section card layout, status badge | Standard M3 detail | ❌ Giữ rename/disconnect/reconnect logic |
| **ProfileScreen** | Form cơ bản | Section card cho profile fields | CareConnect profile | ❌ Giữ onUpdateProfile callback |

### 🔑 Bottom Navigator — Trọng tâm thay đổi

**Hiện tại (AppNavigation.kt):**
```
NavigationBar (M3 standard) với 4 item: Home / Health / Alerts / Settings
+ pill indicator background cho selected
```

**Mới (theo SyncSense pattern):**
```
┌──────────────────────────────────────────────────┬─────┐
│   [Home] [Health] [Alerts] [Settings]            │ SOS │
│   ●pill bar (RoundedCornerShape 999dp)           │ ○FAB│
│   white, elevation 10dp, ambient/spot shadow     │ red │
└──────────────────────────────────────────────────┴─────┘
```

- **Pill bar (trái, weight=1):** 4 tab, white container, RoundedCornerShape(999dp), elevation 10dp
  - Icon + label, animateDpAsState cho selected size (25→27dp), animateColorAsState cho color
  - Selected: black icon + label SemiBold; Unselected: gray (#9D9D9D)
- **SOS button (phải, fixed size):** circle, 76dp, error/red container, elevation 14dp
  - Icon Phone hoặc Warning, kích thước 52% của FAB
  - Bấm → kích hoạt manual emergency flow hiện tại (`alertViewModel.triggerFallAlert()` + `navController.navigate(FallAlert.route)`)
- Padding: 16dp horizontal, 14dp vertical
- Ẩn ở: Login, Register, RoleSelection, FallAlert, DevicePairing, DeviceDetail, EventDetail, Profile

---

## 3. Component cần tạo mới

| Component | Mục đích | Nhận data qua |
|-----------|----------|---------------|
| `AifdFloatingBottomBar` | Pill bar + SOS FAB tổng thể | Items list + selectedRoute + onClickItem + onSosClick |
| `AifdBottomNavItem` | 1 tab trong pill bar | item + selected + onClick |
| `AifdEmergencyNavButton` | SOS FAB tròn bên phải | onClick |
| `AifdHealthMetricCard` | Card HR/SpO2/Steps cho HomeScreen | icon + label + value + unit + status |
| `AifdDeviceStatusCard` | Card thiết bị BLE | DeviceInfo (đã có model sẵn) |
| `AifdGreetingCard` | Card chào (Wearer name / Caregiver name + alertCount) | name + role + alertCount |
| `AifdSectionCard` | Wrapper section trong Settings | title + content slot |
| `AifdSettingsRow` | 1 row trong Settings | icon + title + subtitle + onClick |
| `AifdChartCard` | Wrapper chart + title + range selector | title + chartData + timeRange |
| `AifdEmptyState` | Hiển thị khi chưa có data | icon + title + subtitle + ctaLabel + onCta |
| `AifdEventListItem` | 1 event trong History | FallEvent (đã có model) |
| `AifdRoleCard` | Card chọn Wearer/Caregiver | role + selected + onClick |
| `AifdPrimaryButton` | Button chính (kích thước lớn cho elderly) | label + onClick |
| `AifdDangerButton` | Button đỏ (Clear/Logout/SOS) | label + onClick |

**Quy tắc:**
- Tất cả dùng Material 3 theme
- KHÔNG hard-code màu khi có sẵn `MaterialTheme.colorScheme.X`
- KHÔNG truyền ViewModel xuống component — chỉ truyền data + callbacks
- Đặt trong `app/src/main/java/com/aifd/ui/components/aifd/`

---

## 4. Color palette đề xuất cho AIFD

**Giữ nguyên** `AIFDTheme` hiện tại (`Color.kt`, `Theme.kt`), CHỈ bổ sung tone "soft container":

| Token | Hex | Mục đích |
|-------|-----|---------|
| `surface` (đã có) | M3 default | Card background |
| `surfaceContainerHigh` (đã có) | M3 default | Elevated card |
| `primary` (đã có) | M3 default | Action buttons |
| `error` (đã có) | M3 default | SOS, HR cao |
| `AIFDThemeExt.safe` (đã có) | Green | Status NORMAL |
| `AIFDThemeExt.warning` (đã có) | Yellow | Status LOW |
| ➕ Background screen | M3 `surface` với alpha rất thấp | Nền dashboard mềm |

**Lý do giữ palette hiện tại:**
1. SyncSense và CareConnect đều dùng default Material3 colors → không có gì để học
2. AIFD đã có `AIFDThemeExt` với safe/warning — đủ cho health context
3. Thay palette = rủi ro UI rối, không nhất quán với FallAlertScreen hiện tại

---

## 5. Phần KHÔNG copy từ repo ngoài

| Repo | Phần không copy | Lý do |
|------|----------------|-------|
| SyncSense | Hilt dependency injection | AIFD dùng manual `viewModel(factory)` — thêm Hilt = đại tu architecture |
| SyncSense | Firebase Firestore | AIFD dùng SharedPreferences + BLE local-first |
| SyncSense | painterResource icons | AIFD dùng `material-icons-extended` — không cần thêm drawable |
| SyncSense | HomeScreen hiện trạng | Vẫn chưa code → không có gì để học UI |
| CareConnect | Firebase Auth | AIFD dùng hardcoded credentials trong LoginScreen |
| CareConnect | Multi-tenant admin role | AIFD chỉ Wearer/Caregiver |
| healthConnect | Health Connect SDK | AIFD dùng BLE GATT trực tiếp |
| ComposeCharts | **Toàn bộ dependency** | Kotlin version mismatch (2.0 vs 1.9.20) — quá rủi ro |
| RapidAid-SOS-App | **Toàn bộ** | AIFD's FallAlertScreen đã tốt hơn; user đã chỉ định không tham khảo |

---

## 6. Kế hoạch implement theo từng bước (incremental + build check)

> ✅ = build check sau bước này. ⚠️ = bước rủi ro cao.

### Step A — Foundation (component layer)
1. ✅ Tạo `AifdEmptyState`, `AifdSectionCard`, `AifdSettingsRow`, `AifdHealthMetricCard`
2. ✅ Tạo `AifdFloatingBottomBar` + `AifdBottomNavItem` + `AifdEmergencyNavButton` (chưa wire vào AppNavigation)
3. ✅ Tạo `AifdChartCard` (wrap `LineChart` hiện tại)

### Step B — Bottom Navigator ⚠️
4. ✅ Replace `BottomNavigationBar` cũ trong `AppNavigation.kt` bằng `AifdFloatingBottomBar`
5. ✅ Wire SOS button → `alertViewModel.triggerFallAlert()` + navigate `Screen.FallAlert.route`
6. ✅ Verify ẩn nav trên 8 màn hình quy định
7. ✅ assembleDebug

### Step C — HomeScreen
8. ✅ Refactor `HomeScreen.kt` dùng các component AifdX
9. ✅ Verify `HomeViewModel.uiState` vẫn drive UI đúng (HR/SpO2/device từ BLE)
10. ✅ assembleDebug

### Step D — MonitoringScreen ⚠️ (data critical)
11. ✅ Refactor `MonitoringScreen.kt` chỉ phần UI render — KHÔNG đổi ViewModel
12. ✅ Wrap chart vào `AifdChartCard`, thêm `AifdEmptyState` khi chartData rỗng/all-zero
13. ✅ Test edge case: chart `emptyList()`, `List(12) { 0 }`, mới connect, đổi tab nhanh
14. ✅ assembleDebug

### Step E — HistoryScreen + SettingsScreen
15. ✅ Refactor `HistoryScreen.kt` dùng `AifdEventListItem` + `AifdEmptyState`
16. ✅ Refactor `SettingsScreen.kt` dùng `AifdSectionCard` + `AifdSettingsRow` + thêm Danger Zone
17. ✅ assembleDebug

### Step F — Auth & Role
18. ✅ Refactor `LoginScreen`, `RegisterScreen`, `RoleSelectionScreen` chỉ UI
19. ✅ assembleDebug

### Step G — Device & Profile (low priority)
20. ✅ Tinh chỉnh `DevicePairingScreen`, `DeviceDetailScreen`, `ProfileScreen` nếu còn thời gian
21. ✅ assembleDebug

### Step H — FallAlert verify 🔒
22. ✅ Verify `FallAlertScreen` mở được từ SOS button mới
23. ✅ Verify bottom nav bị ẩn ở `FallAlertScreen`
24. ✅ Verify countdown / I'm Safe / Call for Help / auto call vẫn chạy
25. **KHÔNG redesign**, chỉ tinh chỉnh spacing/typography nếu cần

### Step I — Final
26. ✅ `./gradlew clean`
27. ✅ `./gradlew assembleDebug`
28. ✅ `./gradlew lintDebug` (best-effort)
29. ✅ Viết `UI_UPGRADE_REPORT.md`

---

## 7. Acceptance criteria nhắc lại (theo prompt)

### Build
- ✅ `./gradlew assembleDebug` thành công
- ✅ Không lỗi Kotlin/Compose

### UI/UX
- ✅ Bottom nav mới: `Home | Health | Alerts | Settings | [SOS]`
- ✅ FallAlertScreen giữ UI hiện tại
- ✅ Chart đẹp/ổn định hơn

### Logic (KHÔNG được phá)
- ✅ Login/Register/RoleSelection vẫn hoạt động
- ✅ BLE pipeline: `BleManager → BleForegroundService → MonitoringViewModel → VitalsStore → UI`
- ✅ MonitoringScreen.currentHR/SpO2 từ `sensorData` (cùng nguồn Home)
- ✅ Chart 1H/24H từ `VitalsStore.get1hChart/get24hChart`
- ✅ Clear Health Data reset chart
- ✅ FallAlert: countdown 15s, I'm Safe, Call for Help, auto call

### SharedPreferences keys KHÔNG đổi
```
logged_in, username, user_role, theme_mode, app_language,
device_mac, device_name,
last_heart_rate, last_spo2, last_vital_timestamp,
hr_history, spo2_history,
vitals_5min, vitals_1h
```

### Stability
- ✅ Không crash với data rỗng / all-zero / chưa BLE
- ✅ Không crash khi đổi tab nhanh / Live↔1H↔24H nhanh
- ✅ Không crash khi đổi theme/language/role

---

## 8. Tóm tắt quyết định kỹ thuật

| Quyết định | Lý do |
|------------|-------|
| ✅ Áp dụng SyncSense floating bottom bar pattern | Best in class cho dạng app này |
| ❌ Không thêm Hilt | Architecture đại tu, rủi ro cao |
| ❌ Không thêm Firebase | Khác hệ kiến trúc, phá BLE local-first |
| ❌ Không thêm ComposeCharts | Kotlin version mismatch |
| ✅ Refactor Charts.kt hiện tại | Đã hoạt động, chỉ cần cleanup |
| ❌ Không thay palette màu chính | M3 default + AIFDThemeExt đã đủ; SyncSense/CareConnect cũng dùng default |
| ✅ Material Icons Extended (đã có sẵn) | Không cần thêm drawable assets |
| 🔒 Giữ FallAlertScreen | User đã chỉ định, UI hiện tại đủ tốt |
| ❌ Không clone RapidAid-SOS-App | User đã chỉ định |

---

**Kết luận:** Plan này an toàn cho production. Mọi thay đổi đều ở UI layer, không đụng ViewModel/Service/BleManager/VitalsStore. Mỗi step có build check. FallAlertScreen được bảo vệ. Sẵn sàng implement nếu được xác nhận.
