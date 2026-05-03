#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#include "fall_detection_model.h"
#include "max30102_sensor.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

static const int I2C_SDA_PIN = 8;
static const int I2C_SCL_PIN = 9;
static const int LED_PIN = 48;

static const uint8_t BMI160_ADDR_LOW = 0x68;
static const uint8_t BMI160_ADDR_HIGH = 0x69;
static const uint8_t BMI160_CHIP_ID = 0xD1;

static const uint8_t REG_CHIP_ID = 0x00;
static const uint8_t REG_GYR_DATA = 0x0C;
static const uint8_t REG_ACC_DATA = 0x12;
static const uint8_t REG_ACC_CONF = 0x40;
static const uint8_t REG_ACC_RANGE = 0x41;
static const uint8_t REG_GYR_CONF = 0x42;
static const uint8_t REG_GYR_RANGE = 0x43;
static const uint8_t REG_CMD = 0x7E;

static const float ACC_LSB_PER_G = 16384.0f;     // BMI160 +/-2g
static const float GYR_LSB_PER_DPS = 16.4f;      // BMI160 +/-2000 dps

static const uint32_t SAMPLE_RATE_HZ = 50;
static const uint32_t SAMPLE_PERIOD_MS = 1000 / SAMPLE_RATE_HZ;
static const uint32_t SERIAL_PRINT_PERIOD_MS = 1000;

static const int kWindowSize = 100;
static const int kFeatureCount = 6;
static const int kInferenceStride = 50;
static const int kTensorArenaSize = 60 * 1024;
static const float FALL_DECISION_THRESHOLD = 0.40f;
static const uint8_t INVALID_VITAL_VALUE = 255;

struct ImuSample {
  float ax = 0.0f;
  float ay = 0.0f;
  float az = 0.0f;
  float gx = 0.0f;
  float gy = 0.0f;
  float gz = 0.0f;
  uint32_t tsMs = 0;
};

namespace {
const tflite::Model *model = nullptr;
tflite::ErrorReporter *errorReporter = nullptr;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *inputTensor = nullptr;
TfLiteTensor *outputTensor = nullptr;
uint8_t tensorArena[kTensorArenaSize];
int outputElementCount = 0;
}  // namespace

uint8_t bmi160Addr = BMI160_ADDR_LOW;
bool bmiOk = false;
bool max30102Ok = false;
bool modelOk = false;

ImuSample imuWindow[kWindowSize];
ImuSample latestImu;
bool latestImuValid = false;
int windowHead = 0;
int windowCount = 0;
int samplesSinceInference = 0;

float latestFallProb = 0.0f;
float latestNonFallProb = 1.0f;
bool latestFallDetected = false;
bool latestInferenceValid = false;
uint32_t inferenceCount = 0;

uint32_t lastSampleMs = 0;
uint32_t lastSerialPrintMs = 0;

bool writeReg(uint8_t reg, uint8_t value) {
  for (int i = 0; i < 3; ++i) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    Wire.write(value);
    if (Wire.endTransmission() == 0) return true;
    delay(1);
  }
  return false;
}

bool readRegs(uint8_t reg, uint8_t *buffer, size_t len) {
  for (int i = 0; i < 3; ++i) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) {
      delay(1);
      continue;
    }

    if (Wire.requestFrom((int)bmi160Addr, (int)len) != (int)len) {
      delay(1);
      continue;
    }

    for (size_t j = 0; j < len; ++j) {
      buffer[j] = Wire.read();
    }
    return true;
  }
  return false;
}

bool readReg(uint8_t reg, uint8_t &value) {
  return readRegs(reg, &value, 1);
}

int16_t toInt16(uint8_t lsb, uint8_t msb) {
  return (int16_t)((msb << 8) | lsb);
}

void scanI2C() {
  Serial.println("Scanning I2C bus...");
  byte count = 0;
  for (byte addr = 1; addr < 127; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("I2C device found at address 0x%02X\n", addr);
      ++count;
    }
  }
  if (count == 0) {
    Serial.println("No I2C devices found");
  } else {
    Serial.printf("Total %u I2C device(s) found\n", count);
  }
}

