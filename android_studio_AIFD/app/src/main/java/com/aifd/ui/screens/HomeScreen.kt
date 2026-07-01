package com.aifd.ui.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.LinearEasing
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.BatteryAlert
import androidx.compose.material.icons.filled.BatteryFull
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.outlined.Bluetooth
import androidx.compose.material.icons.automirrored.filled.TrendingFlat
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aifd.data.ConnectionStatus
import com.aifd.data.HealthStatus
import com.aifd.data.UserRole
import com.aifd.ui.components.DeviceCard
import com.aifd.ui.components.StatCard
import com.aifd.ui.components.aifd.AifdHealthMetricCard
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import com.aifd.viewmodel.HomeUiState
import com.aifd.viewmodel.HomeViewModel
import com.aifd.viewmodel.MetricTab
import com.aifd.viewmodel.MonitoringUiState
import com.aifd.viewmodel.MonitoringViewModel
import com.aifd.viewmodel.CloudLoadState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.mutableStateOf

@Composable
fun HomeScreen(
    homeViewModel: HomeViewModel,
    monitoringViewModel: MonitoringViewModel? = null,
    role: UserRole,
    userName: String = "",
    alertCount: Int,
    onNavigateToMonitoring: (MetricTab?) -> Unit = {},
    onNavigateToDeviceDetail: () -> Unit = {},
    onNavigateToBlePairing: () -> Unit = {},
    onTriggerFallAlert: () -> Unit = {}
) {
    val uiState by homeViewModel.uiState.collectAsState()
    val monitoringUiState by monitoringViewModel?.uiState?.collectAsState() ?: remember { mutableStateOf<MonitoringUiState?>(null) }
    
    val isWearer = role == UserRole.WEARER
    LaunchedEffect(isWearer) {
        if (!isWearer) {
            monitoringViewModel?.fetch1hDataIfNeeded()
        }
    }

    HomeScreenContent(
        uiState = uiState,
        monitoringUiState = monitoringUiState,
        role = role,
        userName = userName,
        alertCount = alertCount,
        onNavigateToMonitoring = onNavigateToMonitoring,
        onNavigateToDeviceDetail = onNavigateToDeviceDetail,
        onNavigateToBlePairing = onNavigateToBlePairing,
        onTriggerFallAlert = onTriggerFallAlert
    )
}

