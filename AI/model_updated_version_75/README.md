# Model V75

**V64 + dropout=0.3 (less regularization, more capacity)**

| Metric | Value |
|---|---|
| F1 | 90.49% |
| Recall | 95.90% |
| FAR | 16.04% |
| Size | 62.09 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_75/models`
main.cpp: `#include "fall_detection_v75.h"`
