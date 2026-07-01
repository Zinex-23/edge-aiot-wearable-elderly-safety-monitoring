# Model V60

**Mixed kernels K3/K5/K5/K3 — multi-scale temporal context**

| Metric | Value |
|---|---|
| F1 | 89.09% |
| Recall | 89.93% |
| FAR | 11.94% |
| Size | 64.85 KB |

## Files
- `models/fall_detection_v60.tflite` — INT8 quantized
- `models/fall_detection_v60.h` — C header (variable: `fall_detection_model_tflite`)
- `results/metrics_v60.md` — detailed metrics
- `results/dashboard.png` — training dashboard
- `docs/experiment_report.md` — full report

## Deploy to ESP32-S3
In `S3_BLE/platformio.ini`:
```
build_flags = -I ../AI/model_updated_version_60/models
```
In `S3_BLE/src/main.cpp`:
```cpp
#include "fall_detection_v60.h"
```