@Composable
private fun HomeScreenContent(
    uiState: HomeUiState,
    monitoringUiState: MonitoringUiState? = null,
    role: UserRole,
    userName: String = "",
    alertCount: Int,
    onNavigateToMonitoring: (MetricTab?) -> Unit = {},
    onNavigateToDeviceDetail: () -> Unit = {},
    onNavigateToBlePairing: () -> Unit = {},
    onTriggerFallAlert: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    val device = uiState.device
    val healthData = uiState.healthData
    val isWearer = role == UserRole.WEARER
    val isConnected = device?.connectionStatus == ConnectionStatus.CONNECTED
    val isLowBattery = device != null && device.battery < 20

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        GreetingBanner(
            userName = userName,
            role = role,
            onEmergencyClick = if (isWearer) onTriggerFallAlert else null
        )

        if (isWearer) {
            when {
                isConnected -> {
                    // Show DeviceCard when connected
                    if (device != null) {
                        DeviceCard(device = device, onClick = onNavigateToDeviceDetail)
                        
                        // Show Low Battery alert if needed (only when connected)
                        if (isLowBattery) {
                            ElevatedCard(
                                colors = CardDefaults.elevatedCardColors(
                                    containerColor = AIFDThemeExt.colors.warningContainer
                                ),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.BatteryAlert,
                                        contentDescription = null,
                                        tint = AIFDThemeExt.colors.warning
                                    )
                                    Column {
                                        Text(strings.lowBattery, fontWeight = FontWeight.Medium)
                                        Text(
                                            strings.chargeSoon,
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
                device != null -> {
                    // Show Red Alert Card when disconnected but device is known
                    ElevatedCard(
                        colors = CardDefaults.elevatedCardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(20.dp)
                            )
                            Column(modifier = Modifier.weight(1f)) {
                                Text(strings.deviceDisconnected, fontWeight = FontWeight.Medium)
                                Text(
                                    strings.tapToReconnect,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            OutlinedButton(onClick = onNavigateToBlePairing) {
                                Text(strings.connect)
                            }
                        }
                    }
                }
                else -> {
                    // Show Unpaired Device Card when no device is paired
                    UnpairedDeviceCard(onClick = onNavigateToBlePairing)
                }
            }
        }


        if (isWearer) {
            AifdHealthMetricCard(
                icon         = Icons.Default.Favorite,
                label        = strings.heartRate,
                value        = healthData?.heartRate?.toString() ?: "--",
                unit         = "bpm",
                status       = healthData?.heartRateStatus,
                statusLabel  = healthData?.heartRateStatus?.name?.lowercase()
                    ?.replaceFirstChar { it.uppercase() } ?: strings.unknown,
                accentColor  = MaterialTheme.colorScheme.error,
                onClick      = { onNavigateToMonitoring(null) }
            )

            AifdHealthMetricCard(
                icon         = Icons.Default.Favorite,
                label        = strings.bloodOxygen,
                value        = healthData?.spO2?.toString() ?: "--",
                unit         = "%",
                status       = healthData?.spO2Status,
                statusLabel  = healthData?.spO2Status?.name?.lowercase()
                    ?.replaceFirstChar { it.uppercase() } ?: strings.unknown,
                accentColor  = MaterialTheme.colorScheme.primary,
                onClick      = { onNavigateToMonitoring(null) }
            )
        } else {
            CaregiverHealthSummaryCard(
                icon = Icons.Default.Favorite,
                title = "${strings.heartRate} (1h)",
                stats = monitoringUiState?.hr1hStats ?: Triple(0,0,0),
                unit = "bpm",
                accentColor = MaterialTheme.colorScheme.error,
                loadState = monitoringUiState?.cloudLoadState ?: CloudLoadState.IDLE,
                onClick = { onNavigateToMonitoring(MetricTab.HEART_RATE) }
            )

            CaregiverHealthSummaryCard(
                icon = Icons.Default.Assessment,
                title = "${strings.bloodOxygen} (1h)",
                stats = monitoringUiState?.spo21hStats ?: Triple(0,0,0),
                unit = "%",
                accentColor = MaterialTheme.colorScheme.primary,
                loadState = monitoringUiState?.cloudLoadState ?: CloudLoadState.IDLE,
                onClick = { onNavigateToMonitoring(MetricTab.SPO2) }
            )
        }



        if (isWearer && !isConnected) {
            OutlinedButton(
                onClick = onNavigateToBlePairing,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.Outlined.Bluetooth, contentDescription = null, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(8.dp))
                Text(strings.pairDevice, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun UnpairedDeviceCard(onClick: () -> Unit) {
    val strings = AppLocalizations.strings

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(androidx.compose.foundation.shape.RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Outlined.Bluetooth,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(24.dp)
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = strings.pairDevice,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = strings.tapToReconnect,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun GreetingBanner(
    userName: String,
    role: UserRole,
    onEmergencyClick: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val strings = AppLocalizations.strings
    val greeting = remember(userName, role) {
        strings.getRandomGreeting(userName, role)
    }

    ElevatedCard(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 4.dp)
    ) {
        Box(
            modifier = Modifier
                .background(
                    Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary,
                            MaterialTheme.colorScheme.tertiary
                        )
                    )
                )
                .padding(24.dp)
                .fillMaxWidth()
        ) {
            // Subtle background decoration
            Box(
                modifier = Modifier
                    .size(150.dp)
                    .align(Alignment.TopEnd)
                    .offset(x = 40.dp, y = (-60).dp)
                    .background(Color.White.copy(alpha = 0.1f), CircleShape)
            )
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .align(Alignment.BottomStart)
                    .offset(x = (-20).dp, y = 30.dp)
                    .background(Color.White.copy(alpha = 0.05f), CircleShape)
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .background(Color.White.copy(alpha = 0.2f), CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = if (userName.isNotBlank()) userName.take(1).uppercase() else "A",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.labelLarge
                            )
                        }
                        Spacer(Modifier.width(10.dp))
                        Text(
                            text = strings.hello + if (userName.isNotBlank()) ", $userName!" else "!",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.ExtraBold,
                            color = Color.White,
                            letterSpacing = 0.5.sp
                        )
                    }

                    Text(
                        text = greeting,
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White.copy(alpha = 0.9f),
                        lineHeight = 20.sp,
                        fontWeight = FontWeight.Medium
                    )
                }

                if (onEmergencyClick != null) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Surface(
                            onClick = onEmergencyClick,
                            shape = CircleShape,
                            color = Color.White.copy(alpha = 0.9f),
                            modifier = Modifier.size(56.dp),
                            shadowElevation = 8.dp
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    Icons.Default.Phone,
                                    contentDescription = strings.emergency,
                                    tint = MaterialTheme.colorScheme.error,
                                    modifier = Modifier.size(28.dp)
                                )
                            }
                        }
                        Spacer(Modifier.height(4.dp))
                        Text(
                            text = strings.emergency,
                            color = Color.White,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}


@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun HomeScreenPreview() {
    AIFDTheme {
        HomeScreenContent(
            uiState = HomeUiState(),
            role = UserRole.WEARER,
            userName = "Wearer Name",
            alertCount = 2
        )
    }
}

@Composable
private fun CaregiverHealthSummaryCard(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    stats: Triple<Int, Int, Int>,
    unit: String,
    accentColor: Color,
    loadState: CloudLoadState = CloudLoadState.IDLE,
    onClick: () -> Unit
) {
    val strings = AppLocalizations.strings

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(accentColor.copy(alpha = 0.1f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        tint = accentColor,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f)
                )
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            Spacer(Modifier.height(16.dp))
            
            when (loadState) {
                CloudLoadState.LOADING -> {
                    val infiniteTransition = rememberInfiniteTransition(label = "loading")
                    val angle by infiniteTransition.animateFloat(
                        initialValue = 0f,
                        targetValue = 360f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(1000, easing = LinearEasing),
                            repeatMode = RepeatMode.Restart
                        ),
                        label = "rotation"
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Sync,
                            contentDescription = null,
                            tint = accentColor,
                            modifier = Modifier
                                .size(24.dp)
                                .rotate(angle)
                        )
                        Spacer(Modifier.width(12.dp))
                        Text(
                            text = strings.syncingData,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                CloudLoadState.ERROR -> {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = strings.networkDisconnected,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
                else -> {
                    if (stats.first == 0 && stats.second == 0 && stats.third == 0) {
                        Text(
                            text = strings.noDataInPastHour,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            StatColumn(
                                label = strings.average,
                                value = "${stats.first} $unit",
                                valueColor = accentColor,
                                icon = Icons.AutoMirrored.Filled.TrendingFlat
                            )
                            Box(
                                modifier = Modifier
                                    .width(1.dp)
                                    .height(36.dp)
                                    .background(MaterialTheme.colorScheme.outlineVariant)
                            )
                            StatColumn(
                                label = strings.min,
                                value = "${stats.second} $unit",
                                valueColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                icon = Icons.Default.KeyboardArrowDown
                            )
                            Box(
                                modifier = Modifier
                                    .width(1.dp)
                                    .height(36.dp)
                                    .background(MaterialTheme.colorScheme.outlineVariant)
                            )
                            StatColumn(
                                label = strings.max,
                                value = "${stats.third} $unit",
                                valueColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                icon = Icons.Default.KeyboardArrowUp
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatColumn(
    label: String, 
    value: String, 
    valueColor: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector? = null
) {
    Column(horizontalAlignment = Alignment.Start) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (icon != null) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(Modifier.width(4.dp))
            }
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.Bold,
            color = valueColor
        )
    }
}