bool detectBMI160() {
  uint8_t chipId = 0;
  Serial.println("Detecting BMI160...");

  bmi160Addr = BMI160_ADDR_LOW;
  if (readReg(REG_CHIP_ID, chipId)) {
    Serial.printf("  Address 0x68: got 0x%02X, expected 0xD1\n", chipId);
    if (chipId == BMI160_CHIP_ID) return true;
  } else {
    Serial.println("  Address 0x68: no response");
  }

  bmi160Addr = BMI160_ADDR_HIGH;
  if (readReg(REG_CHIP_ID, chipId)) {
    Serial.printf("  Address 0x69: got 0x%02X, expected 0xD1\n", chipId);
    if (chipId == BMI160_CHIP_ID) return true;
  } else {
    Serial.println("  Address 0x69: no response");
  }

  return false;
}

bool initBMI160() {
  if (!detectBMI160()) return false;

  if (!writeReg(REG_CMD, 0x11)) return false;  // accelerometer normal mode
  delay(10);
  if (!writeReg(REG_CMD, 0x15)) return false;  // gyroscope normal mode
  delay(80);

  if (!writeReg(REG_ACC_CONF, 0x28)) return false;
  if (!writeReg(REG_ACC_RANGE, 0x03)) return false;
  if (!writeReg(REG_GYR_CONF, 0x28)) return false;
  if (!writeReg(REG_GYR_RANGE, 0x00)) return false;

  delay(10);
  return true;
}

bool readAccelRaw(int16_t &axRaw, int16_t &ayRaw, int16_t &azRaw) {
  uint8_t data[6];
  if (!readRegs(REG_ACC_DATA, data, sizeof(data))) return false;
  axRaw = toInt16(data[0], data[1]);
  ayRaw = toInt16(data[2], data[3]);
  azRaw = toInt16(data[4], data[5]);
  return true;
}

bool readGyroRaw(int16_t &gxRaw, int16_t &gyRaw, int16_t &gzRaw) {
  uint8_t data[6];
  if (!readRegs(REG_GYR_DATA, data, sizeof(data))) return false;
  gxRaw = toInt16(data[0], data[1]);
  gyRaw = toInt16(data[2], data[3]);
  gzRaw = toInt16(data[4], data[5]);
  return true;
}

bool readImuSample(ImuSample &sample) {
  if (!bmiOk) return false;

  int16_t axRaw = 0;
  int16_t ayRaw = 0;
  int16_t azRaw = 0;
  int16_t gxRaw = 0;
  int16_t gyRaw = 0;
  int16_t gzRaw = 0;

  if (!readAccelRaw(axRaw, ayRaw, azRaw)) return false;
  if (!readGyroRaw(gxRaw, gyRaw, gzRaw)) return false;

  sample.ax = axRaw / ACC_LSB_PER_G;
  sample.ay = ayRaw / ACC_LSB_PER_G;
  sample.az = azRaw / ACC_LSB_PER_G;
  sample.gx = gxRaw / GYR_LSB_PER_DPS;
  sample.gy = gyRaw / GYR_LSB_PER_DPS;
  sample.gz = gzRaw / GYR_LSB_PER_DPS;
  sample.tsMs = millis();
  return true;
}

void pushImuSample(const ImuSample &sample) {
  imuWindow[windowHead] = sample;
  windowHead = (windowHead + 1) % kWindowSize;
  if (windowCount < kWindowSize) {
    ++windowCount;
  }
  ++samplesSinceInference;
}

int oldestWindowIndex() {
  if (windowCount < kWindowSize) return 0;
  return windowHead;
}

ImuSample orderedSampleAt(int index) {
  int start = oldestWindowIndex();
  return imuWindow[(start + index) % kWindowSize];
}

