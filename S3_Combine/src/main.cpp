#include <Arduino.h>
#include <NimBLEDevice.h>
#include <Wire.h>
#include <math.h>
#include <stdio.h>
#include <string>

#include "fall_detection_model.h"
#include "max30102_sensor.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#ifndef S3_I2C_SDA_GPIO
#define S3_I2C_SDA_GPIO 8
#endif
#ifndef S3_I2C_SCL_GPIO
#define S3_I2C_SCL_GPIO 9
#endif
static const int I2C_SDA_PIN = S3_I2C_SDA_GPIO;
static const int I2C_SCL_PIN = S3_I2C_SCL_GPIO;
static const int LED_PIN = 48;

// BLE: same service + ALERT/VITALS/CONTROL as S3_BLE (BLE_PROTOCOL.md)
static const char *BLE_DEVICE_NAME = "ESP32-fall-detection-BLE";
static const char *BLE_SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char *BLE_STATUS_CHAR_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8";
static const char *BLE_VITALS_CHAR_UUID = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1";
static const char *BLE_CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03";
// Extra: batched IMU for dashboard (5 samples @ 50 Hz -> notify every 100 ms)
static const char *BLE_IMU_CHAR_UUID = "6d3b70a9-64d3-4c98-9b9c-8a4a8e8d2f10";

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

static const uint32_t SAMPLE_RATE_HZ = 50;
static const uint32_t SAMPLE_PERIOD_MS = 1000 / SAMPLE_RATE_HZ;
static const uint32_t SERIAL_PRINT_PERIOD_MS = 1000;

static const int kWindowSize = 100;
static const int kFeatureCount = 6;
static const int kInferenceStride = 100;
static const int kTensorArenaSize = 60 * 1024;
static const float FALL_DECISION_THRESHOLD = 0.40f;
static const float CANDIDATE_ACC_THRESHOLD = 1.8f;
static const float CANDIDATE_GYRO_THRESHOLD = 50.0f;
static const uint8_t INVALID_VITAL_VALUE = 255;

static const uint32_t VITALS_SAMPLE_PERIOD_MS = 5000;
static const uint32_t VITALS_DISPATCH_PERIOD_MS = 25000;
static const uint8_t VITALS_BATCH_SIZE = 5;
static const size_t VITALS_QUEUE_CAPACITY = 32;
static const size_t FALL_QUEUE_CAPACITY = 16;
static const uint16_t BLE_NOTIFY_SPACING_MS = 25;
static const uint16_t BLE_IMU_NOTIFY_SPACING_MS = 12;
static const uint32_t SIMULATED_UNIX_EPOCH_BASE_UTC = 1776729600UL;

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

struct VitalSample {
  uint8_t heartRate = INVALID_VITAL_VALUE;
  uint8_t spo2 = INVALID_VITAL_VALUE;
  uint32_t timestampSec = 0;
};

struct VitalsBatchPacket {
  uint32_t sequence = 0;
  uint8_t heartRate[VITALS_BATCH_SIZE] = {
      INVALID_VITAL_VALUE, INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
      INVALID_VITAL_VALUE, INVALID_VITAL_VALUE};
  uint8_t spo2[VITALS_BATCH_SIZE] = {
      INVALID_VITAL_VALUE, INVALID_VITAL_VALUE, INVALID_VITAL_VALUE,
      INVALID_VITAL_VALUE, INVALID_VITAL_VALUE};
  uint32_t timestampSec[VITALS_BATCH_SIZE] = {0, 0, 0, 0, 0};
};

struct FallAlertPacket {
  uint32_t sequence = 0;
  uint32_t timestampSec = 0;
  uint8_t statusCode = 1;
  float fallProb = 0.0f;
  float nonFallProb = 0.0f;
};

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
bool latestModelInvoked = false;
uint32_t latestWindowTsStartMs = 0;
uint32_t latestWindowTsEndMs = 0;
uint32_t inferenceCount = 0;

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

NimBLEServer *bleServer = nullptr;
NimBLECharacteristic *statusCharacteristic = nullptr;
NimBLECharacteristic *vitalsCharacteristic = nullptr;
NimBLECharacteristic *imuCharacteristic = nullptr;
NimBLECharacteristic *controlCharacteristic = nullptr;
bool bleClientConnected = false;
bool bleFlushRequested = false;
bool bleClientReady = false;

