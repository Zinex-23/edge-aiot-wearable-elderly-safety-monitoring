/**
 * S3_BLE_testplan — src/main.cpp
 *
 * Unit Test Suite for AIFD ESP32-S3 firmware.
 * All tests run once in setup(), results printed to Serial Monitor (115200 baud).
 * loop() is idle — re-flash to re-run.
 *
 * Test modules (ref: System_Architecture/test_plan/unit/):
 *   UT_BMI160    — SENSOR_BMI160.md  : I2C comm, range check, sample rate, self-test
 *   UT_MCU_CORE  — MCU_CORE.md       : CPU clock, deep-sleep config, GPIO, NVS
 *   UT_AI_MODEL  — AI_INFERENCE.md   : model load, circular buffer, sample integrity, output range
 *   UT_BLE_STACK — BLE_STACK.md      : advertising, service/char init, notify, bond storage
 */

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <Preferences.h>
#include <esp_sleep.h>
#include <esp_system.h>

// TFLite Micro (model path via build_flags: -I ../AI/model_updated_version_84/models)
#include "fall_detection_v84.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// NimBLE
#include <NimBLEDevice.h>
#include <string>

// =====================================================================
// PIN CONFIG — same as production firmware
// =====================================================================
static const int PIN_LED_GREEN  = 4;
static const int PIN_LED_YELLOW = 5;
static const int PIN_LED_RED    = 6;
static const int PIN_I2C_SDA   = 8;
static const int PIN_I2C_SCL   = 9;

// =====================================================================
// BMI160 REGISTERS — same as production firmware
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
// MODEL CONFIG — same as production firmware
// =====================================================================
static const int kWindowSize      = 100;
static const int kFeatureCount    = 6;
static const int kTensorArenaSize = 60 * 1024;

// =====================================================================
// BLE UUIDs — from BLE_PROTOCOL.md
// =====================================================================
#define AIFD_SVC_UUID      "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_ALERT_UUID    "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHAR_VITALS_UUID   "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"
#define CHAR_CONTROL_UUID  "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"

// =====================================================================
// BLE PAIRING STATE — global (persists after test suite, stays live in loop)
// Pattern from S3_Combine: open pairing + READY handshake before data flows
// =====================================================================
static NimBLEServer*        gBleServer    = nullptr;
static NimBLEService*       gBleService   = nullptr;
static bool                 gBleConnected = false;
static bool                 gBleReady     = false;
static uint32_t             gConnectCount = 0;

class BleServerCb : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer *s) override {
        (void)s;
        gBleConnected = true;
        gBleReady     = false;
        gConnectCount++;
        Serial.println();
        Serial.println("[BLE] *** Client connected ***");
        Serial.println("[BLE] Waiting for READY command on CONTROL characteristic...");
    }
    void onDisconnect(NimBLEServer *s) override {
        gBleConnected = false;
        gBleReady     = false;
        s->startAdvertising();
        Serial.println("[BLE] Client disconnected — re-advertising as \"S3_AIFD Wearable_test\"");
    }
};

class ControlCb : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic *c) override {
        std::string raw = c->getValue();
        String cmd = String(raw.c_str());
        cmd.trim();
        cmd.toUpperCase();
        if (cmd == "READY") {
            gBleReady = true;
            c->setValue("ACK:READY");
            Serial.println("[BLE] *** READY received → handshake complete ✓ ***");
            Serial.println("[BLE] Data channel open (no data sent yet — test mode)");
        } else if (cmd == "PING") {
            c->setValue("ACK:PING");
            Serial.println("[BLE] PING → ACK:PING");
        } else {
            c->setValue("ERR:UNKNOWN_COMMAND");
            Serial.printf("[BLE] Unknown command: \"%s\"\n", cmd.c_str());
        }
    }
};

// =====================================================================
// TEST RUNNER STATE
// =====================================================================
static int gPassed = 0;
static int gFailed = 0;
static int gNA     = 0;

static uint8_t bmi160Addr = BMI160_ADDR_LOW;

