# Training And Reproduction Guide

## Main training package

The selected result is stored in:
- `result_balanced_v2/`

The code snapshot used in that package is stored in:
- `result_balanced_v2/code/preprocess.py`
- `result_balanced_v2/code/windowing.py`
- `result_balanced_v2/code/train.py`
- `result_balanced_v2/code/evaluate.py`
- `result_balanced_v2/code/convert_tflite.py`
- `result_balanced_v2/code/export_header.py`

## Data preparation flow

1. Load all CSV files from `HR_IMU/fall`
2. Load all CSV files from `HR_IMU/non-fall`
3. Normalize column names to:
   - `timestamp, ax, ay, az, gx, gy, gz`
4. Keep only valid rows and valid files
5. Create windows of `100` samples with stride `50`
6. Label fall windows as `1`
7. Label non-fall windows as `0`
8. Undersample the non-fall class to match fall count
9. Split train/validation/test with stratification

## Reproduction checklist

To reproduce the same training logic, keep these settings fixed:

- sampling rate: `50 Hz`
- window size: `100`
- stride: `50`
- class balance strategy: undersample majority class
- epochs: `60`
- batch size: `32`
- optimizer: `Adam`
- loss: `binary_crossentropy`
- output activation: `sigmoid`
- decision threshold: `0.40`

## Files to inspect for reproduction

- configuration:
  - `result_balanced_v2/logs/config.json`
- training history:
  - `result_balanced_v2/logs/history.csv`
- summary metrics:
  - `result_balanced_v2/results/metrics_summary.txt`
- dataset stats:
  - `result_balanced_v2/dataset/dataset_summary.csv`
  - `result_balanced_v2/dataset/window_summary.csv`

## Notes on reproducibility

If you retrain later and want comparable results:

1. Keep the same source dataset
2. Keep the same windowing parameters
3. Keep the same balancing strategy
4. Keep the same inference threshold
5. Keep the same sensor feature order

If any of these change, the result is no longer directly comparable.
