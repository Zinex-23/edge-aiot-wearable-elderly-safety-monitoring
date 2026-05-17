# Model V86

**aug σ=0.05 + L2=5e-4 + LR aggressive — two strongest fixes**

| Metric | Value |
|---|---|
| F1 | 92.28% |
| Recall | 98.13% |
| FAR | 14.55% |
| Size | 62.10 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_86/models`
main.cpp: `#include "fall_detection_v86.h"`
