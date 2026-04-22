package com.aifd.data

import java.util.Date
import kotlin.math.max
import kotlin.math.min
import kotlin.random.Random

/**
 * Provides realistic mock data for development and demonstration.
 * In production, this would be replaced by real BLE data sources.
 */
object MockDataProvider {

    val device = DeviceInfo(
        name = "AIFD Wearable Pro",
        id = "AIFD-001-2024",
        battery = 78,
        signalStrength = -45,
        connectionStatus = ConnectionStatus.CONNECTED,
        firmwareVersion = "2.1.4",
        lastSyncTime = Date(System.currentTimeMillis() - 5 * 60 * 1000)
    )

    fun createHealthData(): HealthData {
        val hrHistory = generateHeartRateHistory()
        return HealthData(
            heartRate = 72,
            heartRateStatus = HealthStatus.NORMAL,
            heartRateHistory = hrHistory,
            heartRateMin = hrHistory.minOrNull() ?: 60,
            heartRateMax = hrHistory.maxOrNull() ?: 100,
            spO2 = 98,
            spO2Status = HealthStatus.NORMAL,
            spO2History = generateSpO2History(),
            stepCount = 4523,
            stepGoal = 10000,
            lastUpdated = Date()
        )
    }

    val emergencyContacts = listOf(
        EmergencyContact(
            id = "1",
            name = "Sarah Johnson",
            phone = "+1 (555) 123-4567",
            relationship = "Daughter",
            isPrimary = true
        ),
        EmergencyContact(
            id = "2",
            name = "Dr. Michael Chen",
            phone = "+1 (555) 987-6543",
            relationship = "Primary Care Physician",
            isPrimary = false
        )
    )

    val fallEvents = listOf(
        FallEvent(
            id = "1",
            timestamp = Date(System.currentTimeMillis() - 2 * 60 * 60 * 1000),
            type = EventType.FALL,
            title = "Fall Detected",
            status = EventStatus.RESOLVED,
            location = "Living Room",
            deviceName = "AIFD Wearable Pro",
            userResponse = "I'm Safe"
        ),
        FallEvent(
            id = "2",
            timestamp = Date(System.currentTimeMillis() - 24 * 60 * 60 * 1000),
            type = EventType.DISCONNECT,
            title = "Device Disconnected",
            status = EventStatus.RESOLVED,
            deviceName = "AIFD Wearable Pro"
        ),
        FallEvent(
            id = "3",
            timestamp = Date(System.currentTimeMillis() - 48 * 60 * 60 * 1000),
            type = EventType.LOW_BATTERY,
            title = "Low Battery Warning",
            status = EventStatus.DISMISSED,
            deviceName = "AIFD Wearable Pro"
        ),
        FallEvent(
            id = "4",
            timestamp = Date(System.currentTimeMillis() - 5L * 24 * 60 * 60 * 1000),
            type = EventType.FALL,
            title = "Fall Detected",
            status = EventStatus.RESOLVED,
            location = "Bathroom",
            deviceName = "AIFD Wearable Pro",
            userResponse = "Called for Help"
        )
    )

    val nearbyDevices = listOf(
        NearbyDevice(id = "AIFD-001-2024", name = "AIFD Wearable Pro", signalStrength = -45),
        NearbyDevice(id = "AIFD-002-2024", name = "AIFD Band Lite", signalStrength = -62),
        NearbyDevice(id = "OTHER-001", name = "Unknown Device", signalStrength = -78)
    )

    val weeklySteps = listOf(
        DailySteps("Mon", 8234),
        DailySteps("Tue", 6521),
        DailySteps("Wed", 9102),
        DailySteps("Thu", 4523),
        DailySteps("Fri", 7865),
        DailySteps("Sat", 5432),
        DailySteps("Sun", 3210)
    )

    private fun generateHeartRateHistory(): List<Int> {
        val data = mutableListOf<Int>()
        var value = 72.0
        for (i in 0 until 24) {
            value += Random.nextDouble() * 6 - 3
            value = max(60.0, min(100.0, value))
            data.add(value.toInt())
        }
        return data
    }

    private fun generateSpO2History(): List<Int> {
        val data = mutableListOf<Int>()
        var value = 98.0
        for (i in 0 until 24) {
            value += Random.nextDouble() * 2 - 1
            value = max(94.0, min(100.0, value))
            data.add(value.toInt())
        }
        return data
    }

    fun generateChartData(baseValue: Double, variance: Double, minVal: Double, maxVal: Double, points: Int): List<Int> {
        val data = mutableListOf<Int>()
        var value = baseValue
        for (i in 0 until points) {
            value += Random.nextDouble() * variance * 2 - variance
            value = max(minVal, min(maxVal, value))
            data.add(value.toInt())
        }
        return data
    }
}
