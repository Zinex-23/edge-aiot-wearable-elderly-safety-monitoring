# Model V71

**V64 + LR=1e-4 (finer convergence on best arch)**

| Metric | Value |
|---|---|
| F1 | 90.45% |
| Recall | 93.66% |
| FAR | 13.43% |
| Size | 61.51 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_71/models`
main.cpp: `#include "fall_detection_v71.h"`
