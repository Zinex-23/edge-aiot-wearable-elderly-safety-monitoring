# Model V56

**V50 base + Dropout=0.5 (more regularization)**

| Metric | Value |
|---|---|
| F1 | 90.74% |
| Recall | 89.55% |
| FAR | 7.84% |
| Size | 77.23 KB |

## Files
- `models/fall_detection_v56.tflite` — INT8 quantized
- `models/fall_detection_v56.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v56.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_56/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v56.h"
```
