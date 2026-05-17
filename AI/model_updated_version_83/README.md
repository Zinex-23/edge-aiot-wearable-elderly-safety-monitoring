# Model V83

**Dropout=0.5 + L2=5e-4 — strong regularization**

| Metric | Value |
|---|---|
| F1 | 90.81% |
| Recall | 95.90% |
| FAR | 15.30% |
| Size | 62.01 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_83/models`
main.cpp: `#include "fall_detection_v83.h"`