uint32_t lastSampleMs = 0;
uint32_t lastSerialPrintMs = 0;

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
    Serial.println("BLE client connected (send READY from client to open IMU stream + flush)");
  }

  void onDisconnect(NimBLEServer *server) override {
    bleClientConnected = false;
    bleClientReady = false;
    bleFlushRequested = false;
    server->startAdvertising();
    Serial.println("BLE disconnected; advertising restarted");
  }
};

class ControlCharacteristicCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *characteristic) override {
    std::string value = characteristic->getValue();
    String command = String(value.c_str());
    command.trim();
    command.toUpperCase();

    if (command == "READY") {
      bleClientReady = true;
      requestFlushAfterReady();
      characteristic->setValue("ACK:READY");
      Serial.println("BLE: READY -> backlog flush + IMU notify enabled");
      return;
    }
    if (command == "PING") {
      characteristic->setValue("ACK:PING");
      return;
    }
    characteristic->setValue("ERR:UNKNOWN_COMMAND");
  }
};

uint32_t currentUnixTimeSecUtc() {
  return SIMULATED_UNIX_EPOCH_BASE_UTC + (millis() / 1000UL);
}

void recoverI2C() {
  Serial.println("[I2C] Attempting manual SCL recovery...");
  pinMode(I2C_SDA_PIN, INPUT_PULLUP);
  pinMode(I2C_SCL_PIN, OUTPUT);
  for (int i = 0; i < 10; i++) {
    digitalWrite(I2C_SCL_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(I2C_SCL_PIN, HIGH);
    delayMicroseconds(5);
  }
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);
}

