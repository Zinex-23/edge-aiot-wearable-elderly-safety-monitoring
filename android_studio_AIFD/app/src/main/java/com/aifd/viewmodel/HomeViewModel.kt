package com.aifd.viewmodel

import android.app.Application
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import android.util.Log
import androidx.core.content.edit
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aifd.ble.BleManager
import com.aifd.data.*
import com.aifd.service.BleForegroundService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.Date

data class HomeUiState(
    val device: DeviceInfo? = null,
    val healthData: HealthData? = null,
    val isLoading: Boolean = false
)

class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private var service: BleForegroundService? = null
    private var isBound = false

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as? BleForegroundService.LocalBinder ?: return
            service = localBinder.getService()
            isBound = true
            Log.i("HomeVM", "Service bound ✓")
            observeBleData()
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            service = null
            isBound = false
        }
    }

    init {
        val ctx = application.applicationContext
        val prefs = ctx.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val savedDeviceName = prefs.getString("device_name", null)
        val savedDeviceMac = prefs.getString("device_mac", null)
        val username = prefs.getString("username", "") ?: ""
        
        // Only load mock data if it's the demo account; real accounts load last known values
        if (username == "000") {
            _uiState.update { it.copy(healthData = MockDataProvider.createHealthData()) }
        } else {
            val lastHR = prefs.getInt("last_heart_rate", 0)
            val lastSpO2 = prefs.getInt("last_spo2", 0)
            val hrHistory = prefs.getString("hr_history", null)
                ?.split(",")?.mapNotNull { it.trim().toIntOrNull() }
                ?: List(24) { 0 }
            val spo2History = prefs.getString("spo2_history", null)
                ?.split(",")?.mapNotNull { it.trim().toIntOrNull() }
                ?: List(24) { 0 }
            if (lastHR > 0 || lastSpO2 > 0) {
                _uiState.update {
                    it.copy(
                        healthData = HealthData(
                            heartRate = lastHR,
                            heartRateStatus = if (lastHR > 100) HealthStatus.HIGH
                                else if (lastHR in 1..59) HealthStatus.LOW else HealthStatus.NORMAL,
                            heartRateHistory = hrHistory,
                            heartRateMin = hrHistory.filter { v -> v > 0 }.minOrNull() ?: 0,
                            heartRateMax = hrHistory.filter { v -> v > 0 }.maxOrNull() ?: 0,
                            spO2 = lastSpO2,
                            spO2Status = if (lastSpO2 in 1..94) HealthStatus.LOW else HealthStatus.NORMAL,
                            spO2History = spo2History,
                            stepCount = 0,
                            stepGoal = 10000,
                            lastUpdated = Date(prefs.getLong("last_vital_timestamp", System.currentTimeMillis()))
                        )
                    )
                }
            }
        }

        if (savedDeviceName != null && savedDeviceMac != null) {
            val initialStatus = if (username == "000") ConnectionStatus.CONNECTED else ConnectionStatus.DISCONNECTED
            _uiState.update { 
                it.copy(
                    device = DeviceInfo(
                        id = savedDeviceMac,
                        name = savedDeviceName,
                        battery = if (username == "000") 85 else 0,
                        signalStrength = if (username == "000") -55 else 0,
                        connectionStatus = initialStatus
                    )
                )
            }
        }

        val intent = Intent(ctx, BleForegroundService::class.java)
        ctx.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    fun resetForUser(username: String) {
        if (username == "000") {
            _uiState.value = HomeUiState(healthData = MockDataProvider.createHealthData())
        } else {
            val ctx = getApplication<Application>().applicationContext
            val prefs = ctx.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            val lastHR = prefs.getInt("last_heart_rate", 0)
            val lastSpO2 = prefs.getInt("last_spo2", 0)
            _uiState.value = if (lastHR > 0 || lastSpO2 > 0) {
                val hrHistory = prefs.getString("hr_history", null)
                    ?.split(",")?.mapNotNull { it.trim().toIntOrNull() } ?: List(24) { 0 }
                val spo2History = prefs.getString("spo2_history", null)
                    ?.split(",")?.mapNotNull { it.trim().toIntOrNull() } ?: List(24) { 0 }
                HomeUiState(healthData = HealthData(
                    heartRate = lastHR,
                    heartRateStatus = if (lastHR > 100) HealthStatus.HIGH
                        else if (lastHR in 1..59) HealthStatus.LOW else HealthStatus.NORMAL,
                    heartRateHistory = hrHistory,
                    heartRateMin = hrHistory.filter { it > 0 }.minOrNull() ?: 0,
                    heartRateMax = hrHistory.filter { it > 0 }.maxOrNull() ?: 0,
                    spO2 = lastSpO2,
                    spO2Status = if (lastSpO2 in 1..94) HealthStatus.LOW else HealthStatus.NORMAL,
                    spO2History = spo2History,
                    stepCount = 0, stepGoal = 10000, lastUpdated = Date()
                ))
            } else {
                HomeUiState()
            }
        }
    }

    fun updateDevice(device: DeviceInfo?) {
        val isDemo = MockDataProvider.DEMO_MODE
        
        if (isDemo && device == null) {
            // For demo account, keep the existing mock device if new one is null
            return
        }
        _uiState.update { it.copy(device = device) }
    }

    private fun observeBleData() {
        val ble = service?.bleManager ?: return
        val prefs = getApplication<Application>()
            .getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val username = prefs.getString("username", "") ?: ""

        viewModelScope.launch {
            ble.sensorData.collect { data ->
                if (data.heartRate == 0 && data.spo2 == 0) return@collect

                // Pure state computation — no I/O inside update lambda
                var newHRHistory: List<Int> = emptyList()
                var newSpO2History: List<Int> = emptyList()
                var newHealthData: HealthData? = null

                _uiState.update { state ->
                    val health = state.healthData ?: if (username == "000") MockDataProvider.createHealthData() else HealthData(
                        heartRate = 0,
                        heartRateStatus = HealthStatus.NORMAL,
                        heartRateHistory = List(24) { 0 },
                        heartRateMin = 0,
                        heartRateMax = 0,
                        spO2 = 0,
                        spO2Status = HealthStatus.NORMAL,
                        spO2History = List(24) { 0 },
                        stepCount = 0,
                        stepGoal = 10000,
                        lastUpdated = Date()
                    )

                    val hrStatus = when {
                        data.heartRate > 100 -> HealthStatus.HIGH
                        data.heartRate < 60 && data.heartRate > 0 -> HealthStatus.LOW
                        else -> HealthStatus.NORMAL
                    }
                    val spO2Status = if (data.spo2 < 95 && data.spo2 > 0) HealthStatus.LOW else HealthStatus.NORMAL

                    newHRHistory = if (data.heartRate > 0) health.heartRateHistory.drop(1) + data.heartRate
                                   else health.heartRateHistory
                    newSpO2History = if (data.spo2 > 0) health.spO2History.drop(1) + data.spo2
                                     else health.spO2History

                    newHealthData = health.copy(
                        heartRate = if (data.heartRate > 0) data.heartRate else health.heartRate,
                        heartRateStatus = hrStatus,
                        heartRateHistory = newHRHistory,
                        heartRateMin = newHRHistory.filter { it > 0 }.minOrNull() ?: 55,
                        heartRateMax = newHRHistory.filter { it > 0 }.maxOrNull() ?: 110,
                        spO2 = if (data.spo2 > 0) data.spo2 else health.spO2,
                        spO2Status = spO2Status,
                        spO2History = newSpO2History,
                        lastUpdated = Date()
                    )
                    state.copy(healthData = newHealthData)
                }

                // Persist AFTER state update — SharedPreferences.apply() is async but
                // calling it inside _uiState.update held the main-thread update lock longer.
                val health = newHealthData ?: return@collect
                if (username != "000") {
                    prefs.edit {
                        putInt("last_heart_rate", health.heartRate)
                        putInt("last_spo2", health.spO2)
                        putLong("last_vital_timestamp", System.currentTimeMillis())
                        putString("hr_history", newHRHistory.joinToString(","))
                        putString("spo2_history", newSpO2History.joinToString(","))
                    }
                }
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        if (isBound) {
            getApplication<Application>().applicationContext.unbindService(serviceConnection)
            isBound = false
        }
    }
}
