# Model V62

**V54+V59 combo: D32 + batch=32 (best F1 + best FAR combo)**

| Metric | Value |
|---|---|
| F1 | 91.07% |
| Recall | 97.01% |
| FAR | 16.04% |
| Size | 78.52 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_62/models`
main.cpp: `#include "fall_detection_v62.h"`
