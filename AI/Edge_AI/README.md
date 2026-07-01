# Edge_AI

This folder is the final handoff package for the fall detection project based on the selected model in `result_balanced_v2`.

## What is included

- The full final result folder:
  - `result_balanced_v2/`
- Extra project-level documentation:
  - `docs/WORKFLOW.md`
  - `docs/TRAINING_AND_REPRODUCTION.md`
  - `docs/MODEL_USAGE.md`
  - `docs/PARAMETER_REFERENCE.md`
  - `docs/how-to-use-model-on-esp32s3.md`
  - `docs/ESP32-AI-prompt.md`

## Final selected model

Use this file for deployment on ESP32-S3:
- `result_balanced_v2/models/fall_detection_model.h`

Reference model files:
- `result_balanced_v2/models/fall_detection_model.tflite`
- `result_balanced_v2/models/best_model.keras`

## Final training result

- Data source: `HR_IMU` only
- Class balancing strategy: undersample non-fall windows to match fall windows
- Balanced window count:
  - fall: `1628`
  - non-fall: `1628`
  - total: `3256`

Final test metrics:
- Accuracy: `0.9080`
- Precision: `0.8541`
- Recall: `0.9836`
- F1-score: `0.9143`
- False alarm rate: `0.1673`
- Miss rate: `0.0164`

## Important threshold note

The deployment threshold selected for the model is:
- `0.40`

Some later visualization edits temporarily drew a `0.50` marker in one analysis figure. For actual deployment and for the chosen model package, use:
- `0.40`

## Recommended reading order

1. `docs/WORKFLOW.md`
2. `docs/PARAMETER_REFERENCE.md`
3. `docs/TRAINING_AND_REPRODUCTION.md`
4. `docs/MODEL_USAGE.md`
5. `result_balanced_v2/results/dashboard.png`

## Quick start

If you want to deploy directly on ESP32-S3:

1. Open `docs/MODEL_USAGE.md`
2. Use `result_balanced_v2/models/fall_detection_model.h`
3. Feed windows of shape `100 x 6`
4. Use channel order:
   - `ax, ay, az, gx, gy, gz`
5. Sample at `50 Hz`
6. Predict `fall` when model output probability is `>= 0.40`
