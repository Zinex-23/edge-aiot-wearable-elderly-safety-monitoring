# Experiment Report — V67

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=32
- LR=0.0003 | Dropout=0.5 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: Max regularize: D32 + dropout=0.5 + batch=32 + FAR penalty×2.5

## Results
- Accuracy: 0.8862
- Recall: 0.9664
- F1: 0.8946
- FAR: 0.1940
- Size: 78.70 KB | Threshold: 0.70
