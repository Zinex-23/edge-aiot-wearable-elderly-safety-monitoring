# Model V84

**Gaussian noise aug σ=0.05 — fix overfitting at root**

| Metric | Value |
|---|---|
| F1 | 93.45% |
| Recall | 98.51% |
| FAR | 12.31% |
| Size | 62.09 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_84/models`
main.cpp: `#include "fall_detection_v84.h"`
