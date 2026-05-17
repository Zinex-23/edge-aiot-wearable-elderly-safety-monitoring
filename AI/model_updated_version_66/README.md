# Model V66

**V22 arch tuned: D24 + dropout=0.45 + batch=32**

| Metric | Value |
|---|---|
| F1 | 92.09% |
| Recall | 95.52% |
| FAR | 11.94% |
| Size | 46.81 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_66/models`
main.cpp: `#include "fall_detection_v66.h"`
