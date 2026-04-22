#include <Arduino.h>
#include <NimBLEDevice.h>
#include <Wire.h>
#include <math.h>

#include "../../esp32-S3-build/include/fall_detection_model.h"
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
// BLE
// =====================================================
static const char *BLE_DEVICE_NAME = "ESP32-fall-detection-BLE";
static const char *BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char *BLE_STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8";
static const char *BLE_VITALS_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1";
static const char *BLE_CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03";

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
static const int kInferenceStride = 100;
static const int kTensorArenaSize = 60 * 1024;

static const float FALL_DECISION_THRESHOLD = 0.40f;
static const float CANDIDATE_ACC_THRESHOLD = 1.8f;
static const float CANDIDATE_GYRO_THRESHOLD = 50.0f;

// =====================================================
// VITALS BATCHING
// =====================================================
static const uint32_t VITALS_SAMPLE_PERIOD_MS = 5000;
static const uint32_t VITALS_DISPATCH_PERIOD_MS = 25000;
static const uint8_t VITALS_BATCH_SIZE = 5;
static const uint8_t INVALID_VITAL_VALUE = 255;
static const size_t VITALS_QUEUE_CAPACITY = 32;
static const size_t FALL_QUEUE_CAPACITY = 16;
static const uint16_t BLE_NOTIFY_SPACING_MS = 30;
static const uint32_t SIMULATED_UNIX_EPOCH_BASE_UTC = 1776729600UL;  // 2026-04-21 00:00:00 UTC

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
const tflite::Model *model = nullptr;
tflite::ErrorReporter *errorReporter = nullptr;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *inputTensor = nullptr;
TfLiteTensor *outputTensor = nullptr;
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
// VITALS STATE
// =====================================================
struct VitalSample {
  uint8_t heartRate = INVALID_VITAL_VALUE;
  uint8_t spo2 = INVALID_VITAL_VALUE;
  uint32_t timestampSec = 0;
};

struct VitalsBatchPacket {
  uint32_t sequence = 0;
  uint8_t heartRate[VITALS_BATCH_SIZE] = {INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
                                          INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
                                          INVALID_VITAL_VALUE};
  uint8_t spo2[VITALS_BATCH_SIZE] = {INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
                                     INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
                                     INVALID_VITAL_VALUE};
  uint32_t timestampSec[VITALS_BATCH_SIZE] = {0, 0, 0, 0, 0};
};

struct FallAlertPacket {
  uint32_t sequence = 0;
  uint32_t timestampSec = 0;
  uint8_t statusCode = 1;
  float fallProb = 0.0f;
  float nonFallProb = 0.0f;
};

VitalSample vitalsHistory[VITALS_BATCH_SIZE];
uint8_t vitalsHistoryHead = 0;
uint8_t vitalsHistoryCount = 0;
uint32_t lastVitalsSampleMs = 0;
uint32_t lastVitalsDispatchMs = 0;
uint32_t nextVitalsSequence = 1;
uint32_t nextFallSequence = 1;

VitalsBatchPacket vitalsQueue[VITALS_QUEUE_CAPACITY];
size_t vitalsQueueHead = 0;
size_t vitalsQueueCount = 0;

FallAlertPacket fallQueue[FALL_QUEUE_CAPACITY];
size_t fallQueueHead = 0;
size_t fallQueueCount = 0;

// =====================================================
// BLE STATE
// =====================================================
NimBLEServer *bleServer = nullptr;
NimBLECharacteristic *statusCharacteristic = nullptr;
NimBLECharacteristic *vitalsCharacteristic = nullptr;
NimBLECharacteristic *controlCharacteristic = nullptr;
bool bleClientConnected = false;
bool bleFlushRequested = false;
bool bleClientReady = false;

void requestFlushAfterReady() {
  if (!bleClientConnected) return;
  if (!bleClientReady) return;
  bleFlushRequested = true;
}

class BleServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *server) override {
    (void)server;
    bleClientConnected = true;
    bleClientReady = false;
    bleFlushRequested = false;
    Serial.println("BLE client connected");
    Serial.println("Waiting for READY command from client before flushing backlog");
  }

  void onDisconnect(NimBLEServer *server) override {
    bleClientConnected = false;
    bleClientReady = false;
    bleFlushRequested = false;
    server->startAdvertising();
    Serial.println("BLE client disconnected");
    Serial.println("BLE advertising restarted");
  }
};

class ControlCharacteristicCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *characteristic) override {
    std::string value = characteristic->getValue();
    String command = String(value.c_str());
    command.trim();
    command.toUpperCase();

    Serial.print("Control command received: ");
    Serial.println(command);

    if (command == "READY") {
      bleClientReady = true;
      requestFlushAfterReady();
      characteristic->setValue("ACK:READY");
      return;
    }