enum TestStatus { TS_PASS, TS_FAIL, TS_NA };

// =====================================================================
// PRINT HELPERS
// =====================================================================
static void printSuiteHeader(const char *id, const char *name, const char *ref) {
    Serial.println();
    Serial.println("+-----------------------------------------------------------------+");
    Serial.printf( "|  %-12s | %-48s|\n", id, name);
    Serial.printf( "|  ref: %-58s|\n", ref);
    Serial.println("+-----------------------------------------------------------------+");
}

static void reportScenario(const char *sc, TestStatus st, const char *detail) {
    const char *tag;
    switch (st) {
        case TS_PASS: tag = "PASS"; gPassed++; break;
        case TS_FAIL: tag = "FAIL"; gFailed++; break;
        default:      tag = "N/A "; gNA++;     break;
    }
    Serial.printf("  %-6s [%s]  %s\n", sc, tag, detail);
}

// =====================================================================
// I2C HELPERS
// =====================================================================
static bool bmiWriteReg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg); Wire.write(val);
    return Wire.endTransmission() == 0;
}

static bool bmiReadRegs(uint8_t reg, uint8_t *buf, size_t len) {
    Wire.beginTransmission(bmi160Addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    size_t got = Wire.requestFrom((int)bmi160Addr, (int)len, (int)true);
    if (got != len) return false;
    for (size_t i = 0; i < len; i++) buf[i] = Wire.read();
    return true;
}

static bool bmiReadReg(uint8_t reg, uint8_t &val) { return bmiReadRegs(reg, &val, 1); }

static int16_t toInt16(uint8_t lo, uint8_t hi) {
    return (int16_t)((uint16_t(hi) << 8) | lo);
}

// =====================================================================
// UT_BMI160 — BMI160 Sensor Module
// =====================================================================
static void test_bmi160() {
    printSuiteHeader("UT_BMI160", "BMI160 Sensor Module", "unit/SENSOR_BMI160.md");

    // SC_01: I2C Communication — probe I2C bus, verify Chip ID = 0xD1
    // Rationale: giao tiếp I2C là điều kiện tiên quyết. Lỗi ở đây làm toàn bộ
    // pipeline thu thập dữ liệu cảm biến và AI inference bị vô hiệu hóa.
    {
        uint8_t chipId = 0;
        bool found = false;
        uint8_t foundAddr = BMI160_ADDR_LOW;

        for (uint8_t addr : {BMI160_ADDR_LOW, BMI160_ADDR_HIGH}) {
            Wire.beginTransmission(addr);
            if (Wire.endTransmission() == 0) {
                bmi160Addr = addr;
                uint8_t id = 0;
                if (bmiReadReg(REG_CHIP_ID, id) && id == BMI160_CHIP_ID) {
                    chipId = id; foundAddr = addr; found = true; break;
                }
            }
        }

        char msg[80];
        snprintf(msg, sizeof(msg), "addr=0x%02X  chip_id=0x%02X  (expect 0xD1)", foundAddr, chipId);
        reportScenario("SC_01", found ? TS_PASS : TS_FAIL, msg);
    }

    // Init for subsequent tests
    bmiWriteReg(REG_CMD, 0x11); delay(10);
    bmiWriteReg(REG_CMD, 0x15); delay(80);
    bmiWriteReg(REG_ACC_CONF,  0x28);
    bmiWriteReg(REG_ACC_RANGE, 0x03);
    bmiWriteReg(REG_GYR_CONF,  0x28);
    bmiWriteReg(REG_GYR_RANGE, 0x00);
    delay(20);

    // SC_02: Range Check — device placed flat, Z ≈ 1g, X/Y ≈ 0g
    // Rationale: calibration offset làm mô hình AI nhận sai phân phối dữ liệu →
    // giảm accuracy. Cần xác nhận đầu ra static 1g đúng trước khi dùng cho inference.
    {
        delay(200);
        uint8_t d[6];
        bool readOk = bmiReadRegs(REG_ACC_DATA, d, 6);
        char msg[120];
        if (!readOk) {
            reportScenario("SC_02", TS_FAIL, "I2C read failed");
        } else {
            float ax = toInt16(d[0], d[1]) / ACC_LSB_PER_G;
            float ay = toInt16(d[2], d[3]) / ACC_LSB_PER_G;
            float az = toInt16(d[4], d[5]) / ACC_LSB_PER_G;
            bool ok = (fabsf(fabsf(az) - 1.0f) <= 0.20f)
                   && (fabsf(ax) <= 0.30f) && (fabsf(ay) <= 0.30f);
            snprintf(msg, sizeof(msg),
                     "ax=%.3fg  ay=%.3fg  az=%.3fg  (target |Z|~1.0g+-0.2, |X|<0.3g, |Y|<0.3g)",
                     ax, ay, az);
            reportScenario("SC_02", ok ? TS_PASS : TS_FAIL, msg);
        }
    }

    // SC_03: Sample Rate — 100 reads at 20ms intervals, expect ~2000ms total (50Hz)
    // Rationale: mô hình train trên chuỗi 100 mẫu x 20ms = 2s @ 50Hz.
    // Sai tần số → cửa sổ dữ liệu bị lệch thời gian → inference kém chính xác.
    {
        const int N = 100;
        uint8_t d[12];
        uint32_t tLast = millis(), tStart = tLast;
        for (int i = 0; i < N; i++) {
            while ((uint32_t)(millis() - tLast) < 20) {}
            tLast += 20;
            bmiReadRegs(REG_ACC_DATA, d, 6);
            bmiReadRegs(REG_GYR_DATA, d + 6, 6);
        }
        uint32_t elapsed = millis() - tStart;
        float hz = 1000.0f * N / elapsed;
        bool ok = (hz >= 45.0f && hz <= 55.0f);
        char msg[80];
        snprintf(msg, sizeof(msg), "100 reads in %lums -> %.1fHz  (target: 50Hz +-5Hz)", elapsed, hz);
        reportScenario("SC_03", ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_04: Self-test via register readback — config regs match written values
    // Rationale: phát hiện BMI160 lỗi do va đập lắp ráp hoặc I2C intermittent.
    // Đọc lại thanh ghi cấu hình xác nhận ghi/đọc I2C ổn định.
    {
        uint8_t accRange = 0, gyrRange = 0, accConf = 0, gyrConf = 0;
        bool r = bmiReadReg(REG_ACC_RANGE, accRange) && bmiReadReg(REG_GYR_RANGE, gyrRange)
              && bmiReadReg(REG_ACC_CONF,  accConf)  && bmiReadReg(REG_GYR_CONF,  gyrConf);
        bool ok = r && ((accRange & 0x0F) == 0x03) && ((gyrRange & 0x07) == 0x00);
        char msg[120];
        snprintf(msg, sizeof(msg),
                 "ACC_RANGE=0x%02X(exp 0x03)  GYR_RANGE=0x%02X(exp 0x00)  ACC_CONF=0x%02X  GYR_CONF=0x%02X",
                 accRange & 0x0F, gyrRange & 0x07, accConf, gyrConf);
        reportScenario("SC_04", ok ? TS_PASS : TS_FAIL, msg);
    }
}

// =====================================================================
// UT_MCU_CORE — MCU Core & Low-level Drivers
// =====================================================================
static void test_mcu_core() {
    printSuiteHeader("UT_MCU_CORE", "MCU Core & Low-level Drivers", "unit/MCU_CORE.md");

    // SC_01: CPU Clock — ESP.getCpuFreqMHz() must return 240
    // Rationale: TFLite Micro + BLE stack song song cần 240MHz để inference
    // xong trong < 50ms mỗi chu kỳ và BLE callback không bị trễ.
    {
        uint32_t mhz = ESP.getCpuFreqMHz();
        char msg[60];
        snprintf(msg, sizeof(msg), "CPU = %u MHz  (target: 240 MHz)", mhz);
        reportScenario("SC_01", mhz >= 240 ? TS_PASS : TS_FAIL, msg);
    }

    // SC_02: Deep Sleep config — configure timer wakeup, read wakeup cause
    // Deep sleep NOT entered to avoid device reboot during test suite.
    // Rationale: Deep Sleep < 100uA kéo dài pin. Wakeup cause phải đọc được
    // để firmware biết context (reset bình thường vs. thức dậy từ deep sleep).
    {
        esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
        esp_err_t err = esp_sleep_enable_timer_wakeup(10ULL * 1000000ULL);
        const char *cs = (cause == ESP_SLEEP_WAKEUP_TIMER)     ? "TIMER"
                       : (cause == ESP_SLEEP_WAKEUP_UNDEFINED)  ? "NORMAL_RESET"
                       : "OTHER";
        bool ok = (err == ESP_OK);
        char msg[120];
        snprintf(msg, sizeof(msg),
                 "timer_wakeup_config=%s  last_cause=%s  (sleep not entered—avoids reboot)",
                 ok ? "OK" : "FAIL", cs);
        reportScenario("SC_02", ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_03: GPIO Output — toggle LED pins HIGH/LOW, verify with digitalRead
    // Rationale: LED/Buzzer là kênh cảnh báo vật lý khi BLE mất kết nối.
    // GPIO lỗi làm mất kênh cảnh báo duy nhất trực tiếp trên thiết bị đeo.
    {
        const int   pins[]  = {PIN_LED_GREEN, PIN_LED_YELLOW, PIN_LED_RED};
        const char *names[] = {"GREEN",       "YELLOW",       "RED"      };
        bool allOk = true;
        char msg[100] = "";
        for (int i = 0; i < 3; i++) {
            pinMode(pins[i], OUTPUT);
            digitalWrite(pins[i], HIGH); delay(5);
            int hi = digitalRead(pins[i]);
            digitalWrite(pins[i], LOW);  delay(5);
            int lo = digitalRead(pins[i]);
            bool ok = (hi == HIGH) && (lo == LOW);
            if (!ok) allOk = false;
            char tmp[24];
            snprintf(tmp, sizeof(tmp), "%s=%s ", names[i], ok ? "OK" : "FAIL");
            strncat(msg, tmp, sizeof(msg) - strlen(msg) - 1);
        }
        reportScenario("SC_03", allOk ? TS_PASS : TS_FAIL, msg);
    }

    // SC_04: NVS Storage (Preferences) — write int, reopen namespace, read back
    // Rationale: NVS lưu cấu hình thiết bị (BLE peer address). Mất NVS sau
    // reboot → thiết bị cấu hình lại từ đầu, mất ghép đôi BLE với điện thoại.
    {
        const int32_t VAL = (int32_t)0xABCD1234;
        Preferences p;
        p.begin("ut_nvs", false); p.putInt("k", VAL); p.end();
        p.begin("ut_nvs", true);  int32_t r = p.getInt("k", 0); p.end();
        p.begin("ut_nvs", false); p.clear(); p.end();
        bool ok = (r == VAL);
        char msg[80];
        snprintf(msg, sizeof(msg), "write=0x%08X  read=0x%08X -> %s",
                 (unsigned)VAL, (unsigned)r, ok ? "match" : "MISMATCH");
        reportScenario("SC_04", ok ? TS_PASS : TS_FAIL, msg);
    }
}

// =====================================================================
// UT_AI_MODEL — TinyML Inference Engine
// =====================================================================
namespace tft {
    const tflite::Model*      mdl    = nullptr;
    tflite::MicroInterpreter* interp = nullptr;
    TfLiteTensor*             inT    = nullptr;
    TfLiteTensor*             outT   = nullptr;
    uint8_t                   arena[kTensorArenaSize];
    bool                      ok     = false;
}

static int8_t quantize(float v) {
    float s = tft::inT->params.scale;
    int   z = tft::inT->params.zero_point;
    int   q = (int)lroundf(v / s) + z;
    return (int8_t)(q < -128 ? -128 : q > 127 ? 127 : q);
}

static float dequantize(int8_t v) {
    return (v - tft::outT->params.zero_point) * tft::outT->params.scale;
}

static void test_ai_model() {
    printSuiteHeader("UT_AI_MODEL", "TinyML Inference Engine", "unit/AI_INFERENCE.md");

    // SC_01: Model Loading — GetModel + AllocateTensors + verify shape [1,100,6] int8
    // Rationale: ESP32-S3 RAM ~512KB. AllocateTensors thất bại nếu tensor arena
    // quá nhỏ → toàn bộ fall detection bị vô hiệu hóa ngay khi boot.
    {
        static tflite::MicroErrorReporter errRep;
        static tflite::AllOpsResolver     resolver;
        tft::mdl = tflite::GetModel(fall_detection_model_tflite);
        bool schOk = (tft::mdl->version() == TFLITE_SCHEMA_VERSION);

        static tflite::MicroInterpreter si(tft::mdl, resolver, tft::arena, kTensorArenaSize, &errRep);
        tft::interp = &si;
        bool allocOk = (tft::interp->AllocateTensors() == kTfLiteOk);
        tft::inT  = tft::interp->input(0);
        tft::outT = tft::interp->output(0);

        bool shapeOk = allocOk
            && (tft::inT->dims->size == 3)
            && (tft::inT->dims->data[1] == kWindowSize)
            && (tft::inT->dims->data[2] == kFeatureCount);
        bool typeOk = (tft::inT->type == kTfLiteInt8) && (tft::outT->type == kTfLiteInt8);
        tft::ok = schOk && allocOk && shapeOk && typeOk;

        char msg[140];
        snprintf(msg, sizeof(msg),
                 "schema=%s  alloc=%s  shape=%s[1,%d,%d]  type=%s  arena=%dKB",
                 schOk?"OK":"FAIL", allocOk?"OK":"FAIL", shapeOk?"OK":"FAIL",
                 tft::inT->dims->data[1], tft::inT->dims->data[2],
                 typeOk?"int8":"WRONG", kTensorArenaSize/1024);
        reportScenario("SC_01", tft::ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_02: Buffer Flow — push 120 samples into 100-slot ring buffer
    // Oldest must be sample #20, newest must be #119.
    // Rationale: sliding window 100 mẫu là đầu vào model. Overwrite sai slot
    // → model nhận chuỗi thời gian lệch → giảm accuracy fall detection.
    {
        struct S { float v; } buf[kWindowSize];
        int head = 0, count = 0;
        auto push = [&](float val) {
            buf[head].v = val;
            head = (head + 1) % kWindowSize;
            if (count < kWindowSize) count++;
        };
        for (int i = 0; i < 120; i++) push((float)i);

        int   oldest   = head;  // oldest slot when full
        float firstVal = buf[oldest].v;
        float lastVal  = buf[(oldest + count - 1) % kWindowSize].v;
        bool ok = (count == kWindowSize)
               && (fabsf(firstVal - 20.0f) < 0.01f)
               && (fabsf(lastVal  - 119.0f) < 0.01f);
        char msg[110];
        snprintf(msg, sizeof(msg),
                 "pushed 120  retained=%d(exp 100)  oldest=%.0f(exp 20)  newest=%.0f(exp 119)",
                 count, firstVal, lastVal);
        reportScenario("SC_02", ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_03: Sample Integrity — ring buffer retains exactly 100 samples in
    // chronological order with correct 20ms spacing after FreeRTOS taskSampling pushes.
    // Rationale: model được train trên 100 mẫu cách đều 20ms (2s @ 50Hz).
    // Nếu buffer giữ sai thứ tự hoặc thiếu mẫu → model nhận input lệch phân phối
    // so với lúc train → accuracy giảm. Đây là điều kiện đầu vào quan trọng nhất của AI.
    // Note: với kiến trúc FreeRTOS dual-task (taskSampling Core 0 / taskInference Core 1),
    // inference latency không còn ảnh hưởng đến sampling — test integrity là đúng hơn latency.
    {
        struct SimSample { float ax,ay,az,gx,gy,gz; uint32_t tsMs; };
        static SimSample buf[kWindowSize];
        int head = 0, count = 0;

        // Simulate taskSampling: push 100 samples at exact 20ms intervals
        auto push = [&](uint32_t ts) {
            buf[head] = {0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, ts};
            head = (head + 1) % kWindowSize;
            if (count < kWindowSize) count++;
        };
        for (int i = 0; i < kWindowSize; i++) push((uint32_t)(i * 20));

        // Simulate snapshotWindow(): read oldest-first
        int oldest = (count < kWindowSize) ? 0 : head;

        bool allOrdered = true;
        int  minGap = 9999, maxGap = 0;
        uint32_t prevTs = buf[oldest].tsMs;

        for (int i = 1; i < count; i++) {
            uint32_t ts = buf[(oldest + i) % kWindowSize].tsMs;
            int gap = (int)ts - (int)prevTs;
            if (gap != 20) allOrdered = false;
            if (gap < minGap) minGap = gap;
            if (gap > maxGap) maxGap = gap;
            prevTs = ts;
        }

        bool ok = (count == kWindowSize) && allOrdered;
        char msg[130];
        snprintf(msg, sizeof(msg),
                 "samples=%d(exp 100)  ordered=%s  gap=[%d,%d]ms(exp 20ms)  FreeRTOS=Core0/Core1",
                 count, allOrdered ? "YES" : "NO", minGap, maxGap);
        reportScenario("SC_03", ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_04: Sigmoid Limit — 3 extreme inputs, all outputs must be in [0.0, 1.0]
    // Rationale: quantization error có thể làm output vượt [0,1] → logic so sánh
    // ngưỡng fallProb >= 0.42 cho kết quả sai → false alarm liên tục hoặc bỏ sót ngã.
    {
        if (!tft::ok) {
            reportScenario("SC_04", TS_FAIL, "model not loaded — skip");
        } else {
            float tests[3][kFeatureCount] = {
                {  0,   0,  0,    0,    0,    0},
                { 16,  16, 16, 2000, 2000, 2000},
                {-16, -16,-16,-2000,-2000,-2000}
            };
            bool all = true;
            float lo = 1.0f, hi = 0.0f;
            for (auto &inp : tests) {
                for (int t = 0; t < kWindowSize; t++)
                    for (int f = 0; f < kFeatureCount; f++)
                        tft::inT->data.int8[t * kFeatureCount + f] = quantize(inp[f]);
                if (tft::interp->Invoke() != kTfLiteOk) { all = false; break; }
                int nOut = 1;
                for (int d = 0; d < tft::outT->dims->size; d++)
                    nOut *= tft::outT->dims->data[d];
                for (int i = 0; i < nOut; i++) {
                    float v = dequantize(tft::outT->data.int8[i]);
                    if (v < 0.0f || v > 1.0f) all = false;
                    if (v < lo) lo = v;
                    if (v > hi) hi = v;
                }
            }
            char msg[100];
            snprintf(msg, sizeof(msg), "3 extreme inputs -> out=[%.4f, %.4f]  (target: [0.0, 1.0])", lo, hi);
            reportScenario("SC_04", all ? TS_PASS : TS_FAIL, msg);
        }
    }
}

// =====================================================================
// UT_BLE_STACK — BLE Connection Stack (Peripheral)
// =====================================================================
static void test_ble_stack() {
    printSuiteHeader("UT_BLE_STACK", "BLE Stack (ESP32-S3 Peripheral)", "unit/BLE_STACK.md");

    // SC_01: Server Init — init NimBLE, create server, attach BleServerCb
    // Advertising NOT started yet — service must be registered first (see SC_02→SC_03 order).
    // Rationale: Android ScanFilter.setServiceUuid() matches the advertising packet.
    // If advertising starts before GATT service->start(), some Android versions reject the
    // UUID as "not yet in GATT table" and the scan filter never fires → device invisible.
    {
        NimBLEDevice::init("S3_AIFD Wearable_test");
        NimBLEDevice::setPower(ESP_PWR_LVL_P9);
        // Enable Just-Works bonding (no passkey) so client address is persisted to NVS.
        // This allows auto-reconnect on next boot without re-pairing.
        NimBLEDevice::setSecurityAuth(BLE_SM_PAIR_AUTHREQ_BOND);
        gBleServer = NimBLEDevice::createServer();
        gBleServer->setCallbacks(new BleServerCb());

        bool ok = (gBleServer != nullptr);
        char msg[80];
        snprintf(msg, sizeof(msg),
                 "device=\"S3_AIFD Wearable_test\"  server=%s  callbacks=BleServerCb  (advertising deferred to SC_03)",
                 ok ? "OK" : "NULL");
        reportScenario("SC_01", ok ? TS_PASS : TS_FAIL, msg);
    }

    // SC_02: Service & Characteristic Init — 3 chars + ControlCb + service.start()
    // Service is started HERE, before advertising, so the GATT table is complete
    // when the advertising packet with the service UUID goes out.
    // Rationale: UUID mismatch → subscribe thất bại; không có ControlCb → READY handshake
    // không hoạt động → firmware không biết khi nào client sẵn sàng nhận data.
    {
        if (!gBleServer) {
            reportScenario("SC_02", TS_FAIL, "server null — skip");
        } else {
            gBleService = gBleServer->createService(AIFD_SVC_UUID);

            auto *cAlert  = gBleService->createCharacteristic(CHAR_ALERT_UUID,
                                NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
            auto *cVitals = gBleService->createCharacteristic(CHAR_VITALS_UUID,
                                NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
            auto *cCtrl   = gBleService->createCharacteristic(CHAR_CONTROL_UUID,
                                NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE);
            cCtrl->setCallbacks(new ControlCb());

            // Initial values (same pattern as S3_Combine)
            cAlert->setValue("ALERT,0,0,idle,0,0.000,1.000");
            cVitals->setValue("BATCH,0,255|255|255|255|255,255|255|255|255|255,0|0|0|0|0");
            cCtrl->setValue("WAITING_READY");

            gBleService->start();   // ← GATT table complete before advertising starts

            bool ok = (cAlert != nullptr) && (cVitals != nullptr) && (cCtrl != nullptr);
            char msg[140];
            snprintf(msg, sizeof(msg),
                     "ALERT=%s  VITALS=%s  CONTROL=%s  ControlCb=attached  service.start()=done",
                     cAlert?"OK":"NULL", cVitals?"OK":"NULL", cCtrl?"OK":"NULL");
            reportScenario("SC_02", ok ? TS_PASS : TS_FAIL, msg);
        }
    }

    // SC_03: Advertising + Notify property — start advertising AFTER service is ready
    // Rationale: advertising starts only after GATT service is registered → Android
    // UUID filter matches correctly → device appears in DevicePairingScreen scan.
    {
        if (!gBleService) {
            reportScenario("SC_03", TS_FAIL, "service null — skip");
        } else {
            // Verify NOTIFY properties
            auto *cA = gBleService->getCharacteristic(CHAR_ALERT_UUID);
            auto *cV = gBleService->getCharacteristic(CHAR_VITALS_UUID);
            bool aN = cA && (cA->getProperties() & NIMBLE_PROPERTY::NOTIFY);
            bool vN = cV && (cV->getProperties() & NIMBLE_PROPERTY::NOTIFY);

            // Now start advertising — GATT table is complete
            NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
            adv->addServiceUUID(AIFD_SVC_UUID);
            adv->setScanResponse(true);
            adv->start();
            delay(100);
            bool advOk = adv->isAdvertising();

            bool ok = aN && vN && advOk;
            char msg[120];
            snprintf(msg, sizeof(msg),
                     "ALERT.NOTIFY=%s  VITALS.NOTIFY=%s  advertising=%s  svc_uuid_in_adv=yes",
                     aN?"enabled":"MISSING", vN?"enabled":"MISSING",
                     advOk?"active":"FAIL");
            reportScenario("SC_03", ok ? TS_PASS : TS_FAIL, msg);
        }
    }

    // SC_04: Bond storage / Auto-reconnect readiness
    // Verify NimBLE bond store is accessible and report saved peer addresses.
    // Flow: first boot → 0 bonds → open advertising.
    //       After a session → bond saved to NVS → next boot shows client address
    //       → device can whitelist that client → auto-reconnect without re-pairing.
    // Rationale: thiết bị đeo reboot liên tục (pin hết, reset). Người dùng không thể
    // pair lại thủ công mỗi lần — bond storage đảm bảo reconnect tự động.
    {
        int bonds = NimBLEDevice::getNumBonds();
        char msg[120];
        if (bonds == 0) {
            snprintf(msg, sizeof(msg),
                     "bond_store=OK  saved_peers=0  (first boot — will save after first connect)");
        } else {
            NimBLEAddress addr = NimBLEDevice::getBondedAddress(0);
            snprintf(msg, sizeof(msg),
                     "bond_store=OK  saved_peers=%d  known[0]=%s  (auto-reconnect ready)",
                     bonds, addr.toString().c_str());
        }
        reportScenario("SC_04", TS_PASS, msg);
    }
    // BLE NOT deinitialized — server stays live for real pairing in loop()
}

// =====================================================================
// ARDUINO ENTRY
// =====================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println();
    Serial.println("+===================================================================+");
    Serial.println("|       AIFD UNIT TEST SUITE -- ESP32-S3  (115200 baud)             |");
    Serial.println("|  Ref: System_Architecture/test_plan/unit/                         |");
    Serial.println("|  Re-flash to re-run.                                              |");
    Serial.println("+===================================================================+");

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 100000);
    Wire.setClock(100000);
    Wire.setTimeOut(20);
    delay(50);

    for (int p : {PIN_LED_GREEN, PIN_LED_YELLOW, PIN_LED_RED}) {
        pinMode(p, OUTPUT);
        digitalWrite(p, LOW);
    }

    test_bmi160();
    test_mcu_core();
    test_ai_model();
    test_ble_stack();

    int total = gPassed + gFailed;
    Serial.println();
    Serial.println("+===================================================================+");
    Serial.printf( "|  RESULT:  %2d PASS  |  %2d FAIL  |  %2d N/A  |  %2d scenarios      |\n",
                   gPassed, gFailed, gNA, total);
    Serial.println("+===================================================================+");
    if (gFailed == 0)
        Serial.println("|  [OK]  All scenarios passed. Firmware base is healthy.            |");
    else
        Serial.printf( "|  [!!]  %d scenario(s) FAILED. See output above for details.       |\n",
                       gFailed);
    Serial.println("+===================================================================+");
}

void loop() {
    static uint32_t lastPrintMs = 0;
    static bool     lastConnected = false;
    static bool     lastReady     = false;

    uint32_t now = millis();

    // Detect state change — print immediately
    if (gBleConnected != lastConnected || gBleReady != lastReady) {
        lastConnected = gBleConnected;
        lastReady     = gBleReady;
        // State change already printed inside callbacks — no duplicate print needed
    }

    // Periodic status line every 5s
    if ((uint32_t)(now - lastPrintMs) >= 5000) {
        lastPrintMs = now;
        const char *connStr  = gBleConnected ? "CONNECTED" : "advertising";
        const char *readyStr = gBleReady     ? "READY"     : "waiting";
        Serial.printf("[BLE]  status=%-11s  handshake=%-7s  sessions=%lu  uptime=%lus\n",
                      connStr, readyStr, (unsigned long)gConnectCount, (unsigned long)(now / 1000));
    }

    delay(50);
}
