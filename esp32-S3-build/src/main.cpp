#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <math.h>

#include "fall_detection_model.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// =====================================================
// PINS
// =====================================================
static const int I2C_SDA_PIN = 8;
static const int I2C_SCL_PIN = 9;
static const int BUTTON_PIN = 10;
static const int LED_PIN = 48;

// =====================================================
// WIFI + THINGSBOARD
// =====================================================
static const char* WIFI_SSID = "TRAN PHUOC DIEN";
static const char* WIFI_PASS = "11223344";
static const char* TB_TELEMETRY_URL =
    "https://visiflow-dev.m-tech.com.vn/api/v1/AIFD/telemetry";

// =====================================================
// BMI160 REGISTERS
// =====================================================
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

static const float ACC_LSB_PER_G = 16384.0f;
static const float GYR_LSB_PER_DPS = 16.4f;

// =====================================================
// SAMPLING + MODEL
// =====================================================
static const uint32_t SAMPLE_RATE_HZ = 50;
static const uint32_t SAMPLE_PERIOD_MS = 1000 / SAMPLE_RATE_HZ;

static const int kWindowSize = 100;
static const int kFeatureCount = 6;
static const int kInferenceStride = 100;  // 2s at 50Hz
static const int kTensorArenaSize = 60 * 1024;

static const float FALL_DECISION_THRESHOLD = 0.40f;
static const float CANDIDATE_ACC_THRESHOLD = 1.8f;
static const float CANDIDATE_GYRO_THRESHOLD = 50.0f;

// =====================================================
// BUTTON STATE
// =====================================================
bool acquisitionEnabled = false;
bool buttonState = HIGH;
bool lastButtonReading = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

// =====================================================
// MODEL STATE
// =====================================================
namespace {
const tflite::Model* model = nullptr;
tflite::ErrorReporter* errorReporter = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* inputTensor = nullptr;
TfLiteTensor* outputTensor = nullptr;
uint8_t tensorArena[kTensorArenaSize];
int outputElementCount = 0;
}  // namespace

// =====================================================
// IMU WINDOW
// =====================================================
struct ImuSample {
  float ax = 0.0f;
  float ay = 0.0f;
  float az = 0.0f;
  float gx = 0.0f;
  float gy = 0.0f;
  float gz = 0.0f;
  uint32_t tsMs = 0;
};

ImuSample imuWindow[kWindowSize];
int windowHead = 0;
int windowCount = 0;
int samplesSinceInference = 0;

uint8_t bmi160Addr = BMI160_ADDR_LOW;
bool bmiOk = false;
uint32_t lastSampleMs = 0;

// =====================================================
// UTILS
// =====================================================
int16_t toInt16(uint8_t lsb, uint8_t msb) {
  return (int16_t)((msb << 8) | lsb);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    Serial.print(".");
    delay(300);
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connect failed");
  }
}

void uploadTelemetryToThingsBoard(const ImuSample& sample, int status, const char* statusLetter) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Telemetry upload skipped: no WiFi");
      return;
    }
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(2000);

  if (!http.begin(client, TB_TELEMETRY_URL)) {
    Serial.println("TB HTTP begin failed");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  String payload = "{";
  payload += "\"ax\":" + String(sample.ax, 3) + ",";
  payload += "\"ay\":" + String(sample.ay, 3) + ",";
  payload += "\"az\":" + String(sample.az, 3) + ",";
  payload += "\"gx\":" + String(sample.gx, 2) + ",";
  payload += "\"gy\":" + String(sample.gy, 2) + ",";
  payload += "\"gz\":" + String(sample.gz, 2) + ",";
  payload += "\"status\":" + String(status) + ",";
  payload += "\"status_letter\":\"" + String(statusLetter) + "\"";
  payload += "}";

  int code = http.POST(payload);
  Serial.print("TB telemetry HTTP code: ");
  Serial.println(code);

  if (code <= 0) {
    Serial.print("TB telemetry POST failed: ");
    Serial.println(http.errorToString(code));
  }

  http.end();
}