int countTensorElements(const TfLiteTensor *tensor) {
  int count = 1;
  for (int i = 0; i < tensor->dims->size; ++i) {
    count *= tensor->dims->data[i];
  }
  return count;
}

float clamp01(float value) {
  if (value < 0.0f) return 0.0f;
  if (value > 1.0f) return 1.0f;
  return value;
}

int8_t quantizeInput(float value) {
  const float scale = inputTensor->params.scale;
  const int zeroPoint = inputTensor->params.zero_point;
  int quantized = (int)lroundf(value / scale) + zeroPoint;
  if (quantized > 127) quantized = 127;
  if (quantized < -128) quantized = -128;
  return (int8_t)quantized;
}

float dequantizeOutput(int8_t value) {
  return (value - outputTensor->params.zero_point) * outputTensor->params.scale;
}

bool initModel() {
  model = tflite::GetModel(fall_detection_model_tflite);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.println("Model schema mismatch");
    return false;
  }

  static tflite::MicroErrorReporter microErrorReporter;
  static tflite::AllOpsResolver resolver;
  errorReporter = &microErrorReporter;

  static tflite::MicroInterpreter staticInterpreter(
      model, resolver, tensorArena, kTensorArenaSize, errorReporter);
  interpreter = &staticInterpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("AllocateTensors failed");
    return false;
  }

  inputTensor = interpreter->input(0);
  outputTensor = interpreter->output(0);
  outputElementCount = countTensorElements(outputTensor);

  if (inputTensor->type != kTfLiteInt8 || outputTensor->type != kTfLiteInt8) {
    Serial.println("Model tensor type is not int8");
    return false;
  }

  if (inputTensor->dims->size != 3 ||
      inputTensor->dims->data[0] != 1 ||
      inputTensor->dims->data[1] != kWindowSize ||
      inputTensor->dims->data[2] != kFeatureCount) {
    Serial.println("Unexpected input tensor shape");
    Serial.printf("Input dims size=%d\n", inputTensor->dims->size);
    return false;
  }

  if (outputElementCount != 1 && outputElementCount != 2) {
    Serial.println("Unexpected output tensor shape");
    Serial.printf("Output elements=%d\n", outputElementCount);
    return false;
  }

  Serial.println("TFLite Micro ready");
  Serial.printf("Input: scale=%.6f zero_point=%d shape=[1,%d,%d]\n",
                inputTensor->params.scale,
                inputTensor->params.zero_point,
                kWindowSize,
                kFeatureCount);
  Serial.printf("Output: scale=%.6f zero_point=%d elements=%d\n",
                outputTensor->params.scale,
                outputTensor->params.zero_point,
                outputElementCount);
  return true;
}

bool runFallInference(float &fallProb, float &nonFallProb) {
  if (!modelOk || windowCount < kWindowSize) return false;

  for (int t = 0; t < kWindowSize; ++t) {
    ImuSample sample = orderedSampleAt(t);
    inputTensor->data.int8[t * kFeatureCount + 0] = quantizeInput(sample.ax);
    inputTensor->data.int8[t * kFeatureCount + 1] = quantizeInput(sample.ay);
    inputTensor->data.int8[t * kFeatureCount + 2] = quantizeInput(sample.az);
    inputTensor->data.int8[t * kFeatureCount + 3] = quantizeInput(sample.gx);
    inputTensor->data.int8[t * kFeatureCount + 4] = quantizeInput(sample.gy);
    inputTensor->data.int8[t * kFeatureCount + 5] = quantizeInput(sample.gz);
  }

  if (interpreter->Invoke() != kTfLiteOk) {
    Serial.println("Invoke failed");
    return false;
  }

  if (outputElementCount == 1) {
    fallProb = clamp01(dequantizeOutput(outputTensor->data.int8[0]));
    nonFallProb = 1.0f - fallProb;
  } else {
    nonFallProb = clamp01(dequantizeOutput(outputTensor->data.int8[0]));
    fallProb = clamp01(dequantizeOutput(outputTensor->data.int8[1]));
  }

  return true;
}

