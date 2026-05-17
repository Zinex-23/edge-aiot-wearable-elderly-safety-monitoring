# Model V69

**V54+V59+V57 combo: D32 + batch=32 + L2=5e-4**

| Metric | Value |
|---|---|
| F1 | 91.26% |
| Recall | 97.39% |
| FAR | 16.04% |
| Size | 78.70 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_69/models`
main.cpp: `#include "fall_detection_v69.h"`