bool writeReg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(bmi160Addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegs(uint8_t reg, uint8_t* buffer, size_t len) {
  Wire.beginTransmission(bmi160Addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;

  size_t got = Wire.requestFrom((int)bmi160Addr, (int)len, (int)true);
  if (got != len) return false;

  for (size_t i = 0; i < len; ++i) {
    buffer[i] = Wire.read();
  }
  return true;
}

bool readReg(uint8_t reg, uint8_t& value) {
  return readRegs(reg, &value, 1);
}

bool probeAddress(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

bool detectBMI160() {
  uint8_t chipId = 0;

  bmi160Addr = BMI160_ADDR_LOW;
  if (readReg(REG_CHIP_ID, chipId) && chipId == BMI160_CHIP_ID) return true;

  bmi160Addr = BMI160_ADDR_HIGH;
  if (readReg(REG_CHIP_ID, chipId) && chipId == BMI160_CHIP_ID) return true;

  return false;
}

bool initBMI160() {
  if (!detectBMI160()) return false;

  if (!writeReg(REG_CMD, 0x11)) return false;
  delay(10);

  if (!writeReg(REG_CMD, 0x15)) return false;
  delay(80);

  // 0x28 selects 100Hz ODR in normal mode for BMI160 accel/gyro.
  // The firmware still samples at 50Hz, so every 20ms we read the latest sensor data.
  if (!writeReg(REG_ACC_CONF, 0x28)) return false;
  if (!writeReg(REG_ACC_RANGE, 0x03)) return false;

  if (!writeReg(REG_GYR_CONF, 0x28)) return false;
  if (!writeReg(REG_GYR_RANGE, 0x00)) return false;

  delay(10);
  return true;
}

bool readAccelRaw(int16_t& axRaw, int16_t& ayRaw, int16_t& azRaw) {
  uint8_t d[6];
  if (!readRegs(REG_ACC_DATA, d, 6)) return false;
  axRaw = toInt16(d[0], d[1]);
  ayRaw = toInt16(d[2], d[3]);
  azRaw = toInt16(d[4], d[5]);
  return true;
}

bool readGyroRaw(int16_t& gxRaw, int16_t& gyRaw, int16_t& gzRaw) {
  uint8_t d[6];
  if (!readRegs(REG_GYR_DATA, d, 6)) return false;
  gxRaw = toInt16(d[0], d[1]);
  gyRaw = toInt16(d[2], d[3]);
  gzRaw = toInt16(d[4], d[5]);
  return true;
}

bool readImuSample(ImuSample& sample) {
  if (!bmiOk) return false;

  int16_t axRaw, ayRaw, azRaw;
  int16_t gxRaw, gyRaw, gzRaw;
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

void resetWindow() {
  windowHead = 0;
  windowCount = 0;
  samplesSinceInference = 0;
}

void pushSample(const ImuSample& sample) {
  imuWindow[windowHead] = sample;
  windowHead = (windowHead + 1) % kWindowSize;
  if (windowCount < kWindowSize) {
    windowCount++;
  }
  samplesSinceInference++;
}

int oldestIndex() {
  if (windowCount < kWindowSize) return 0;
  return windowHead;
}

ImuSample orderedSampleAt(int idx) {
  int start = oldestIndex();
  return imuWindow[(start + idx) % kWindowSize];
}

bool windowIsCandidate(float& maxAccMag, float& maxGyroMag) {
  maxAccMag = 0.0f;
  maxGyroMag = 0.0f;

  for (int i = 0; i < kWindowSize; ++i) {
    ImuSample s = orderedSampleAt(i);
    float accMag = sqrtf(s.ax * s.ax + s.ay * s.ay + s.az * s.az);
    float gyroMag = sqrtf(s.gx * s.gx + s.gy * s.gy + s.gz * s.gz);

    if (accMag > maxAccMag) maxAccMag = accMag;
    if (gyroMag > maxGyroMag) maxGyroMag = gyroMag;
  }

  return (maxAccMag > CANDIDATE_ACC_THRESHOLD) ||
         (maxGyroMag > CANDIDATE_GYRO_THRESHOLD);
}

int8_t quantizeInput(float value) {
  const float scale = inputTensor->params.scale;
  const int zeroPoint = inputTensor->params.zero_point;

  int q = (int)lroundf(value / scale) + zeroPoint;
  if (q > 127) q = 127;
  if (q < -128) q = -128;
  return (int8_t)q;
}

float dequantizeOutput(int8_t value) {
  return (value - outputTensor->params.zero_point) * outputTensor->params.scale;
}

int countTensorElements(const TfLiteTensor* tensor) {
  int count = 1;
  for (int i = 0; i < tensor->dims->size; ++i) {
    count *= tensor->dims->data[i];
  }
  return count;
}

bool initModel() {
  model = tflite::GetModel(fall_detection_model_tflite);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.println("Model schema mismatch");
    return false;
  }

  static tflite::MicroErrorReporter microErrorReporter;
  errorReporter = &microErrorReporter;
  static tflite::AllOpsResolver resolver;
  static tflite::MicroInterpreter staticInterpreter(
      model, resolver, tensorArena, kTensorArenaSize, errorReporter);

  interpreter = &staticInterpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("AllocateTensors failed");
    return false;
  }

  inputTensor = interpreter->input(0);
  outputTensor = interpreter->output(0);

  Serial.printf("Input type: %d\n", inputTensor->type);
  Serial.printf("Output type: %d\n", outputTensor->type);
  Serial.printf("Input scale: %.9f zp: %d\n",
                inputTensor->params.scale,
                inputTensor->params.zero_point);
  Serial.printf("Output scale: %.9f zp: %d\n",
                outputTensor->params.scale,
                outputTensor->params.zero_point);
  Serial.print("Output dims:");
  for (int i = 0; i < outputTensor->dims->size; ++i) {
    Serial.print(i == 0 ? " [" : ", ");
    Serial.print(outputTensor->dims->data[i]);
  }
  Serial.println("]");

  if (inputTensor->type != kTfLiteInt8 || outputTensor->type != kTfLiteInt8) {
    Serial.println("Model tensor type is not int8");
    return false;
  }

  if (inputTensor->dims->size != 3 ||
      inputTensor->dims->data[0] != 1 ||
      inputTensor->dims->data[1] != kWindowSize ||
      inputTensor->dims->data[2] != kFeatureCount) {
    Serial.println("Unexpected input tensor shape");
    return false;
  }

  outputElementCount = countTensorElements(outputTensor);
  if (outputElementCount != 1 && outputElementCount != 2) {
    Serial.println("Unexpected output tensor shape");
    return false;
  }

  Serial.println("TFLite Micro ready");
  return true;
}

bool runInference(float& fallProb, float& nonFallProb, uint32_t& tsStart, uint32_t& tsEnd) {
  if (windowCount < kWindowSize) return false;

  float maxAccMag = 0.0f;
  float maxGyroMag = 0.0f;
  bool candidate = windowIsCandidate(maxAccMag, maxGyroMag);

  ImuSample first = orderedSampleAt(0);
  ImuSample last = orderedSampleAt(kWindowSize - 1);
  tsStart = first.tsMs;
  tsEnd = last.tsMs;

  if (!candidate) {
    fallProb = 0.0f;
    nonFallProb = 1.0f;
    return true;
  }

  for (int t = 0; t < kWindowSize; ++t) {
    ImuSample s = orderedSampleAt(t);
    inputTensor->data.int8[t * kFeatureCount + 0] = quantizeInput(s.ax);
    inputTensor->data.int8[t * kFeatureCount + 1] = quantizeInput(s.ay);
    inputTensor->data.int8[t * kFeatureCount + 2] = quantizeInput(s.az);
    inputTensor->data.int8[t * kFeatureCount + 3] = quantizeInput(s.gx);
    inputTensor->data.int8[t * kFeatureCount + 4] = quantizeInput(s.gy);
    inputTensor->data.int8[t * kFeatureCount + 5] = quantizeInput(s.gz);
  }

  if (interpreter->Invoke() != kTfLiteOk) {
    Serial.println("Invoke failed");
    return false;
  }

  if (outputElementCount == 1) {
    fallProb = dequantizeOutput(outputTensor->data.int8[0]);
    if (fallProb < 0.0f) fallProb = 0.0f;
    if (fallProb > 1.0f) fallProb = 1.0f;
    nonFallProb = 1.0f - fallProb;
  } else {
    nonFallProb = dequantizeOutput(outputTensor->data.int8[0]);
    fallProb = dequantizeOutput(outputTensor->data.int8[1]);
  }
  return true;
}

void handleButton() {
  bool reading = digitalRead(BUTTON_PIN);

  if (reading != lastButtonReading) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;

      if (buttonState == LOW) {
        acquisitionEnabled = !acquisitionEnabled;
        digitalWrite(LED_PIN, acquisitionEnabled ? HIGH : LOW);
        resetWindow();
        lastSampleMs = millis();

        Serial.print("Acquisition -> ");
        Serial.println(acquisitionEnabled ? "ON" : "OFF");
      }
    }
  }

  lastButtonReading = reading;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println();
  Serial.println("=== ESP32-S3 BMI160 Fall Detection ===");

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  delay(50);

  Serial.printf("Probe BMI160 0x68: %s\n", probeAddress(0x68) ? "OK" : "FAIL");
  Serial.printf("Probe BMI160 0x69: %s\n", probeAddress(0x69) ? "OK" : "FAIL");

  bmiOk = initBMI160();
  Serial.println(bmiOk ? "BMI160 OK" : "BMI160 NOT FOUND");

  connectWiFi();

  if (!initModel()) {
    Serial.println("Model init failed");
    while (true) delay(1000);
  }

  Serial.println("Nhan button de bat/tat thu thap va suy luan.");
  Serial.println("Sau khi bat, moi 2 giay se in fall hoac non-fall.");
}

