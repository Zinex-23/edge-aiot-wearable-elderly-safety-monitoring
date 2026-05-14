package com.aifd

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material.icons.Icons
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.edit
import com.aifd.data.UserProfile
import com.aifd.data.UserRole
import com.aifd.navigation.AppNavigation
import com.aifd.ui.localization.AppLanguage
import com.aifd.ui.localization.ProvideAppStrings
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AppThemeMode

class MainActivity : ComponentActivity() {

    private var _startOnFallAlert = mutableStateOf(false)
    private var bleService: com.aifd.service.BleForegroundService? = null
    private var isBound = false

    private val serviceConnection = object : android.content.ServiceConnection {
        override fun onServiceConnected(name: android.content.ComponentName?, binder: android.os.IBinder?) {
            val localBinder = binder as? com.aifd.service.BleForegroundService.LocalBinder
            bleService = localBinder?.getService()
            isBound = true
            bleService?.setAppForeground(true)
        }

        override fun onServiceDisconnected(name: android.content.ComponentName?) {
            bleService = null
            isBound = false
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        _startOnFallAlert.value = intent.action == com.aifd.service.BleForegroundService.ACTION_FALL_DETECTED
                || intent.getBooleanExtra("is_fall", false)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Ensure activity can show over lock screen for fall alerts
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }

        val prefs = getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE)

        // Always start the foreground BLE service — fall detection is always active
        com.aifd.service.BleForegroundService.start(this)

        // Initial check for fall alert
        _startOnFallAlert.value = intent?.action == com.aifd.service.BleForegroundService.ACTION_FALL_DETECTED
                || intent?.getBooleanExtra("is_fall", false) == true

