#include <Arduino.h>
#include <NimBLEDevice.h>

// =====================================================
// CẤU HÌNH BLE (Khớp với App Android)
// =====================================================
static const char* BLE_DEVICE_NAME = "S3_Zinex_Test";
static const char* SERVICE_UUID     = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char* STATUS_CHAR_UUID  = "beb5483e-36e1-4688-b7f5-ea07361b26a8";
static const char* CONTROL_CHAR_UUID = "f9b2c417-1d15-4ad4-9b52-b94aa0f76b03";

NimBLEServer* pServer = nullptr;
NimBLECharacteristic* pStatusChar = nullptr;
bool deviceConnected = false;
uint32_t fallSequence = 1;
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 30000; // 30 giây

// Callbacks xử lý kết nối
class MyServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) {
        deviceConnected = true;
        Serial.println(">> App đã kết nối!");
    };
    void onDisconnect(NimBLEServer* pServer) {
        deviceConnected = false;
        Serial.println(">> App đã ngắt kết nối. Đang phát lại quảng cáo...");
        pServer->startAdvertising();
    }
};

void setup() {
    Serial.begin(115200);
    
    // Khởi tạo BLE
    NimBLEDevice::init(BLE_DEVICE_NAME);
    pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    // Tạo Service
    NimBLEService* pService = pServer->createService(SERVICE_UUID);

    // Tạo Characteristic Status (Để gửi tin nhắn ALERT)
    pStatusChar = pService->createCharacteristic(
        STATUS_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    // Tạo Characteristic Control (Để App gửi lệnh READY)
    pService->createCharacteristic(
        CONTROL_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE
    );

    pService->start();

    // Bắt đầu phát quảng cáo (Advertising)
    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->start();

    Serial.println("--- BLE Zinex Auto-Test Ready ---");
    Serial.println("Tên BLE: zinex_test_BLE");
    Serial.println("Mỗi 10 giây sẽ tự động gửi tín hiệu FALL...");
}

void loop() {
    unsigned long currentTime = millis();

    // Tự động gửi tín hiệu mỗi 10 giây nếu đã kết nối
    if (currentTime - lastSendTime >= SEND_INTERVAL) {
        lastSendTime = currentTime;

        if (deviceConnected) {
            // Định dạng Payload ALERT cho App Android nhận diện
            String payload = "ALERT,";
            payload += String(fallSequence++) + ",";
            payload += String(currentTime / 1000) + ",";
            payload += "fall,1,0.990,0.010";

            pStatusChar->setValue((uint8_t*)payload.c_str(), payload.length());
            pStatusChar->notify();

            Serial.print(">> [AUTO] Đã gửi tín hiệu FALL: ");
            Serial.println(payload);
        } else {
            Serial.println(">> [WAIT] Đang chờ App kết nối...");
        }
    }

    delay(100);
}
