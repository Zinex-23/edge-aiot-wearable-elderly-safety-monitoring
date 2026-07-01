# Experiment Report — Model V53

## Config
- Architecture: 4×Conv1D [32, 48, 64, 96], Kernels=[7, 7, 7, 7], Dense=20
- LR: 0.0003 | Dropout: 0.4 | L2: 0.0001 | Batch: 64
- Class weight: {0: 1.0, 1: 1.2}
- Note: K7 kernels — larger temporal receptive field

## Results
- Accuracy: 0.9049
- Recall:   0.9776
- F1:       0.9113
- FAR:      0.1679
- Size:     98.52 KB
- Threshold: 0.43
