# Parameter Reference

This file explains the main parameters used in the final selected package.

## A. Data source parameters

### `data_source`
- Value: `HR_IMU`
- Meaning: only the HR_IMU dataset is used for the final selected model package.

### `fall_path`
- Value: `HR_IMU/fall`
- Meaning: source directory for fall sequences.

### `non_fall_path`
- Value: `HR_IMU/non-fall`
- Meaning: source directory for non-fall sequences.

## B. CSV schema parameters

### `timestamp`
- Meaning: time value for each sample.
- Use: sorting, logging, debug, temporal metadata.
- Not used directly as a model feature.

### `ax`, `ay`, `az`
- Meaning: accelerometer values on x/y/z axes.
- Use: model input features.

### `gx`, `gy`, `gz`
- Meaning: gyroscope values on x/y/z axes.
- Use: model input features.

## C. Windowing parameters

### `sampling_rate`
- Value: `50 Hz`
- Meaning: 50 samples per second.
- Device implication: collect one sample every `20 ms`.

### `window_size`
- Value: `100`
- Meaning: each model input window has 100 time steps.
- Time implication: `100 / 50 = 2 seconds`.

### `window_length_seconds`
- Value: `2 seconds`
- Meaning: duration covered by one model input window.

### `stride`
- Value: `50`
- Meaning: the sliding window moves forward by 50 samples each time.
- Time implication: `1 second` shift per inference cycle.

### `overlap`
- Value: `50%`
- Meaning: adjacent windows share half of their content.

### `input_shape`
- Value: `(100, 6)`
- Meaning: 100 time steps and 6 IMU channels.

### `feature_order`
- Value: `ax, ay, az, gx, gy, gz`
- Meaning: exact order expected by the model.
- Warning: changing this order breaks inference correctness.

## D. Balancing parameters

### `balancing_strategy`
- Value: `undersampling`
- Meaning: the larger class is reduced by random sampling.

### `balanced_ratio`
- Value: `1:1`
- Meaning: the training dataset has equal numbers of fall and non-fall windows.

### `fall_windows_before_balancing`
- Value: `1628`
- Meaning: number of fall windows created before balancing.

### `non_fall_windows_before_balancing`
- Value: `5468`
- Meaning: number of non-fall windows created before balancing.

### `fall_windows_after_balancing`
- Value: `1628`
- Meaning: final fall windows used for split/training.

### `non_fall_windows_after_balancing`
- Value: `1628`
- Meaning: final non-fall windows used for split/training.

### `total_windows_used`
- Value: `3256`
- Meaning: total number of windows entering the final pipeline.

## E. Split parameters

### `train_ratio`
- Value: `70%`
- Meaning: training subset size.

### `validation_ratio`
- Value: `15%`
- Meaning: validation subset size.

### `test_ratio`
- Value: `15%`
- Meaning: held-out test subset size.

### `stratified_split`
- Value: `true`
- Meaning: class ratio is preserved across splits.

## F. Model architecture parameters

### `Conv1D(16, 3, relu)`
- Meaning: first 1D convolution layer.
- `16`: number of filters.
- `3`: kernel size.
- `relu`: activation function.

### `MaxPooling1D(2)`
- Meaning: reduces temporal resolution by factor 2 and lowers compute.

### `Conv1D(32, 3, relu)`
- Meaning: second feature extraction layer with more channels.

### `GlobalAveragePooling1D()`
- Meaning: compresses temporal features into one vector with low parameter cost.

### `Dense(32, relu)`
- Meaning: small fully connected hidden layer for final discrimination.

### `Dense(1, sigmoid)`
- Meaning: single output neuron producing fall probability from 0 to 1.

## G. Training parameters

### `epochs`
- Value: `60`
- Meaning: maximum number of training passes over the training data.

### `batch_size`
- Value: `32`
- Meaning: number of windows processed together before gradient update.

### `optimizer`
- Value: `Adam`
- Meaning: adaptive gradient optimizer used during training.

### `loss`
- Value: `binary_crossentropy`
- Meaning: loss function for binary classification.

### `early_stopping`
- Value: `enabled`
- Meaning: stops training early when validation no longer improves enough.

## H. Inference parameters

### `selected_threshold`
- Value: `0.40`
- Meaning: decision cutoff for converting model probability into class label.

### `decision_rule`
- Value:
  - `p(fall) >= 0.40` -> `fall`
  - `p(fall) < 0.40` -> `non-fall`
- Meaning: final classification rule used for deployment.

### `inference_frequency`
- Recommended value: every `50` new samples
- Meaning: generate one new decision every `1 second` with rolling windows.

## I. Export parameters

### `keras_model`
- File: `result_balanced_v2/models/best_model.keras`
- Meaning: training/evaluation model for desktop use.

### `tflite_model`
- File: `result_balanced_v2/models/fall_detection_model.tflite`
- Meaning: converted model for TinyML deployment.

### `header_model`
- File: `result_balanced_v2/models/fall_detection_model.h`
- Meaning: C/C++ byte array version for ESP32 firmware embedding.

### `tflite_size_kb`
- Value: `10.71 KB`
- Meaning: quantized model size after export.

### `tflite_input_shape`
- Value: `[1, 100, 6]`
- Meaning: deployed runtime input tensor shape.

### `tflite_output_shape`
- Value: `[1, 1]`
- Meaning: one scalar probability output.

## J. Evaluation parameters and meanings

### `accuracy`
- Value: `0.9080`
- Meaning: overall fraction of correct predictions.

### `precision`
- Value: `0.8541`
- Meaning: among predicted falls, how many are true falls.

### `recall`
- Value: `0.9836`
- Meaning: among true falls, how many are detected.

### `F1-score`
- Value: `0.9143`
- Meaning: harmonic mean of precision and recall.

### `false_alarm_rate`
- Value: `0.1673`
- Meaning: proportion of non-fall windows incorrectly predicted as fall.

### `miss_rate`
- Value: `0.0164`
- Meaning: proportion of fall windows missed by the model.

### `confusion_matrix`
- Value: `[[204, 41], [4, 240]]`
- Meaning:
  - `204`: true non-fall predicted as non-fall
  - `41`: non-fall predicted as fall
  - `4`: fall predicted as non-fall
  - `240`: true fall predicted as fall

### `roc_auc`
- Value: `0.9712`
- Meaning: ranking quality across thresholds for ROC.

### `pr_auc`
- Value: `0.9669`
- Meaning: ranking quality across thresholds for precision-recall.

## K. File map

### `results/dashboard.png`
- Meaning: one combined image summarizing training and evaluation plots.

### `results/decision_analysis.png`
- Meaning: threshold sweep analysis.

### `results/error_analysis.png`
- Meaning: false positive and false negative analysis.

### `results/temporal_behavior.png`
- Meaning: prediction behavior over ordered test windows.

### `results/threshold_metrics.csv`
- Meaning: tabular threshold sweep metrics.

## L. Practical ESP32-S3 implications

### Why this model is deployable
- small TFLite file size
- lightweight CNN
- only 6 sensor channels
- 50 Hz input rate
- rolling window inference is practical on ESP32-S3

### What must stay unchanged on device

1. Sample rate should stay near `50 Hz`
2. Feature order must stay `ax, ay, az, gx, gy, gz`
3. Window length must stay `100` samples
4. Decision threshold must stay `0.40`
5. Sensor units should match training convention as closely as possible
