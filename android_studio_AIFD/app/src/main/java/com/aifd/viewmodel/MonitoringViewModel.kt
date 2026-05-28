package com.aifd.viewmodel

import android.app.Application
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.IBinder
import android.util.Log
import androidx.core.content.edit
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aifd.ble.BleManager
import com.aifd.data.*
import com.aifd.service.BleForegroundService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

enum class MetricTab { HEART_RATE, SPO2 }
enum class TimeRange { LIVE, ONE_HOUR, TWENTY_FOUR_HOURS }

enum class CloudLoadState { IDLE, LOADING, SUCCESS, ERROR }

data class MonitoringUiState(
    val activeTab: MetricTab = MetricTab.HEART_RATE,
    val timeRange: TimeRange = TimeRange.LIVE,
    val chartData: List<Int> = emptyList(),
    val currentHR: Int = 0,
    val currentSpO2: Int = 0,
    val healthData: HealthData? = null,
    val weeklySteps: List<DailySteps> = emptyList(),
    val isConnected: Boolean = false,
    val bmiSnapshot: BleManager.BmiSnapshot? = null,
    val cloudLoadState: CloudLoadState = CloudLoadState.IDLE,
    val cloudError: String = ""
)

class MonitoringViewModel(application: Application) : AndroidViewModel(application) {

    companion object {
        private const val TAG = "MonitoringVM"
        private const val PREFS = "aifd_prefs"
        private const val KEY_CLOUD_1H_HR   = "cloud_1h_hr"
        private const val KEY_CLOUD_1H_SPO2 = "cloud_1h_spo2"
        private const val KEY_CLOUD_24H_HR   = "cloud_24h_hr"
        private const val KEY_CLOUD_24H_SPO2 = "cloud_24h_spo2"
        private const val REFRESH_1H_MS  = 5 * 60_000L    // 5 minutes
        private const val REFRESH_24H_MS = 5 * 60_000L    // 5 minutes
    }

    private val _uiState = MutableStateFlow(MonitoringUiState())
    val uiState: StateFlow<MonitoringUiState> = _uiState.asStateFlow()

    private var service: BleForegroundService? = null
    private var isBound = false
    private var liveTickJob: Job? = null
    private var cloudRefreshJob: Job? = null

    // Local bucket store for LIVE chart
    private val vitalsStore = VitalsStore(application.applicationContext)

    // Cloud cache from SharedPreferences (offline fallback)
    private var cloud1hHr:   List<Int> = emptyList()
    private var cloud1hSpo2: List<Int> = emptyList()
    private var cloud24hHr:  List<Int> = emptyList()
    private var cloud24hSpo2: List<Int> = emptyList()

    // Track connected device MAC and userId
    private var connectedDeviceMac: String = ""
    private var currentUserId: String = ""

    // Timestamps of last cloud fetches
    private var lastFetch1hMs  = 0L
    private var lastFetch24hMs = 0L

    // Vitals anomaly tracking — tránh tạo event spam
    private var lastHrStatus: HealthStatus = HealthStatus.NORMAL
    private var lastSpo2Status: HealthStatus = HealthStatus.NORMAL
    private var lastVitalsEventMs: Long = 0L
    private val VITALS_EVENT_COOLDOWN_MS = 5 * 60_000L  // 5 phút giữa các event vitals

    // Sync failure tracking — chỉ log sau N lần thất bại liên tiếp
    private var syncFailCount = 0
    private val SYNC_FAIL_THRESHOLD = 3

