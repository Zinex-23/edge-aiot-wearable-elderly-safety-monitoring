# Model V78

**V64 + last filter 96→128 (wider feature extraction)**

| Metric | Value |
|---|---|
| F1 | 90.49% |
| Recall | 95.90% |
| FAR | 16.04% |
| Size | 69.98 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_78/models`
main.cpp: `#include "fall_detection_v78.h"`
