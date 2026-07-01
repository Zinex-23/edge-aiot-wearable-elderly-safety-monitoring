# Model V64

**V27 arch [32,64,64,96]/K3/D32 + batch=32**

| Metric | Value |
|---|---|
| F1 | 93.17% |
| Recall | 96.64% |
| FAR | 10.82% |
| Size | 62.09 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_64/models`
main.cpp: `#include "fall_detection_v64.h"`
