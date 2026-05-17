# Model V76

**V64 + cw=1.1 + FAR penalty×2.5 (less recall bias → lower FAR)**

| Metric | Value |
|---|---|
| F1 | 90.31% |
| Recall | 92.16% |
| FAR | 11.94% |
| Size | 62.10 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_76/models`
main.cpp: `#include "fall_detection_v76.h"`
