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
    val fallEvents: List<FallEvent> = MockDataProvider.fallEvents,
    val selectedEventId: String? = null,
    val emergencyContacts: List<EmergencyContact> = MockDataProvider.emergencyContacts,
    val notificationSettings: NotificationSettings = NotificationSettings()
)

class AlertViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(AlertUiState())
    val uiState: StateFlow<AlertUiState> = _uiState.asStateFlow()

    private var bleService: BleForegroundService? = null
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
        val intent = Intent(application, BleForegroundService::class.java)
        application.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
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
                if (seconds == 0) {
                    // This will be handled by service calling placeEmergencyCall
                    // but we can update UI state here if needed
                }
            }
        }
    }

    fun triggerFallAlert() {
        // UI can trigger alert too (e.g. panic button), but usually it comes from Service
        // For now, if UI triggers it, we notify the service? 
        // No, the user logic is "ESP32 detects fall".
    }

    fun dismissAsSafe() {
        bleService?.cancelEmergencyCountdown()
        
        val newEvent = FallEvent(
            id = System.currentTimeMillis().toString(),
            timestamp = Date(),
            type = EventType.FALL,
            title = "Fall Detected",
            status = EventStatus.RESOLVED,
            deviceName = "AIFD Wearable Pro",
            userResponse = "I'm Safe"
        )
        _uiState.update {
            it.copy(
                isFallAlertActive = false,
                isCallingHelp = false,
                fallEvents = listOf(newEvent) + it.fallEvents
            )
        }
    }

    fun callForHelp() {
        bleService?.callNow()
        
        _uiState.update { it.copy(isCallingHelp = true) }
        
        val newEvent = FallEvent(
            id = System.currentTimeMillis().toString(),
            timestamp = Date(),
            type = EventType.FALL,
            title = "Manual Emergency Call",
            status = EventStatus.PENDING,
            deviceName = "AIFD Wearable Pro",
            userResponse = "Called for Help"
        )
        _uiState.update {
            it.copy(
                isFallAlertActive = false,
                isCallingHelp = false,
                fallEvents = listOf(newEvent) + it.fallEvents
            )
        }
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

    override fun onCleared() {
        super.onCleared()
        getApplication<Application>().unbindService(serviceConnection)
    }
}
