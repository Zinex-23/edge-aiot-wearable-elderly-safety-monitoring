# Experiment Report — V79

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=48
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V64 + Dense=48 (more classification capacity)

## Results
- F1: 0.9158 | Recall: 0.9328 | FAR: 0.1045
- Accuracy: 0.9142 | Size: 64.05 KB | Threshold: 0.67
