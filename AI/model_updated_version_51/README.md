# Model V51

**V50 base, cw=1:1, FAR-penalized scoring**

| Metric | Value |
|---|---|
| F1 | 81.25% |
| Recall | 72.76% |
| FAR | 6.34% |
| Size | 76.64 KB |

## Files
- `models/fall_detection_v51.tflite` — INT8 quantized
- `models/fall_detection_v51.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v51.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_51/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v51.h"
```
