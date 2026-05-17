# Model V63

**V56+V59 combo: dropout=0.5 + batch=32 (FAR reduction focus)**

| Metric | Value |
|---|---|
| F1 | 89.82% |
| Recall | 92.16% |
| FAR | 13.06% |
| Size | 77.14 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_63/models`
main.cpp: `#include "fall_detection_v63.h"`
