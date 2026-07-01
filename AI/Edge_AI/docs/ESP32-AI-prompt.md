# Prompt To Generate ESP32-S3 BMI160 Fall Detection Code

Write complete production-style code for an `ESP32-S3 Super Mini` using `PlatformIO` in `VS Code`.

Goal:
- Read IMU data from a `BMI160` sensor
- Collect these signals:
  - `ax`
  - `ay`
  - `az`
  - `gx`
  - `gy`
  - `gz`
  - `ts` (timestamp in milliseconds)
- Sampling rate must be exactly `50 Hz`
- Run a fall detection AI model on-device
- Print final output to `Serial` as:
  - `fall`
  - `non-fall`

Use the already exported TensorFlow Lite Micro model header:
- `fall_detection_model.h`

Model assumptions:
- Input tensor shape: `1 x 100 x 6`
- Channel order:
  - `ax, ay, az, gx, gy, gz`
- Window size:
  - `100 samples`
- Sampling rate:
  - `50 Hz`
- One inference every `50 samples` using a rolling window
- Classification threshold:
  - `0.40`

Required behavior:

1. Hardware and framework
- Target board: `ESP32-S3 Super Mini`
- Framework: `Arduino`
- IDE: `PlatformIO`
- Use `Wire` for I2C communication
- Use a BMI160 library compatible with Arduino/PlatformIO
- Include all required headers

2. Sensor setup
- Initialize `BMI160`
- Configure accelerometer and gyroscope
- Set sensor output data rate close to `50 Hz`
- If exact 50 Hz setting is not available, explain the chosen BMI160 configuration
- Add clear serial logs for initialization success/failure

3. Data acquisition
- Sample sensor data at `50 Hz` using a non-blocking timing approach based on `millis()` or `micros()`
- For every sample, read:
  - accelerometer x/y/z
  - gyroscope x/y/z
  - timestamp `ts`
- Store the latest `100` samples in a rolling buffer
- Keep the timestamp array too for debugging

4. Unit handling
- Ensure `ax, ay, az` are converted to the same unit used in training
- Ensure `gx, gy, gz` are converted to the same unit used in training
- Clearly document the chosen units in code comments
- If BMI160 outputs raw sensor values, convert them properly

5. Model input preparation
- Build a `100 x 6` input window from the rolling buffer
- Preserve exact feature order:
  - `ax, ay, az, gx, gy, gz`
- Quantize input properly if the model is `int8`
- Read input scale and zero point from TensorFlow Lite Micro tensor parameters if possible
- If scale/zero-point are hardcoded, document where they come from and keep them as named constants

6. Inference logic
- Run inference every `50 new samples` after the first `100` samples are collected
- Read the model output probability for `fall`
- Apply threshold:
  - if probability `>= 0.40` -> `fall`
  - else -> `non-fall`
- Print result to `Serial`

7. Serial output format
- Print readable logs like:
```text
ts_start=123456 ts_end=125436 fall_prob=0.73 prediction=fall
```
- Also print debug IMU status during startup

8. TensorFlow Lite Micro integration
- Use `fall_detection_model.h`
- Create:
  - model
  - interpreter
  - tensor arena
- Keep memory usage reasonable for ESP32-S3
- Add comments showing where to adjust tensor arena size if needed

9. Project structure
Generate at least these files:
- `platformio.ini`
- `src/main.cpp`

10. Code quality
- Write clean, compilable C++ code
- Avoid placeholders
- Do not omit any important section
- Include comments only where useful
- Make sure the code is ready to build in PlatformIO

11. Important implementation details
- Use `Serial.begin(115200)`
- Use `Wire.begin(...)` and clearly mark SDA/SCL pins with constants
- Make pin definitions easy to modify
- Add a small helper function to print one sample for debugging
- Add a helper function to run inference on the current window
- Add a helper function to maintain the rolling buffer

12. Output requirement
Return the full contents of:
- `platformio.ini`
- `src/main.cpp`

Do not give only an explanation. Output real code that I can paste directly into a PlatformIO project.
