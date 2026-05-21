package com.aifd.data

import java.util.Date

/**
 * Connection status for BLE device.
 */
enum class ConnectionStatus {
    CONNECTED,
    DISCONNECTED,
    CONNECTING
}

enum class UserRole {
    WEARER,
    CAREGIVER
}

/**
 * Health status severity levels.
 */
enum class HealthStatus {
    NORMAL,
    HIGH,
    LOW
}

/**
 * BLE device information.
 */
data class DeviceInfo(
    val name: String,
    val id: String,
    val battery: Int,
    val signalStrength: Int,
    val connectionStatus: ConnectionStatus,
    val firmwareVersion: String = "2.1.4",
    val lastSyncTime: Date = Date()
)

/**
 * Aggregated health data from the wearable.
 */
data class HealthData(
    val heartRate: Int,
    val heartRateStatus: HealthStatus,
    val heartRateHistory: List<Int>,
    val heartRateMin: Int,
    val heartRateMax: Int,
    val spO2: Int,
    val spO2Status: HealthStatus,
    val spO2History: List<Int>,
    val stepCount: Int,
    val stepGoal: Int,
    val lastUpdated: Date
)

/**
 * Emergency contact entry.
 */
data class EmergencyContact(
    val id: String,
    val name: String,
    val phone: String,
    val relationship: String,
    val isPrimary: Boolean
)

/**
 * Types of recorded events.
 */
enum class EventType {
    FALL,         // ESP32 phát hiện té ngã
    SAFE,         // ESP32 xác nhận an toàn (false alarm hoặc bấm nút)
    ALERT,        // Cảnh báo chung
    VITALS,       // HR/SpO2 vượt ngưỡng an toàn
    DISCONNECT,   // Mất kết nối BLE
    LOW_BATTERY,  // Pin thiết bị yếu
    SYNC_FAILED   // Không đồng bộ được lên cloud
}

/**
 * Resolution status for events.
 */
enum class EventStatus {
    RESOLVED,
    PENDING,
    DISMISSED
}

/**
 * A recorded fall / alert event.
 */
data class FallEvent(
    val id: String,
    val timestamp: Date,
    val type: EventType,
    val title: String,
    val status: EventStatus,
    val location: String? = null,
    val deviceName: String,
    val userResponse: String? = null,
    val detail: String? = null   // Thêm thông tin: "HR: 115 bpm", "SpO2: 91%", v.v.
)

/**
 * Nearby BLE device discovered during scanning.
 */
data class NearbyDevice(
    val id: String,
    val name: String,
    val signalStrength: Int
)

/**
 * Notification preferences.
 */
data class NotificationSettings(
    val fallAlerts: Boolean = true,
    val deviceAlerts: Boolean = true,
    val reminders: Boolean = false
)

/**
 * Daily step entry for weekly chart.
 */
data class DailySteps(
    val day: String,
    val steps: Int
)

/**
 * User profile information for registration and account.
 */
data class UserProfile(
    val username: String = "",
    val caregiverName: String = "",
    val wearerName: String = "",
    val wearerBornYear: String = "",
    val wearerGender: String = "",
    val caregiverPhone: String = ""
)
