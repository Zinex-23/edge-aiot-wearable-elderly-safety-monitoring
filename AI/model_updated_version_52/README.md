# Model V52

**V50 base, cw=1:1.5, Recall-maximizing scoring**

| Metric | Value |
|---|---|
| F1 | 92.55% |
| Recall | 97.39% |
| FAR | 13.06% |
| Size | 77.06 KB |

## Files
- `models/fall_detection_v52.tflite` — INT8 quantized
- `models/fall_detection_v52.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v52.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_52/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v52.h"
```
