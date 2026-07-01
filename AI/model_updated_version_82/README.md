# Model V82

**patience=20 + ReduceLR(factor=0.1, patience=5) — aggressive LR**

| Metric | Value |
|---|---|
| F1 | 92.66% |
| Recall | 98.88% |
| FAR | 14.55% |
| Size | 61.93 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_82/models`
main.cpp: `#include "fall_detection_v82.h"`
