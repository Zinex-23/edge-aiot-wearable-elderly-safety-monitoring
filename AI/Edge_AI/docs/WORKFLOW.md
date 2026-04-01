# End-to-End Workflow

## 1. Raw data source

The selected final model in this package was trained using only:
- `HR_IMU/fall`
- `HR_IMU/non-fall`

No `UNI` data is used in `result_balanced_v2`.

## 2. CSV normalization

Each source file is normalized to the exact schema:

- `timestamp`
- `ax`
- `ay`
- `az`
- `gx`
- `gy`
- `gz`

Only these columns are kept.

## 3. Rebuilt dataset

The normalized rebuilt datasets are stored in:

- `result_balanced_v2/dataset/rebuilt/fall.csv`
- `result_balanced_v2/dataset/rebuilt/non_fall.csv`

## 4. Windowing

Time-series data is converted into fixed windows for training:

- sampling rate: `50 Hz`
- window length: `2 seconds`
- samples per window: `100`
- overlap: `50%`
- stride: `50` samples
- input channels: `6`

Input tensor per window:
- `(100, 6)`

Channel order:
- `ax, ay, az, gx, gy, gz`

## 5. Original class distribution

Before balancing:
- fall windows: `1628`
- non-fall windows: `5468`

This is imbalanced toward non-fall.

## 6. Balancing strategy

To improve training behavior and recall, non-fall windows were reduced by random undersampling.

After balancing:
- fall windows: `1628`
- non-fall windows: `1628`

Final ratio:
- `1:1`

## 7. Train/validation/test split

Balanced windows were split with stratification:

- train: `70%`
- validation: `15%`
- test: `15%`

Final split counts:
- train: fall `1140`, non-fall `1139`
- validation: fall `244`, non-fall `244`
- test: fall `244`, non-fall `245`

## 8. Model training

The chosen model is a lightweight TinyCNN:

1. `Conv1D(16, 3, activation='relu')`
2. `MaxPooling1D(2)`
3. `Conv1D(32, 3, activation='relu')`
4. `GlobalAveragePooling1D()`
5. `Dense(32, activation='relu')`
6. `Dense(1, activation='sigmoid')`

Training setup:
- epochs: `60`
- batch size: `32`
- optimizer: `Adam`
- loss: `binary_crossentropy`
- early stopping: enabled

## 9. Threshold tuning

The model outputs `p(fall)`.

Decision rule:
- if `p(fall) >= 0.40` -> `fall`
- else -> `non-fall`

This `0.40` threshold is the deployment threshold for the selected model.

## 10. Evaluation

Main artifacts:
- `result_balanced_v2/results/metrics_summary.txt`
- `result_balanced_v2/results/dashboard.png`
- `result_balanced_v2/results/confusion_matrix.png`
- `result_balanced_v2/results/roc_curve.png`
- `result_balanced_v2/results/precision_recall_curve.png`

Final test metrics:
- accuracy: `0.9080`
- precision: `0.8541`
- recall: `0.9836`
- F1-score: `0.9143`

## 11. TinyML export

The trained Keras model was converted to:

- `result_balanced_v2/models/fall_detection_model.tflite`
- `result_balanced_v2/models/fall_detection_model.h`

The `.h` file is the one embedded into ESP32-S3 firmware.

## 12. Deployment on ESP32-S3

Device-side runtime steps:

1. Sample BMI160 or compatible IMU at `50 Hz`
2. Read:
   - `ax, ay, az, gx, gy, gz`
3. Fill a rolling buffer of `100` samples
4. Build input tensor `(100, 6)`
5. Run the model
6. Compare output with threshold `0.40`
7. Print `fall` or `non-fall`