        // Bind to service to manage foreground state
        val intent = Intent(this, com.aifd.service.BleForegroundService::class.java)
        bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE)

        setContent {
            var startOnFallAlert by _startOnFallAlert
            
            var themeMode by rememberSaveable {
                mutableStateOf(
                    AppThemeMode.valueOf(
                        prefs.getString("theme_mode", AppThemeMode.LIGHT.name) ?: AppThemeMode.LIGHT.name
                    )
                )
            }
            var language by rememberSaveable {
                mutableStateOf(
                    AppLanguage.valueOf(
                        prefs.getString("app_language", AppLanguage.ENGLISH.name) ?: AppLanguage.ENGLISH.name
                    )
                )
            }
            var selectedRole by rememberSaveable {
                mutableStateOf(
                    prefs.getString("user_role", null)?.let { UserRole.valueOf(it) }
                )
            }
            var isLoggedIn by rememberSaveable { mutableStateOf(prefs.getBoolean("logged_in", false)) }
            var username by rememberSaveable {
                mutableStateOf(prefs.getString("username", "") ?: "")
            }
            var userProfile by remember {
                mutableStateOf(
                    UserProfile(
                        username = username,
                        caregiverName = prefs.getString("caregiver_name", "") ?: "",
                        wearerName = prefs.getString("wearer_name", "") ?: "",
                        wearerAge = prefs.getString("wearer_age", "") ?: "",
                        wearerGender = prefs.getString("wearer_gender", "") ?: "",
                        caregiverPhone = prefs.getString("caregiver_phone", "0702341350") ?: "0702341350"
                    )
                )
            }

            val ctx = LocalContext.current
            val permissionLauncher = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestMultiplePermissions()
            ) { result -> 
                val allGranted = result.values.all { it }
                if (allGranted) {
                    Log.i("MainActivity", "Permissions granted! Re-triggering BLE Service auto-connect…")
                    com.aifd.service.BleForegroundService.start(ctx)
                }
            }

            // Prompt user to enable Bluetooth if it is currently off
            val enableBtLauncher = rememberLauncherForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) { /* result handled by BleForegroundService BT receiver */ }

            LaunchedEffect(Unit) {
                val btManager = getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
                if (btManager?.adapter?.isEnabled == false) {
                    Log.i("MainActivity", "Bluetooth is OFF — requesting user to enable")
                    @Suppress("DEPRECATION")
                    enableBtLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                }
            }

            LaunchedEffect(Unit) {
                val permissions = mutableListOf(
                    Manifest.permission.CALL_PHONE,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    permissions.add(Manifest.permission.BLUETOOTH_SCAN)
                    permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
                }
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    permissions.add(Manifest.permission.POST_NOTIFICATIONS)
                }

                permissionLauncher.launch(permissions.toTypedArray())
            }

            ProvideAppStrings(language = language) {
                AIFDTheme(themeMode = themeMode) {
                    Surface(
                        modifier = Modifier.fillMaxSize(),
                        color = MaterialTheme.colorScheme.background
                    ) {
                        AppNavigation(
                            startOnFallAlert = startOnFallAlert,
                            onFallAlertHandled = { startOnFallAlert = false },
                            themeMode = themeMode,
                            language = language,
                            selectedRole = selectedRole,
                            isLoggedIn = isLoggedIn,
                            username = username,
                            userProfile = userProfile,
                            onThemeModeChange = {
                                themeMode = it
                                prefs.edit { putString("theme_mode", it.name) }
                            },
                            onLanguageChange = {
                                language = it
                                prefs.edit { putString("app_language", it.name) }
                            },
                            onRoleChange = {
                                selectedRole = it
                                prefs.edit {
                                    if (it == null) remove("user_role") else putString("user_role", it.name)
                                }
                            },
                            onLoginSuccess = { name ->
                                isLoggedIn = true
                                username = name
                                if (name == "000" && com.aifd.data.MockDataProvider.DEMO_MODE) {
                                    // Full setup for demo account (only in DEMO_MODE)
                                    val demoProfile = UserProfile(
                                        username = "000",
                                        caregiverName = "Nguyễn Văn A",
                                        caregiverPhone = "0702341350",
                                        wearerName = "Trần Thị B",
                                        wearerAge = "75",
                                        wearerGender = "Nữ"
                                    )
                                    userProfile = demoProfile
                                    selectedRole = UserRole.WEARER
                                    prefs.edit {
                                        putString("user_role", UserRole.WEARER.name)
                                        putString("caregiver_name", demoProfile.caregiverName)
                                        putString("wearer_name", demoProfile.wearerName)
                                        putString("wearer_age", demoProfile.wearerAge)
                                        putString("wearer_gender", demoProfile.wearerGender)
                                        putString("caregiver_phone", demoProfile.caregiverPhone)
                                        putString("device_name", "ESP32-S3 Wearable")
                                        putString("device_mac", "AA:BB:CC:DD:EE:FF")
                                    }
                                } else if (name == "000" || name == "dien572") {
                                    // For real user (or 000 with DEMO_MODE=off), clear everything and act like a normal user
                                    userProfile = UserProfile(username = name)
                                    selectedRole = null
                                    prefs.edit {
                                        remove("user_role")
                                        remove("caregiver_name")
                                        remove("wearer_name")
                                        remove("wearer_age")
                                        remove("wearer_gender")
                                        remove("caregiver_phone")
                                        remove("device_name")
                                        remove("device_mac")
                                        
                                        // Clear any stored sensor data for a clean slate
                                        remove("last_heart_rate")
                                        remove("last_spo2")
                                        remove("last_vital_timestamp")
                                        remove("hr_history")
                                        remove("spo2_history")
                                        remove("monitoring_hr_live")
                                        remove("monitoring_spo2_live")
                                        remove("fall_events_json")
                                    }
                                }
                                prefs.edit(commit = true) {
                                    putBoolean("logged_in", true)
                                    putString("username", name)
                                }
                            },
                            onRegisterSuccess = { profile: UserProfile ->
                                isLoggedIn = true
                                username = profile.username
                                userProfile = profile
                                prefs.edit {
                                    putBoolean("logged_in", true)
                                    putString("username", profile.username)
                                    putString("caregiver_name", profile.caregiverName)
                                    putString("wearer_name", profile.wearerName)
                                    putString("wearer_age", profile.wearerAge)
                                    putString("wearer_gender", profile.wearerGender)
                                    putString("caregiver_phone", profile.caregiverPhone)
                                }
                            },
                            onUpdateProfile = { profile ->
                                userProfile = profile
                                username = profile.username
                                prefs.edit {
                                    putString("username", profile.username)
                                    putString("caregiver_name", profile.caregiverName)
                                    putString("wearer_name", profile.wearerName)
                                    putString("wearer_age", profile.wearerAge)
                                    putString("wearer_gender", profile.wearerGender)
                                    putString("caregiver_phone", profile.caregiverPhone)
                                }
                            },
                            onLogout = {
                                isLoggedIn = false
                                selectedRole = null
                                username = ""
                                prefs.edit {
                                    putBoolean("logged_in", false)
                                    remove("username")
                                    remove("user_role")
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        bleService?.setAppForeground(true)
    }

    override fun onPause() {
        super.onPause()
        bleService?.setAppForeground(false)
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isBound) {
            unbindService(serviceConnection)
            isBound = false
        }
    }
}
