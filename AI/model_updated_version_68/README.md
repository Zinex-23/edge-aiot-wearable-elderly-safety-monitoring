# Model V68

**V58+V59 combo: LR=1e-4 + batch=32**

| Metric | Value |
|---|---|
| F1 | 90.33% |
| Recall | 95.90% |
| FAR | 16.42% |
| Size | 77.23 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_68/models`
main.cpp: `#include "fall_detection_v68.h"`
