# Model V61

**V22 arch [16,32,48,64]/K5 + D32 + batch=32**

| Metric | Value |
|---|---|
| F1 | 87.36% |
| Recall | 90.30% |
| FAR | 16.42% |
| Size | 46.95 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_61/models`
main.cpp: `#include "fall_detection_v61.h"`
