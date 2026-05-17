# Model V57

**V50 base + L2=5e-4 (stronger weight decay)**

| Metric | Value |
|---|---|
| F1 | 91.55% |
| Recall | 97.01% |
| FAR | 14.93% |
| Size | 77.23 KB |

## Files
- `models/fall_detection_v57.tflite` — INT8 quantized
- `models/fall_detection_v57.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v57.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_57/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v57.h"
```
