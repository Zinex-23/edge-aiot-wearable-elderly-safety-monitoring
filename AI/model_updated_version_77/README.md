# Model V77

**V54+V59+V58: [32,48,64,96]/K5/D32 + batch=32 + LR=1e-4**

| Metric | Value |
|---|---|
| F1 | 91.31% |
| Recall | 92.16% |
| FAR | 9.70% |
| Size | 78.70 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_77/models`
main.cpp: `#include "fall_detection_v77.h"`
