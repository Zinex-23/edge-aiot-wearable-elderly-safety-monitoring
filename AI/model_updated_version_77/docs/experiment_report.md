# Experiment Report — V77

## Config
- Arch: 4×Conv1D [32, 48, 64, 96], K=[5, 5, 5, 5], Dense=32
- LR=0.0001 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=250
- Note: V54+V59+V58: [32,48,64,96]/K5/D32 + batch=32 + LR=1e-4

## Results
- F1: 0.9131 | Recall: 0.9216 | FAR: 0.0970
- Accuracy: 0.9123 | Size: 78.70 KB | Threshold: 0.64
