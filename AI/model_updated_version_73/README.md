# Model V73

**V23 arch [32,64,96,96]/K3 + D32+batch=32 (V23 had FAR=7.84%)**

| Metric | Value |
|---|---|
| F1 | 90.71% |
| Recall | 91.04% |
| FAR | 9.70% |
| Size | 77.88 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_73/models`
main.cpp: `#include "fall_detection_v73.h"`
