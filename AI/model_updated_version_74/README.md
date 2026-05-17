# Model V74

**V64 arch switched to K5 + D32 + batch=32**

| Metric | Value |
|---|---|
| F1 | 91.36% |
| Recall | 96.64% |
| FAR | 14.93% |
| Size | 86.46 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_74/models`
main.cpp: `#include "fall_detection_v74.h"`
