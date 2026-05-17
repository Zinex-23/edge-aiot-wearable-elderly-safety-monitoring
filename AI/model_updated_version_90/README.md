# Model V90

**BEST COMBO: drop=0.45+L2=5e-4+aug0.05+LR_aggr+p=20**

| Metric | Value |
|---|---|
| F1 | 89.79% |
| Recall | 95.15% |
| FAR | 16.79% |
| Size | 62.10 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_90/models`
main.cpp: `#include "fall_detection_v90.h"`
