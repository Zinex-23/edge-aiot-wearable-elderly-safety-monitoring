# Experiment Report — V83

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.5 | L2=0.0005
- EarlyStopping patience=25 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.0 | Cosine LR=False
- Note: Dropout=0.5 + L2=5e-4 — strong regularization

## Results
- F1: 0.9081 | Recall: 0.9590 | FAR: 0.1530
- Accuracy: 0.9030 | Size: 62.01 KB | Threshold: 0.36
- Stopped at epoch: 66
- Train/Val loss gap (last epoch): -0.1226 (overfitting)
