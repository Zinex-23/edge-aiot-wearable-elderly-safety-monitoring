# Experiment Report — V78

## Config
- Arch: 4×Conv1D [32, 64, 64, 128], K=[3, 3, 3, 3], Dense=32
- LR=0.0003 | Dropout=0.4 | L2=0.0001 | Batch=32
- Class weight: {0: 1.0, 1: 1.2} | Epochs=200
- Note: V64 + last filter 96→128 (wider feature extraction)

## Results
- F1: 0.9049 | Recall: 0.9590 | FAR: 0.1604
- Accuracy: 0.8993 | Size: 69.98 KB | Threshold: 0.53
