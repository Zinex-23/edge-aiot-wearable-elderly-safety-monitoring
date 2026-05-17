# Model V70

**5 conv layers [16,32,48,64,96]/K5 — novel depth + batch=32**

| Metric | Value |
|---|---|
| F1 | 91.14% |
| Recall | 94.03% |
| FAR | 12.31% |
| Size | 83.25 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_70/models`
main.cpp: `#include "fall_detection_v70.h"`
