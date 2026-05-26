package com.aifd.service

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Binder
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import android.bluetooth.BluetoothAdapter
import androidx.core.app.NotificationCompat
import com.aifd.MainActivity
import com.aifd.R
import com.aifd.ble.BleManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * BleForegroundService — the immortal guardian that keeps the BLE connection alive,
 * detects falls from ESP32, and makes emergency calls even when the screen is locked.
 *
 * Architecture:
 *  - Runs as a Foreground Service: Android cannot kill it due to the persistent notification.
 *  - Owns BleManager: BLE connectivity survives app backgrounding and screen lock.
 *  - On fall detection: WakeLock wakes the screen, broadcasts to UI to show FallAlertScreen,
 *    and starts a 15-second coroutine timer. If the user does not cancel, it places the call.
 *  - UI binds to this service via IBinder to show live connection state.
 */
class BleForegroundService : Service() {

    // ─── Constants ────────────────────────────────────────────────────────────
    // ─── Constants ────────────────────────────────────────────────────────────
    companion object {
        const val TAG = "BleForegroundService"
        const val NOTIFICATION_CHANNEL_ID = "aifd_ble_monitoring"
        const val FALL_ALERT_CHANNEL_ID = "aifd_fall_alerts"
        const val NOTIFICATION_ID = 1001
        const val FALL_ALERT_NOTIFICATION_ID = 1002

        /** Broadcast sent to UI when ESP32 reports a fall. */
        const val ACTION_FALL_DETECTED = "com.aifd.action.FALL_DETECTED"
        const val ACTION_DISMISS_SAFE = "com.aifd.action.DISMISS_SAFE"
        const val ACTION_CALL_HELP = "com.aifd.action.CALL_HELP"
        
        /** Broadcast sent to UI to update connection state label. */
        const val ACTION_CONNECTION_STATE = "com.aifd.action.CONNECTION_STATE"
        const val EXTRA_IS_CONNECTED = "is_connected"
        const val EXTRA_DEVICE_NAME = "device_name"

        const val WAKELOCK_TIMEOUT_MS = 60_000L // 60s max screen wake
        const val COUNTDOWN_DURATION_MS = 15_000L // 15s before auto-call
        const val DISCONNECT_NOTIFICATION_ID = 1003

        /** Convenience to start the service from any context. */
        fun start(context: Context) {
            val intent = Intent(context, BleForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        /** Convenience to stop the service from any context. */
        fun stop(context: Context) {
            val intent = Intent(context, BleForegroundService::class.java)
            context.stopService(intent)
        }
    }

    // ─── Service state ────────────────────────────────────────────────────────
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var emergencyCountdownJob: Job? = null
    private var autoReconnectJob: Job? = null

    private val bluetoothReceiver = object : android.content.BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == android.bluetooth.BluetoothAdapter.ACTION_STATE_CHANGED) {
                val state = intent.getIntExtra(android.bluetooth.BluetoothAdapter.EXTRA_STATE, android.bluetooth.BluetoothAdapter.ERROR)
                if (state == android.bluetooth.BluetoothAdapter.STATE_ON) {
                    Log.i(TAG, "Bluetooth turned ON, re-triggering auto-connect…")
                    bleManager.autoConnectBondedEsp32()
                }
            }
        }
    }

    private val _countdownSeconds = MutableStateFlow(15)
    val countdownSeconds: StateFlow<Int> = _countdownSeconds.asStateFlow()

    private val _isFallAlertActive = MutableStateFlow(false)
    val isFallAlertActive: StateFlow<Boolean> = _isFallAlertActive.asStateFlow()

    // BleManager owned by the service — survives UI lifecycle
    lateinit var bleManager: BleManager
        private set

    private var wakeLock: PowerManager.WakeLock? = null
    private var isAppInForeground = false

    fun setAppForeground(inForeground: Boolean) {
        isAppInForeground = inForeground
        if (inForeground && _isFallAlertActive.value) {
            // If we are now in foreground and alert is active, hide the heads-up notification
            dismissFallAlertNotification()
        }
    }
    // ─── Binder for UI binding ───────────────────────────────────────────────
    inner class LocalBinder : Binder() {
        fun getService(): BleForegroundService = this@BleForegroundService
    }

    private val binder = LocalBinder()

    override fun onBind(intent: Intent?): IBinder = binder

    // ─── Lifecycle ────────────────────────────────────────────────────────────
    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Service created")

        bleManager = BleManager(applicationContext)

        createNotificationChannels()
        startForeground(NOTIFICATION_ID, buildNotification(connected = false, deviceName = null))

        // Register for Bluetooth state changes
        registerReceiver(bluetoothReceiver, android.content.IntentFilter(android.bluetooth.BluetoothAdapter.ACTION_STATE_CHANGED))

        // Observe BLE state
        serviceScope.launch {
            var wasConnected = false
            bleManager.bleState.collect { state ->
                when (state) {
                    is BleManager.BleState.Connected -> {
                        wasConnected = true
                        updateNotification(connected = true, deviceName = state.deviceName)
                        broadcastConnectionState(connected = true, deviceName = state.deviceName)
                    }
                    is BleManager.BleState.Disconnected, is BleManager.BleState.Error -> {
                        // Only notify if we were previously connected (avoids alert on first launch)
                        if (wasConnected) {
                            wasConnected = false
                            showDisconnectNotification()
                        }
                        updateNotification(connected = false, deviceName = null)
                        broadcastConnectionState(connected = false, deviceName = null)
                    }
                    else -> {}
                }
            }
        }

        // Observe fall events
        serviceScope.launch {
            bleManager.fallDetected.collect { fallStatus ->
                Log.w(TAG, "⚠️ FALL DETECTED! sequence=${fallStatus.sequence} prob=${fallStatus.fallProb}")
                handleFallDetected()
            }
        }

        // Device button "I'm Safe" — cancel countdown without waiting for user to tap app
        serviceScope.launch {
            bleManager.safeReceived.collect {
                Log.i(TAG, "SAFE received from device — cancelling countdown")
                cancelEmergencyCountdown()
            }
        }

        // Periodic safety-net reconnect (every 60s) — BleManager handles short-term backoff;
        // this catches the case where there is no bonded device yet or after long idle periods.
        autoReconnectJob = serviceScope.launch {
            while (true) {
                delay(60_000)
                if (bleManager.bleState.value !is BleManager.BleState.Connected) {
                    Log.d(TAG, "Periodic connection check: Not connected. Retrying…")
                    bleManager.autoConnectBondedEsp32()
                }
            }
        }

        bleManager.autoConnectBondedEsp32()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_DISMISS_SAFE -> cancelEmergencyCountdown()
            ACTION_CALL_HELP -> callNow()
            else -> {
                if (bleManager.bleState.value !is BleManager.BleState.Connected) {
                    bleManager.autoConnectBondedEsp32()
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        try { unregisterReceiver(bluetoothReceiver) } catch (e: Exception) {}
        emergencyCountdownJob?.cancel()
        autoReconnectJob?.cancel()
        serviceScope.cancel()
        bleManager.disconnect()
        releaseWakeLock()
    }

    // ─── Fall Detection Handler ──────────────────────────────────────────────

    private fun handleFallDetected() {
        if (_isFallAlertActive.value) return // Already handling one
        
        emergencyCountdownJob?.cancel()
        _isFallAlertActive.value = true
        _countdownSeconds.value = 15

        acquireWakeLock()
        showFallAlertNotification()

        // Launch MainActivity with ACTION_FALL_DETECTED
        val intent = Intent(this, MainActivity::class.java).apply {
            action = ACTION_FALL_DETECTED
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("is_fall", true)
        }
        try {
            startActivity(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Could not start MainActivity from background: ${e.message}")
        }

        // Start 15-second countdown
        emergencyCountdownJob = serviceScope.launch {
            for (i in 15 downTo 1) {
                _countdownSeconds.value = i
                // Update notification every second to show countdown
                showFallAlertNotification(i)
                delay(1000)
            }
            // Countdown expired
            Log.w(TAG, "Countdown expired — auto-calling!")
            _isFallAlertActive.value = false
            dismissFallAlertNotification()
            
            // Notify UI to go to Home if it was on alert screen
            sendBroadcast(Intent(ACTION_DISMISS_SAFE).apply { `package` = packageName })
            
            placeEmergencyCall()
        }
    }

    fun cancelEmergencyCountdown() {
        Log.i(TAG, "Emergency countdown cancelled by user")
        emergencyCountdownJob?.cancel()
        emergencyCountdownJob = null
        _isFallAlertActive.value = false
        _countdownSeconds.value = 15
        dismissFallAlertNotification()
        releaseWakeLock()
        bleManager.stopAlertSound()
        
        // Notify UI to go to Home
        sendBroadcast(Intent(ACTION_DISMISS_SAFE).apply { `package` = packageName })
    }

    /** Called when wearer presses the manual emergency button on HomeScreen. */
    fun triggerManualAlert() {
        if (_isFallAlertActive.value) return
        Log.w(TAG, "Manual emergency button pressed — starting countdown")
        handleFallDetected()
    }

    fun callNow() {
        emergencyCountdownJob?.cancel()
        emergencyCountdownJob = null
        _isFallAlertActive.value = false
        bleManager.stopAlertSound()
        dismissFallAlertNotification()
        placeEmergencyCall()
    }

    // ─── Emergency Call ──────────────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    private fun placeEmergencyCall() {
        val prefs = getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)
        val number = prefs.getString("caregiver_phone", "0702341350") ?: "0702341350"
        
        try {
            val callIntent = Intent(Intent.ACTION_CALL).apply {
                data = android.net.Uri.parse("tel:$number")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(callIntent)
        } catch (e: Exception) {
            val dialIntent = Intent(Intent.ACTION_DIAL).apply {
                data = android.net.Uri.parse("tel:$number")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(dialIntent)
        }
    }

    // ─── Wake Lock ───────────────────────────────────────────────────────────

    private fun acquireWakeLock() {
        releaseWakeLock()
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(
            PowerManager.SCREEN_BRIGHT_WAKE_LOCK or
                    PowerManager.ACQUIRE_CAUSES_WAKEUP or
                    PowerManager.ON_AFTER_RELEASE,
            "aifd:FallDetectionWakeLock"
        ).apply { acquire(WAKELOCK_TIMEOUT_MS) }
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    // ─── Notifications ───────────────────────────────────────────────────────

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            
            // Standard monitoring channel
            val monitorChannel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "AIFD Theo dõi an toàn",
                NotificationManager.IMPORTANCE_LOW
            )
            nm.createNotificationChannel(monitorChannel)

            // High-priority fall alert channel
            val alertChannel = NotificationChannel(
                FALL_ALERT_CHANNEL_ID,
                "Cảnh báo ngã khẩn cấp",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Kích hoạt khi phát hiện có người ngã"
                enableLights(true)
                lightColor = android.graphics.Color.RED
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 200, 500, 200, 500)
                setSound(
                    android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_ALARM),
                    Notification.AUDIO_ATTRIBUTES_DEFAULT
                )
            }
            nm.createNotificationChannel(alertChannel)
        }
    }

    private fun buildNotification(connected: Boolean, deviceName: String?): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val title = if (connected) "Đang theo dõi an toàn" else "Chờ kết nối thiết bị..."
        val text = if (connected && deviceName != null) "Thiết bị: $deviceName" else "AIFD chạy nền"

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    private fun showFallAlertNotification(secondsLeft: Int = 15) {
        // If app is already in foreground and showing the full-screen UI, 
        // we don't need the heads-up notification cluttering the top.
        if (isAppInForeground) {
            Log.d(TAG, "App is in foreground, skipping heads-up notification")
            return
        }

        val fullScreenIntent = PendingIntent.getActivity(
            this, 1,
            Intent(this, MainActivity::class.java).apply {
                action = ACTION_FALL_DETECTED
                putExtra("is_fall", true)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val safeIntent = PendingIntent.getService(
            this, 2,
            Intent(this, BleForegroundService::class.java).apply { action = ACTION_DISMISS_SAFE },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val callIntent = PendingIntent.getService(
            this, 3,
            Intent(this, BleForegroundService::class.java).apply { action = ACTION_CALL_HELP },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("⚠️ PHÁT HIỆN NGÃ!")
            .setContentText("Sẽ tự động gọi cứu hộ trong ${secondsLeft}s")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setFullScreenIntent(fullScreenIntent, true)
            .setOngoing(true)
            .setAutoCancel(false)
            .setVibrate(longArrayOf(0, 500, 200, 500))
            .setSound(android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_ALARM))
            .addAction(0, "TÔI AN TOÀN", safeIntent)
            .addAction(0, "GỌI NGAY", callIntent)
            .build()

        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(FALL_ALERT_NOTIFICATION_ID, notification)
    }

    private fun dismissFallAlertNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.cancel(FALL_ALERT_NOTIFICATION_ID)
    }

    private fun showDisconnectNotification() {
        val pendingIntent = PendingIntent.getActivity(
            this, 4,
            Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("Mất kết nối thiết bị")
            .setContentText("Vòng đeo tay đã ngắt kết nối. Kiểm tra lại thiết bị.")
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(DISCONNECT_NOTIFICATION_ID, notification)
    }

    private fun updateNotification(connected: Boolean, deviceName: String?) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(NOTIFICATION_ID, buildNotification(connected, deviceName))
    }

    private fun broadcastConnectionState(connected: Boolean, deviceName: String?) {
        sendBroadcast(Intent(ACTION_CONNECTION_STATE).apply {
            `package` = packageName
            putExtra(EXTRA_IS_CONNECTED, connected)
            putExtra(EXTRA_DEVICE_NAME, deviceName)
        })
    }
}
