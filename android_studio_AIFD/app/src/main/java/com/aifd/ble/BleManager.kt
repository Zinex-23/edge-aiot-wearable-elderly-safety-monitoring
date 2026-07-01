package com.aifd.ble

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.media.MediaPlayer
import android.os.Handler
import androidx.core.content.edit
import android.os.Looper
import android.media.AudioManager
import android.util.Log
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import android.os.Build
import java.util.LinkedList
import java.util.UUID
import kotlin.text.Charsets

/**
 * Real BLE Manager for ESP32-S3 fall detection device.
 *
 * Strategy: Auto-connect to any **bonded** Bluetooth device whose name starts
 * with "ESP32". This avoids unreliable BLE advertising scan, because the user
 * pairs the ESP32 via system Bluetooth settings first, then the app automatically
 * picks it up and subscribes to GATT notifications.
 *
 * ESP32 BLE Protocol:
 * - Service UUID: 4fafc201-1fb5-459e-8fcc-c5c9c331914b
 * - ALERT Characteristic (notify): beb5483e-36e1-4688-b7f5-ea07361b26a8
 *   Format: "ALERT,seq,ts_sec,fall,status_code,fall_prob,non_fall_prob"
 *           "SAFE,seq,ts_sec"  (device button pressed — cancel countdown)
 * - VITALS Characteristic (notify): 7b809f11-63f0-4dca-8e4d-2b4e8384e7c1
 *   Format: "BATCH,seq,hr0|hr1|hr2|hr3|hr4,spo2_0|...|spo2_4,ts0|...|ts4"
 * - CONTROL Characteristic (write): f9b2c417-1d15-4ad4-9b52-b94aa0f76b03
 *   Write "READY" to open data channel; device replies "ACK:READY"
 */
class BleManager(private val context: Context) {

    companion object {
        const val TAG = "BleManager"
        const val ESP32_PREFIX = "ESP32"

        val SERVICE_UUID: UUID = UUID.fromString("4fafc201-1fb5-459e-8fcc-c5c9c331914b")
        val STATUS_CHAR_UUID: UUID = UUID.fromString("beb5483e-36e1-4688-b7f5-ea07361b26a8")
        val VITALS_CHAR_UUID: UUID = UUID.fromString("7b809f11-63f0-4dca-8e4d-2b4e8384e7c1")
        val CONTROL_CHAR_UUID: UUID = UUID.fromString("f9b2c417-1d15-4ad4-9b52-b94aa0f76b03")
        val CCCD_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    }

    // ── State classes ────────────────────────────────────────────────────
    sealed class BleState {
        data object Idle : BleState()
        data object Scanning : BleState()
        data class Connected(val deviceAddress: String, val deviceName: String) : BleState()
        data object Disconnected : BleState()
        data class Error(val message: String) : BleState()
    }

    data class FallStatus(
        val sequence: Int,
        val timestampSec: Long,
        val prediction: String,
        val statusCode: Int,
        val fallProb: Float,
        val nonFallProb: Float
    )

    data class VitalsBatch(
        val sequence: Int,
        val heartRates: List<Int>,
        val spo2s: List<Int>,
        val timestamps: List<Long>
    )

    data class SensorData(
        val heartRate: Int = 0,
        val spo2: Int = 0,
        val timestamp: Long = System.currentTimeMillis()
    )

    /**
     * Live BMI160 peak snapshot (real sensor data).
     * Emitted every ~5s while connected.
     */
    data class BmiSnapshot(
        val sequence: Int,
        val timestampSec: Long,
        val peakAccG: Float,
        val peakGyroDps: Float,
        val active: Boolean,
        val receivedAtMs: Long = System.currentTimeMillis()
    )

    data class ScannedDevice(val name: String, val address: String, val rssi: Int)

    // ── Flows ────────────────────────────────────────────────────────────
    private val _bleState = MutableStateFlow<BleState>(BleState.Idle)
    val bleState = _bleState.asStateFlow()

    private val _sensorData = MutableStateFlow(SensorData())
    val sensorData = _sensorData.asStateFlow()

    private val _vitalsBatch = MutableSharedFlow<VitalsBatch>(replay = 0, extraBufferCapacity = 1)
    val vitalsBatch: SharedFlow<VitalsBatch> = _vitalsBatch.asSharedFlow()

    // Latest BMI160 snapshot — StateFlow so subscribers always see the current value
    private val _bmiSnapshot = MutableStateFlow<BmiSnapshot?>(null)
    val bmiSnapshot = _bmiSnapshot.asStateFlow()