    if (command == "PING") {
      characteristic->setValue("ACK:PING");
      return;
    }

    characteristic->setValue("ERR:UNKNOWN_COMMAND");
  }
};

// =====================================================
// UTILS
// =====================================================
int16_t toInt16(uint8_t lsb, uint8_t msb) {
  return (int16_t)((msb << 8) | lsb);
}

bool writeReg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(bmi160Addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegs(uint8_t reg, uint8_t *buffer, size_t len) {
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

bool readReg(uint8_t reg, uint8_t &value) {
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

bool readAccelRaw(int16_t &axRaw, int16_t &ayRaw, int16_t &azRaw) {
  uint8_t d[6];
  if (!readRegs(REG_ACC_DATA, d, 6)) return false;
  axRaw = toInt16(d[0], d[1]);
  ayRaw = toInt16(d[2], d[3]);
  azRaw = toInt16(d[4], d[5]);
  return true;
}

bool readGyroRaw(int16_t &gxRaw, int16_t &gyRaw, int16_t &gzRaw) {
  uint8_t d[6];
  if (!readRegs(REG_GYR_DATA, d, 6)) return false;
  gxRaw = toInt16(d[0], d[1]);
  gyRaw = toInt16(d[2], d[3]);
  gzRaw = toInt16(d[4], d[5]);
  return true;
}

bool readBMI160StepCount(uint16_t &stepCount) {
  (void)stepCount;
  return false;
}

bool initBMI160() {
  if (!detectBMI160()) return false;

  if (!writeReg(REG_CMD, 0x11)) return false;
  delay(10);

  if (!writeReg(REG_CMD, 0x15)) return false;
  delay(80);

  if (!writeReg(REG_ACC_CONF, 0x28)) return false;
  if (!writeReg(REG_ACC_RANGE, 0x03)) return false;

  if (!writeReg(REG_GYR_CONF, 0x28)) return false;
  if (!writeReg(REG_GYR_RANGE, 0x00)) return false;

  delay(10);
  return true;
}

bool readImuSample(ImuSample &sample) {
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

uint32_t currentUnixTimeSecUtc() {
  return SIMULATED_UNIX_EPOCH_BASE_UTC + (millis() / 1000UL);
}

bool readVitalsSample(VitalSample &sample) {
  sample.timestampSec = currentUnixTimeSecUtc();
  sample.heartRate = (uint8_t)random(68, 96);
  sample.spo2 = (uint8_t)random(94, 100);
  return true;
}

void resetWindow() {
  windowHead = 0;
  windowCount = 0;
  samplesSinceInference = 0;
}

void resetVitalsState() {
  vitalsHistoryHead = 0;
  vitalsHistoryCount = 0;
  lastVitalsSampleMs = millis();
  lastVitalsDispatchMs = millis();
}

void pushSample(const ImuSample &sample) {
  imuWindow[windowHead] = sample;
  windowHead = (windowHead + 1) % kWindowSize;
  if (windowCount < kWindowSize) {
    windowCount++;
  }
  samplesSinceInference++;
}

void pushVitalsHistory(const VitalSample &sample) {
  vitalsHistory[vitalsHistoryHead] = sample;
  vitalsHistoryHead = (vitalsHistoryHead + 1) % VITALS_BATCH_SIZE;
  if (vitalsHistoryCount < VITALS_BATCH_SIZE) {
    vitalsHistoryCount++;
  }
}

VitalSample orderedVitalSampleAt(uint8_t idx) {
  uint8_t start = (vitalsHistoryCount < VITALS_BATCH_SIZE) ? 0 : vitalsHistoryHead;
  return vitalsHistory[(start + idx) % VITALS_BATCH_SIZE];
}

bool buildLatestVitalsBatch(VitalsBatchPacket &packet) {
  if (vitalsHistoryCount < VITALS_BATCH_SIZE) return false;

  packet.sequence = nextVitalsSequence++;
  for (uint8_t i = 0; i < VITALS_BATCH_SIZE; ++i) {
    VitalSample sample = orderedVitalSampleAt(i);
    packet.heartRate[i] = sample.heartRate;
    packet.spo2[i] = sample.spo2;
    packet.timestampSec[i] = sample.timestampSec;
  }
  return true;
}

size_t vitalsQueueIndex(size_t index) {
  return (vitalsQueueHead + index) % VITALS_QUEUE_CAPACITY;
}

size_t fallQueueIndex(size_t index) {
  return (fallQueueHead + index) % FALL_QUEUE_CAPACITY;
}

void enqueueVitalsBatch(const VitalsBatchPacket &packet) {
  if (vitalsQueueCount == VITALS_QUEUE_CAPACITY) {
    vitalsQueueHead = vitalsQueueIndex(1);
    vitalsQueueCount--;
  }

  size_t tail = vitalsQueueIndex(vitalsQueueCount);
  vitalsQueue[tail] = packet;
  vitalsQueueCount++;
}

void dequeueVitalsBatch() {
  if (vitalsQueueCount == 0) return;
  vitalsQueueHead = vitalsQueueIndex(1);
  vitalsQueueCount--;
}

void enqueueFallAlert(const FallAlertPacket &packet) {
  if (fallQueueCount == FALL_QUEUE_CAPACITY) {
    fallQueueHead = fallQueueIndex(1);
    fallQueueCount--;
  }

  size_t tail = fallQueueIndex(fallQueueCount);
  fallQueue[tail] = packet;
  fallQueueCount++;
}

void dequeueFallAlert() {
  if (fallQueueCount == 0) return;
  fallQueueHead = fallQueueIndex(1);
  fallQueueCount--;
}

int oldestIndex() {
  if (windowCount < kWindowSize) return 0;
  return windowHead;
}

ImuSample orderedSampleAt(int idx) {
  int start = oldestIndex();
  return imuWindow[(start + idx) % kWindowSize];
}

bool windowIsCandidate(float &maxAccMag, float &maxGyroMag) {
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

int countTensorElements(const TfLiteTensor *tensor) {
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

bool runInference(float &fallProb,
                  float &nonFallProb,
                  uint32_t &tsStart,
                  uint32_t &tsEnd) {
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
        resetVitalsState();
        lastSampleMs = millis();

        Serial.print("Acquisition -> ");
        Serial.println(acquisitionEnabled ? "ON" : "OFF");
      }
    }
  }

  lastButtonReading = reading;
}

bool notifyIfConnected(NimBLECharacteristic *characteristic, const String &payload) {
  characteristic->setValue(
      reinterpret_cast<const uint8_t *>(payload.c_str()),
      payload.length());
  if (!bleClientConnected) return false;
  characteristic->notify();
  delay(BLE_NOTIFY_SPACING_MS);
  return bleClientConnected;
}

String formatVitalsBatchPayload(const VitalsBatchPacket &packet) {
  String payload = "BATCH,";
  payload += String(packet.sequence);
  payload += ",";
  for (uint8_t i = 0; i < VITALS_BATCH_SIZE; ++i) {
    if (i > 0) payload += "|";
    payload += String(packet.heartRate[i]);
  }
  payload += ",";
  for (uint8_t i = 0; i < VITALS_BATCH_SIZE; ++i) {
    if (i > 0) payload += "|";
    payload += String(packet.spo2[i]);
  }
  payload += ",";
  for (uint8_t i = 0; i < VITALS_BATCH_SIZE; ++i) {
    if (i > 0) payload += "|";
    payload += String(packet.timestampSec[i]);
  }
  return payload;
}

String formatFallAlertPayload(const FallAlertPacket &packet) {
  String payload = "ALERT,";
  payload += String(packet.sequence);
  payload += ",";
  payload += String(packet.timestampSec);
  payload += ",fall,";
  payload += String(packet.statusCode);
  payload += ",";
  payload += String(packet.fallProb, 3);
  payload += ",";
  payload += String(packet.nonFallProb, 3);
  return payload;
}

bool sendVitalsBatch(const VitalsBatchPacket &packet) {
  String payload = formatVitalsBatchPayload(packet);
  bool sent = notifyIfConnected(vitalsCharacteristic, payload);
  if (sent) {
    Serial.print("Vitals batch sent: ");
    Serial.println(payload);
  }
  return sent;
}

bool sendFallAlert(const FallAlertPacket &packet) {
  String payload = formatFallAlertPayload(packet);
  bool sent = notifyIfConnected(statusCharacteristic, payload);
  if (sent) {
    Serial.print("Fall alert sent: ");
    Serial.println(payload);
  }
  return sent;
}

void flushBleBacklog() {
  if (!bleClientConnected) return;

  while (bleClientConnected && fallQueueCount > 0) {
    if (!sendFallAlert(fallQueue[fallQueueHead])) break;
    dequeueFallAlert();
  }

  while (bleClientConnected && vitalsQueueCount > 0) {
    if (!sendVitalsBatch(vitalsQueue[vitalsQueueHead])) break;
    dequeueVitalsBatch();
  }

  if (bleClientConnected) {
    Serial.println("Backlog flush completed");
  }
  bleFlushRequested = false;
}

void queueOrSendVitalsBatch(const VitalsBatchPacket &packet) {
  if (bleClientConnected && sendVitalsBatch(packet)) return;
  enqueueVitalsBatch(packet);
  Serial.print("Vitals batch queued, size=");
  Serial.println((int)vitalsQueueCount);
}

void queueOrSendFallAlert(const FallAlertPacket &packet) {
  if (bleClientConnected && sendFallAlert(packet)) return;
  enqueueFallAlert(packet);
  Serial.print("Fall alert queued, size=");
  Serial.println((int)fallQueueCount);
}

void maybeSampleVitals() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastVitalsSampleMs) < VITALS_SAMPLE_PERIOD_MS) return;
  lastVitalsSampleMs += VITALS_SAMPLE_PERIOD_MS;

  VitalSample sample;
  if (!readVitalsSample(sample)) {
    Serial.println("Vitals read failed");
    return;
  }

  pushVitalsHistory(sample);
  Serial.print("Vitals sample collected: hr=");
  Serial.print(sample.heartRate);
  Serial.print(" spo2=");
  Serial.print(sample.spo2);
  Serial.print(" ts=");
  Serial.println(sample.timestampSec);
}