bool initBMI160();

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
  for (int attempt = 0; attempt < 3; ++attempt) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    uint8_t err = Wire.endTransmission(false);
    if (err != 0) {
      if (attempt == 1) {
        Serial.printf("[I2C] Error %d. Toggling SCL recovery...\n", err);
        recoverI2C();
        writeReg(REG_CMD, 0xB6); // Soft reset sensor
        delay(50);
        initBMI160();
      }
      delay(2);
      continue;
    }
    size_t got = Wire.requestFrom((int)bmi160Addr, (int)len, (int)true);
    if (got != len) {
      if (attempt == 1) recoverI2C();
      delay(2);
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

#ifndef S3_COMBINE_FULL_I2C_SCAN
#define S3_COMBINE_FULL_I2C_SCAN 0
#endif

static bool probeI2CAddress(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission(true) == 0;
}

void scanI2C() {
#if S3_COMBINE_FULL_I2C_SCAN
  Serial.println("Scanning I2C bus (full 1-126)...");
#else
  Serial.println("Scanning I2C bus (quick probe: 0x57, 0x68, 0x69)...");
#endif
  Serial.flush();
  byte count = 0;
#if S3_COMBINE_FULL_I2C_SCAN
  for (byte addr = 1; addr < 127; ++addr) {
    if (probeI2CAddress(addr)) {
      Serial.printf("I2C device found at address 0x%02X\n", addr);
      ++count;
    }
    yield();
  }
#else
  static const uint8_t kProbeAddrs[] = {0x57, 0x68, 0x69};
  for (uint8_t addr : kProbeAddrs) {
    if (probeI2CAddress(addr)) {
      Serial.printf("I2C device found at address 0x%02X\n", addr);
      ++count;
    }
    yield();
  }
#endif
  if (count == 0) {
    Serial.println("No I2C devices at probed address(es).");
  } else {
    Serial.printf("Total %u I2C device(s) found\n", count);
  }
  Serial.flush();
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
  int16_t axRaw = 0, ayRaw = 0, azRaw = 0;
  int16_t gxRaw = 0, gyRaw = 0, gzRaw = 0;
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

static float accelMagG(const ImuSample &s) {
  return sqrtf(s.ax * s.ax + s.ay * s.ay + s.az * s.az);
}

static float windowMeanAccelMagG() {
  if (windowCount < kWindowSize) return 0.0f;
  float sum = 0.0f;
  for (int i = 0; i < kWindowSize; ++i) {
    sum += accelMagG(orderedSampleAt(i));
  }
  return sum / (float)kWindowSize;
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

void pushVitalsHistory(const VitalSample &sample) {
  vitalsHistory[vitalsHistoryHead] = sample;
  vitalsHistoryHead = (vitalsHistoryHead + 1) % VITALS_BATCH_SIZE;
  if (vitalsHistoryCount < VITALS_BATCH_SIZE) {
    ++vitalsHistoryCount;
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
    VitalSample s = orderedVitalSampleAt(i);
    packet.heartRate[i] = s.heartRate;
    packet.spo2[i] = s.spo2;
    packet.timestampSec[i] = s.timestampSec;
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
    --vitalsQueueCount;
  }
  vitalsQueue[vitalsQueueIndex(vitalsQueueCount)] = packet;
  ++vitalsQueueCount;
}

void dequeueVitalsBatch() {
  if (vitalsQueueCount == 0) return;
  vitalsQueueHead = vitalsQueueIndex(1);
  --vitalsQueueCount;
}

void enqueueFallAlert(const FallAlertPacket &packet) {
  if (fallQueueCount == FALL_QUEUE_CAPACITY) {
    fallQueueHead = fallQueueIndex(1);
    --fallQueueCount;
  }
  fallQueue[fallQueueIndex(fallQueueCount)] = packet;
  ++fallQueueCount;
}

void dequeueFallAlert() {
  if (fallQueueCount == 0) return;
  fallQueueHead = fallQueueIndex(1);
  --fallQueueCount;
}

void queueOrSendVitalsBatch(const VitalsBatchPacket &packet);
void queueOrSendFallAlert(const FallAlertPacket &packet);

bool readVitalsSample(VitalSample &sample) {
  sample.timestampSec = currentUnixTimeSecUtc();
  if (!max30102Ok) {
    sample.heartRate = INVALID_VITAL_VALUE;
    sample.spo2 = INVALID_VITAL_VALUE;
    return true;
  }
  VitalsReading r = max30102_getLatestVitals();
  sample.heartRate = r.heartRate;
  sample.spo2 = r.spo2;
  return true;
}

void resetVitalsState() {
  vitalsHistoryHead = 0;
  vitalsHistoryCount = 0;
  lastVitalsSampleMs = millis();
  lastVitalsDispatchMs = millis();
}

void maybeSampleVitals() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastVitalsSampleMs) < VITALS_SAMPLE_PERIOD_MS) return;
  lastVitalsSampleMs += VITALS_SAMPLE_PERIOD_MS;
  VitalSample sample;
  if (!readVitalsSample(sample)) return;
  pushVitalsHistory(sample);
}

void maybeDispatchVitalsBatch() {
  uint32_t now = millis();
  if ((uint32_t)(now - lastVitalsDispatchMs) < VITALS_DISPATCH_PERIOD_MS) return;
  lastVitalsDispatchMs += VITALS_DISPATCH_PERIOD_MS;
  VitalsBatchPacket packet;
  if (!buildLatestVitalsBatch(packet)) return;
  queueOrSendVitalsBatch(packet);
}

bool notifyIfConnected(NimBLECharacteristic *characteristic, const String &payload,
                       uint16_t spacingMs) {
  characteristic->setValue(reinterpret_cast<const uint8_t *>(payload.c_str()),
                           payload.length());
  if (!bleClientConnected) return false;
  characteristic->notify();
  delay(spacingMs);
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
  return notifyIfConnected(vitalsCharacteristic, formatVitalsBatchPayload(packet),
                           BLE_NOTIFY_SPACING_MS);
}

bool sendFallAlert(const FallAlertPacket &packet) {
  return notifyIfConnected(statusCharacteristic, formatFallAlertPayload(packet),
                           BLE_NOTIFY_SPACING_MS);
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
  bleFlushRequested = false;
}

void queueOrSendVitalsBatch(const VitalsBatchPacket &packet) {
  if (bleClientConnected && bleClientReady && sendVitalsBatch(packet)) return;
  enqueueVitalsBatch(packet);
}

void queueOrSendFallAlert(const FallAlertPacket &packet) {
  if (bleClientConnected && bleClientReady && sendFallAlert(packet)) return;
  enqueueFallAlert(packet);
}

