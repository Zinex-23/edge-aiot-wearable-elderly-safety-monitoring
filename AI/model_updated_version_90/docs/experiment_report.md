# Experiment Report — V90

## Config
- Arch: [32,64,64,96]/K3/D32 + batch=32
- LR=0.0003 | Dropout=0.45 | L2=0.0005
- EarlyStopping patience=20 | ReduceLR factor=0.1 patience=5
- Augmentation sigma=0.05 | Cosine LR=False
- Note: BEST COMBO: drop=0.45+L2=5e-4+aug0.05+LR_aggr+p=20

## Results
- F1: 0.8979 | Recall: 0.9515 | FAR: 0.1679
- Accuracy: 0.8918 | Size: 62.10 KB | Threshold: 0.74
- Stopped at epoch: 93
- Train/Val loss gap (last epoch): 0.0016 (ok)
