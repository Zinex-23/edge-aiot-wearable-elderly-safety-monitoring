# Model V55

**Wider filters [48,64,80,96] — more feature capacity**

| Metric | Value |
|---|---|
| F1 | 91.68% |
| Recall | 96.64% |
| FAR | 14.18% |
| Size | 104.00 KB |

## Files
- `models/fall_detection_v55.tflite` — INT8 quantized
- `models/fall_detection_v55.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v55.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_55/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v55.h"
```