    private val _fallDetected = MutableSharedFlow<FallStatus>(replay = 0, extraBufferCapacity = 1)
    val fallDetected: SharedFlow<FallStatus> = _fallDetected.asSharedFlow()

    // Emitted when device sends SAFE packet (button pressed on device during fall alert)
    private val _safeReceived = MutableSharedFlow<Unit>(replay = 0, extraBufferCapacity = 1)
    val safeReceived: SharedFlow<Unit> = _safeReceived.asSharedFlow()

    private val _nearbyDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    val nearbyDevices = _nearbyDevices.asStateFlow()

    private val _isVibrating = MutableStateFlow(false)
    val isVibrating = _isVibrating.asStateFlow()

    private val _isSoundEnabled = MutableStateFlow(true)
    val isSoundEnabled = _isSoundEnabled.asStateFlow()

    fun setSoundEnabled(enabled: Boolean) {
        _isSoundEnabled.value = enabled
    }
    fun stopAlertSound() {
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
            Log.i(TAG, "Alert sound stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping alert sound: ${e.message}")
        }
    }


    // ── Internal ─────────────────────────────────────────────────────────
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager.adapter
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private var bluetoothGatt: BluetoothGatt? = null
    private val handler = Handler(Looper.getMainLooper())
    private val discoveredDevices = mutableListOf<ScannedDevice>()
    private var mediaPlayer: MediaPlayer? = null
    private var lastScanUpdateTimestamp = 0L

    // Queue for sequential GATT descriptor writes (BLE only supports one at a time)
    private val descriptorWriteQueue = LinkedList<BluetoothGattDescriptor>()
    private var isWritingDescriptor = false

    // Exponential backoff state for reconnection
    private var reconnectAttempts = 0
    private val reconnectRunnable = Runnable {
        if (_bleState.value !is BleState.Connected) {
            Log.i(TAG, "Exponential backoff retry #$reconnectAttempts")
            autoConnectBondedEsp32()
        }
    }

    // The single device the user explicitly chose. Once set, ALL connection attempts
    // (manual + background auto-reconnect) target THIS address only — never a different
    // bonded device. Cleared on disconnect().
    @Volatile private var targetAddress: String? = null

    // Guard against multiple simultaneous GATT connection attempts.
    // BleForegroundService + multiple ViewModels all call autoConnectBondedEsp32() on startup;
    // without this flag, 3 connect() calls arrive at ESP32 within milliseconds → all rejected
    // and the extra GATT clients leak, wedging the Bluetooth stack into permanent error 133.
    @Volatile private var isConnecting = false

    // While the user is actively scanning (pairing screen), background auto-reconnect must
    // stand down. An in-flight direct connectGatt() holds the LE initiator and starves the
    // scanner on Samsung — the device is then never discovered ("can't find device").
    @Volatile private var scanning = false

    // Connection watchdog: a connectGatt() that never reaches STATE_CONNECTED also never
    // fires onConnectionStateChange (e.g. link-layer timeout, BT toggled, stack wedged).
    // Without this, isConnecting would stay true forever and block every future attempt.
    private val CONNECT_TIMEOUT_MS = 12_000L
    private val connectTimeoutRunnable = Runnable {
        if (_bleState.value !is BleState.Connected && isConnecting) {
            Log.w(TAG, "Connect watchdog fired — no callback in ${CONNECT_TIMEOUT_MS / 1000}s, forcing teardown")
            forceCloseGatt()
            isConnecting = false
            _bleState.value = BleState.Disconnected
            retryConnectionAfterDelay()
        }
    }

    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true

    /** Closes the active GATT client cleanly so no half-open client leaks into the BT stack. */
    @SuppressLint("MissingPermission")
    private fun forceCloseGatt() {
        try {
            bluetoothGatt?.disconnect()
            bluetoothGatt?.close()
        } catch (e: Exception) {
            Log.w(TAG, "forceCloseGatt: ${e.message}")
        }
        bluetoothGatt = null
    }

    // =====================================================================
    // 1. AUTO-CONNECT: Find bonded ESP32 and connect GATT automatically
    // =====================================================================

    /**
     * Scans the phone's bonded (paired) devices for any whose name starts with
     * "ESP32". If found, immediately initiates a GATT connection. This is the
     * recommended approach when the user pairs via system Bluetooth settings.
     *
     * @return true if a bonded ESP32 was found and connection was initiated
     */
    @SuppressLint("MissingPermission")
    fun autoConnectBondedEsp32(): Boolean {
        if (_bleState.value is BleState.Connected) {
            Log.d(TAG, "autoConnectBondedEsp32 skipped — already connected")
            return true
        }
        if (isConnecting) {
            Log.d(TAG, "autoConnectBondedEsp32 skipped — already connecting")
            return true
        }
        if (scanning) {
            Log.d(TAG, "autoConnectBondedEsp32 skipped — user is scanning (scanner has radio priority)")
            return false
        }
        // The user-chosen address always wins. Fall back to the persisted MAC, then a name match.
        val savedMac = targetAddress ?: context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            .getString("device_mac", null)

        // Priority 1: the exact device the user selected / last connected to.
        if (savedMac != null) {
            try {
                val device = bluetoothAdapter?.getRemoteDevice(savedMac)
                if (device != null) {
                    Log.i(TAG, "Auto-connecting to target ${device.address}…")
                    connectGatt(device)
                    return true
                }
            } catch (e: Exception) {
                Log.w(TAG, "getRemoteDevice($savedMac) failed: ${e.message}")
            }
        }

        // Priority 2: no target yet — match the first bonded ESP32/S3 by name.
        val bonded = bluetoothAdapter?.bondedDevices ?: return false
        val esp32 = bonded.firstOrNull { device ->
            val n = device.name ?: return@firstOrNull false
            n.startsWith("ESP32", ignoreCase = true) || n.startsWith("S3", ignoreCase = true)
        }
        if (esp32 != null) {
            Log.i(TAG, "Auto-connecting to bonded ${esp32.name} (${esp32.address})…")
            connectGatt(esp32)
            return true
        }
        Log.i(TAG, "No target and no bonded ESP32 found in ${bonded.size} bonded devices")
        return false
    }

    // =====================================================================
    // 2. MANUAL SCAN: For DevicePairingScreen
    // =====================================================================

    private fun isLocationEnabled(): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val lm = context.getSystemService(Context.LOCATION_SERVICE) as? android.location.LocationManager
            return lm?.isLocationEnabled ?: false
        } else {
            @Suppress("DEPRECATION")
            val mode = android.provider.Settings.Secure.getInt(
                context.contentResolver,
                android.provider.Settings.Secure.LOCATION_MODE,
                android.provider.Settings.Secure.LOCATION_MODE_OFF
            )
            return mode != android.provider.Settings.Secure.LOCATION_MODE_OFF
        }
    }

    @SuppressLint("MissingPermission")
    fun startScan() {
        // Explicitly stop any previous scan to avoid SCAN_FAILED_ALREADY_STARTED (Error 1)
        try { bluetoothLeScanner?.stopScan(leScanCallback) } catch (_: Exception) {}

        if (_bleState.value is BleState.Scanning) return

        Log.i(TAG, "startScan() called")

        // Scanner gets radio priority: cancel any pending/in-flight background connect so the
        // LE initiator doesn't starve discovery (root cause of "device not found" on Samsung).
        scanning = true
        handler.removeCallbacks(reconnectRunnable)
        handler.removeCallbacks(connectTimeoutRunnable)
        if (isConnecting) {
            isConnecting = false
            forceCloseGatt()
        }

        if (!isLocationEnabled()) {
            Log.e(TAG, "Location is OFF. Scanning will be blocked by system!")
            _bleState.value = BleState.Error("Vui lòng bật Vị trí (GPS) để tìm thiết bị")
            // Still proceed to show bonded devices at least
        } else {
            _bleState.value = BleState.Scanning
        }

        discoveredDevices.clear()

        // Show ALL bonded devices immediately — user already explicitly paired them,
        // so no name filter here. device.name can be null when OS hasn't cached it yet.
        try {
            val bonded = bluetoothAdapter?.bondedDevices ?: emptySet()
            val savedMac = context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
                .getString("device_mac", null)
            synchronized(discoveredDevices) {
                bonded.forEach { device ->
                    val name = try {
                        device.name?.takeIf { it.isNotBlank() } ?: "ESP32 (${device.address.takeLast(5)})"
                    } catch (_: Exception) {
                        "ESP32 (${device.address.takeLast(5)})"
                    }
                    // Mark previously-used device to help user identify it
                    val displayName = if (device.address.equals(savedMac, ignoreCase = true))
                        "$name ★" else name
                    discoveredDevices.add(ScannedDevice(displayName, device.address, -50))
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting bonded devices: ${e.message}")
        }
        _nearbyDevices.value = discoveredDevices.toList()

        if (!isLocationEnabled()) return

        // Active BLE scan — filtered by Service UUID so only ESP32 advertising our service
        // is discovered; reduces battery drain and avoids irrelevant devices.
        try {
            bluetoothLeScanner = bluetoothAdapter?.bluetoothLeScanner
            if (bluetoothLeScanner == null) {
                Log.e(TAG, "BluetoothLeScanner is null (BT might be off)")
                _bleState.value = BleState.Error("Bluetooth đang tắt")
                return
            }

            val filters = listOf(
                ScanFilter.Builder()
                    .setServiceUuid(android.os.ParcelUuid(SERVICE_UUID))
                    .build()
            )
            val settings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build()

            Log.i(TAG, "Starting active BLE scan filtered by service UUID")
            bluetoothLeScanner?.startScan(filters, settings, leScanCallback)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting scan: ${e.message}")
            // Fallback: unfiltered scan if service-UUID filter fails (some Android versions reject it)
            try {
                val settings = ScanSettings.Builder()
                    .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                    .build()
                bluetoothLeScanner?.startScan(null, settings, leScanCallback)
                Log.w(TAG, "Falling back to unfiltered scan")
            } catch (e2: Exception) {
                _bleState.value = BleState.Error("Lỗi scan: ${e2.message}")
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun stopScan() {
        Log.i(TAG, "stopScan() called")
        scanning = false
        try { bluetoothLeScanner?.stopScan(leScanCallback) } catch (_: Exception) {}
        if (_bleState.value is BleState.Scanning) _bleState.value = BleState.Idle
    }

    @SuppressLint("MissingPermission")
    private val leScanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val address = result.device.address
            val name = try { 
                result.device.name ?: result.scanRecord?.deviceName ?: "Unknown"
            } catch (_: Exception) {
                result.scanRecord?.deviceName ?: "Unknown"
            }
            
            val lowercaseName = name.lowercase()
            // Strict filter for active scan: must contain s3 or esp
            if (!lowercaseName.contains("s3") && !lowercaseName.contains("esp")) return

            synchronized(discoveredDevices) {
                if (discoveredDevices.none { it.address == address }) {
                    discoveredDevices.add(ScannedDevice(name, address, result.rssi))
                    
                    // Throttle updates to avoid overloading the UI thread (preventing "ACTION_HOVER_EXIT" crashes)
                    val now = System.currentTimeMillis()
                    if (now - lastScanUpdateTimestamp > 500L || discoveredDevices.size == 1) {
                        _nearbyDevices.value = discoveredDevices.toList()
                        lastScanUpdateTimestamp = now
                    }
                }
            }
        }
        override fun onScanFailed(errorCode: Int) {
            _bleState.value = BleState.Error("Scan failed: $errorCode")
        }
    }

    // =====================================================================
    // 3. GATT CONNECTION
    // =====================================================================

    /**
     * Explicit user request to connect to ONE specific device (tapped in the list).
     * This becomes the single connection target: every pending attempt to any other
     * device is torn down first, and all future auto-reconnects target this address only.
     */
    @SuppressLint("MissingPermission")
    fun connect(address: String) {
        if (_bleState.value is BleState.Connected
            && (_bleState.value as BleState.Connected).deviceAddress.equals(address, ignoreCase = true)
        ) return

        Log.i(TAG, "connect($address): user-selected — tearing down everything else")

        // 1. This device is now the only target.
        targetAddress = address
        context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            .edit { putString("device_mac", address) }

        // 2. Cancel every pending retry/watchdog and fully close any existing/leaked client.
        handler.removeCallbacks(reconnectRunnable)
        handler.removeCallbacks(connectTimeoutRunnable)
        reconnectAttempts = 0
        isConnecting = false
        stopScan()
        forceCloseGatt()

        // 3. Connect fresh to exactly the tapped device.
        try {
            val device = bluetoothAdapter?.getRemoteDevice(address) ?: run {
                _bleState.value = BleState.Error("Device not found")
                return
            }
            connectGatt(device)
        } catch (e: Exception) {
            Log.e(TAG, "Exception in connect: ${e.message}")
            _bleState.value = BleState.Error("Connection failed: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    private fun connectGatt(device: BluetoothDevice) {
        isConnecting = true
        // Arm the watchdog: if no STATE_CONNECTED/DISCONNECTED callback arrives in time, self-heal.
        handler.removeCallbacks(connectTimeoutRunnable)
        handler.postDelayed(connectTimeoutRunnable, CONNECT_TIMEOUT_MS)
        try {
            // Reset state before connecting — always start from a clean, single GATT client.
            handler.post {
                _bleState.value = BleState.Idle
                forceCloseGatt()

                handler.postDelayed({
                    bluetoothGatt = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                        device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
                    } else {
                        device.connectGatt(context, false, gattCallback)
                    }
                }, 200) // Small delay to let stack settle
            }
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException in connectGatt: ${e.message}")
            _bleState.value = BleState.Error("Thiếu quyền Bluetooth")
            retryConnectionAfterDelay()
        } catch (e: Exception) {
            Log.e(TAG, "Exception in connectGatt: ${e.message}")
            _bleState.value = BleState.Error("Lỗi kết nối: ${e.message}")
            retryConnectionAfterDelay()
        }
    }

    @SuppressLint("MissingPermission")
    fun disconnect() {
        // User-initiated disconnect: stop all retries and forget the target.
        targetAddress = null
        isConnecting = false
        reconnectAttempts = 0
        handler.removeCallbacks(reconnectRunnable)
        handler.removeCallbacks(connectTimeoutRunnable)
        forceCloseGatt()
        _bleState.value = BleState.Disconnected
        _nearbyDevices.value = emptyList()
    }

    private fun refreshGattCache(gatt: BluetoothGatt): Boolean {
        return try {
            val method = gatt.javaClass.getMethod("refresh")
            val result = method.invoke(gatt) as? Boolean ?: false
            Log.i(TAG, "GATT cache refresh: $result")
            result
        } catch (e: Exception) {
            Log.w(TAG, "GATT cache refresh not available: ${e.message}")
            false
        }
    }

    private fun retryConnectionAfterDelay() {
        handler.removeCallbacks(reconnectRunnable)
        val delayMs = when (reconnectAttempts) {
            0 -> 2_000L
            1 -> 5_000L
            2 -> 10_000L
            3 -> 20_000L
            else -> 60_000L
        }
        Log.i(TAG, "Scheduling reconnect attempt ${reconnectAttempts + 1} in ${delayMs / 1000}s")
        reconnectAttempts++
        handler.postDelayed(reconnectRunnable, delayMs)
    }

    private fun resetReconnectBackoff() {
        reconnectAttempts = 0
        isConnecting = false
        handler.removeCallbacks(reconnectRunnable)
        handler.removeCallbacks(connectTimeoutRunnable)
    }

    /** Called by BleForegroundService when Bluetooth is turned off or back on. */
    fun resetConnectingState() {
        isConnecting = false
        forceCloseGatt()
        handler.removeCallbacks(reconnectRunnable)
        handler.removeCallbacks(connectTimeoutRunnable)
    }

    @SuppressLint("MissingPermission")
    private val gattCallback = object : BluetoothGattCallback() {

        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            Log.i(TAG, "onConnectionStateChange status=$status newState=$newState device=${gatt.device.address}")
            // A real callback arrived — the watchdog is no longer needed.
            handler.removeCallbacks(connectTimeoutRunnable)
            handler.post {
                when (newState) {
                    BluetoothProfile.STATE_CONNECTED -> {
                        isConnecting = false
                        if (status == BluetoothGatt.GATT_SUCCESS) {
                            // Clear Android GATT cache so fresh service discovery finds new
                            // characteristics added after the last bonding (e.g. new VITALS char)
                            refreshGattCache(gatt)
                            Log.i(TAG, "GATT connected, requesting MTU 512…")
                            val mtuRequested = gatt.requestMtu(512)
                            if (!mtuRequested) {
                                Log.w(TAG, "MTU request failed, falling back to discoverServices")
                                gatt.discoverServices()
                            }
                        } else {
                            // Connection failed before fully established — full cleanup
                            Log.e(TAG, "Connection attempt failed with status $status")
                            bluetoothGatt = null
                            gatt.disconnect()
                            gatt.close()
                            _bleState.value = BleState.Error("Lỗi GATT: $status")
                            retryConnectionAfterDelay()
                        }
                    }
                    BluetoothProfile.STATE_DISCONNECTED -> {
                        isConnecting = false
                        // Always fully close the client so it never leaks into the BT stack
                        // (leaked clients are the #1 cause of permanent GATT error 133).
                        if (status == 133) {
                            Log.w(TAG, "GATT Error 133 — full teardown before retry")
                            // If the ESP32 was reflashed without bonding, the old bond keys will cause
                            // immediate connection rejection (Error 133). We must unpair it to recover.
                            try {
                                val currentDevice = gatt.device
                                if (currentDevice != null && currentDevice.bondState != BluetoothDevice.BOND_NONE) {
                                    val m = currentDevice.javaClass.getMethod("removeBond")
                                    val result = m.invoke(currentDevice) as? Boolean ?: false
                                    Log.i(TAG, "Unpaired device to clear broken bond state (result: $result)")
                                }
                            } catch (e: Exception) {
                                Log.e(TAG, "Failed to remove bond: ${e.message}")
                            }
                        } else {
                            Log.i(TAG, "GATT disconnected (status=$status)")
                        }
                        try { gatt.disconnect() } catch (_: Exception) {}
                        try { gatt.close() } catch (_: Exception) {}
                        bluetoothGatt = null
                        _bleState.value = BleState.Disconnected
                        retryConnectionAfterDelay()
                    }
                }
            }
        }

        @SuppressLint("MissingPermission")
        override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
            super.onMtuChanged(gatt, mtu, status)
            Log.i(TAG, "onMtuChanged to $mtu status=$status, discovering services now…")
            handler.post {
                gatt.discoverServices()
            }
        }

        @SuppressLint("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                Log.e(TAG, "Service discovery failed: $status")
                _bleState.value = BleState.Error("Lỗi khám phá dịch vụ: $status")
                return
            }

            // Debug: log found services
            gatt.services.forEach { svc ->
                Log.d(TAG, "Found service: ${svc.uuid}")
            }

            val service = gatt.getService(SERVICE_UUID)
            if (service == null) {
                Log.e(TAG, "ESP32 custom service not found!")
                _bleState.value = BleState.Error("ESP32 service not found")
                return
            }

            Log.i(TAG, "Service found! Subscribing to notifications…")

            // Queue notifications sequentially (BLE only supports 1 write at a time)
            descriptorWriteQueue.clear()
            isWritingDescriptor = false
            queueNotification(gatt, service, STATUS_CHAR_UUID)
            queueNotification(gatt, service, VITALS_CHAR_UUID)
            writeNextDescriptor(gatt)

            val deviceName = gatt.device.name ?: "ESP32"
            resetReconnectBackoff()
            _bleState.value = BleState.Connected(gatt.device.address, deviceName)
        }

        @SuppressLint("MissingPermission")
        private fun queueNotification(gatt: BluetoothGatt, service: BluetoothGattService, charUuid: UUID) {
            val characteristic = service.getCharacteristic(charUuid)
            if (characteristic == null) {
                Log.e(TAG, "Characteristic not found: $charUuid")
                return
            }
            gatt.setCharacteristicNotification(characteristic, true)
            val descriptor = characteristic.getDescriptor(CCCD_UUID)
            if (descriptor == null) {
                Log.e(TAG, "CCCD Descriptor not found for characteristic: $charUuid")
                return
            }
            descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            descriptorWriteQueue.add(descriptor)
        }

        @SuppressLint("MissingPermission")
        private fun writeNextDescriptor(gatt: BluetoothGatt) {
            if (descriptorWriteQueue.isEmpty()) {
                isWritingDescriptor = false
                Log.i(TAG, "All notifications subscribed ✓")
                handler.postDelayed({ sendReadyCommand() }, 100) // Small delay to let Android stack breathe
                return
            }
            isWritingDescriptor = true
            val descriptor = descriptorWriteQueue.poll()
            if (descriptor != null) {
                val success = gatt.writeDescriptor(descriptor)
                if (!success) {
                    Log.e(TAG, "writeDescriptor failed to initiate for ${descriptor.characteristic.uuid}! Retrying...")
                    descriptorWriteQueue.addFirst(descriptor)
                    handler.postDelayed({ writeNextDescriptor(gatt) }, 50)
                }
            }
        }

        @SuppressLint("MissingPermission")
        fun sendReadyCommand() {
            val gatt = bluetoothGatt ?: return
            val service = gatt.getService(SERVICE_UUID)
            if (service == null) {
                Log.e(TAG, "Service not found in sendReadyCommand")
                return
            }
            val controlChar = service.getCharacteristic(CONTROL_CHAR_UUID)
            if (controlChar == null) {
                Log.e(TAG, "Control characteristic not found in sendReadyCommand")
                return
            }
            
            controlChar.value = "READY".toByteArray(Charsets.UTF_8)
            val success = gatt.writeCharacteristic(controlChar)
            Log.i(TAG, "Initiated READY command to ESP32: success=$success")
        }

        @SuppressLint("MissingPermission")
        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            Log.d(TAG, "Descriptor written for ${descriptor.characteristic.uuid}, status=$status")
            if (status != BluetoothGatt.GATT_SUCCESS) {
                Log.e(TAG, "Descriptor write failed with status $status! Retrying...")
                descriptorWriteQueue.addFirst(descriptor)
                handler.postDelayed({ writeNextDescriptor(gatt) }, 50)
                return
            }
            writeNextDescriptor(gatt)
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            super.onCharacteristicWrite(gatt, characteristic, status)
            if (characteristic.uuid == CONTROL_CHAR_UUID) {
                Log.i(TAG, "READY command write callback received, status=$status")
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            val data = characteristic.value ?: return
            val payload = String(data, Charsets.UTF_8).trim()
            Log.d(TAG, "Received payload on ${characteristic.uuid}: $payload")

            when (characteristic.uuid) {
                STATUS_CHAR_UUID -> parseAlertPayload(payload)
                VITALS_CHAR_UUID -> parseVitalsPayload(payload)
            }
        }
    }

    // =====================================================================
    // 4. DATA PARSING — Matches ESP32 firmware CSV format
    // =====================================================================

    /** Parses ALERT and SAFE packets from the ALERT characteristic. */
    private fun parseAlertPayload(payload: String) {
        when (BlePacketParser.classify(payload)) {
            BlePacketParser.PacketKind.SAFE -> {
                BlePacketParser.parseSafe(payload) ?: run {
                    Log.w(TAG, "SAFE malformed: $payload"); return
                }
                Log.i(TAG, "SAFE packet received from device — cancelling countdown")
                _safeReceived.tryEmit(Unit)
            }
            BlePacketParser.PacketKind.ALERT -> {
                val raw = BlePacketParser.parseAlert(payload) ?: run {
                    Log.w(TAG, "ALERT malformed: $payload"); return
                }
                // Override device uptime with phone wall-clock seconds for UI consistency
                val fall = raw.copy(timestampSec = System.currentTimeMillis() / 1000)
                Log.d(TAG, "Alert: ${fall.prediction} (${fall.fallProb}) seq=${fall.sequence}")
                if (fall.prediction == "fall") {
                    Log.w(TAG, "⚠️ FALL DETECTED! prob=${fall.fallProb}")
                    _fallDetected.tryEmit(fall)
                    saveFallEvent(fall)
                    vibrateDevice()
                    playAlertSound()
                }
            }
            else -> Log.w(TAG, "Unknown ALERT-char packet: $payload")
        }
    }

    private fun saveFallEvent(fall: FallStatus) {
        val prefs = context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val username = prefs.getString("username", "") ?: ""
        if (username == "000") return // Don't save for demo account

        val eventsJson = prefs.getString("fall_events_json", "[]") ?: "[]"
        // Simple CSV-like storage if we don't have Gson, but let's just use a simple string for now
        // or a pipe-separated list of values.
        val newEvent = "${fall.timestampSec}|${fall.prediction}|${fall.fallProb}"
        val updatedEvents = if (eventsJson == "[]") newEvent else "$eventsJson#$newEvent"
        
        prefs.edit {
            putString("fall_events_json", updatedEvents)
            // Also update last alert info
            putLong("last_fall_timestamp", fall.timestampSec)
        }
    }

    /**
     * VITALS characteristic carries two packet types — dispatched by prefix:
     *   BATCH,...  → HR/SpO2 batch (5 samples, every 25s) — simulated HR/SpO2 today
     *   BMI,...    → live BMI160 peak snapshot (every 5s)  — REAL sensor data
     */
    private fun parseVitalsPayload(payload: String) {
        when (BlePacketParser.classify(payload)) {
            BlePacketParser.PacketKind.BATCH -> {
                val batch = BlePacketParser.parseBatch(payload) ?: run {
                    Log.w(TAG, "BATCH malformed: $payload"); return
                }
                Log.d(TAG, "Vitals batch received, seq=${batch.sequence}, count=${batch.heartRates.size}")
                _vitalsBatch.tryEmit(batch)
                // Update real-time sensor data with the latest VALID reading in this batch
                val latestHR   = batch.heartRates.lastOrNull { it >= 0 } ?: -1
                val latestSPO2 = batch.spo2s.lastOrNull { it >= 0 } ?: -1
                if (latestHR >= 0 || latestSPO2 >= 0) {
                    _sensorData.value = SensorData(
                        heartRate = if (latestHR >= 0) latestHR else 0,
                        spo2      = if (latestSPO2 >= 0) latestSPO2 else 0,
                        timestamp = System.currentTimeMillis()
                    )
                    saveSensorData(latestHR, latestSPO2)
                }
            }
            BlePacketParser.PacketKind.BMI -> {
                val snap = BlePacketParser.parseBmi(payload) ?: run {
                    Log.w(TAG, "BMI malformed: $payload"); return
                }
                Log.d(TAG, "BMI: acc=${snap.peakAccG}g gyro=${snap.peakGyroDps}dps active=${snap.active}")
                _bmiSnapshot.value = snap
            }
            else -> Log.w(TAG, "Unknown VITALS packet: $payload")
        }
    }

    private fun saveSensorData(hr: Int, spo2: Int) {
        val prefs = context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val username = prefs.getString("username", "") ?: ""
        if (username == "000") return // Don't save for demo account

        prefs.edit {
            if (hr >= 0) putInt("last_heart_rate", hr)
            if (spo2 >= 0) putInt("last_spo2", spo2)
            putLong("last_timestamp", System.currentTimeMillis())

            // Update history strings (keep last 24 points)
            if (hr >= 0) {
                val hrHistory = (prefs.getString("hr_history", "") ?: "").split(",").filter { it.isNotEmpty() }
                val newHrHistory = (hrHistory.takeLast(23) + hr.toString()).joinToString(",")
                putString("hr_history", newHrHistory)
            }
            if (spo2 >= 0) {
                val spo2History = (prefs.getString("spo2_history", "") ?: "").split(",").filter { it.isNotEmpty() }
                val newSpo2History = (spo2History.takeLast(23) + spo2.toString()).joinToString(",")
                putString("spo2_history", newSpo2History)
            }
        }
    }

    private fun playAlertSound() {
        if (!_isSoundEnabled.value) {
            Log.i(TAG, "Sound alert is disabled by user")
            return
        }

        try {
            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            
            // 1. SYSTEM LEVEL: Force MAX volume for ALARM stream
            val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
            audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxVolume, 0)

            // 2. PLAYER LEVEL: Clean up and initialize
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
            
            val resId = context.resources.getIdentifier("event_sos", "raw", context.packageName)
            if (resId != 0) {
                mediaPlayer = MediaPlayer()
                
                // 3. CHANNEL LEVEL: Set attributes to bypass DND and Silent modes
                val audioAttributes = android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_ALARM)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
                
                mediaPlayer?.setAudioAttributes(audioAttributes)
                
                // 4. RESOURCE LOADING
                val afd = context.resources.openRawResourceFd(resId)
                mediaPlayer?.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                afd.close()
                
                mediaPlayer?.prepare()
                
                // 5. GAIN LEVEL: Force 100% output on both left and right channels
                mediaPlayer?.setVolume(1f, 1f)
                
                mediaPlayer?.setOnCompletionListener { 
                    it.release() 
                    mediaPlayer = null
                }
                mediaPlayer?.start()
                Log.i(TAG, "Playing emergency alert: event_sos at TRIPLE-MAX volume")
            } else {
                Log.e(TAG, "!!! CRITICAL: Sound file 'event_sos' NOT FOUND in res/raw !!!")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error playing alert sound: ${e.message}")
        }
    }

    private fun vibrateDevice() {
        _isVibrating.value = true
        handler.postDelayed({ _isVibrating.value = false }, 3000)
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE)
                        as? android.os.VibratorManager
                vm?.defaultVibrator?.vibrate(
                    android.os.VibrationEffect.createWaveform(
                        longArrayOf(0, 500, 200, 500, 200, 500), -1
                    )
                )
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE)
                        as? android.os.Vibrator
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator?.vibrate(
                        android.os.VibrationEffect.createWaveform(
                            longArrayOf(0, 500, 200, 500, 200, 500), -1
                        )
                    )
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(longArrayOf(0, 500, 200, 500, 200, 500), -1)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "vibrateDevice error: ${e.message}")
        }
    }
}
