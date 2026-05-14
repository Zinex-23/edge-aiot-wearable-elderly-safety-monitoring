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
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class MetricTab { HEART_RATE, SPO2 }
enum class TimeRange { LIVE, ONE_HOUR, TWENTY_FOUR_HOURS }

data class MonitoringUiState(
    val activeTab: MetricTab = MetricTab.HEART_RATE,
    val timeRange: TimeRange = TimeRange.LIVE,
    val chartData: List<Int> = emptyList(),
    val currentHR: Int = 0,
    val currentSpO2: Int = 0,
    val healthData: HealthData? = null,
    val weeklySteps: List<DailySteps> = emptyList(),
    val isConnected: Boolean = false
)

class MonitoringViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(MonitoringUiState())
    val uiState: StateFlow<MonitoringUiState> = _uiState.asStateFlow()

    private var service: BleForegroundService? = null
    private var isBound = false
    private var liveTickJob: Job? = null

    // VitalsStore — persists historical bucket data for 1h/24h charts
    private val vitalsStore = VitalsStore(application.applicationContext)

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
        val prefs = ctx.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val username = prefs.getString("username", "") ?: ""

        if (username == "000") {
            val mockHealth = MockDataProvider.createHealthData()
            _uiState.update {
                it.copy(
                    isConnected = true,
                    healthData  = mockHealth,
                    currentHR   = mockHealth.heartRate,
                    currentSpO2 = mockHealth.spO2,
                    weeklySteps = MockDataProvider.weeklySteps
                )
            }
            refreshChart()
        }

        val intent = Intent(ctx, BleForegroundService::class.java)
        ctx.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)

        // Tick to refresh chart buckets every second
        startLiveTick()
    }

    // ── Public actions ────────────────────────────────────────────────────

    fun selectTab(tab: MetricTab) {
        _uiState.update { it.copy(activeTab = tab) }
        refreshChart()
    }

    fun selectTimeRange(range: TimeRange) {
        _uiState.update { it.copy(timeRange = range) }
        refreshChart()
    }

    fun resetForUser(username: String) {
        if (username == "000") {
            val mockHealth = MockDataProvider.createHealthData()
            _uiState.value = MonitoringUiState(
                isConnected = true,
                healthData  = mockHealth,
                currentHR   = mockHealth.heartRate,
                currentSpO2 = mockHealth.spO2,
                weeklySteps = MockDataProvider.weeklySteps
            )
            refreshChart()
        } else {
            _uiState.value = MonitoringUiState()
            refreshChart()
        }
    }

    fun clearVitalsData() {
        vitalsStore.clearAll()
        _uiState.update {
            it.copy(chartData = emptyList(), currentHR = 0, currentSpO2 = 0, healthData = null)
        }
        getApplication<Application>().applicationContext
            .getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE).edit {
                remove("monitoring_hr_live")
                remove("monitoring_spo2_live")
                remove("last_heart_rate")
                remove("last_spo2")
            }
    }

    fun getStats(): Triple<Int, Int, Int> {
        val data = _uiState.value.chartData.filter { it > 0 }
        if (data.isEmpty()) return Triple(0, 0, 0)
        return Triple(data.average().toInt(), data.minOrNull() ?: 0, data.maxOrNull() ?: 0)
    }

    // ── Internal ──────────────────────────────────────────────────────────

    private fun observeBleData() {
        val ble = service?.bleManager ?: return
        val username = getApplication<Application>().applicationContext
            .getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            .getString("username", "") ?: ""
        if (username == "000") return

        // Batch readings → VitalsStore (bucket history for charts)
        viewModelScope.launch {
            ble.vitalsBatch.collect { batch ->
                batch.heartRates.zip(batch.spo2s).forEach { (hr, spo2) ->
                    if (hr > 0 || spo2 > 0) vitalsStore.addReading(hr, spo2)
                }
            }
        }

        // Single reading → update "Current" display IMMEDIATELY, same timing as HomeViewModel.
        // This is the single source of truth for the live current value shown on both screens.
        viewModelScope.launch {
            ble.sensorData.collect { data ->
                if (data.heartRate == 0 && data.spo2 == 0) return@collect
                if (data.heartRate > 0 || data.spo2 > 0) {
                    vitalsStore.addReading(data.heartRate, data.spo2)
                }
                _uiState.update { state ->
                    val hr   = if (data.heartRate > 0) data.heartRate else state.currentHR
                    val spo2 = if (data.spo2      > 0) data.spo2      else state.currentSpO2
                    val newHealth = (state.healthData ?: emptyHealthData()).copy(
                        heartRate       = hr,
                        heartRateStatus = hrStatus(hr),
                        spO2            = spo2,
                        spO2Status      = spo2Status(spo2),
                        lastUpdated     = java.util.Date()
                    )
                    state.copy(currentHR = hr, currentSpO2 = spo2, healthData = newHealth)
                }
            }
        }

        // Connection state
        viewModelScope.launch {
            ble.bleState.collect { state ->
                _uiState.update { it.copy(isConnected = state is BleManager.BleState.Connected) }
            }
        }
    }

    /** Refreshes chart bucket data every second. Current values are NOT updated here. */
    private fun startLiveTick() {
        liveTickJob?.cancel()
        liveTickJob = viewModelScope.launch {
            while (true) {
                delay(1_000)
                val username = getApplication<Application>().applicationContext
                    .getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
                    .getString("username", "") ?: ""
                if (username == "000") continue

                _uiState.update { state ->
                    val updatedChart = when (state.timeRange) {
                        TimeRange.LIVE              -> emptyList()
                        TimeRange.ONE_HOUR          -> vitalsStore.get1hChart(state.activeTab == MetricTab.HEART_RATE)
                        TimeRange.TWENTY_FOUR_HOURS -> vitalsStore.get24hChart(state.activeTab == MetricTab.HEART_RATE)
                    }
                    state.copy(chartData = updatedChart)
                }
            }
        }
    }

    private fun refreshChart() {
        val state = _uiState.value
        val username = getApplication<Application>().applicationContext
            .getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            .getString("username", "") ?: ""

        if (username == "000") {
            if (state.timeRange == TimeRange.LIVE) return
            val points = when (state.timeRange) {
                TimeRange.ONE_HOUR          -> 60
                TimeRange.TWENTY_FOUR_HOURS -> 144
                else                        -> 20
            }
            val data = when (state.activeTab) {
                MetricTab.HEART_RATE -> MockDataProvider.generateChartData(72.0, 3.0, 55.0, 110.0, points)
                MetricTab.SPO2       -> MockDataProvider.generateChartData(97.0, 1.0, 92.0, 100.0, points)
            }
            _uiState.update { it.copy(chartData = data) }
            return
        }

        val newChart = when (state.timeRange) {
            TimeRange.LIVE              -> state.chartData
            TimeRange.ONE_HOUR          -> vitalsStore.get1hChart(state.activeTab == MetricTab.HEART_RATE)
            TimeRange.TWENTY_FOUR_HOURS -> vitalsStore.get24hChart(state.activeTab == MetricTab.HEART_RATE)
        }
        _uiState.update { it.copy(chartData = newChart) }
    }

    private fun emptyHealthData() = HealthData(
        heartRate = 0, heartRateStatus = HealthStatus.NORMAL,
        heartRateHistory = emptyList(), heartRateMin = 0, heartRateMax = 0,
        spO2 = 0, spO2Status = HealthStatus.NORMAL, spO2History = emptyList(),
        stepCount = 0, stepGoal = 10000, lastUpdated = java.util.Date()
    )

    private fun hrStatus(hr: Int) = when {
        hr > 100    -> HealthStatus.HIGH
        hr in 1..59 -> HealthStatus.LOW
        else        -> HealthStatus.NORMAL
    }

    private fun spo2Status(spo2: Int) = when {
        spo2 in 1..94 -> HealthStatus.LOW
        else          -> HealthStatus.NORMAL
    }

    override fun onCleared() {
        super.onCleared()
        liveTickJob?.cancel()
        vitalsStore.saveToPrefs()
        if (isBound) {
            getApplication<Application>().applicationContext.unbindService(serviceConnection)
            isBound = false
        }
    }
}
