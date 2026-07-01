# Model V59

**V50 base + BatchSize=32 (better generalization)**

| Metric | Value |
|---|---|
| F1 | 92.19% |
| Recall | 92.54% |
| FAR | 8.21% |
| Size | 77.23 KB |

## Files
- `models/fall_detection_v59.tflite` — INT8 quantized
- `models/fall_detection_v59.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v59.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_59/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v59.h"
```