void maybeDispatchVitalsBatch() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastVitalsDispatchMs) < VITALS_DISPATCH_PERIOD_MS) return;
  lastVitalsDispatchMs += VITALS_DISPATCH_PERIOD_MS;

  VitalsBatchPacket packet;
  if (!buildLatestVitalsBatch(packet)) return;
  queueOrSendVitalsBatch(packet);
}

void initBle() {
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);
  bleServer = NimBLEDevice::createServer();
  bleServer->setCallbacks(new BleServerCallbacks());

  NimBLEService *service = bleServer->createService(BLE_SERVICE_UUID);

  statusCharacteristic = service->createCharacteristic(
      BLE_STATUS_CHAR_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  vitalsCharacteristic = service->createCharacteristic(
      BLE_VITALS_CHAR_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  controlCharacteristic = service->createCharacteristic(
      BLE_CONTROL_CHAR_UUID,
      NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
  controlCharacteristic->setCallbacks(new ControlCharacteristicCallbacks());

  statusCharacteristic->setValue("ALERT,0,0,idle,0,0.000,1.000");
  vitalsCharacteristic->setValue(
      "BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
  controlCharacteristic->setValue("WAITING_READY");

  service->start();

  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();

  Serial.println("BLE advertising started");
  Serial.printf("Device name: %s\n", BLE_DEVICE_NAME);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  randomSeed((uint32_t)esp_random());

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println();
  Serial.println("=== ESP32-S3 BMI160 Fall Detection BLE ===");

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
  Wire.setClock(100000);
  Wire.setTimeOut(20);
  delay(50);

  Serial.printf("Probe BMI160 0x68: %s\n", probeAddress(0x68) ? "OK" : "FAIL");
  Serial.printf("Probe BMI160 0x69: %s\n", probeAddress(0x69) ? "OK" : "FAIL");

  bmiOk = initBMI160();
  Serial.println(bmiOk ? "BMI160 OK" : "BMI160 NOT FOUND");

  initBle();

  if (!initModel()) {
    Serial.println("Model init failed");
    while (true) delay(1000);
  }

  resetVitalsState();

  Serial.println("Nhan button de bat/tat thu thap va suy luan.");
  Serial.println("BLE status notify: chi gui khi co fall.");
  Serial.println("BLE vitals notify: lay mau moi 5s va gui 1 batch 5 diem moi 25s.");
  Serial.println("BLE backlog chi flush sau khi client subscribe xong va gui lenh READY.");
}

void loop() {
  handleButton();

  if (bleFlushRequested && bleClientConnected) {
    flushBleBacklog();
  }

  if (!acquisitionEnabled) {
    delay(10);
    return;
  }

  maybeSampleVitals();
  maybeDispatchVitalsBatch();

  uint32_t now = millis();
  if ((uint32_t)(now - lastSampleMs) < SAMPLE_PERIOD_MS) {
    delay(1);
    return;
  }

  lastSampleMs += SAMPLE_PERIOD_MS;

  ImuSample sample;
  if (!readImuSample(sample)) {
    Serial.println("IMU read failed");
    delay(5);
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

  const bool isFall = fallProb >= FALL_DECISION_THRESHOLD;
  Serial.print("ts_start=");
  Serial.print(tsStart);
  Serial.print(" ts_end=");
  Serial.print(tsEnd);
  Serial.print(" fall_prob=");
  Serial.print(fallProb, 3);
  Serial.print(" non_fall_prob=");
  Serial.print(nonFallProb, 3);
  Serial.print(" prediction=");
  Serial.println(isFall ? "fall" : "non-fall");

  if (!isFall) return;

  FallAlertPacket packet;
  packet.sequence = nextFallSequence++;
  packet.timestampSec = currentUnixTimeSecUtc();
  packet.statusCode = 1;
  packet.fallProb = fallProb;
  packet.nonFallProb = nonFallProb;
  queueOrSendFallAlert(packet);
}
