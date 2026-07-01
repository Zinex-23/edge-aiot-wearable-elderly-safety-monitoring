#include <Arduino.h>
#include <NimBLEDevice.h>

// =====================================================
// CẤU HÌNH BLE (Khớp với App Android)
// =====================================================
static const char* BLE_DEVICE_NAME   = "S3_Zinex_Test";
static const char* SERVICE_UUID      = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char* STATUS_CHAR_UUID  = "beb5483e-36e1-4688-b7f5-ea07361b26a8"; // ALERT (fall)
static const char* VITALS_CHAR_UUID  = "7b809f11-63f0-4dca-8e4d-2b4e8384e7c1"; // BATCH (HR + SpO2)
static const char* CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03"; // READY handshake

NimBLEServer*         pServer      = nullptr;
NimBLECharacteristic* pStatusChar  = nullptr;
NimBLECharacteristic* pVitalsChar  = nullptr;
bool     deviceConnected  = false;
uint32_t fallSequence     = 1;
uint32_t vitalsSequence   = 1;

unsigned long lastFallTime   = 0;
unsigned long lastVitalsTime = 0;

// Fall mỗi 2 phút
const unsigned long FALL_INTERVAL   = 120000UL;
// Vitals mỗi 2 giây
const unsigned long VITALS_INTERVAL = 2000UL;

// Giả lập HR và SpO2 dao động nhẹ
uint8_t simulatedHR   = 72;
uint8_t simulatedSpO2 = 98;

class MyServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) {
        deviceConnected = true;
        Serial.println(">> App đã kết nối!");
    }
    void onDisconnect(NimBLEServer* pServer) {
        deviceConnected = false;
        Serial.println(">> App đã ngắt kết nối. Đang phát lại quảng cáo...");
        pServer->startAdvertising();
    }
};

void setup() {
    Serial.begin(115200);

    NimBLEDevice::init(BLE_DEVICE_NAME);
    pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    NimBLEService* pService = pServer->createService(SERVICE_UUID);

    // Characteristic STATUS — gửi ALERT khi phát hiện ngã
    pStatusChar = pService->createCharacteristic(
        STATUS_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    // Characteristic VITALS — gửi BATCH HR/SpO2 liên tục
    pVitalsChar = pService->createCharacteristic(
        VITALS_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    // Characteristic CONTROL — nhận lệnh READY từ app
    pService->createCharacteristic(
        CONTROL_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE
    );

    pService->start();

    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->start();

    Serial.println("--- BLE Zinex Test Ready ---");
    Serial.printf("Fall mỗi %lu giây | Vitals mỗi %lu giây\n",
                  FALL_INTERVAL / 1000, VITALS_INTERVAL / 1000);
}

void loop() {
    unsigned long now = millis();

    if (!deviceConnected) {
        if (now - lastVitalsTime >= 2000) {
            lastVitalsTime = now;
            Serial.println(">> [WAIT] Đang chờ App kết nối...");
        }
        delay(100);
        return;
    }

    // --- Gửi VITALS (HR + SpO2) mỗi 2 giây ---
    if (now - lastVitalsTime >= VITALS_INTERVAL) {
        lastVitalsTime = now;

        // Dao động nhẹ để mô phỏng thực tế
        simulatedHR   = 70 + random(0, 16);   // 70–85 bpm
        simulatedSpO2 = 96 + random(0, 4);    // 96–99 %

        // Format: BATCH,seq,hr,spo2,timestamp
        // parseVitalsPayload() của app hỗ trợ single-value (không cần pipe)
        String vitalsPayload = "BATCH,";
        vitalsPayload += String(vitalsSequence++) + ",";
        vitalsPayload += String(simulatedHR) + ",";
        vitalsPayload += String(simulatedSpO2) + ",";
        vitalsPayload += String(now / 1000);

        pVitalsChar->setValue((uint8_t*)vitalsPayload.c_str(), vitalsPayload.length());
        pVitalsChar->notify();

        Serial.printf(">> [VITALS] %s\n", vitalsPayload.c_str());
    }

    // --- Gửi FALL ALERT mỗi 2 phút ---
    if (now - lastFallTime >= FALL_INTERVAL) {
        lastFallTime = now;

        String alertPayload = "ALERT,";
        alertPayload += String(fallSequence++) + ",";
        alertPayload += String(now / 1000) + ",";
        alertPayload += "fall,1,0.990,0.010";

        pStatusChar->setValue((uint8_t*)alertPayload.c_str(), alertPayload.length());
        pStatusChar->notify();

        Serial.printf(">> [FALL] %s\n", alertPayload.c_str());
    }

    delay(50);
}
