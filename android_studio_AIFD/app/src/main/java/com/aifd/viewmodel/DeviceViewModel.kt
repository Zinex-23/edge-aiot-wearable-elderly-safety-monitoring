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

data class DeviceUiState(
    val device: DeviceInfo? = null,
    val nearbyDevices: List<NearbyDevice> = emptyList(),
    val isScanning: Boolean = false,
    val connectingDeviceId: String? = null,
    val connectionProgress: Int = 0,
    val errorMessage: String? = null
)

/**
 * DeviceViewModel — Binds to BleForegroundService to access the BleManager.
 * All BLE logic (connect, scan, fall detection) lives in the Service.
 * This ViewModel is a bridge between the Service and the UI.
 */
class DeviceViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow(DeviceUiState())
    val uiState: StateFlow<DeviceUiState> = _uiState.asStateFlow()

    // Nullable until service is bound
    var service: BleForegroundService? = null
        private set

    // Expose BleManager via service binding (or null if not bound yet)
    val bleManager: BleManager?
        get() = service?.bleManager

    private var isBound = false

    private val serviceConnection = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName?, binder: IBinder?) {
            val localBinder = binder as? BleForegroundService.LocalBinder ?: return
            service = localBinder.getService()
            isBound = true
            Log.i("DeviceVM", "Service bound ✓")
            observeServiceState()
            
            // If a scan was requested while the service was still binding, start it now
            if (pendingScan) {
                Log.i("DeviceVM", "Triggering pending scan...")
                startScan()
            }
        }

        override fun onServiceDisconnected(name: ComponentName?) {
            service = null
            isBound = false
            Log.w("DeviceVM", "Service unbound")
        }
    }

    init {
        // Load saved device for demo purposes
        val ctx = application.applicationContext
        val prefs = ctx.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val savedName = prefs.getString("device_name", null)
        val savedMac = prefs.getString("device_mac", null)
        
        if (savedName != null && savedMac != null) {
            val initialStatus = if (MockDataProvider.DEMO_MODE) ConnectionStatus.CONNECTED else ConnectionStatus.DISCONNECTED
            _uiState.update {
                it.copy(
                    device = DeviceInfo(
                        id = savedMac,
                        name = savedName,
                        battery = if (MockDataProvider.DEMO_MODE) 85 else 0,
                        signalStrength = if (MockDataProvider.DEMO_MODE) -55 else 0,
                        connectionStatus = initialStatus
                    )
                )
            }
        }

        // Start + bind the service
        BleForegroundService.start(ctx)
        val intent = Intent(ctx, BleForegroundService::class.java)
        ctx.bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)
    }

    private fun observeServiceState() {
        val svc = service ?: return

        // Observe BLE state
        viewModelScope.launch {
            svc.bleManager.bleState.collect { state ->
                val isDemo = MockDataProvider.DEMO_MODE
                
                when (state) {
                    is BleManager.BleState.Connected -> {
                        val newDevice = DeviceInfo(
                            id = state.deviceAddress,
                            name = state.deviceName,
                            battery = 100,
                            signalStrength = -60,
                            connectionStatus = ConnectionStatus.CONNECTED
                        )
                        _uiState.update {
                            it.copy(
                                device = newDevice,
                                isScanning = false,
                                connectingDeviceId = null,
                                connectionProgress = 0
                            )
                        }
                    }
                    is BleManager.BleState.Disconnected -> {
                        _uiState.update { s ->
                            // For demo account "000", if we have a saved device, 
                            // don't show it as disconnected unless explicitly requested.
                            val isDemo = MockDataProvider.DEMO_MODE
                            
                            if (isDemo && s.device != null) {
                                s.copy(
                                    device = s.device.copy(connectionStatus = ConnectionStatus.CONNECTED),
                                    isScanning = false,
                                    connectingDeviceId = null
                                )
                            } else {
                                s.device?.let { d ->
                                    s.copy(
                                        device = d.copy(connectionStatus = ConnectionStatus.DISCONNECTED),
                                        isScanning = false,
                                        connectingDeviceId = null
                                    )
                                } ?: s.copy(isScanning = false, connectingDeviceId = null)
                            }
                        }
                    }
                    is BleManager.BleState.Error -> {
                        Log.e("DeviceVM", "BLE Error: ${state.message}")
                        _uiState.update { it.copy(isScanning = false, connectingDeviceId = null, errorMessage = state.message) }
                    }
                    is BleManager.BleState.Scanning -> {
                        _uiState.update { it.copy(isScanning = true) }
                    }
                    else -> {}
                }
            }
        }

        // Observe nearby devices from scan
        viewModelScope.launch {
            svc.bleManager.nearbyDevices.collect { scanned ->
                val nearby = scanned.map { NearbyDevice(id = it.address, name = it.name, signalStrength = it.rssi) }
                _uiState.update { it.copy(nearbyDevices = nearby) }
            }
        }
    }

    // ─── Public API ──────────────────────────────────────────────────────────

    fun autoConnectEsp32() {
        service?.bleManager?.autoConnectBondedEsp32()
    }

    private var pendingScan = false

    fun startScan() {
        Log.i("DeviceVM", "Requesting startScan (service bound: ${service != null})")
        _uiState.update { it.copy(isScanning = true, nearbyDevices = emptyList(), errorMessage = null) }
        
        val svc = service
        if (svc != null) {
            svc.bleManager.startScan()
            pendingScan = false
        } else {
            Log.w("DeviceVM", "Service not bound yet, marking scan as pending...")
            pendingScan = true
        }

        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (_uiState.value.isScanning) {
                service?.bleManager?.stopScan()
                _uiState.update { it.copy(isScanning = false) }
                pendingScan = false
            }
        }, 10_000)
    }

    fun connectToDevice(nearby: NearbyDevice) {
        _uiState.update { it.copy(connectingDeviceId = nearby.id, connectionProgress = 10, errorMessage = null) }
        service?.bleManager?.connect(nearby.id)
    }

    fun renameDevice(newName: String) {
        _uiState.update { state ->
            state.device?.let { d -> state.copy(device = d.copy(name = newName)) } ?: state
        }
    }

    fun disconnectDevice() {
        service?.bleManager?.disconnect()
        _uiState.update { state ->
            state.device?.let { d ->
                state.copy(device = d.copy(connectionStatus = ConnectionStatus.DISCONNECTED))
            } ?: state
        }
    }

    fun reconnectDevice() {
        val address = _uiState.value.device?.id ?: return
        _uiState.update { state ->
            state.device?.let { d ->
                state.copy(device = d.copy(connectionStatus = ConnectionStatus.CONNECTING))
            } ?: state
        }
        service?.bleManager?.connect(address)
    }

    /** Cancel the background emergency countdown (user confirmed they are safe). */
    fun cancelEmergencyCountdown() {
        service?.cancelEmergencyCountdown()
    }

    /** Immediately trigger the emergency call from the ViewModel layer. */
    fun callNow() {
        service?.callNow()
    }

    override fun onCleared() {
        super.onCleared()
        try {
            if (isBound) {
                getApplication<Application>().applicationContext.unbindService(serviceConnection)
            }
        } catch (e: Exception) {
            Log.e("DeviceVM", "Error unbinding service: ${e.message}")
        }
    }
}
