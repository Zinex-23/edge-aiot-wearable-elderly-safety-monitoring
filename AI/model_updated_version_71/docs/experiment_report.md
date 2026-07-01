# Experiment Report — V71

## Config
- Arch: 4×Conv1D [32, 64, 64, 96], K=[3, 3, 3, 3], Dense=32
- LR=0.0001 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=250
- Note: V64 + LR=1e-4 (finer convergence on best arch)

## Results
- F1: 0.9045 | Recall: 0.9366 | FAR: 0.1343
- Accuracy: 0.9011 | Size: 61.51 KB | Threshold: 0.69
