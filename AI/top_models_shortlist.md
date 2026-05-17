# Top Models Shortlist — V1 đến V80

**Ngày:** 2026-05-16 | **Chọn từ:** 80 model đã train

Bảng dưới chọn ra **7 model tốt nhất**, mỗi cái phục vụ một mục tiêu cụ thể. Không có model nào tốt nhất cho mọi trường hợp — chọn theo ưu tiên của deployment.

---

## Bảng so sánh 7 model được chọn

| Hạng | Version | Architecture | Acc | Recall | F1 | FAR | Miss | Size | Mục tiêu |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 🥇 | **V84** | [32,64,64,96]/K3/D32 + aug σ=0.05 | **93.10%** | **98.51%** | **93.45%** | 12.31% | **1.49%** | 62.1 KB | Best Overall (V1–V90) |
| 🥈 | **V80** | [32,64,64,96]/K3/D32 + L2=3e-4 + batch=32 | 93.10% | 97.39% | 93.38% | **11.19%** | 2.61% | 62.1 KB | Runner-up — FAR thấp hơn V84 |
| 🥉 | **V64** | [32,64,64,96]/K3/D32 + batch=32 | 92.91% | 96.64% | 93.17% | **10.82%** | 3.36% | 62.1 KB | FAR thấp nhất nhóm top-F1 |
| 👁️ | **V35** | [32,64,64,96]/K3/D16 + CW=1.2 | 92.16% | **98.51%** | 92.63% | 14.18% | **1.49%** | 42.7 KB | Safety-first — ít bỏ sót nhất |
| ⚡ | **V59** | [32,48,64,96]/K5/D20 + batch=32 | 92.16% | 92.54% | 92.19% | **8.21%** | 7.46% | 77.2 KB | Ít false alarm nhất (Recall>90%) |
| 📦 | **V22** | [16,32,48,64]/K5/D16 | 92.35% | 94.78% | 92.53% | 10.07% | 5.22% | **34.5 KB** | Compact nhất — F1>92% |
| 🪶 | **V1** | [16,32]/K3/D16 (Balanced V2) | 90.80% | 98.36% | 91.43% | 16.73% | 1.64% | **10.7 KB** | Ultra-compact — Flash hạn chế |

---

## Hướng dẫn chọn model

```
Bạn cần gì?
│
├─ Hiệu năng tổng thể tốt nhất
│      → V84 (F1=93.45%, Recall=98.51%) ← RECOMMENDED
│
├─ Ít false alarm nhất (FAR thấp) mà Recall vẫn >95%
│      → V64 (FAR=10.82%, Recall=96.64%)
│
├─ Ít false alarm nhất mà Recall chỉ cần >90%
│      → V59 (FAR=8.21%, Recall=92.54%)
│
├─ Không được bỏ sót cú ngã nào (safety-first, Recall >98%)
│      → V35 (Recall=98.51%, Miss=1.49%)
│      hoặc V1 (Recall=98.36%, Size=10.7KB nếu cần nhỏ)
│
├─ Flash hạn chế (<50KB)
│      → V22 (34.5KB, F1=92.53%) ← compact tốt nhất
│      → V35 (42.7KB, Recall=98.51%) ← nếu ưu tiên recall
│
└─ Flash rất hạn chế (<15KB)
       → V1/Balanced V2 (10.7KB, F1=91.43%)
```

---

## Deploy từng model lên ESP32-S3

Chỉ cần thay 2 dòng trong `S3_BLE/`:

**`platformio.ini`**
```ini
build_flags =
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
    -I ../AI/model_updated_version_XX/models   ; ← đổi XX
```

**`src/main.cpp`**
```cpp
#include "fall_detection_vXX.h"   // ← đổi XX
```

| Model | Folder | Include file |
|---|---|---|
| V84 | `model_updated_version_84/models/` | `fall_detection_v84.h` |
| V80 | `model_updated_version_80/models/` | `fall_detection_v80.h` |
| V64 | `model_updated_version_64/models/` | `fall_detection_v64.h` |
| V54 | `model_updated_version_54/models/` | `fall_detection_v54.h` |
| V35 | `model_updated_version_35/models/` | `fall_detection_v35.h` |
| V59 | `model_updated_version_59/models/` | `fall_detection_v59.h` |
| V22 | `model_updated_version_22/models/` | `fall_detection_v22.h` |
| V1  | `Edge_AI/result_balanced_v2/models/` | `fall_detection_model.h` (tên cũ) |

> Tất cả 7 model đều đã có file `.h` sẵn sàng include. Variable name đồng nhất: `fall_detection_model_tflite[]`.

---

## Threshold khuyến nghị theo model

| Model | Threshold gốc | Điều chỉnh thực tế |
|---|---|---|
| V80 | 0.66 | Thử 0.55–0.70 |
| V64 | 0.54 | Thử 0.45–0.60 |
| V54 | ~0.50 | Thử 0.45–0.55 |
| V35 | ~0.40 | Giữ thấp để giữ recall |
| V59 | ~0.50 | Thử 0.45–0.55 |
| V22 | ~0.50 | Thử 0.45–0.55 |
| V1  | 0.40 | Theo tài liệu gốc |

Threshold trong `src/main.cpp`:
```cpp
static const float FALL_DECISION_THRESHOLD = 0.65f;  // ← điều chỉnh tại đây
```
