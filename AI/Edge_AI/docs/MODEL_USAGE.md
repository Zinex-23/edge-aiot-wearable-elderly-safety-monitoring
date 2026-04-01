# Model Usage Guide

## Which file is used on ESP32-S3

Use this file in firmware:
- `result_balanced_v2/models/fall_detection_model.h`

Reference source:
- `result_balanced_v2/models/fall_detection_model.tflite`

Do not deploy:
- `result_balanced_v2/models/best_model.keras`

## What data the ESP32 must collect

For every sample, collect exactly:

- `ax`
- `ay`
- `az`
- `gx`
- `gy`
- `gz`

You may also collect:
- `timestamp`

But `timestamp` is not a model feature. It is only for timing and logging.

## Required sampling behavior

- sample rate: `50 Hz`
- one sample every `20 ms`
- window length: `100 samples`
- equivalent time span: `2 seconds`

Recommended rolling inference:
- keep the latest `100` samples
- run inference every `50` new samples
- this means one new decision every `1 second`

## Exact input format

Input tensor shape:
- `1 x 100 x 6`

Per-window shape:
- `100 x 6`

Channel order:
- `ax, ay, az, gx, gy, gz`

## Decision rule

The model returns one probability:
- `p(fall)`

Decision:
- if `p(fall) >= 0.40` -> `fall`
- else -> `non-fall`

## Important note about threshold figures

For deployment, use:
- `0.40`

If any visualization file shows a different vertical marker such as `0.50`, that figure is only a later analysis rendering issue. The selected deployment threshold for this package remains:
- `0.40`

## Sensor unit guidance

The runtime sensor units must match the training convention as closely as possible.

Recommended convention:
- accelerometer: `g`
- gyroscope: `deg/s`

If your BMI160 library returns:
- `m/s^2` for acceleration, convert to `g`
- `rad/s` for gyro, convert to `deg/s`

## Minimal device-side pipeline

1. Read IMU at `50 Hz`
2. Store `ax, ay, az, gx, gy, gz`
3. Maintain rolling window of `100` samples
4. Quantize input if needed by TFLite Micro
5. Run inference
6. Compare output to `0.40`
7. Print `fall` or `non-fall`

## Supporting documents

- `docs/how-to-use-model-on-esp32s3.md`
- `docs/ESP32-AI-prompt.md`