    private val isoFmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).also {
        it.timeZone = TimeZone.getTimeZone("UTC")
    }

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as? BleForegroundService.LocalBinder ?: return
            service = localBinder.getService()
            isBound = true
            Log.i(TAG, "Service bound ✓")
            observeBleData()
        }
        override fun onServiceDisconnected(name: ComponentName?) {
            service = null
            isBound = false
        }
    }

    init {
        val ctx = application.applicationContext
        EventRepository.init(ctx)
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        currentUserId = prefs.getString("username", "") ?: ""

        loadCloudCacheFromPrefs(prefs)

        if (currentUserId == "000") {
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
        } else {
            val lastHR = prefs.getInt("last_heart_rate", 0)
            val lastSpO2 = prefs.getInt("last_spo2", 0)
            if (lastHR > 0 || lastSpO2 > 0) {
                val newHealth = HealthData(
                    heartRate = lastHR,
                    heartRateStatus = hrStatus(lastHR),
                    heartRateHistory = emptyList(),
                    heartRateMin = 0,
                    heartRateMax = 0,
                    spO2 = lastSpO2,
                    spO2Status = spo2Status(lastSpO2),
                    spO2History = emptyList(),
                    stepCount = 0,
                    stepGoal = 10000,
                    lastUpdated = Date(prefs.getLong("last_vital_timestamp", System.currentTimeMillis()))
                )
                _uiState.update {
                    it.copy(healthData = newHealth, currentHR = lastHR, currentSpO2 = lastSpO2)
                }
            }
        }

        val intent = Intent(ctx, BleForegroundService::class.java)
        ctx.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)

        startLiveTick()
        startCloudRefreshLoop()
    }

    // ── Public actions ────────────────────────────────────────────────────────

    fun selectTab(tab: MetricTab) {
        _uiState.update { it.copy(activeTab = tab) }
        refreshChart()
    }

    fun selectTimeRange(range: TimeRange) {
        _uiState.update { it.copy(timeRange = range) }
        refreshChart()
        // Trigger immediate cloud fetch if switching to 1h/24h and cache is stale
        if (range == TimeRange.ONE_HOUR && isStale(lastFetch1hMs, REFRESH_1H_MS)) {
            fetchCloudVitals("1h")
        }
        if (range == TimeRange.TWENTY_FOUR_HOURS && isStale(lastFetch24hMs, REFRESH_24H_MS)) {
            fetchCloudVitals("24h")
        }
    }

    fun forceRefreshCloud() {
        lastFetch1hMs  = 0L
        lastFetch24hMs = 0L
        when (_uiState.value.timeRange) {
            TimeRange.ONE_HOUR          -> fetchCloudVitals("1h")
            TimeRange.TWENTY_FOUR_HOURS -> fetchCloudVitals("24h")
            else -> {}
        }
    }

    fun resetForUser(username: String) {
        currentUserId = username
        lastFetch1hMs  = 0L
        lastFetch24hMs = 0L
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
            val ctx = getApplication<Application>().applicationContext
            val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val lastHR = prefs.getInt("last_heart_rate", 0)
            val lastSpO2 = prefs.getInt("last_spo2", 0)
            
            _uiState.value = if (lastHR > 0 || lastSpO2 > 0) {
                MonitoringUiState(
                    healthData = HealthData(
                        heartRate = lastHR,
                        heartRateStatus = hrStatus(lastHR),
                        heartRateHistory = emptyList(),
                        heartRateMin = 0,
                        heartRateMax = 0,
                        spO2 = lastSpO2,
                        spO2Status = spo2Status(lastSpO2),
                        spO2History = emptyList(),
                        stepCount = 0,
                        stepGoal = 10000,
                        lastUpdated = Date(prefs.getLong("last_vital_timestamp", System.currentTimeMillis()))
                    ),
                    currentHR = lastHR,
                    currentSpO2 = lastSpO2
                )
            } else {
                MonitoringUiState()
            }
            refreshChart()
        }
    }

    fun clearVitalsData() {
        vitalsStore.clearAll()
        cloud1hHr    = emptyList(); cloud1hSpo2  = emptyList()
        cloud24hHr   = emptyList(); cloud24hSpo2 = emptyList()
        lastFetch1hMs = 0L; lastFetch24hMs = 0L
        _uiState.update {
            it.copy(chartData = emptyList(), currentHR = 0, currentSpO2 = 0, healthData = null)
        }
        val prefs = getApplication<Application>().applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.edit {
            remove("monitoring_hr_live"); remove("monitoring_spo2_live")
            remove("last_heart_rate"); remove("last_spo2")
            remove(KEY_CLOUD_1H_HR); remove(KEY_CLOUD_1H_SPO2)
            remove(KEY_CLOUD_24H_HR); remove(KEY_CLOUD_24H_SPO2)
        }
    }

    fun getStats(): Triple<Int, Int, Int> {
        val data = _uiState.value.chartData.filter { it > 0 }
        if (data.isEmpty()) return Triple(0, 0, 0)
        return Triple(data.average().toInt(), data.minOrNull() ?: 0, data.maxOrNull() ?: 0)
    }

    // ── BLE observation ───────────────────────────────────────────────────────

    private fun observeBleData() {
        val ble = service?.bleManager ?: return
        if (currentUserId == "000") return

        // Capture device MAC; create DISCONNECT event when connection drops
        var wasConnected = false
        viewModelScope.launch {
            ble.bleState.collect { state ->
                val isConnected = state is BleManager.BleState.Connected
                _uiState.update { it.copy(isConnected = isConnected) }
                if (isConnected) {
                    connectedDeviceMac = (state as BleManager.BleState.Connected).deviceAddress
                    wasConnected = true
                } else if (wasConnected) {
                    wasConnected = false
                    EventRepository.addEvent(
                        FallEvent(
                            id = System.currentTimeMillis().toString(),
                            timestamp = Date(),
                            type = EventType.DISCONNECT,
                            title = "Mất kết nối thiết bị",
                            status = EventStatus.RESOLVED,
                            deviceName = connectedDeviceMac.ifBlank { "AIFD Wearable" },
                            detail = "BLE connection lost"
                        )
                    )
                }
            }
        }

        // Batch readings → local bucket store + cloud upload
        viewModelScope.launch {
            ble.vitalsBatch.collect { batch ->
                // Dùng thời gian thực nhận batch — timestamp của ESP32 là relative boot time
                val receivedAtIso = isoFmt.format(Date(System.currentTimeMillis()))
                val hrAvg   = batch.heartRates.filter { it > 0 }.average().takeIf { !it.isNaN() }?.toInt()
                val spo2Avg = batch.spo2s.filter { it > 0 }.average().takeIf { !it.isNaN() }?.toInt()
                if (hrAvg != null || spo2Avg != null) {
                    vitalsStore.addReading(hrAvg ?: 0, spo2Avg ?: 0)
                    uploadVitalToCloud(hrAvg, spo2Avg, receivedAtIso)
                }
            }
        }

        // Single reading → update current display + check vitals thresholds
        viewModelScope.launch {
            ble.sensorData.collect { data ->
                if (data.heartRate == 0 && data.spo2 == 0) return@collect
                if (data.heartRate > 0 || data.spo2 > 0) {
                    vitalsStore.addReading(data.heartRate, data.spo2)
                }
                val hr   = if (data.heartRate > 0) data.heartRate else _uiState.value.currentHR
                val spo2 = if (data.spo2 > 0) data.spo2 else _uiState.value.currentSpO2

                // Check threshold transitions (chỉ log khi THAY ĐỔI sang bất thường + cooldown)
                checkVitalsAnomalies(hr, spo2, connectedDeviceMac.ifBlank { "AIFD Wearable" })

                _uiState.update { state ->
                    val newHealth = (state.healthData ?: emptyHealthData()).copy(
                        heartRate       = hr,
                        heartRateStatus = hrStatus(hr),
                        spO2            = spo2,
                        spO2Status      = spo2Status(spo2),
                        lastUpdated     = Date()
                    )
                    state.copy(currentHR = hr, currentSpO2 = spo2, healthData = newHealth)
                }
            }
        }

        // Fall detected → upload to cloud
        viewModelScope.launch {
            ble.fallDetected.collect { fallStatus ->
                uploadFallEventToCloud(
                    type     = "fall_auto",
                    fallProb = fallStatus.fallProb.toDouble(),
                    tsMs     = fallStatus.timestampSec * 1000L
                )
            }
        }

        // BMI snapshot
        viewModelScope.launch {
            ble.bmiSnapshot.collect { snap ->
                if (snap != null) _uiState.update { it.copy(bmiSnapshot = snap) }
            }
        }
    }

    // ── Cloud upload ──────────────────────────────────────────────────────────

    private fun uploadVitalToCloud(hr: Int?, spo2: Int?, tsIso: String) {
        if (currentUserId.isBlank() || currentUserId == "000") {
            Log.d(TAG, "uploadVital skipped: userId='$currentUserId'")
            return
        }
        if (!isNetworkAvailable()) {
            Log.d(TAG, "uploadVital skipped: no network")
            return
        }
        viewModelScope.launch(Dispatchers.IO) {
            val mac = connectedDeviceMac.ifBlank { "unknown" }
            val result = CloudApi.postVital(
                deviceId     = mac,
                userId       = currentUserId,
                heartRate    = hr,
                spo2         = spo2,
                timestampIso = tsIso
            )
            Log.d(TAG, "uploadVital hr=$hr spo2=$spo2 → ok=${result.ok} err=${result.error}")
            if (result.ok) {
                syncFailCount = 0
            } else if (!result.error.contains("network", ignoreCase = true)) {
                // Chỉ đếm lỗi server (không phải lỗi mạng)
                syncFailCount++
                if (syncFailCount >= SYNC_FAIL_THRESHOLD) {
                    syncFailCount = 0
                    EventRepository.addEvent(
                        FallEvent(
                            id = System.currentTimeMillis().toString(),
                            timestamp = Date(),
                            type = EventType.SYNC_FAILED,
                            title = "Không đồng bộ được cloud",
                            status = EventStatus.PENDING,
                            deviceName = mac,
                            detail = "Lỗi upload: ${result.error.take(60)}"
                        )
                    )
                }
            }
        }
    }

    private fun checkVitalsAnomalies(hr: Int, spo2: Int, deviceName: String) {
        val now = System.currentTimeMillis()
        val cooldownOk = (now - lastVitalsEventMs) > VITALS_EVENT_COOLDOWN_MS

        val newHrStatus   = hrStatus(hr)
        val newSpo2Status = spo2Status(spo2)

        // HR transition TO abnormal
        if (cooldownOk && newHrStatus != HealthStatus.NORMAL && newHrStatus != lastHrStatus) {
            val (title, detail) = when (newHrStatus) {
                HealthStatus.HIGH -> "Nhịp tim cao bất thường" to "HR: $hr bpm (ngưỡng > 100)"
                HealthStatus.LOW  -> "Nhịp tim thấp bất thường" to "HR: $hr bpm (ngưỡng < 60)"
                else -> return
            }
            EventRepository.addEvent(
                FallEvent(
                    id = now.toString(),
                    timestamp = Date(now),
                    type = EventType.VITALS,
                    title = title,
                    status = EventStatus.PENDING,
                    deviceName = deviceName,
                    detail = detail
                )
            )
            lastVitalsEventMs = now
        }

        // SpO2 transition TO abnormal
        if (cooldownOk && newSpo2Status != HealthStatus.NORMAL && newSpo2Status != lastSpo2Status) {
            EventRepository.addEvent(
                FallEvent(
                    id = (now + 1).toString(),
                    timestamp = Date(now),
                    type = EventType.VITALS,
                    title = "SpO2 thấp cảnh báo",
                    status = EventStatus.PENDING,
                    deviceName = deviceName,
                    detail = "SpO2: $spo2% (ngưỡng < 95%)"
                )
            )
            lastVitalsEventMs = now
        }

        lastHrStatus   = newHrStatus
        lastSpo2Status = newSpo2Status
    }

    private fun uploadFallEventToCloud(type: String, fallProb: Double?, tsMs: Long) {
        if (currentUserId.isBlank() || currentUserId == "000") return
        viewModelScope.launch(Dispatchers.IO) {
            val mac   = connectedDeviceMac.ifBlank { "unknown" }
            val tsIso = isoFmt.format(Date(tsMs))
            CloudApi.postFallEvent(
                deviceId     = mac,
                userId       = currentUserId,
                type         = type,
                fallProb     = fallProb,
                timestampIso = tsIso
            )
        }
    }

    // ── Cloud fetch ───────────────────────────────────────────────────────────

    private fun startCloudRefreshLoop() {
        cloudRefreshJob?.cancel()
        cloudRefreshJob = viewModelScope.launch {
            while (true) {
                delay(60_000L) // check every minute; actual fetch respects intervals
                val state = _uiState.value
                if (state.timeRange == TimeRange.ONE_HOUR && isStale(lastFetch1hMs, REFRESH_1H_MS)) {
                    fetchCloudVitals("1h")
                }
                if (state.timeRange == TimeRange.TWENTY_FOUR_HOURS && isStale(lastFetch24hMs, REFRESH_24H_MS)) {
                    fetchCloudVitals("24h")
                }
            }
        }
    }

    private fun fetchCloudVitals(range: String) {
        if (currentUserId.isBlank() || currentUserId == "000") return
        if (!isNetworkAvailable()) {
            // Offline: use cache already loaded from prefs
            _uiState.update { it.copy(cloudLoadState = CloudLoadState.IDLE) }
            refreshChart()
            return
        }
        _uiState.update { it.copy(cloudLoadState = CloudLoadState.LOADING) }
        viewModelScope.launch {
            val mac = connectedDeviceMac.ifBlank { "" }
            val items = withContext(Dispatchers.IO) {
                CloudApi.getVitals(userId = currentUserId, deviceId = "", range = range)
            }
            if (items.isEmpty() && range == "1h" && cloud1hHr.isNotEmpty()) {
                // No new data — keep cache, don't overwrite
                _uiState.update { it.copy(cloudLoadState = CloudLoadState.IDLE) }
                return@launch
            }

            // Bucket cloud data by timestamp into chart slots
            val (hrList, spo2List) = if (range == "1h") {
                bucketCloud(items, slotCount = 12, slotMs = 5 * 60_000L)
            } else {
                bucketCloud(items, slotCount = 24, slotMs = 60 * 60_000L)
            }
            val filledHr   = hrList.count   { it > 0 }
            val filledSpO2 = spo2List.count { it > 0 }
            Log.d(TAG, "fetchCloudVitals[$range]: ${items.size} raw → ${hrList.size} buckets " +
                       "(hr filled=$filledHr/${hrList.size}, spo2 filled=$filledSpO2/${spo2List.size})")
            if (items.isNotEmpty()) {
                Log.d(TAG, "  oldest ts=${items.firstOrNull()?.timestamp}, newest ts=${items.lastOrNull()?.timestamp}")
            }

            val prefs = getApplication<Application>().applicationContext
                .getSharedPreferences(PREFS, Context.MODE_PRIVATE)

            if (range == "1h") {
                cloud1hHr   = hrList
                cloud1hSpo2 = spo2List
                lastFetch1hMs = System.currentTimeMillis()
                prefs.edit {
                    putString(KEY_CLOUD_1H_HR,   hrList.joinToString(","))
                    putString(KEY_CLOUD_1H_SPO2, spo2List.joinToString(","))
                }
            } else {
                cloud24hHr   = hrList
                cloud24hSpo2 = spo2List
                lastFetch24hMs = System.currentTimeMillis()
                prefs.edit {
                    putString(KEY_CLOUD_24H_HR,   hrList.joinToString(","))
                    putString(KEY_CLOUD_24H_SPO2, spo2List.joinToString(","))
                }
            }
            _uiState.update { it.copy(cloudLoadState = CloudLoadState.SUCCESS) }
            refreshChart()
        }
    }

    /**
     * Bucket cloud vitals into fixed-size slots aligned to the current time.
     * Returns (hrBuckets, spo2Buckets) where each list has [slotCount] entries.
     * Slot 0 = oldest, slot [slotCount-1] = newest. Empty slots = 0.
     */
    private fun bucketCloud(
        items: List<CloudVital>,
        slotCount: Int,
        slotMs: Long
    ): Pair<List<Int>, List<Int>> {
        val now = System.currentTimeMillis()
        // Anchor newest slot to current bucket boundary
        val currentSlot = (now / slotMs) * slotMs
        val oldestSlot  = currentSlot - (slotCount - 1) * slotMs

        // Accumulators per slot
        val hrSum    = LongArray(slotCount)
        val hrCount  = IntArray(slotCount)
        val spSum    = LongArray(slotCount)
        val spCount  = IntArray(slotCount)

        items.forEach { item ->
            val tsMs = parseIsoToMs(item.timestamp) ?: return@forEach
            if (tsMs < oldestSlot || tsMs > currentSlot + slotMs) return@forEach
            val idx = ((tsMs - oldestSlot) / slotMs).toInt().coerceIn(0, slotCount - 1)
            val hr = item.heartRate
            if (hr != null && hr > 0) {
                hrSum[idx]  = hrSum[idx] + hr
                hrCount[idx] = hrCount[idx] + 1
            }
            val sp = item.spo2
            if (sp != null && sp > 0) {
                spSum[idx]  = spSum[idx] + sp
                spCount[idx] = spCount[idx] + 1
            }
        }

        val hrOut   = List(slotCount) { i -> if (hrCount[i] > 0) (hrSum[i] / hrCount[i]).toInt() else 0 }
        val spOut   = List(slotCount) { i -> if (spCount[i] > 0) (spSum[i] / spCount[i]).toInt() else 0 }
        return hrOut to spOut
    }

    private fun parseIsoToMs(iso: String): Long? {
        if (iso.isBlank()) return null
        return try {
            isoFmt.parse(iso)?.time
        } catch (_: Exception) {
            null
        }
    }

    private fun loadCloudCacheFromPrefs(prefs: android.content.SharedPreferences) {
        cloud1hHr    = parseIntList(prefs.getString(KEY_CLOUD_1H_HR,   null))
        cloud1hSpo2  = parseIntList(prefs.getString(KEY_CLOUD_1H_SPO2, null))
        cloud24hHr   = parseIntList(prefs.getString(KEY_CLOUD_24H_HR,  null))
        cloud24hSpo2 = parseIntList(prefs.getString(KEY_CLOUD_24H_SPO2, null))
    }

    private fun parseIntList(s: String?): List<Int> {
        if (s.isNullOrBlank()) return emptyList()
        return s.split(",").mapNotNull { it.trim().toIntOrNull() }
    }

    private fun isStale(lastMs: Long, intervalMs: Long) =
        System.currentTimeMillis() - lastMs > intervalMs

    // ── Live tick ─────────────────────────────────────────────────────────────

    private fun startLiveTick() {
        liveTickJob?.cancel()
        liveTickJob = viewModelScope.launch {
            while (true) {
                delay(1_000)
                if (currentUserId == "000") continue
                _uiState.update { state ->
                    val isHR = state.activeTab == MetricTab.HEART_RATE
                    // Ưu tiên cloud data; fallback về vitalsStore khi cloud chưa có
                    val updatedChart = when (state.timeRange) {
                        TimeRange.LIVE -> emptyList()
                        TimeRange.ONE_HOUR -> {
                            val cloud = if (isHR) cloud1hHr else cloud1hSpo2
                            cloud.ifEmpty { vitalsStore.get1hChart(isHR) }
                        }
                        TimeRange.TWENTY_FOUR_HOURS -> {
                            val cloud = if (isHR) cloud24hHr else cloud24hSpo2
                            cloud.ifEmpty { vitalsStore.get24hChart(isHR) }
                        }
                    }
                    state.copy(chartData = updatedChart)
                }
            }
        }
    }

    private fun refreshChart() {
        val state  = _uiState.value
        if (currentUserId == "000") {
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

        val isHR = state.activeTab == MetricTab.HEART_RATE
        val newChart: List<Int> = when (state.timeRange) {
            TimeRange.LIVE -> emptyList()
            TimeRange.ONE_HOUR -> {
                val cloud = if (isHR) cloud1hHr else cloud1hSpo2
                cloud.ifEmpty { vitalsStore.get1hChart(isHR) }
            }
            TimeRange.TWENTY_FOUR_HOURS -> {
                val cloud = if (isHR) cloud24hHr else cloud24hSpo2
                cloud.ifEmpty { vitalsStore.get24hChart(isHR) }
            }
        }
        _uiState.update { it.copy(chartData = newChart) }
    }

    // ── Network helper ────────────────────────────────────────────────────────

    private fun isNetworkAvailable(): Boolean {
        val cm = getApplication<Application>().applicationContext
            .getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val cap = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    // ── Health helpers ────────────────────────────────────────────────────────

    private fun emptyHealthData() = HealthData(
        heartRate = 0, heartRateStatus = HealthStatus.NORMAL,
        heartRateHistory = emptyList(), heartRateMin = 0, heartRateMax = 0,
        spO2 = 0, spO2Status = HealthStatus.NORMAL, spO2History = emptyList(),
        stepCount = 0, stepGoal = 10000, lastUpdated = Date()
    )

    private fun hrStatus(hr: Int) = when {
        hr > 100    -> HealthStatus.HIGH
        hr in 1..59 -> HealthStatus.LOW
        else        -> HealthStatus.NORMAL
    }

    private fun spo2Status(spo2: Int) = when {
        spo2 in 1..94 -> HealthStatus.LOW
        else           -> HealthStatus.NORMAL
    }

    override fun onCleared() {
        super.onCleared()
        liveTickJob?.cancel()
        cloudRefreshJob?.cancel()
        vitalsStore.saveToPrefs()
        if (isBound) {
            getApplication<Application>().applicationContext.unbindService(serviceConnection)
            isBound = false
        }
    }
}
