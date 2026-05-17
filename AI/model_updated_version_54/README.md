# Model V54

**V50 base + Dense=32 (more classification capacity)**

| Metric | Value |
|---|---|
| F1 | 93.07% |
| Recall | 97.76% |
| FAR | 12.31% |
| Size | 78.68 KB |

## Files
- `models/fall_detection_v54.tflite` — INT8 quantized
- `models/fall_detection_v54.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v54.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_54/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v54.h"
```
