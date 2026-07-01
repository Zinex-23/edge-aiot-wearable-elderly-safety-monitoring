# Experiment Report — V81

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=10 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.0 | Cosine LR=False
- Note: patience=10 — user suggestion, baseline test

## Results
- F1: 0.9131 | Recall: 0.9216 | FAR: 0.0970
- Accuracy: 0.9123 | Size: 61.51 KB | Threshold: 0.74
- Stopped at epoch: 30
- Train/Val loss gap (last epoch): -0.1512 (overfitting)
