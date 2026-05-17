# Model V80

**V64 + L2=3e-4 (tuned regularization between 1e-4 and 5e-4)**

| Metric | Value |
|---|---|
| F1 | 93.38% |
| Recall | 97.39% |
| FAR | 11.19% |
| Size | 62.10 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_80/models`
main.cpp: `#include "fall_detection_v80.h"`
