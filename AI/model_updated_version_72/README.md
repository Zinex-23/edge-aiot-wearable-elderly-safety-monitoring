# Model V72

**V64 + batch=16 (smaller batch → better generalization)**

| Metric | Value |
|---|---|
| F1 | 89.97% |
| Recall | 97.01% |
| FAR | 18.66% |
| Size | 61.93 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_72/models`
main.cpp: `#include "fall_detection_v72.h"`
