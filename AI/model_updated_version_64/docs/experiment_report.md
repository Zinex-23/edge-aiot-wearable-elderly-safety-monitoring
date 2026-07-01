# Experiment Report — V64

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2}
- Note: V27 arch [32,64,64,96]/K3/D32 + batch=32

## Results
- Accuracy: 0.9291
- Recall: 0.9664
- F1: 0.9317
- FAR: 0.1082
- Size: 62.09 KB | Threshold: 0.54
