package com.aifd.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.ViewModelProvider
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.aifd.data.*
import com.aifd.ui.components.aifd.AifdFloatingBottomBar
import com.aifd.ui.components.aifd.AifdNavSpec
import com.aifd.ui.localization.AppLanguage
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.screens.*
import com.aifd.ui.theme.AppThemeMode
import com.aifd.viewmodel.*

/**
 * Sealed class defining all navigation routes in the app.
 */
sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Monitoring : Screen("monitoring")
    data object Alerts : Screen("alerts")
    data object Settings : Screen("settings")
    data object FallAlert : Screen("fall_alert")
    data object DevicePairing : Screen("device_pairing")
    data object DeviceDetail : Screen("device_detail")
    data object EventDetail : Screen("event_detail")
    data object Profile : Screen("profile")
}

/**
 * Bottom navigation items.
 */
data class BottomNavItem(
    val screen: Screen,
    val label: @Composable () -> String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector
)

@Composable
fun AppNavigation(
    startOnFallAlert: Boolean = false,
    onFallAlertHandled: () -> Unit = {},
    themeMode: AppThemeMode,
    language: AppLanguage,
    selectedRole: UserRole?,
    isLoggedIn: Boolean,
    username: String,
    userProfile: UserProfile,
    onThemeModeChange: (AppThemeMode) -> Unit,
    onLanguageChange: (AppLanguage) -> Unit,
    onRoleChange: (UserRole?) -> Unit,
    onLoginSuccess: (String) -> Unit,
    onRegisterSuccess: (UserProfile) -> Unit,
    onUpdateProfile: (UserProfile) -> Unit,
    onLogout: () -> Unit
) {
    val navController = rememberNavController()
    val context = androidx.compose.ui.platform.LocalContext.current

    // Sync navigation when alert is dismissed (e.g. from notification button)
    DisposableEffect(Unit) {
        val receiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(context: android.content.Context?, intent: android.content.Intent?) {
                if (intent?.action == com.aifd.service.BleForegroundService.ACTION_DISMISS_SAFE) {
                    navController.popBackStack(Screen.Home.route, inclusive = false)
                    onFallAlertHandled()
                }
            }
        }
        val filter = android.content.IntentFilter(com.aifd.service.BleForegroundService.ACTION_DISMISS_SAFE)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(receiver, filter, android.content.Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.registerReceiver(receiver, filter)
        }
        onDispose {
            context.unregisterReceiver(receiver)
        }
    }

    // Handle initial fall alert navigation from intent
    LaunchedEffect(startOnFallAlert) {
        if (startOnFallAlert) {
            navController.navigate(Screen.FallAlert.route) {
                launchSingleTop = true
            }
            onFallAlertHandled()
        }
    }

    var authScreen by remember { mutableStateOf("login") }

    if (!isLoggedIn) {
        if (authScreen == "login") {
            LoginScreen(
                onLoginSuccess = onLoginSuccess,
                onNavigateToRegister = { authScreen = "register" }
            )
        } else {
            RegisterScreen(
                onRegisterSuccess = onRegisterSuccess,
                onNavigateToLogin = { authScreen = "login" }
            )
        }
        return
    }

    if (selectedRole == null) {
        RoleSelectionScreen(onRoleSelected = onRoleChange)
        return
    }

    val factory = ViewModelProvider.AndroidViewModelFactory.getInstance(
        context.applicationContext as android.app.Application
    )
    val homeViewModel: HomeViewModel = viewModel(factory = factory)
    val monitoringViewModel: MonitoringViewModel = viewModel(factory = factory)
    val deviceViewModel: DeviceViewModel = viewModel(factory = factory)
    val alertViewModel: AlertViewModel = viewModel(factory = factory)

    // Reset ViewModel state when the logged-in user changes (e.g. switching accounts)
    LaunchedEffect(username) {
        homeViewModel.resetForUser(username)
        monitoringViewModel.resetForUser(username)
    }

    // Sync device connection state from DeviceViewModel -> HomeViewModel
    LaunchedEffect(deviceViewModel) {
        deviceViewModel.uiState.collect { devState ->
            homeViewModel.updateDevice(devState.device)
        }
    }

    val strings = AppLocalizations.strings
    val prefs = remember { context.getSharedPreferences("aifd_prefs", Context.MODE_PRIVATE) }


    val aifdNavItems = remember(language) {
        listOf(
            AifdNavSpec(Screen.Home.route,       strings.home,     Icons.Filled.Home,          Icons.Outlined.Home),
            AifdNavSpec(Screen.Monitoring.route, strings.health,   Icons.Filled.Favorite,      Icons.Outlined.FavoriteBorder),
            AifdNavSpec(Screen.Alerts.route,     strings.alerts,   Icons.Filled.Notifications, Icons.Outlined.Notifications),
            AifdNavSpec(Screen.Settings.route,   strings.settings, Icons.Filled.Settings,      Icons.Outlined.Settings)
        )
    }

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    // Screens where bottom nav should be hidden — per UI upgrade spec
    val hideBottomNav = currentRoute in listOf(
        Screen.FallAlert.route,
        Screen.DevicePairing.route,
        Screen.DeviceDetail.route,
        Screen.EventDetail.route,
        Screen.Profile.route
    )

    Scaffold(
        bottomBar = {
            if (!hideBottomNav) {
                AifdFloatingBottomBar(
                    items = aifdNavItems,
                    currentRoute = currentRoute,
                    onItemClick = { spec ->
                        navController.navigate(spec.route) {
                            popUpTo(Screen.Home.route) { inclusive = false }
                            launchSingleTop = true
                        }
                    }
                )
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding),
            enterTransition = {
                slideIntoContainer(
                    towards = AnimatedContentTransitionScope.SlideDirection.Left,
                    animationSpec = tween(400)
                ) + fadeIn(animationSpec = tween(400))
            },
            exitTransition = {
                slideOutOfContainer(
                    towards = AnimatedContentTransitionScope.SlideDirection.Left,
                    animationSpec = tween(400)
                ) + fadeOut(animationSpec = tween(400))
            },
            popEnterTransition = {
                slideIntoContainer(
                    towards = AnimatedContentTransitionScope.SlideDirection.Right,
                    animationSpec = tween(400)
                ) + fadeIn(animationSpec = tween(400))
            },
            popExitTransition = {
                slideOutOfContainer(
                    towards = AnimatedContentTransitionScope.SlideDirection.Right,
                    animationSpec = tween(400)
                ) + fadeOut(animationSpec = tween(400))
            }
        ) {
            composable(Screen.Home.route) {
                val alertUiState by alertViewModel.uiState.collectAsState()
                val navigateToMonitoring = {
                    navController.navigate(Screen.Monitoring.route) {
                        popUpTo(Screen.Home.route) { inclusive = false }
                        launchSingleTop = true
                    }
                }
                HomeScreen(
                    homeViewModel = homeViewModel,
                    role = selectedRole,
                    userName = if (selectedRole == UserRole.WEARER) userProfile.wearerName else userProfile.caregiverName,
                    alertCount = alertUiState.fallEvents.count { it.status == EventStatus.PENDING },
                    onNavigateToMonitoring = navigateToMonitoring,
                    onNavigateToDeviceDetail = {
                        if (selectedRole == UserRole.WEARER) {
                            navController.navigate(Screen.DeviceDetail.route)
                        }
                    },
                    onNavigateToBlePairing = {
                        if (selectedRole == UserRole.WEARER) {
                            navController.navigate(Screen.DevicePairing.route)
                        }
                    },
                    onTriggerFallAlert = {
                        if (selectedRole == UserRole.WEARER) {
                            alertViewModel.triggerFallAlert()
                            navController.navigate(Screen.FallAlert.route)
                        }
                    }
                )
            }

            composable(Screen.Monitoring.route) {
                MonitoringScreen(
                    viewModel = monitoringViewModel,
                    role = selectedRole
                )
            }

            composable(Screen.Alerts.route) {
                val alertState by alertViewModel.uiState.collectAsState()
                HistoryScreen(
                    events = alertState.fallEvents,
                    onEventClick = { eventId ->
                        alertViewModel.selectEvent(eventId)
                        navController.navigate(Screen.EventDetail.route)
                    }
                )
            }

            composable(Screen.Settings.route) {
                val deviceState by deviceViewModel.uiState.collectAsState()
                SettingsScreen(
                    role = selectedRole,
                    device = deviceState.device,
                    themeMode = themeMode,
                    language = language,
                    onThemeModeChange = onThemeModeChange,
                    onLanguageChange = onLanguageChange,
                    onRoleChange = { onRoleChange(it) },
                    onNavigateToBlePairing = {
                        if (selectedRole == UserRole.WEARER) {
                            navController.navigate(Screen.DevicePairing.route)
                        }
                    },
                    onNavigateToDeviceDetail = {
                        if (selectedRole == UserRole.WEARER) {
                            navController.navigate(Screen.DeviceDetail.route)
                        }
                    },
                    onNavigateToEmergencyContacts = { /* TODO */ },
                    onNavigateToNotifications = { /* TODO */ },
                    onNavigateToAccount = { navController.navigate(Screen.Profile.route) },
                    onLogout = onLogout,
                    onClearData = { monitoringViewModel.clearVitalsData() }
                )
            }

            composable(Screen.FallAlert.route) {
                val context = LocalContext.current
                val emergencyNumber = userProfile.caregiverPhone.ifBlank { "0702341350" }

                val callPermissionLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.RequestPermission()
                ) { isGranted ->
                    if (isGranted) {
                        try {
                            val intent = Intent(Intent.ACTION_CALL).apply {
                                data = Uri.parse("tel:$emergencyNumber")
                            }
                            context.startActivity(intent)
                        } catch (e: Exception) {
                            e.printStackTrace()
                        }
                    } else {
                        // Fallback to dialer if still not granted
                        val intent = Intent(Intent.ACTION_DIAL).apply {
                            data = Uri.parse("tel:$emergencyNumber")
                        }
                        context.startActivity(intent)
                    }
                }
                
                FallAlertScreen(
                    onDismissAsSafe = {
                        alertViewModel.dismissAsSafe()
                        deviceViewModel.cancelEmergencyCountdown() // Cancel service countdown
                        navController.popBackStack(Screen.Home.route, inclusive = false)
                    },
                    onCallForHelp = {
                        alertViewModel.callForHelp()
                        deviceViewModel.cancelEmergencyCountdown() // Stop background duplicate
                        
                        // Launch call intent
                        try {
                            val hasPermission = androidx.core.content.ContextCompat.checkSelfPermission(
                                context,
                                android.Manifest.permission.CALL_PHONE
                            ) == android.content.pm.PackageManager.PERMISSION_GRANTED

                            if (hasPermission) {
                                val intent = Intent(Intent.ACTION_CALL).apply {
                                    data = Uri.parse("tel:$emergencyNumber")
                                }
                                context.startActivity(intent)
                            } else {
                                // Request permission
                                callPermissionLauncher.launch(android.Manifest.permission.CALL_PHONE)
                            }
                        } catch (e: Exception) {
                            e.printStackTrace()
                        }
                        
                        navController.popBackStack(Screen.Home.route, inclusive = false)
                    }
                )
            }

            composable(Screen.DevicePairing.route) {
                if (selectedRole != UserRole.WEARER) return@composable
                val deviceState by deviceViewModel.uiState.collectAsState()
                LaunchedEffect(Unit) {
                    deviceViewModel.startScan()
                }
                DevicePairingScreen(
                    isScanning = deviceState.isScanning,
                    nearbyDevices = deviceState.nearbyDevices,
                    currentDevice = deviceState.device,
                    connectingDeviceId = deviceState.connectingDeviceId,
                    connectionProgress = deviceState.connectionProgress,
                    errorMessage = deviceState.errorMessage,
                    onScan = deviceViewModel::startScan,
                    onConnect = deviceViewModel::connectToDevice,
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.DeviceDetail.route) {
                if (selectedRole != UserRole.WEARER) return@composable
                val deviceState by deviceViewModel.uiState.collectAsState()
                DeviceDetailScreen(
                    device = deviceState.device,
                    onRename = deviceViewModel::renameDevice,
                    onReconnect = deviceViewModel::reconnectDevice,
                    onDisconnect = {
                        deviceViewModel.disconnectDevice()
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Home.route) { inclusive = true }
                        }
                    },
                    onNavigateToBlePairing = { navController.navigate(Screen.DevicePairing.route) },
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.EventDetail.route) {
                val event = alertViewModel.getSelectedEvent()
                EventDetailScreen(
                    event = event,
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.Profile.route) {
                ProfileScreen(
                    userProfile = userProfile,
                    onSave = onUpdateProfile,
                    onBack = { navController.popBackStack() }
                )
            }
        }
    }
}

@Composable
fun BottomNavigationBar(
    navController: NavHostController,
    items: List<BottomNavItem>
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    NavigationBar(
        tonalElevation = 0.dp,
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        items.forEach { item ->
            val selected = currentDestination?.hierarchy?.any { it.route == item.screen.route } == true

            // Custom navigation item to avoid the persistent "pill" indicator
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(12.dp))
                    .clickable {
                        navController.navigate(item.screen.route) {
                            popUpTo(Screen.Home.route) { inclusive = false }
                            launchSingleTop = true
                        }
                    }
                    .padding(4.dp)
                    .background(
                        color = if (selected) MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.4f)
                                else Color.Transparent,
                        shape = RoundedCornerShape(12.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = if (selected) item.selectedIcon else item.unselectedIcon,
                        contentDescription = item.label(),
                        tint = if (selected) MaterialTheme.colorScheme.primary
                               else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = item.label(),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                        color = if (selected) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                    )
                }
            }
        }
    }
}
