package com.aifd.viewmodel

import android.app.Application
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import android.util.Log
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
    val healthData: HealthData? = MockDataProvider.createHealthData(),
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
        val intent = Intent(ctx, BleForegroundService::class.java)
        ctx.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    /** Called from AppNavigation when BLE device state changes */
    fun updateDevice(device: DeviceInfo?) {
        _uiState.update { it.copy(device = device) }
    }

    private fun observeBleData() {
        val ble = service?.bleManager ?: return

        viewModelScope.launch {
            ble.sensorData.collect { data ->
                _uiState.update { state ->
                    val health = state.healthData ?: MockDataProvider.createHealthData()
                    
                    // Only update if we have a valid heart rate or SpO2
                    if (data.heartRate == 0 && data.spo2 == 0) return@update state

                    val hrStatus = when {
                        data.heartRate > 100 -> HealthStatus.HIGH
                        data.heartRate < 60 && data.heartRate > 0 -> HealthStatus.LOW
                        else -> HealthStatus.NORMAL
                    }

                    val spO2Status = if (data.spo2 < 95 && data.spo2 > 0) HealthStatus.LOW else HealthStatus.NORMAL

                    // Update history by dropping oldest and adding newest
                    val newHRHistory = if (data.heartRate > 0) {
                        health.heartRateHistory.drop(1) + data.heartRate
                    } else health.heartRateHistory

                    val newSpO2History = if (data.spo2 > 0) {
                        health.spO2History.drop(1) + data.spo2
                    } else health.spO2History

                    state.copy(
                        healthData = health.copy(
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
                    )
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
