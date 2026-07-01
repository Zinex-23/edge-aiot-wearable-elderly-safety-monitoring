# Experiment Report — V82

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=20 | ReduceLR factor=0.1 patience=5
- Augmentation sigma=0.0 | Cosine LR=False
- Note: patience=20 + ReduceLR(factor=0.1, patience=5) — aggressive LR

## Results
- F1: 0.9266 | Recall: 0.9888 | FAR: 0.1455
- Accuracy: 0.9216 | Size: 61.93 KB | Threshold: 0.28
- Stopped at epoch: 46
- Train/Val loss gap (last epoch): -0.0544 (overfitting)