void appendBleImuBatchNotify(const ImuSample *five) {
  if (!bleClientConnected || !bleClientReady || imuCharacteristic == nullptr) return;
  String p = "";
  p.reserve(250);
  p += "IMU5";
  for (int i = 0; i < 5; ++i) {
    const ImuSample &x = five[i];
    p += "|";
    p += String(x.tsMs);
    p += ",";
    p += String(x.ax, 4);
    p += ",";
    p += String(x.ay, 4);
    p += ",";
    p += String(x.az, 4);
    p += ",";
    p += String(x.gx, 2);
    p += ",";
    p += String(x.gy, 2);
    p += ",";
    p += String(x.gz, 2);
  }
  notifyIfConnected(imuCharacteristic, p, 5); // Reduced delay, using reserve instead
}

void feedBleImuStream(const ImuSample &s) {
  static ImuSample buf[5];
  static int n = 0;
  buf[n++] = s;
  if (n < 5) return;
  n = 0;
  appendBleImuBatchNotify(buf);
}

int countTensorElements(const TfLiteTensor *tensor) {
  int count = 1;
  for (int i = 0; i < tensor->dims->size; ++i) {
    count *= tensor->dims->data[i];
  }
  return count;
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
  if (inputTensor->dims->size != 3 || inputTensor->dims->data[0] != 1 ||
      inputTensor->dims->data[1] != kWindowSize ||
      inputTensor->dims->data[2] != kFeatureCount) {
    Serial.println("Unexpected input tensor shape");
    return false;
  }
  if (outputElementCount != 1 && outputElementCount != 2) {
    Serial.println("Unexpected output tensor shape");
    return false;
  }
  Serial.println("TFLite Micro ready");
  return true;
}

bool runInference(float &fallProb, float &nonFallProb, uint32_t &tsStart,
                  uint32_t &tsEnd, bool &modelInvoked) {
  modelInvoked = false;
  if (!modelOk || windowCount < kWindowSize) return false;

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

  modelInvoked = true;
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
    if (nonFallProb < 0.0f) nonFallProb = 0.0f;
    if (nonFallProb > 1.0f) nonFallProb = 1.0f;
    if (fallProb < 0.0f) fallProb = 0.0f;
    if (fallProb > 1.0f) fallProb = 1.0f;
  }
  return true;
}

