# Model V65

**V37 arch [24,48,64,96]/K5 + D24 + batch=32**

| Metric | Value |
|---|---|
| F1 | 89.90% |
| Recall | 96.27% |
| FAR | 17.91% |
| Size | 75.38 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_65/models`
main.cpp: `#include "fall_detection_v65.h"`
