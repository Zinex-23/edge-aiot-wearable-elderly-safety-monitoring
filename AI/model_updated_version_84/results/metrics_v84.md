# Model V84 — Gaussian Noise Augmentation σ=0.05

**Ngày train:** 2026-05-16 | **🏆 Best Overall từ V1–V90**

---

## 1. Chỉ tiêu đánh giá (Test set)

| Metric | Value | Ý nghĩa |
| :--- | :--- | :--- |
| **Accuracy** | **93.10%** | Tỉ lệ phân loại đúng tổng thể |
| **Recall (Sensitivity)** | **98.51%** | Phát hiện đúng 98.51% cú ngã thật |
| **Precision** | **88.89%** | Trong số báo alarm, 88.89% là ngã thật |
| **F1-score** | **93.45%** | Điểm cân bằng Recall/Precision |
| **FAR (False Alarm Rate)** | **12.31%** | 12.31% ADL bị báo nhầm là ngã |
| **Miss Rate** | **1.49%** | Chỉ bỏ sót 1.49% cú ngã thật |
| **Specificity** | **87.69%** | Phân loại đúng 87.69% non-fall |

---

## 2. Ma trận nhầm lẫn (Confusion Matrix)

|  | **Dự đoán: Non-Fall** | **Dự đoán: Fall** |
| :--- | :---: | :---: |
| **Thực tế: Non-Fall** | TN = 235 | FP = 33 |
| **Thực tế: Fall** | FN = **4** | TP = 264 |

- **Tổng test:** 536 (268 fall + 268 non-fall)
- **FN = 4** → chỉ bỏ sót 4 cú ngã trong 268 mẫu
- **FP = 33** → báo nhầm 33 lần ADL là ngã

---

## 3. Ngưỡng quyết định (Threshold)

| Tham số | Giá trị |
| :--- | :--- |
| **Threshold được chọn** | **0.42** |
| **Phương pháp** | Maximize `recall × 1.5 − FAR × 2.0` trên validation set |

### Recall / FAR theo ngưỡng:

| Threshold | Recall | FAR | Ghi chú |
| :---: | :---: | :---: | :--- |
| 0.30 | 98.88% | 14.55% | Recall cao nhất, FAR cao |
| **0.42** | **98.51%** | **13.43%** | **← Threshold được chọn** |
| 0.50 | 98.13% | 13.43% | Tương đương |
| 0.60 | 97.01% | 13.06% | FAR giảm nhẹ |
| 0.70 | 95.52% | 10.45% | FAR thấp hơn, bỏ sót nhiều hơn |

> **Deploy:** Dùng 0.42 mặc định. Muốn giảm FAR → tăng lên 0.60–0.70. Muốn không bỏ sót ngã → giảm xuống 0.30.

---

## 4. Cấu hình model

| Tham số | Giá trị |
| :--- | :--- |
| Architecture | 4×Conv1D [32,64,64,96], Kernel=3, Dense=32 |
| Learning Rate | 3e-4 (Adam) |
| Dropout | 0.4 |
| L2 Regularization | 3e-4 |
| Batch Size | 32 |
| Class Weight | {Non-Fall:1.0, Fall:1.2} |
| **Augmentation** | **Gaussian noise σ=0.05 trên IMU data** |
| EarlyStopping patience | 25 epochs |
| ReduceLROnPlateau | factor=0.2, patience=10 |
| Stopped epoch | **78 / 300** |

---

## 5. File model

| File | Size |
| :--- | :--- |
| `fall_detection_v84.tflite` | **62.09 KB** (INT8 quantized) |
| `fall_detection_v84.h` | C header — var: `fall_detection_model_tflite` |

---

## 6. Tại sao V84 tốt hơn V80?

| | V80 | V84 |
| :--- | :---: | :---: |
| F1 | 93.38% | **93.45%** |
| Recall | 97.39% | **98.51%** |
| Miss Rate | 2.61% | **1.49%** |
| Overfitting | ⚠️ val plateau sớm | ✅ train/val bám sát |

Augmentation noise buộc model học pattern tổng quát thay vì học thuộc data → val loss theo sát train loss, không còn overfitting.

---

## 7. Deploy lên ESP32-S3

`S3_BLE/platformio.ini`:
```ini
-I ../AI/model_updated_version_84/models
```

`S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v84.h"
static const float FALL_DECISION_THRESHOLD = 0.42f;
```