void initBle() {
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);
  bleServer = NimBLEDevice::createServer();
  bleServer->setCallbacks(new BleServerCallbacks());

  NimBLEService *service = bleServer->createService(BLE_SERVICE_UUID);

  statusCharacteristic = service->createCharacteristic(
      BLE_STATUS_CHAR_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  vitalsCharacteristic = service->createCharacteristic(
      BLE_VITALS_CHAR_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  imuCharacteristic = service->createCharacteristic(
      BLE_IMU_CHAR_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  controlCharacteristic = service->createCharacteristic(
      BLE_CONTROL_CHAR_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
  controlCharacteristic->setCallbacks(new ControlCharacteristicCallbacks());

  statusCharacteristic->setValue("ALERT,0,0,idle,0,0.000,1.000");
  vitalsCharacteristic->setValue(
      "BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
  imuCharacteristic->setValue("IMU5|0,0,0,1,0,0,0");
  controlCharacteristic->setValue("WAITING_READY");

  service->start();

  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();

  Serial.println("BLE advertising started");
  Serial.printf("Device name: %s\n", BLE_DEVICE_NAME);
}

void sampleImuIfDue() {
  uint32_t now = millis();
  
  // Periodic hardware recovery check every 5 seconds
  static uint32_t lastHardwareCheckMs = 0;
  if (!bmiOk || !max30102Ok) {
    if (now - lastHardwareCheckMs > 5000) {
      lastHardwareCheckMs = now;
      Serial.println("[HW] Attempting to reconnect sensors...");
      recoverI2C();
      if (!bmiOk) {
        bmiOk = initBMI160();
        Serial.println(bmiOk ? "[HW] BMI160 Reconnected!" : "[HW] BMI160 still missing");
      }
      if (!max30102Ok) {
        max30102Ok = max30102_init();
        Serial.println(max30102Ok ? "[HW] MAX30102 Reconnected!" : "[HW] MAX30102 still missing");
      }
    }
  }

  if ((uint32_t)(now - lastSampleMs) < SAMPLE_PERIOD_MS) return;
  lastSampleMs = now;

  ImuSample sample;
  if (!readImuSample(sample)) {
    latestImuValid = false;
    // If it fails during runtime, mark it as disconnected to trigger recovery later
    bmiOk = false; 
    return;
  }

  latestImu = sample;
  latestImuValid = true;
  pushImuSample(sample);
  maybeSampleVitals();
  maybeDispatchVitalsBatch();
  feedBleImuStream(sample);

  if (windowCount >= kWindowSize && samplesSinceInference >= kInferenceStride) {
    float fallProb = 0.0f;
    float nonFallProb = 1.0f;
    uint32_t tsStart = 0;
    uint32_t tsEnd = 0;
    bool modelInvoked = false;

    bool ok = runInference(fallProb, nonFallProb, tsStart, tsEnd, modelInvoked);
    samplesSinceInference = 0;

    if (ok) {
      latestFallProb = fallProb;
      latestNonFallProb = nonFallProb;
      latestFallDetected = (fallProb >= FALL_DECISION_THRESHOLD);
      latestInferenceValid = true;
      latestModelInvoked = modelInvoked;
      latestWindowTsStartMs = tsStart;
      latestWindowTsEndMs = tsEnd;
      ++inferenceCount;

      if (latestFallDetected) {
        FallAlertPacket packet;
        packet.sequence = nextFallSequence++;
        packet.timestampSec = currentUnixTimeSecUtc();
        packet.statusCode = 1;
        packet.fallProb = fallProb;
        packet.nonFallProb = nonFallProb;
        queueOrSendFallAlert(packet);
      }

      Serial.printf("inference ts=[%lu..%lu] fall=%.3f invoked=%d alert=%d\n",
                    (unsigned long)tsStart, (unsigned long)tsEnd, fallProb,
                    modelInvoked ? 1 : 0, latestFallDetected ? 1 : 0);
    } else {
      Serial.println("inference_error");
    }
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
    vitals.timestamp = 0;
  }

  const char *aiStatus = "warming-up";
  if (latestInferenceValid) {
    aiStatus = latestFallDetected ? "fall" : "non-fall";
  }

  float winMeanG =
      (windowCount >= kWindowSize) ? windowMeanAccelMagG() : 0.0f;

  Serial.printf(
      "BLE=%s ready=%s | ts=%lu | ACC %.2f,%.2f,%.2f | GYR %.2f,%.2f,%.2f | "
      "HR=%u SpO2=%u | AI=%s fall=%.3f | inf=%lu\n",
      bleClientConnected ? "conn" : "adv",
      bleClientReady ? "yes" : "no",
      (unsigned long)now,
      latestImu.ax, latestImu.ay, latestImu.az,
      latestImu.gx, latestImu.gy, latestImu.gz,
      vitals.heartRate, vitals.spo2,
      aiStatus, latestFallProb, (unsigned long)inferenceCount);
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n=== S3_Combine: BMI160 + MAX30102 + TFLite + BLE ===");
  Serial.printf("I2C SDA=%d SCL=%d\n", I2C_SDA_PIN, I2C_SCL_PIN);

  recoverI2C();
  Wire.setTimeOut(100);
  delay(100);

  scanI2C();

  bmiOk = initBMI160();
  Serial.println(bmiOk ? "BMI160 OK" : "BMI160 FAIL");

  max30102Ok = max30102_init();
  Serial.println(max30102Ok ? "MAX30102 OK" : "MAX30102 FAIL");

  modelOk = initModel();
  if (!modelOk) {
    Serial.println("Model FAIL");
  }

  initBle();
  resetVitalsState();

  lastSampleMs = millis();
  lastSerialPrintMs = millis();
  Serial.println("Subscribe status+vitals+imu, write READY to control to stream IMU.");
}

void loop() {
  updateMax30102();
  sampleImuIfDue();
  printStatusIfDue();

  if (bleFlushRequested && bleClientConnected) {
    flushBleBacklog();
  }
  delay(1);
}
