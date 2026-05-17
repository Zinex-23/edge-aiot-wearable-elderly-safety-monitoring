# Model V88

**Dropout=0.45 + aggressive LR(factor=0.1, p=5) — tuned regularize**

| Metric | Value |
|---|---|
| F1 | 91.84% |
| Recall | 96.64% |
| FAR | 13.81% |
| Size | 62.10 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_88/models`
main.cpp: `#include "fall_detection_v88.h"`