void sampleImuIfDue() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastSampleMs) < SAMPLE_PERIOD_MS) return;
  lastSampleMs = now;

  ImuSample sample;
  if (!readImuSample(sample)) {
    latestImuValid = false;
    return;
  }

  latestImu = sample;
  latestImuValid = true;
  pushImuSample(sample);

  if (windowCount >= kWindowSize && samplesSinceInference >= kInferenceStride) {
    float fallProb = 0.0f;
    float nonFallProb = 1.0f;
    if (runFallInference(fallProb, nonFallProb)) {
      latestFallProb = fallProb;
      latestNonFallProb = nonFallProb;
      latestFallDetected = (fallProb >= FALL_DECISION_THRESHOLD);
      latestInferenceValid = true;
      ++inferenceCount;
    }
    samplesSinceInference = 0;
  }
}

void updateMax30102() {
  if (!max30102Ok) return;
  max30102_update();
}

void printStatusIfDue() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastSerialPrintMs) < SERIAL_PRINT_PERIOD_MS) return;
  lastSerialPrintMs = now;

  VitalsReading vitals;
  if (max30102Ok) {
    vitals = max30102_getLatestVitals();
  } else {
    vitals.heartRate = INVALID_VITAL_VALUE;
    vitals.spo2 = INVALID_VITAL_VALUE;
    vitals.fingerDetected = false;
    vitals.valid = false;
    vitals.timestamp = millis();
  }

  const char *aiStatus = "warming-up";
  if (latestInferenceValid) {
    aiStatus = latestFallDetected ? "fall" : "non-fall";
  }

  Serial.printf(
      "IMU ax=%.3f ay=%.3f az=%.3f g | gyro gx=%.2f gy=%.2f gz=%.2f dps | "
      "HR=%u bpm SpO2=%u%% finger=%s vitals_valid=%s | "
      "AI status=%s fall=%.3f non_fall=%.3f window=%d/%d inference=%lu\n",
      latestImu.ax,
      latestImu.ay,
      latestImu.az,
      latestImu.gx,
      latestImu.gy,
      latestImu.gz,
      vitals.heartRate,
      vitals.spo2,
      vitals.fingerDetected ? "yes" : "no",
      vitals.valid ? "yes" : "no",
      aiStatus,
      latestFallProb,
      latestNonFallProb,
      windowCount,
      kWindowSize,
      (unsigned long)inferenceCount);

  if (!bmiOk) {
    Serial.println("WARN: BMI160 is not initialized; check 0x68/0x69 wiring");
  } else if (!latestImuValid) {
    Serial.println("WARN: BMI160 initialized but latest read failed");
  }

  if (!max30102Ok) {
    Serial.println("WARN: MAX30102 is not initialized; HR/SpO2 stay at 255");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println();
  Serial.println("=== ESP32-S3 Combine: BMI160 + MAX30102 + Fall AI ===");
  Serial.printf("I2C pins: SDA=GPIO%d SCL=GPIO%d\n", I2C_SDA_PIN, I2C_SCL_PIN);

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  delay(100);

  scanI2C();

  bmiOk = initBMI160();
  Serial.println(bmiOk ? "BMI160 initialization SUCCESS"
                       : "BMI160 initialization FAILED");

  max30102Ok = max30102_init();
  Serial.println(max30102Ok ? "MAX30102 initialization SUCCESS"
                            : "MAX30102 initialization FAILED - HR/SpO2 will be 255");

  modelOk = initModel();
  if (!modelOk) {
    Serial.println("Model initialization FAILED - AI status will stay warming-up");
  }

  lastSampleMs = millis();
  lastSerialPrintMs = millis();
  Serial.println("System initialized. Put finger on MAX30102 for valid HR/SpO2.");
}

void loop() {
  updateMax30102();
  sampleImuIfDue();
  printStatusIfDue();
  delay(1);
}
