# Experiment Report — V87

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.4 | L2=0.0003
- EarlyStopping patience=10 | ReduceLR factor=0.2 patience=10
- Augmentation sigma=0.05 | Cosine LR=False
- Note: patience=10 + aug σ=0.05 — user idea + root fix combined

## Results
- F1: 0.8908 | Recall: 0.9440 | FAR: 0.1754
- Accuracy: 0.8843 | Size: 62.10 KB | Threshold: 0.62
- Stopped at epoch: 20
- Train/Val loss gap (last epoch): -0.0551 (overfitting)
