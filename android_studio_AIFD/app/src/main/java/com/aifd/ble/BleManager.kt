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
 * - Status Characteristic (notify): beb5483e-36e1-4688-b7f5-ea07361b26a8
 *   Format: "prediction,status_code,fall_prob,non_fall_prob"
 * - Accel Characteristic (notify): 7b809f11-63f0-4dca-8e4d-2b4e8384e7c1
 *   Format: "ax,ay,az"
 * - Gyro Characteristic (notify): f9b2c417-1d15-4ad4-9b52-b94aa0f76b03
 *   Format: "gx,gy,gz"
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

    data class ScannedDevice(val name: String, val address: String, val rssi: Int)

    // ── Flows ────────────────────────────────────────────────────────────
    private val _bleState = MutableStateFlow<BleState>(BleState.Idle)
    val bleState = _bleState.asStateFlow()

    private val _sensorData = MutableStateFlow(SensorData())
    val sensorData = _sensorData.asStateFlow()

    private val _vitalsBatch = MutableSharedFlow<VitalsBatch>(replay = 0, extraBufferCapacity = 1)
    val vitalsBatch: SharedFlow<VitalsBatch> = _vitalsBatch.asSharedFlow()

    private val _fallDetected = MutableSharedFlow<FallStatus>(replay = 0, extraBufferCapacity = 1)
    val fallDetected: SharedFlow<FallStatus> = _fallDetected.asSharedFlow()

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

    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true

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
        val bonded = bluetoothAdapter?.bondedDevices ?: return false
        val savedMac = context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
            .getString("device_mac", null)

        // Strategy 1: match by name — "ESP32..." or "S3..." (covers both main firmware and test board)
        var esp32 = bonded.firstOrNull { device ->
            val n = device.name ?: return@firstOrNull false
            n.startsWith("ESP32", ignoreCase = true) || n.startsWith("S3", ignoreCase = true)
        }
        // Strategy 2: match by stored MAC address (works when device.name returns null)
        if (esp32 == null && savedMac != null) {
            esp32 = bonded.firstOrNull { it.address.equals(savedMac, ignoreCase = true) }
            if (esp32 != null) Log.i(TAG, "Found device by stored MAC $savedMac (name was null)")
        }

        if (esp32 != null) {
            Log.i(TAG, "Auto-connecting to ${esp32.name ?: "ESP32"} (${esp32.address})…")
            connectGatt(esp32)
            return true
        }
        Log.i(TAG, "No bonded ESP32 found in ${bonded.size} bonded devices (savedMac=$savedMac)")
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

    @SuppressLint("MissingPermission")
    fun connect(address: String) {
        stopScan()
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
        try {
            // Reset state before connecting
            handler.post {
                _bleState.value = BleState.Idle
                bluetoothGatt?.disconnect()
                bluetoothGatt?.close()
                bluetoothGatt = null
                
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
        bluetoothGatt?.disconnect()
        bluetoothGatt?.close()
        bluetoothGatt = null
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
        handler.removeCallbacks(reconnectRunnable)
    }

    @SuppressLint("MissingPermission")
    private val gattCallback = object : BluetoothGattCallback() {

        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            Log.i(TAG, "onConnectionStateChange status=$status newState=$newState device=${gatt.device.address}")
            handler.post {
                when (newState) {
                    BluetoothProfile.STATE_CONNECTED -> {
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
                        if (status == 133) {
                            // GATT_ERROR 133: driver may be wedged — must fully teardown before retry
                            Log.w(TAG, "GATT Error 133 — full teardown before retry")
                            bluetoothGatt = null
                            gatt.disconnect()
                            gatt.close()
                        } else {
                            Log.i(TAG, "GATT disconnected (status=$status)")
                            bluetoothGatt = null
                            gatt.close()
                        }
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
            val characteristic = service.getCharacteristic(charUuid) ?: return
            gatt.setCharacteristicNotification(characteristic, true)
            val descriptor = characteristic.getDescriptor(CCCD_UUID) ?: return
            descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            descriptorWriteQueue.add(descriptor)
        }

        @SuppressLint("MissingPermission")
        private fun writeNextDescriptor(gatt: BluetoothGatt) {
            if (descriptorWriteQueue.isEmpty()) {
                isWritingDescriptor = false
                Log.i(TAG, "All notifications subscribed ✓")
                sendReadyCommand()
                return
            }
            isWritingDescriptor = true
            val descriptor = descriptorWriteQueue.poll()
            if (descriptor != null) {
                gatt.writeDescriptor(descriptor)
            }
        }

        @SuppressLint("MissingPermission")
        fun sendReadyCommand() {
            val gatt = bluetoothGatt ?: return
            val service = gatt.getService(SERVICE_UUID) ?: return
            val controlChar = service.getCharacteristic(CONTROL_CHAR_UUID) ?: return
            
            controlChar.value = "READY".toByteArray(Charsets.UTF_8)
            gatt.writeCharacteristic(controlChar)
            Log.i(TAG, "Sent READY command to ESP32")
        }

        @SuppressLint("MissingPermission")
        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            Log.d(TAG, "Descriptor written for ${descriptor.characteristic.uuid}, status=$status")
            writeNextDescriptor(gatt)
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

    /** "ALERT,seq,ts,fall,status_code,fall_prob,non_fall_prob" */
    private fun parseAlertPayload(payload: String) {
        val parts = payload.split(",")
        if (parts.size != 7 || parts[0] != "ALERT") return
        try {
            val sequence = parts[1].trim().toInt()
            val timestampSec = parts[2].trim().toLong()
            val prediction = parts[3].trim()
            val statusCode = parts[4].trim().toInt()
            val fallProb = parts[5].trim().toFloat()
            val nonFallProb = parts[6].trim().toFloat()

            Log.d(TAG, "Alert: $prediction ($fallProb) seq=$sequence")

            if (prediction == "fall") {
                Log.w(TAG, "⚠️ FALL DETECTED! prob=$fallProb")
                val fall = FallStatus(sequence, timestampSec, prediction, statusCode, fallProb, nonFallProb)
                _fallDetected.tryEmit(fall)
                saveFallEvent(fall)
                
                // Trigger both vibration and sound
                vibrateDevice() 
                playAlertSound()
            }
        } catch (e: Exception) {
            Log.e(TAG, "parseAlertPayload error: ${e.message}")
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

    /** "BATCH,seq,HRs,SPO2s,TSs" where values are pipe-separated */
    private fun parseVitalsPayload(payload: String) {
        val parts = payload.split(",")
        if (parts.size != 5 || parts[0] != "BATCH") return
        try {
            val sequence = parts[1].trim().toInt()
            val hrStrings = parts[2].split("|")
            val spo2Strings = parts[3].split("|")
            val tsStrings = parts[4].split("|")

            val heartRates = hrStrings.map { if (it.trim() == "255") 0 else it.trim().toInt() }
            val spo2s = spo2Strings.map { if (it.trim() == "255") 0 else it.trim().toInt() }
            val timestamps = tsStrings.map { it.trim().toLong() }

            val batch = VitalsBatch(sequence, heartRates, spo2s, timestamps)
            Log.d(TAG, "Vitals batch received, seq=$sequence, count=${heartRates.size}")
            
            _vitalsBatch.tryEmit(batch)
            
            // Update real-time sensor data with the latest sample in the batch
            if (heartRates.isNotEmpty()) {
                val latestHR = heartRates.last()
                val latestSPO2 = spo2s.last()
                if (latestHR > 0 || latestSPO2 > 0) {
                    _sensorData.value = SensorData(
                        heartRate = latestHR,
                        spo2 = latestSPO2,
                        timestamp = System.currentTimeMillis()
                    )
                    saveSensorData(latestHR, latestSPO2)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "parseVitalsPayload error: ${e.message}")
        }
    }

    private fun saveSensorData(hr: Int, spo2: Int) {
        val prefs = context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val username = prefs.getString("username", "") ?: ""
        if (username == "000") return // Don't save for demo account

        prefs.edit {
            if (hr > 0) putInt("last_heart_rate", hr)
            if (spo2 > 0) putInt("last_spo2", spo2)
            putLong("last_timestamp", System.currentTimeMillis())
            
            // Update history strings (keep last 24 points)
            if (hr > 0) {
                val hrHistory = (prefs.getString("hr_history", "") ?: "").split(",").filter { it.isNotEmpty() }
                val newHrHistory = (hrHistory.takeLast(23) + hr.toString()).joinToString(",")
                putString("hr_history", newHrHistory)
            }
            if (spo2 > 0) {
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
        // Assume there is a vibration logic already or we can add it here
        // If there's an existing vibrate() function, we use it.
        _isVibrating.value = true
        handler.postDelayed({ _isVibrating.value = false }, 3000)
    }
}
