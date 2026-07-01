# Model V67

**Max regularize: D32 + dropout=0.5 + batch=32 + FAR penalty×2.5**

| Metric | Value |
|---|---|
| F1 | 89.46% |
| Recall | 96.64% |
| FAR | 19.40% |
| Size | 78.70 KB |

## Deploy
platformio.ini: `-I ../AI/model_updated_version_67/models`
main.cpp: `#include "fall_detection_v67.h"`
