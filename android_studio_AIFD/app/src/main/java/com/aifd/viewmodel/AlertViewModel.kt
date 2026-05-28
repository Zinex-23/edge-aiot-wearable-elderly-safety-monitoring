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
import com.aifd.data.*
import com.aifd.service.BleForegroundService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.Date

data class AlertUiState(
    val isFallAlertActive: Boolean = false,
    val countdown: Int = 15,
    val isCallingHelp: Boolean = false,
    val fallEvents: List<FallEvent> = emptyList(),
    val selectedEventId: String? = null,
    val emergencyContacts: List<EmergencyContact> = MockDataProvider.emergencyContacts,
    val notificationSettings: NotificationSettings = NotificationSettings()
)

class AlertViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(AlertUiState())
    val uiState: StateFlow<AlertUiState> = _uiState.asStateFlow()

    private var bleService: BleForegroundService? = null
    private var connectedDeviceName = "AIFD Wearable"

    var currentUserId = ""
    var currentUserRole: UserRole? = null

    private var cloudRefreshJob: kotlinx.coroutines.Job? = null

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, service: IBinder?) {
            val binder = service as BleForegroundService.LocalBinder
            bleService = binder.getService()
            observeServiceState()
        }
        override fun onServiceDisconnected(name: ComponentName?) {
            bleService = null
        }
    }

    init {
        EventRepository.init(application)
        // Load events from repository and keep in sync
        viewModelScope.launch {
            EventRepository.events.collect { events ->
                _uiState.update { it.copy(fallEvents = events) }
            }
        }
        val intent = Intent(application, BleForegroundService::class.java)
        application.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
        
        startCloudRefreshLoop()
    }

    private fun observeServiceState() {
        val service = bleService ?: return

        viewModelScope.launch {
            service.isFallAlertActive.collect { active ->
                _uiState.update { it.copy(isFallAlertActive = active) }
            }
        }

        viewModelScope.launch {
            service.countdownSeconds.collect { seconds ->
                _uiState.update { it.copy(countdown = seconds) }
            }
        }

        // Lấy tên thiết bị đang kết nối để ghi vào event
        viewModelScope.launch {
            service.bleManager.bleState.collect { state ->
                if (state is com.aifd.ble.BleManager.BleState.Connected) {
                    connectedDeviceName = state.deviceName
                }
            }
        }

        // SAFE signal — ESP32 bấm nút hoặc xác nhận an toàn
        viewModelScope.launch {
            service.bleManager.safeReceived.collect {
                Log.i("AlertVM", "SAFE received → logging Safe event")
                EventRepository.addEvent(
                    FallEvent(
                        id = System.currentTimeMillis().toString(),
                        timestamp = Date(),
                        type = EventType.SAFE,
                        title = "Xác nhận an toàn",
                        status = EventStatus.RESOLVED,
                        deviceName = connectedDeviceName,
                        detail = "Thiết bị xác nhận không có té ngã"
                    )
                )
            }
        }
    }

    fun triggerFallAlert() {
        bleService?.triggerManualAlert()
    }

    fun dismissAsSafe() {
        bleService?.cancelEmergencyCountdown()
        EventRepository.addEvent(
            FallEvent(
                id = System.currentTimeMillis().toString(),
                timestamp = Date(),
                type = EventType.FALL,
                title = "Phát hiện té ngã",
                status = EventStatus.RESOLVED,
                deviceName = connectedDeviceName,
                userResponse = "Tôi ổn"
            )
        )
        _uiState.update { it.copy(isFallAlertActive = false, isCallingHelp = false) }
    }

    fun callForHelp() {
        bleService?.callNow()
        _uiState.update { it.copy(isCallingHelp = true) }
        EventRepository.addEvent(
            FallEvent(
                id = System.currentTimeMillis().toString(),
                timestamp = Date(),
                type = EventType.FALL,
                title = "Gọi cấp cứu thủ công",
                status = EventStatus.PENDING,
                deviceName = connectedDeviceName,
                userResponse = "Đã gọi cấp cứu"
            )
        )
        _uiState.update { it.copy(isFallAlertActive = false, isCallingHelp = false) }
    }

    fun selectEvent(id: String?) {
        _uiState.update { it.copy(selectedEventId = id) }
    }

    fun getSelectedEvent(): FallEvent? {
        val state = _uiState.value
        return state.fallEvents.find { it.id == state.selectedEventId }
    }

    fun updateNotificationSettings(settings: NotificationSettings) {
        _uiState.update { it.copy(notificationSettings = settings) }
    }

    fun fetchCloudEventsNow() {
        if (currentUserId.isBlank() || currentUserId == "000") return
        if (currentUserRole != UserRole.CAREGIVER) return

        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            val cloudEvents = CloudApi.getFallEvents(currentUserId)
            if (cloudEvents.isNotEmpty()) {
                val isoFmt = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", java.util.Locale.US).apply {
                    timeZone = java.util.TimeZone.getTimeZone("UTC")
                }
                cloudEvents.forEach { cEvent ->
                    val parsedDate = try {
                        isoFmt.parse(cEvent.timestamp) ?: Date()
                    } catch (e: Exception) {
                        Date()
                    }
                    // Bỏ qua nếu thông báo cũ hơn thời điểm đã xóa
                    if (parsedDate.time <= EventRepository.lastClearedMs) {
                        return@forEach
                    }

                    val eventType = try {
                        EventType.valueOf(cEvent.type)
                    } catch (e: Exception) {
                        EventType.FALL
                    }
                    val status = if (cEvent.resolved) EventStatus.RESOLVED else EventStatus.PENDING
                    val fallEvent = FallEvent(
                        id = cEvent.id, // Using server ID
                        timestamp = parsedDate,
                        type = eventType,
                        title = if (eventType == EventType.VITALS) "Cảnh báo sinh hiệu" else "Phát hiện té ngã",
                        status = status,
                        deviceName = cEvent.deviceId,
                        detail = if (cEvent.fallProb != null) "Xác suất: ${(cEvent.fallProb * 100).toInt()}%" else "Cảnh báo bất thường"
                    )
                    // Add to repository
                    val repoEvents = EventRepository.events.value
                    if (repoEvents.none { it.id == fallEvent.id }) {
                        EventRepository.addEvent(fallEvent)
                    } else {
                        // If it exists but status changed, we should update it
                        val existing = repoEvents.find { it.id == fallEvent.id }
                        if (existing != null && existing.status != fallEvent.status) {
                            EventRepository.updateEvent(fallEvent)
                        }
                    }
                }
            }
        }
    }

    private fun startCloudRefreshLoop() {
        cloudRefreshJob?.cancel()
        cloudRefreshJob = viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            while (true) {
                kotlinx.coroutines.delay(5_000L) // Poll every 5 seconds
                fetchCloudEventsNow()
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        cloudRefreshJob?.cancel()
        getApplication<Application>().unbindService(serviceConnection)
    }
}
