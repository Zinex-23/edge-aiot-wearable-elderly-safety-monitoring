# Experiment Report — V76

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.1} | Epochs=200
- Note: V64 + cw=1.1 + FAR penalty×2.5 (less recall bias → lower FAR)

## Results
- F1: 0.9031 | Recall: 0.9216 | FAR: 0.1194
- Accuracy: 0.9011 | Size: 62.10 KB | Threshold: 0.73