void loop() {
  handleButton();

  if (!acquisitionEnabled) {
    delay(5);
    return;
  }

  uint32_t now = millis();
  if ((uint32_t)(now - lastSampleMs) < SAMPLE_PERIOD_MS) {
    delay(1);
    return;
  }

  lastSampleMs += SAMPLE_PERIOD_MS;

  ImuSample sample;
  if (!readImuSample(sample)) {
    Serial.println("IMU read failed");
    delay(1);
    return;
  }

  pushSample(sample);

  if (windowCount < kWindowSize || samplesSinceInference < kInferenceStride) {
    return;
  }

  float fallProb = 0.0f;
  float nonFallProb = 0.0f;
  uint32_t tsStart = 0;
  uint32_t tsEnd = 0;

  bool ok = runInference(fallProb, nonFallProb, tsStart, tsEnd);
  samplesSinceInference = 0;

  if (!ok) {
    Serial.println("inference_error");
    return;
  }

  const char* prediction = (fallProb >= FALL_DECISION_THRESHOLD) ? "fall" : "non-fall";
  int status = (fallProb >= FALL_DECISION_THRESHOLD) ? 1 : 0;
  ImuSample latestSample = orderedSampleAt(kWindowSize - 1);

  Serial.print("ts_start=");
  Serial.print(tsStart);
  Serial.print(" ts_end=");
  Serial.print(tsEnd);
  Serial.print(" fall_prob=");
  Serial.print(fallProb, 3);
  Serial.print(" non_fall_prob=");
  Serial.print(nonFallProb, 3);
  Serial.print(" prediction=");
  Serial.println(prediction);

  uploadTelemetryToThingsBoard(latestSample, status, prediction);
}
