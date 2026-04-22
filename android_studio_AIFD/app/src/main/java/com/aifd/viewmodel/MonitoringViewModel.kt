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

enum class MetricTab { HEART_RATE, SPO2, STEPS }
enum class TimeRange { LIVE, ONE_HOUR, TWENTY_FOUR_HOURS }

data class MonitoringUiState(
    val activeTab: MetricTab = MetricTab.HEART_RATE,
    val timeRange: TimeRange = TimeRange.LIVE,
    val chartData: List<Int> = emptyList(),
    val healthData: HealthData? = MockDataProvider.createHealthData(),
    val weeklySteps: List<DailySteps> = MockDataProvider.weeklySteps,
    val isConnected: Boolean = false
)

class MonitoringViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(MonitoringUiState())
    val uiState: StateFlow<MonitoringUiState> = _uiState.asStateFlow()

    private var service: BleForegroundService? = null
    private var isBound = false

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as? BleForegroundService.LocalBinder ?: return
            service = localBinder.getService()
            isBound = true
            Log.i("MonitoringVM", "Service bound ✓")
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

    fun selectTab(tab: MetricTab) {
        _uiState.update { it.copy(activeTab = tab) }
        regenerateChartDataFromHistory()
    }

    fun selectTimeRange(range: TimeRange) {
        _uiState.update { it.copy(timeRange = range) }
        regenerateChartDataFromHistory()
    }

    private fun observeBleData() {
        val ble = service?.bleManager ?: return

        // 1. Observe real-time data for "LIVE" updates
        viewModelScope.launch {
            ble.sensorData.collect { data ->
                _uiState.update { state ->
                    if (state.timeRange != TimeRange.LIVE) return@update state
                    
                    val newValue = when (state.activeTab) {
                        MetricTab.HEART_RATE -> data.heartRate
                        MetricTab.SPO2 -> data.spo2
                        else -> 0
                    }
                    if (newValue == 0) return@update state

                    val currentData = state.chartData
                    val newData = if (currentData.size >= 20) {
                        currentData.drop(1) + newValue
                    } else {
                        currentData + newValue
                    }
                    state.copy(chartData = newData, isConnected = true)
                }
            }
        }

        // 2. Observe batch data to fill history
        viewModelScope.launch {
            ble.vitalsBatch.collect { batch ->
                // Here we could update a more persistent history in Data layer
                // For now, let's just trigger a chart refresh if not in LIVE mode
                if (_uiState.value.timeRange != TimeRange.LIVE) {
                    regenerateChartDataFromHistory()
                }
            }
        }
        
        // Observe connection state
        viewModelScope.launch {
            ble.bleState.collect { state ->
                val connected = state is BleManager.BleState.Connected
                _uiState.update { it.copy(isConnected = connected) }
            }
        }
    }

    private fun regenerateChartDataFromHistory() {
        // In a real app, this would query a Room database
        // Since we are "degrading" from mock to real, and we don't have a DB yet,
        // we'll keep using mock data for non-LIVE ranges for now, 
        // but LIVE will use the real sensorData flow above.
        
        val state = _uiState.value
        if (state.timeRange == TimeRange.LIVE) {
            // Already handled by sensorData collector
            return
        }

        val points = when (state.timeRange) {
            TimeRange.ONE_HOUR -> 60
            TimeRange.TWENTY_FOUR_HOURS -> 144
            else -> 20
        }
        val data = when (state.activeTab) {
            MetricTab.HEART_RATE -> MockDataProvider.generateChartData(72.0, 3.0, 55.0, 110.0, points)
            MetricTab.SPO2 -> MockDataProvider.generateChartData(97.0, 1.0, 92.0, 100.0, points)
            MetricTab.STEPS -> emptyList()
        }
        _uiState.update { it.copy(chartData = data) }
    }

    fun getStats(): Triple<Int, Int, Int> {
        val data = _uiState.value.chartData
        if (data.isEmpty()) return Triple(0, 0, 0)
        val avg = data.average().toInt()
        val minV = data.minOrNull() ?: 0
        val maxV = data.maxOrNull() ?: 0
        return Triple(avg, minV, maxV)
    }

    override fun onCleared() {
        super.onCleared()
        if (isBound) {
            getApplication<Application>().applicationContext.unbindService(serviceConnection)
            isBound = false
        }
    }
}
