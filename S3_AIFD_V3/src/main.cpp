/**
 * S3_AIFD_V3 — src/main.cpp
 *
 * V3 adds WiFi + Firebase RTDB streaming on top of V1's full pipeline.
 *
 * Fall trigger paths:
 *   1. Firebase /status → "fall"  → FDS_STILL_TIMING directly (cloud AI confirmed)
 *   2. Local TFLite (V1 pipeline) → FDS_FALL_WATCH → FDS_STILL_TIMING
 *
 * Button SAFE: writes "non-fall" to Firebase + BLE SAFE packet (like V1)
 *
 * BLE Packet formats (same as V1 / BLE_PROTOCOL.md):
 *   ALERT,<seq>,<ts_sec>,fall,1,<fall_prob>,<non_fall_prob>
 *   SAFE,<seq>,<ts_sec>
 *   BATCH,<seq>,<hr0|...|hr4>,<spo2_0|...|spo2_4>,<ts0|...|ts4>
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <WiFi.h>
#include <Firebase_ESP_Client.h>

#include "fall_detection_v84.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <NimBLEDevice.h>
#include <Adafruit_NeoPixel.h>
#include <string>
#include "MAX30105.h"

// =====================================================================
// PIN CONFIG
// =====================================================================
static const int PIN_LED_VCC = 4;
static const int PIN_LED_DI  = 5;
static const int PIN_BUZZER  = 7;
static const int PIN_BUTTON     = 10;
static const int PIN_I2C_SDA   = 8;
static const int PIN_I2C_SCL   = 9;

static const unsigned int  BUZZER_FREQ_HZ = 2300;
static const unsigned long DEBOUNCE_MS    = 30;
static const unsigned long BLINK_SLOW_MS  = 500;
static const unsigned long BLINK_FAST_MS  = 250;

// =====================================================================
// WiFi + Firebase CONFIG
// (No API Key needed — database rules are public: .read/.write = true)
// =====================================================================
#define WIFI_SSID            "bcabfeaChabdbada"
#define WIFI_PASS            ";;;;;;;;"
#define FIREBASE_HOST        "hospicare-91930-default-rtdb.asia-southeast1.firebasedatabase.app"
#define FIREBASE_STATUS_PATH "/status"

static FirebaseData  fbdoStream;
static FirebaseData  fbdoWrite;
static FirebaseAuth  fbAuth;
static FirebaseConfig fbConfig;

static volatile bool gWifiOk          = false;
static volatile bool gFirebaseOk      = false;
static volatile bool gFirebaseFallFlag = false;  // set by Firebase callback, read by inference task

// =====================================================================
// BMI160 REGISTERS
// =====================================================================
static const uint8_t BMI160_ADDR_LOW  = 0x68;
static const uint8_t BMI160_ADDR_HIGH = 0x69;
static const uint8_t BMI160_CHIP_ID   = 0xD1;
static const uint8_t REG_CHIP_ID   = 0x00;
static const uint8_t REG_GYR_DATA  = 0x0C;
static const uint8_t REG_ACC_DATA  = 0x12;
static const uint8_t REG_ACC_CONF  = 0x40;
static const uint8_t REG_ACC_RANGE = 0x41;
static const uint8_t REG_GYR_CONF  = 0x42;
static const uint8_t REG_GYR_RANGE = 0x43;
static const uint8_t REG_CMD       = 0x7E;
static const float ACC_LSB_PER_G   = 16384.0f;
static const float GYR_LSB_PER_DPS = 16.4f;

// =====================================================================
// SAMPLING + MODEL CONFIG
// =====================================================================
static const uint32_t SAMPLE_PERIOD_MS  = 20;
static const int      kWindowSize       = 100;
static const int      kFeatureCount     = 6;
static const int      kInferenceStride  = 100;
static const int      kTensorArenaSize  = 60 * 1024;

static const float FALL_DECISION_THRESHOLD  = 0.42f;
static const float CANDIDATE_ACC_THRESHOLD  = 7.5f;
static const float CANDIDATE_GYRO_THRESHOLD = 240.0f;
static const float ACTIVITY_ACC_THRESHOLD   = 2.0f;
static const float ACTIVITY_GYRO_THRESHOLD  = 50.0f;
static const float CANCEL_ACC_THRESHOLD     = 3.5f;
static const float CANCEL_GYRO_THRESHOLD    = 150.0f;
static const int   ACTIVITY_WINDOW_COUNT    = 1;
static const float FALL_IMPACT_GYRO_MIN     = 20.0f;
static const float HIGH_IMPACT_ACC_MIN      = 2.0f;
static const float HIGH_IMPACT_GYRO_MIN     = 300.0f;
static const int   STILLNESS_SAMPLES        = 25;
static const float STILLNESS_ACC_MIN        = 0.6f;
static const float STILLNESS_ACC_MAX        = 1.7f;
static const float STILLNESS_GYRO_MAX       = 100.0f;
static const int      FALL_WATCH_WINDOWS      = 5;
static const uint32_t FALL_STILL_DURATION_MS  = 5000;
static const uint32_t FALL_MONITOR_TIMEOUT_MS = 10000;
static const uint32_t AI_WINDOW_DURATION_MS   = 6000;

// =====================================================================
// BLE UUIDs
// =====================================================================
#define AIFD_SVC_UUID      "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_ALERT_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHAR_VITALS_UUID   "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
#define CHAR_CONTROL_UUID  "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

// =====================================================================
// BLE GLOBAL STATE
// =====================================================================
static NimBLEServer*         gBleServer    = nullptr;
static NimBLEService*        gBleService   = nullptr;
static NimBLECharacteristic* gCharAlert    = nullptr;
static NimBLECharacteristic* gCharVitals   = nullptr;
static bool                  gBleConnected = false;
static bool                  gBleReady     = false;
static uint32_t              gConnectCount        = 0;
static volatile bool         gBleJustConnected    = false;
static volatile bool         gBleJustDisconnected = false;

class BleServerCb : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer *s) override {
        (void)s;
        gBleConnected = true; gBleReady = false; gConnectCount++;
        gBleJustConnected = true;
        Serial.println("[BLE] Client connected — waiting for READY");
    }
    void onDisconnect(NimBLEServer *s) override {
        gBleConnected = false; gBleReady = false;
        gBleJustDisconnected = true;
        s->startAdvertising();
        Serial.println("[BLE] Client disconnected — re-advertising");
    }
};

static inline void setStr(NimBLECharacteristic *c, const char *s) {
    c->setValue((uint8_t*)s, strlen(s));
}
static void sendInstantVitals();

class ControlCb : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *c) override {
        std::string raw = c->getValue();
        String cmd = String(raw.c_str()); cmd.trim(); cmd.toUpperCase();
        if (cmd == "READY") {
            gBleReady = true; setStr(c, "ACK:READY");
            Serial.println("[BLE] READY received — handshake complete");
            sendInstantVitals();
        } else if (cmd == "PING") {
            setStr(c, "ACK:PING");
        } else {
            setStr(c, "ERR:UNKNOWN_COMMAND");
        }
    }
};

// =====================================================================
// LED STATE MACHINE
// =====================================================================
enum LedState : uint8_t {
    LED_BOOT = 0,
    LED_ADVERTISING,
    LED_CONNECTED,
    LED_WARNING,
    LED_FALL_WATCH,
    LED_ALARM
};
static const char *LED_STATE_NAMES[] = {
    "BOOT(Blue)", "ADVERTISING(Yellow)", "CONNECTED(Green)",
    "WARNING(Yellow)", "FALL_WATCH(Red)", "ALARM(Red)"
};

static volatile LedState gLedState     = LED_BOOT;
static bool              blinkLevel    = true;
static unsigned long     blinkLastMs   = 0;
static uint32_t          gWarnExpireMs = 0;

static int           btnLastReading = HIGH;
static int           btnStable      = HIGH;
static unsigned long btnLastChange  = 0;

static volatile bool gFallAlertActive = false;

enum FallDetectState : uint8_t { FDS_IDLE, FDS_FALL_WATCH, FDS_STILL_TIMING };
static FallDetectState fallDetectState = FDS_IDLE;

// =====================================================================
// IMU RING BUFFER
// =====================================================================
struct ImuSample {
    float ax=0,ay=0,az=0,gx=0,gy=0,gz=0;
    uint32_t tsMs=0;
};
static ImuSample gImuWindow[kWindowSize];
static int       gWindowHead            = 0;
static int       gWindowCount           = 0;
static int       gSamplesSinceInference = 0;
static SemaphoreHandle_t gImuMutex      = nullptr;
static TaskHandle_t      gInferenceTask = nullptr;
static ImuSample         gSnapshot[kWindowSize];

// =====================================================================
// TFLITE MICRO STATE
// =====================================================================
static uint8_t bmi160Addr = BMI160_ADDR_LOW;
static bool    bmiOk      = false;

namespace {
const tflite::Model*      model            = nullptr;
tflite::ErrorReporter*    errorReporter    = nullptr;
tflite::MicroInterpreter* interpreter      = nullptr;
TfLiteTensor*             inputTensor      = nullptr;
TfLiteTensor*             outputTensor     = nullptr;
uint8_t                   tensorArena[kTensorArenaSize];
int                       outputElementCount = 0;
bool                      modelOk          = false;
}

static uint32_t gAlertSeq  = 0;
static uint32_t gVitalsSeq = 0;
static uint32_t gBmiSeq    = 0;

static volatile float gLastPeakAcc  = 0.0f;
static volatile float gLastPeakGyro = 0.0f;
static volatile bool  gLastActive   = false;
static volatile bool  gWearerActive = false;

// =====================================================================
// RGB LED (WS2812) + BUZZER
// =====================================================================
static Adafruit_NeoPixel gLedNeo(1, PIN_LED_DI, NEO_GRB + NEO_KHZ800);
static const uint32_t CLR_BLUE   = 0x0000FFu;
static const uint32_t CLR_YELLOW = 0xFFA500u;
static const uint32_t CLR_GREEN  = 0x00FF00u;
static const uint32_t CLR_RED    = 0xFF0000u;
static const uint32_t CLR_OFF    = 0x000000u;

static void ledSet(uint32_t color) { gLedNeo.setPixelColor(0, color); gLedNeo.show(); }
static void buzzerOn()  { tone(PIN_BUZZER, BUZZER_FREQ_HZ); }
static void buzzerOff() { noTone(PIN_BUZZER); digitalWrite(PIN_BUZZER, LOW); }

static void applyLedState(LedState st) {
    blinkLevel = true; blinkLastMs = millis();
    switch (st) {
        case LED_BOOT:        ledSet(CLR_BLUE);                                    buzzerOff(); break;
        case LED_ADVERTISING: ledSet(gWearerActive ? CLR_YELLOW : CLR_OFF);        buzzerOff(); break;
        case LED_CONNECTED:   ledSet(gWearerActive ? CLR_GREEN  : CLR_OFF);        buzzerOff(); break;
        case LED_WARNING:     ledSet(CLR_YELLOW);                                  buzzerOff(); break;
        case LED_FALL_WATCH:  ledSet(CLR_RED);                                     buzzerOff(); break;
        case LED_ALARM:       ledSet(CLR_RED);                                     buzzerOn();  break;
    }
}
static void setLedState(LedState next) {
    if (next == gLedState) return;
    LedState prev = gLedState; gLedState = next;
    if (prev == LED_ALARM && next != LED_ALARM) buzzerOff();
    Serial.printf("[LED] %s -> %s\n", LED_STATE_NAMES[prev], LED_STATE_NAMES[next]);
    applyLedState(next);
}
static void handleBlink() {
    LedState st = gLedState;
    if (st == LED_CONNECTED) {
        static bool lastAR = !gWearerActive;
        if (gWearerActive != lastAR) { lastAR = gWearerActive; ledSet(gWearerActive ? CLR_GREEN : CLR_OFF); }
        return;
    }
    unsigned long interval;
    switch (st) {
        case LED_BOOT: case LED_ADVERTISING: case LED_FALL_WATCH: interval = BLINK_SLOW_MS; break;
        case LED_WARNING: case LED_ALARM:                          interval = BLINK_FAST_MS; break;
        default: return;
    }
    unsigned long now = millis();
    if ((unsigned long)(now - blinkLastMs) < interval) return;
    blinkLastMs = now; blinkLevel = !blinkLevel;
    switch (st) {
        case LED_BOOT:        ledSet(blinkLevel ? CLR_BLUE   : CLR_OFF); break;
        case LED_ADVERTISING: ledSet((blinkLevel && gWearerActive) ? CLR_YELLOW : CLR_OFF); break;
        case LED_WARNING:     ledSet(blinkLevel ? CLR_YELLOW : CLR_OFF); break;
        case LED_FALL_WATCH:
        case LED_ALARM:       ledSet(blinkLevel ? CLR_RED    : CLR_OFF); break;
        default: break;
    }
}

// =====================================================================
// BLE NOTIFY HELPERS
// =====================================================================
static void notifyAlert(const char *payload) {
    if (!gBleReady || !gCharAlert) return;
    gCharAlert->setValue((uint8_t*)payload, strlen(payload));
    gCharAlert->notify();
    Serial.printf("[BLE] ALERT notify: %s\n", payload);
}
static void notifyVitals(const char *payload) {
    if (!gBleReady || !gCharVitals) return;
    gCharVitals->setValue((uint8_t*)payload, strlen(payload));
    gCharVitals->notify();
}

// =====================================================================
// VITALS SOURCE — HR/SpO2 (simulated via MAX30102 IR presence)
// =====================================================================
static MAX30105 particleSensor;
static bool maxOk = false;

static uint8_t readHrSample() {
    if (!maxOk) return 255;
    if (particleSensor.getIR() < 50000) return 255;
    return (uint8_t)(65 + (esp_random() % 26));
}
static uint8_t readSpo2Sample() {
    if (!maxOk) return 255;
    if (particleSensor.getIR() < 50000) return 255;
    return (uint8_t)(93 + (esp_random() % 7));
}
static void sendInstantVitals() {
    uint32_t nowSec = millis() / 1000;
    uint8_t hr = readHrSample(), spo2 = readSpo2Sample();
    char buf[80];
    snprintf(buf, sizeof(buf), "BATCH,%lu,%u,%u,%lu",
             (unsigned long)++gVitalsSeq, hr, spo2, (unsigned long)nowSec);
    notifyVitals(buf);
}
static void sendVitalsBatch() {
    uint32_t nowSec = millis() / 1000;
    uint8_t hrs[5], spo2s[5]; uint32_t tss[5];
    for (int i=0;i<5;i++) { hrs[i]=readHrSample(); spo2s[i]=readSpo2Sample(); tss[i]=nowSec-(uint32_t)(4-i)*5; }
    char buf[140];
    snprintf(buf, sizeof(buf),
             "BATCH,%lu,%u|%u|%u|%u|%u,%u|%u|%u|%u|%u,%lu|%lu|%lu|%lu|%lu",
             (unsigned long)++gVitalsSeq,
             hrs[0],hrs[1],hrs[2],hrs[3],hrs[4],
             spo2s[0],spo2s[1],spo2s[2],spo2s[3],spo2s[4],
             (unsigned long)tss[0],(unsigned long)tss[1],
             (unsigned long)tss[2],(unsigned long)tss[3],(unsigned long)tss[4]);
    notifyVitals(buf);
    Serial.print("[VITALS] HR   : ");
    for(int i=0;i<5;i++){if(hrs[i]==255)Serial.print("--  ");else Serial.printf("%-3d ",hrs[i]);}
    Serial.println();
}
static void sendBmiSnapshot() {
    char buf[80];
    snprintf(buf, sizeof(buf), "BMI,%lu,%lu,%.3f,%.1f,%d",
             (unsigned long)++gBmiSeq, (unsigned long)(millis()/1000),
             (float)gLastPeakAcc, (float)gLastPeakGyro, (int)gLastActive);
    notifyVitals(buf);
    Serial.printf("[VITALS] BMI  : Acc=%.2fg, Gyro=%.1fdps\n", (float)gLastPeakAcc, (float)gLastPeakGyro);
}

// =====================================================================
// BMI160 I2C
// =====================================================================
static int16_t toInt16(uint8_t lsb, uint8_t msb) { return (int16_t)((msb<<8)|lsb); }
static bool writeReg(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(bmi160Addr); Wire.write(reg); Wire.write(value);
    return Wire.endTransmission() == 0;
}
static bool readRegs(uint8_t reg, uint8_t *buf, size_t len) {
    Wire.beginTransmission(bmi160Addr); Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    size_t got = Wire.requestFrom((int)bmi160Addr,(int)len,(int)true);
    if (got != len) return false;
    for (size_t i=0;i<len;i++) buf[i]=Wire.read();
    return true;
}
static bool readReg(uint8_t reg, uint8_t &value) { return readRegs(reg,&value,1); }
static bool detectBMI160() {
    uint8_t id=0; bmi160Addr=BMI160_ADDR_LOW;
    if (readReg(REG_CHIP_ID,id) && id==BMI160_CHIP_ID) return true;
    bmi160Addr=BMI160_ADDR_HIGH;
    return readReg(REG_CHIP_ID,id) && id==BMI160_CHIP_ID;
}
static bool initBMI160() {
    if (!detectBMI160()) return false;
    if (!writeReg(REG_CMD,0x11)) return false; delay(10);
    if (!writeReg(REG_CMD,0x15)) return false; delay(80);
    writeReg(REG_ACC_CONF,0x28); writeReg(REG_ACC_RANGE,0x03);
    writeReg(REG_GYR_CONF,0x28); writeReg(REG_GYR_RANGE,0x00);
    delay(10); return true;
}
static bool readImuSample(ImuSample &s) {
    uint8_t d[6];
    if (!readRegs(REG_ACC_DATA,d,6)) return false;
    s.ax=toInt16(d[0],d[1])/ACC_LSB_PER_G; s.ay=toInt16(d[2],d[3])/ACC_LSB_PER_G; s.az=toInt16(d[4],d[5])/ACC_LSB_PER_G;
    if (!readRegs(REG_GYR_DATA,d,6)) return false;
    s.gx=toInt16(d[0],d[1])/GYR_LSB_PER_DPS; s.gy=toInt16(d[2],d[3])/GYR_LSB_PER_DPS; s.gz=toInt16(d[4],d[5])/GYR_LSB_PER_DPS;
    s.tsMs=millis(); return true;
}

// =====================================================================
// RING BUFFER HELPERS
// =====================================================================
static void pushSample(const ImuSample &s) {
    gImuWindow[gWindowHead]=s; gWindowHead=(gWindowHead+1)%kWindowSize;
    if (gWindowCount<kWindowSize) gWindowCount++; gSamplesSinceInference++;
}
static void snapshotWindow(ImuSample *dst) {
    int start=(gWindowCount<kWindowSize)?0:gWindowHead;
    for (int i=0;i<kWindowSize;i++) dst[i]=gImuWindow[(start+i)%kWindowSize];
}

// =====================================================================
// TFLITE MICRO
// =====================================================================
static int8_t quantizeInput(float v) {
    float scale=inputTensor->params.scale; int zp=inputTensor->params.zero_point;
    int q=(int)lroundf(v/scale)+zp;
    if(q>127)q=127; if(q<-128)q=-128; return (int8_t)q;
}
static float dequantizeOutput(int8_t v) {
    return (v-outputTensor->params.zero_point)*outputTensor->params.scale;
}
static bool initModel() {
    model=tflite::GetModel(fall_detection_model_tflite);
    if (model->version()!=TFLITE_SCHEMA_VERSION) { Serial.println("[MODEL] schema mismatch"); return false; }
    static tflite::MicroErrorReporter microErr; errorReporter=&microErr;
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter si(model,resolver,tensorArena,kTensorArenaSize,errorReporter);
    interpreter=&si;
    if (interpreter->AllocateTensors()!=kTfLiteOk) { Serial.println("[MODEL] AllocateTensors failed"); return false; }
    inputTensor=interpreter->input(0); outputTensor=interpreter->output(0);
    outputElementCount=1;
    for(int i=0;i<outputTensor->dims->size;i++) outputElementCount*=outputTensor->dims->data[i];
    Serial.printf("[MODEL] ready (arena=%dKB out=%d)\n",kTensorArenaSize/1024,outputElementCount);
    return true;
}

// =====================================================================
// INFERENCE ON SNAPSHOT (V1 pipeline — unchanged)
// =====================================================================
static bool runInferenceOnSnapshot(const ImuSample *snap, float &fallProb,
                                   int &activityCount, bool &highImpactSeen,
                                   bool &activityActiveOut, bool &candidateActiveOut,
                                   bool &aiWindowActive, uint32_t &aiWindowStartMs)
{
    fallProb = 0.0f;
    if (!modelOk) return false;
    float maxAcc=0,maxGyr=0;
    for (int i=0;i<kWindowSize;i++) {
        float a=sqrtf(snap[i].ax*snap[i].ax+snap[i].ay*snap[i].ay+snap[i].az*snap[i].az);
        float g=sqrtf(snap[i].gx*snap[i].gx+snap[i].gy*snap[i].gy+snap[i].gz*snap[i].gz);
        if(a>maxAcc)maxAcc=a; if(g>maxGyr)maxGyr=g;
    }
    bool candidateActive=(maxAcc>CANDIDATE_ACC_THRESHOLD||maxGyr>CANDIDATE_GYRO_THRESHOLD);
    bool activityActive =(maxAcc>ACTIVITY_ACC_THRESHOLD ||maxGyr>ACTIVITY_GYRO_THRESHOLD);
    activityActiveOut=activityActive; candidateActiveOut=candidateActive;
    gLastPeakAcc=maxAcc; gLastPeakGyro=maxGyr; gLastActive=activityActive;

    static int idleCount=0;
    if (activityActive) {
        idleCount=0;
        if(activityCount<ACTIVITY_WINDOW_COUNT) activityCount++;
        if(maxAcc>HIGH_IMPACT_ACC_MIN&&maxGyr>HIGH_IMPACT_GYRO_MIN) highImpactSeen=true;
    } else {
        idleCount++;
        if(idleCount>=3){activityCount=0;highImpactSeen=false;}
    }
    gWearerActive=(activityCount>=ACTIVITY_WINDOW_COUNT);

    Serial.printf("[GATE] acc=%.2fg gyro=%.1fdps cand=%s activity=%d/%d highImpact=%s\n",
                  maxAcc,maxGyr,candidateActive?"yes":"no",
                  activityCount,ACTIVITY_WINDOW_COUNT,highImpactSeen?"YES":"no");

    if(!candidateActive||activityCount<ACTIVITY_WINDOW_COUNT) return true;
    if(!highImpactSeen) return true;
    if(maxGyr<FALL_IMPACT_GYRO_MIN) return true;

    if(!aiWindowActive){aiWindowActive=true;aiWindowStartMs=millis();Serial.println("[AI] Window opened");}
    uint32_t aiElapsed=millis()-aiWindowStartMs;
    if(aiElapsed>=AI_WINDOW_DURATION_MS){
        aiWindowActive=false;highImpactSeen=false;
        Serial.printf("[AI] Window expired (%lums)\n",(unsigned long)aiElapsed);
        return true;
    }

    for(int t=0;t<kWindowSize;t++){
        inputTensor->data.int8[t*kFeatureCount+0]=quantizeInput(snap[t].ax);
        inputTensor->data.int8[t*kFeatureCount+1]=quantizeInput(snap[t].ay);
        inputTensor->data.int8[t*kFeatureCount+2]=quantizeInput(snap[t].az);
        inputTensor->data.int8[t*kFeatureCount+3]=quantizeInput(snap[t].gx);
        inputTensor->data.int8[t*kFeatureCount+4]=quantizeInput(snap[t].gy);
        inputTensor->data.int8[t*kFeatureCount+5]=quantizeInput(snap[t].gz);
    }
    if(interpreter->Invoke()!=kTfLiteOk){Serial.println("[MODEL] invoke failed");return false;}
    fallProb=(outputElementCount==1)
        ?constrain(dequantizeOutput(outputTensor->data.int8[0]),0.0f,1.0f)
        :dequantizeOutput(outputTensor->data.int8[1]);
    return true;
}

static bool checkStillness(const ImuSample *snap) {
    float accSum=0,gyrSum=0;
    int start=kWindowSize-STILLNESS_SAMPLES;
    for(int i=start;i<kWindowSize;i++){
        accSum+=sqrtf(snap[i].ax*snap[i].ax+snap[i].ay*snap[i].ay+snap[i].az*snap[i].az);
        gyrSum+=sqrtf(snap[i].gx*snap[i].gx+snap[i].gy*snap[i].gy+snap[i].gz*snap[i].gz);
    }
    float mA=accSum/STILLNESS_SAMPLES, mG=gyrSum/STILLNESS_SAMPLES;
    Serial.printf("[STILL] mean_acc=%.2fg mean_gyro=%.1fdps -> %s\n",mA,mG,
                  (mA>=STILLNESS_ACC_MIN&&mA<=STILLNESS_ACC_MAX&&mG<=STILLNESS_GYRO_MAX)?"STILL":"moving");
    return (mA>=STILLNESS_ACC_MIN&&mA<=STILLNESS_ACC_MAX&&mG<=STILLNESS_GYRO_MAX);
}

// =====================================================================
// FALL DETECT STATE MACHINE
// =====================================================================
static int      fallWatchLeft       = 0;
static uint32_t monitorStartMs      = 0;
static uint32_t stillnessStartMs    = 0;
static bool     stillnessTimerArmed = false;
static float    gLastFallProb       = 0.0f;

static void onFallConfirmed(float fallProb) {
    gFallAlertActive=true;
    setLedState(LED_ALARM);
    char buf[80]; uint32_t tsSec=millis()/1000;
    snprintf(buf,sizeof(buf),"ALERT,%lu,%lu,fall,1,%.3f,%.3f",
             (unsigned long)++gAlertSeq,(unsigned long)tsSec,fallProb,1.0f-fallProb);
    notifyAlert(buf);
}

// Enter STILL_TIMING directly (used by Firebase trigger)
static void enterStillTimingFromFirebase() {
    if (gFallAlertActive || fallDetectState != FDS_IDLE) return;
    gLastFallProb       = 1.0f;  // Firebase cloud AI confirmed
    fallDetectState     = FDS_STILL_TIMING;
    monitorStartMs      = millis();
    stillnessTimerArmed = false;
    setLedState(LED_FALL_WATCH);
    Serial.println("[FSM] IDLE -> STILL_TIMING (Firebase cloud trigger)");
}

static void updateFallStateMachine(float fallProb, bool stillnessNow, bool activityActive,
                                   float peakAcc, float peakGyr)
{
    bool isFall       = (fallProb >= FALL_DECISION_THRESHOLD);
    bool cancelActive = (peakAcc > CANCEL_ACC_THRESHOLD || peakGyr > CANCEL_GYRO_THRESHOLD);

    switch (fallDetectState) {
        case FDS_IDLE:
            if (isFall && stillnessNow) {
                gLastFallProb   = fallProb;
                fallDetectState = FDS_FALL_WATCH;
                fallWatchLeft   = FALL_WATCH_WINDOWS - 1;
                setLedState(LED_FALL_WATCH);
                Serial.printf("[FSM] IDLE -> FALL_WATCH (left=%d)\n",fallWatchLeft);
            }
            break;

        case FDS_FALL_WATCH:
            if (cancelActive) {
                fallDetectState=FDS_IDLE;
                setLedState(gBleConnected?LED_CONNECTED:LED_ADVERTISING);
                Serial.printf("[FSM] FALL_WATCH: strong activity (%.2fg/%.1fdps) -> IDLE\n",peakAcc,peakGyr);
                break;
            }
            if (fallWatchLeft>0) {
                fallWatchLeft--;
                Serial.printf("[FSM] FALL_WATCH left=%d\n",fallWatchLeft);
            } else {
                fallDetectState=FDS_STILL_TIMING; monitorStartMs=millis(); stillnessTimerArmed=false;
                Serial.println("[FSM] FALL_WATCH -> STILL_TIMING (monitor timeout=10s)");
            }
            break;

        case FDS_STILL_TIMING: {
            uint32_t monitorElapsed=millis()-monitorStartMs;
            bool isMoving=(cancelActive||!stillnessNow);

            if (monitorElapsed>=FALL_MONITOR_TIMEOUT_MS) {
                fallDetectState=FDS_IDLE; stillnessTimerArmed=false;
                setLedState(gBleConnected?LED_CONNECTED:LED_ADVERTISING);
                Serial.printf("[FSM] STILL_TIMING: timeout %lums -> IDLE (safe)\n",(unsigned long)monitorElapsed);
                break;
            }
            if (isMoving) {
                if(stillnessTimerArmed){stillnessTimerArmed=false;Serial.println("[FSM] STILL_TIMING: motion -> substance reset");}
            } else {
                if(!stillnessTimerArmed){stillnessTimerArmed=true;stillnessStartMs=millis();
                    Serial.printf("[FSM] STILL_TIMING: still -> arm substance (monitor=%lums left)\n",
                                  (unsigned long)(FALL_MONITOR_TIMEOUT_MS-monitorElapsed));}
                uint32_t stillElapsed=millis()-stillnessStartMs;
                Serial.printf("[FSM] STILL_TIMING: still=%lums/%lums monitor=%lums/%lums\n",
                              (unsigned long)stillElapsed,(unsigned long)FALL_STILL_DURATION_MS,
                              (unsigned long)monitorElapsed,(unsigned long)FALL_MONITOR_TIMEOUT_MS);
                if(stillElapsed>=FALL_STILL_DURATION_MS){
                    fallDetectState=FDS_IDLE; stillnessTimerArmed=false;
                    onFallConfirmed(gLastFallProb);
                }
            }
            break;
        }
    }
}

// =====================================================================
// TASK 1: IMU SAMPLING — Core 0, priority MAX-1
// =====================================================================
static void taskSampling(void *pvParams) {
    TickType_t xLastWake=xTaskGetTickCount();
    while (true) {
        vTaskDelayUntil(&xLastWake, pdMS_TO_TICKS(SAMPLE_PERIOD_MS));
        if (!bmiOk) continue;
        ImuSample s;
        if (!readImuSample(s)) { Serial.println("[IMU] read failed"); continue; }
        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        pushSample(s);
        bool windowReady=(gWindowCount>=kWindowSize)&&(gSamplesSinceInference>=kInferenceStride);
        if(windowReady) gSamplesSinceInference=0;
        xSemaphoreGive(gImuMutex);
        if(windowReady&&gInferenceTask!=nullptr) xTaskNotifyGive(gInferenceTask);
    }
}

// =====================================================================
// TASK 2: INFERENCE — Core 1, priority 1
// =====================================================================
static void taskInference(void *pvParams) {
    static uint32_t inferenceCount  = 0;
    static int      activityCount   = 0;
    static bool     highImpactSeen  = false;
    static bool     aiWindowActive  = false;
    static uint32_t aiWindowStartMs = 0;

    while (true) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        // --- Firebase cloud trigger (highest priority) ---
        // Check BEFORE snapshot — Firebase trigger skips AI pipeline entirely
        if (gFirebaseFallFlag && !gFallAlertActive) {
            gFirebaseFallFlag = false;
            enterStillTimingFromFirebase();
            aiWindowActive = false;
            // Still take snapshot so stillness can be checked in this and future windows
        }

        xSemaphoreTake(gImuMutex, portMAX_DELAY);
        snapshotWindow(gSnapshot);
        xSemaphoreGive(gImuMutex);

        // If alarm is already active, skip local AI
        if (gFallAlertActive) { aiWindowActive=false; continue; }

        // --- Local TFLite pipeline (V1 path) ---
        uint32_t t0=millis();
        float fallProb=0.0f; bool activityActive=false,candidateActive=false;
        bool ok=runInferenceOnSnapshot(gSnapshot,fallProb,activityCount,
                                       highImpactSeen,activityActive,candidateActive,
                                       aiWindowActive,aiWindowStartMs);
        uint32_t latencyMs=millis()-t0; inferenceCount++;

        if(!ok){Serial.println("[AI] inference error");continue;}

        bool isFall=(fallProb>=FALL_DECISION_THRESHOLD);
        Serial.printf("[INFER] #%lu fall_prob=%.3f latency=%lums -> %s\n",
                      inferenceCount,fallProb,latencyMs,isFall?"FALL?":"non-fall");

        bool stillnessNow=checkStillness(gSnapshot);
        updateFallStateMachine(fallProb,stillnessNow,activityActive,gLastPeakAcc,gLastPeakGyro);

        // If FSM has committed (FALL_WATCH/STILL_TIMING), close AI window
        if(fallDetectState!=FDS_IDLE) aiWindowActive=false;
    }
}

// =====================================================================
// TASK 3: FIREBASE STREAM — Core 0, priority 2
// Watches /status for "fall" and sets gFirebaseFallFlag
// =====================================================================
static void fbStreamCb(FirebaseStream data) {
    if (data.dataTypeEnum() == fb_esp_rtdb_data_type_string) {
        String val = data.stringData();
        Serial.printf("[FB] /status = \"%s\"\n", val.c_str());
        if (val == "fall") {
            gFirebaseFallFlag = true;
            Serial.println("[FB] *** FALL trigger from Firebase ***");
        }
    }
}
static void fbStreamTimeoutCb(bool timeout) {
    if (timeout) Serial.println("[FB] Stream timeout — resuming...");
}

static void taskFirebaseStream(void *pvParams) {
    // --- Step 1: Connect WiFi ---
    Serial.printf("[WIFI] Connecting to %s...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    uint32_t wifiStart = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if ((uint32_t)(millis()-wifiStart) > 15000) {
            Serial.println("[WIFI] Timeout — Firebase disabled");
            vTaskDelete(nullptr); return;
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
    gWifiOk = true;
    Serial.printf("[WIFI] Connected. IP: %s\n", WiFi.localIP().toString().c_str());

    // --- Step 2: Init Firebase (no auth — public rules) ---
    fbConfig.database_url = FIREBASE_HOST;
    // Leave api_key empty: Firebase ESP Client allows URL-only init
    // when database rules are set to: { ".read": true, ".write": true }
    fbConfig.api_key      = "";

    Firebase.begin(&fbConfig, &fbAuth);
    Firebase.reconnectWiFi(true);
    Serial.println("[FB] Firebase init OK (public rules, no auth)");

    // --- Step 3: Begin stream on /status ---
    if (!Firebase.RTDB.beginStream(&fbdoStream, FIREBASE_STATUS_PATH)) {
        Serial.printf("[FB] beginStream error: %s\n", fbdoStream.errorReason().c_str());
    }
    Firebase.RTDB.setStreamCallback(&fbdoStream, fbStreamCb, fbStreamTimeoutCb);

    gFirebaseOk = true;
    Serial.println("[FB] Stream active on /status");

    // --- Step 4: Keep-alive loop ---
    while (true) {
        // WiFi watchdog
        if (WiFi.status() != WL_CONNECTED) {
            gWifiOk = false;
            Serial.println("[WIFI] Lost connection — reconnecting...");
            WiFi.reconnect();
            uint32_t t=millis();
            while(WiFi.status()!=WL_CONNECTED&&(uint32_t)(millis()-t)<10000)
                vTaskDelay(pdMS_TO_TICKS(500));
            if(WiFi.status()==WL_CONNECTED){
                gWifiOk=true;
                Serial.println("[WIFI] Reconnected");
                // Re-open stream
                Firebase.RTDB.beginStream(&fbdoStream, FIREBASE_STATUS_PATH);
                Firebase.RTDB.setStreamCallback(&fbdoStream, fbStreamCb, fbStreamTimeoutCb);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

// =====================================================================
// BUTTON — debounce + dual action
// =====================================================================
static void handleButton() {
    int reading=digitalRead(PIN_BUTTON); unsigned long now=millis();
    if(reading!=btnLastReading){btnLastChange=now;btnLastReading=reading;}
    if((unsigned long)(now-btnLastChange)>=DEBOUNCE_MS&&reading!=btnStable){
        btnStable=reading;
        if(btnStable!=LOW) return;

        char buf[64]; uint32_t tsSec=millis()/1000;

        if (gFallAlertActive) {
            // SAFE: cancel alarm, write non-fall to Firebase, send BLE SAFE
            gFallAlertActive=false; fallDetectState=FDS_IDLE;
            setLedState(gBleConnected?LED_CONNECTED:LED_ADVERTISING);

            // Write "non-fall" back to Firebase
            if (gFirebaseOk) {
                if (Firebase.RTDB.setString(&fbdoWrite, FIREBASE_STATUS_PATH, "non-fall")) {
                    Serial.println("[FB] Wrote 'non-fall' to /status");
                } else {
                    Serial.printf("[FB] Write error: %s\n", fbdoWrite.errorReason().c_str());
                }
            }

            snprintf(buf,sizeof(buf),"SAFE,%lu,%lu",(unsigned long)++gAlertSeq,(unsigned long)tsSec);
            notifyAlert(buf);
            Serial.printf("[BTN] Safe confirmed — sent: %s\n",buf);
        } else {
            // Manual SOS / test fall trigger
            fallDetectState=FDS_IDLE;
            snprintf(buf,sizeof(buf),"ALERT,%lu,%lu,fall,1,1.000,0.000",
                     (unsigned long)++gAlertSeq,(unsigned long)tsSec);
            gFallAlertActive=true; setLedState(LED_ALARM);
            notifyAlert(buf);
            Serial.printf("[BTN] Manual fall triggered — sent: %s\n",buf);
        }
    }
}

// =====================================================================
// PERIODIC TIMERS
// =====================================================================
static void handleVitalsBatch() {
    static uint32_t lastMs=0; uint32_t now=millis();
    if((uint32_t)(now-lastMs)>=25000){lastMs=now;sendVitalsBatch();}
}
static void handleBmiSnapshot() {
    static uint32_t lastMs=0; uint32_t now=millis();
    if((uint32_t)(now-lastMs)>=5000){lastMs=now;sendBmiSnapshot();}
}
static void handleMaxDebug() {
    static uint32_t lastMs=0; uint32_t now=millis();
    if((uint32_t)(now-lastMs)>=5000){lastMs=now;
        if(maxOk) Serial.printf("[MAX] IR=%ld -> %s\n",particleSensor.getIR(),
                                particleSensor.getIR()>=50000?"Finger DETECTED":"No finger");
        else Serial.println("[MAX] Sensor not initialized");
    }
}

// =====================================================================
// ARDUINO ENTRY
// =====================================================================
void setup() {
    Serial.begin(115200); delay(300);
    Serial.println();
    Serial.println("=======================================================");
    Serial.println("ESP32-S3  AIFD  S3_AIFD_V3");
    Serial.println("  Fall: Firebase /status + local TFLite V84");
    Serial.println("  Vitals: simulated HR/SpO2 every 25s");
    Serial.println("  WiFi: " WIFI_SSID);
    Serial.println("=======================================================");

    // GPIO
    pinMode(PIN_LED_VCC, OUTPUT); digitalWrite(PIN_LED_VCC, HIGH);
    pinMode(PIN_BUTTON,  INPUT_PULLUP);
    pinMode(PIN_BUZZER,  OUTPUT); digitalWrite(PIN_BUZZER, LOW);
    tone(PIN_BUZZER, BUZZER_FREQ_HZ); noTone(PIN_BUZZER);

    gLedNeo.begin(); gLedNeo.setBrightness(50); gLedNeo.show();
    applyLedState(LED_BOOT);

    // I2C
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000); Wire.setTimeOut(20); delay(50);

    // BMI160
    bmiOk = initBMI160();
    Serial.printf("[BMI]   %s (addr=0x%02X)\n", bmiOk?"OK":"NOT FOUND", bmi160Addr);

    // MAX30102
    if (particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        particleSensor.setup(); maxOk=true; Serial.println("[MAX]   OK");
    } else { Serial.println("[MAX]   NOT FOUND"); maxOk=false; }

    // TFLite model
    modelOk=initModel();
    if(!modelOk) Serial.println("[MODEL] init failed — local fall detection disabled");

    // FreeRTOS mutex
    gImuMutex=xSemaphoreCreateMutex(); configASSERT(gImuMutex);

    // FreeRTOS tasks
    xTaskCreatePinnedToCore(taskSampling,      "IMU_SAMPLE",  4096, nullptr,
                            configMAX_PRIORITIES-1, nullptr, 0);
    xTaskCreatePinnedToCore(taskInference,     "AI_INFER",    8192, nullptr,
                            1, &gInferenceTask, 1);
    xTaskCreatePinnedToCore(taskFirebaseStream,"FB_STREAM",   8192, nullptr,
                            2, nullptr, 0);   // Core 0, pri=2 (below IMU_SAMPLE)

    // BLE
    NimBLEDevice::init("S3_AIFD_V3");
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);
    NimBLEDevice::deleteAllBonds();

    gBleServer=NimBLEDevice::createServer();
    gBleServer->setCallbacks(new BleServerCb());

    gBleService=gBleServer->createService(AIFD_SVC_UUID);
    gCharAlert  = gBleService->createCharacteristic(CHAR_ALERT_UUID,
                      NIMBLE_PROPERTY::READ|NIMBLE_PROPERTY::NOTIFY);
    gCharVitals = gBleService->createCharacteristic(CHAR_VITALS_UUID,
                      NIMBLE_PROPERTY::READ|NIMBLE_PROPERTY::NOTIFY);
    auto *cCtrl = gBleService->createCharacteristic(CHAR_CONTROL_UUID,
                      NIMBLE_PROPERTY::READ|NIMBLE_PROPERTY::WRITE);
    cCtrl->setCallbacks(new ControlCb());

    setStr(gCharAlert,  "ALERT,0,0,idle,0,0.000,1.000");
    setStr(gCharVitals, "BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
    setStr(cCtrl,       "WAITING_READY");

    gBleService->start();
    NimBLEAdvertising *adv=NimBLEDevice::getAdvertising();
    adv->addServiceUUID(AIFD_SVC_UUID); adv->setScanResponse(true); adv->start();

    if (!bmiOk||!modelOk) {
        gWarnExpireMs=0; setLedState(LED_WARNING);
    } else {
        setLedState(LED_ADVERTISING);
    }
    Serial.println("[BOOT] Tasks started. Advertising as \"S3_AIFD_V3\"");
    Serial.println("[BOOT] Firebase stream task running — connecting WiFi...");
}

void loop() {
    handleButton();
    handleBlink();
    handleVitalsBatch();
    handleBmiSnapshot();
    handleMaxDebug();

    // BLE connect/disconnect → LED
    if (gBleJustConnected) {
        gBleJustConnected=false;
        if(!gFallAlertActive&&fallDetectState==FDS_IDLE) setLedState(LED_CONNECTED);
    }
    if (gBleJustDisconnected) {
        gBleJustDisconnected=false;
        if(!gFallAlertActive&&fallDetectState==FDS_IDLE) {
            gWarnExpireMs=millis()+3000; setLedState(LED_WARNING);
        }
    }
    // WARNING auto-return to ADVERTISING (BLE drop only; sensor error = permanent)
    if(gLedState==LED_WARNING&&gWarnExpireMs!=0&&millis()>=gWarnExpireMs) {
        gWarnExpireMs=0; setLedState(LED_ADVERTISING);
    }

    // Status print every 5s
    static uint32_t lastStatusMs=0; uint32_t now=millis();
    if((uint32_t)(now-lastStatusMs)>=5000){
        lastStatusMs=now;
        Serial.printf("[STATUS] BLE=%-11s handshake=%-7s WiFi=%-4s Firebase=%-4s uptime=%lus\n",
                      gBleConnected?"CONNECTED":"advertising",
                      gBleReady?"READY":"waiting",
                      gWifiOk?"OK":"--",
                      gFirebaseOk?"OK":"--",
                      (unsigned long)(now/1000));
    }

    delay(10);
}
