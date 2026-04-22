package com.aifd.ui.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
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
import androidx.compose.material.icons.outlined.Bluetooth
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
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import com.aifd.viewmodel.HomeUiState
import com.aifd.viewmodel.HomeViewModel

@Composable
fun HomeScreen(
    homeViewModel: HomeViewModel,
    role: UserRole,
    userName: String = "",
    alertCount: Int,
    onNavigateToMonitoring: () -> Unit = {},
    onNavigateToDeviceDetail: () -> Unit = {},
    onNavigateToBlePairing: () -> Unit = {},
    onTriggerFallAlert: () -> Unit = {}
) {
    val uiState by homeViewModel.uiState.collectAsState()
    HomeScreenContent(
        uiState = uiState,
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
    role: UserRole,
    userName: String = "",
    alertCount: Int,
    onNavigateToMonitoring: () -> Unit = {},
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

        if (isWearer && !isConnected) {
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

        if (isWearer && isLowBattery && isConnected) {
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

        if (isWearer) {
            if (device != null) {
                DeviceCard(device = device, onClick = onNavigateToDeviceDetail)
            } else {
                UnpairedDeviceCard(onClick = onNavigateToBlePairing)
            }
        }


        val hrStatusColor = when (healthData?.heartRateStatus) {
            HealthStatus.HIGH -> MaterialTheme.colorScheme.error
            HealthStatus.LOW -> AIFDThemeExt.colors.warning
            else -> AIFDThemeExt.colors.safe
        }
        StatCard(
            icon = Icons.Default.Favorite,
            iconTint = MaterialTheme.colorScheme.error,
            iconBackground = MaterialTheme.colorScheme.errorContainer,
            label = strings.heartRate,
            value = healthData?.heartRate?.toString() ?: "--",
            unit = "bpm",
            statusText = healthData?.heartRateStatus?.name?.lowercase()?.replaceFirstChar { it.uppercase() }
                ?: strings.unknown,
            statusColor = hrStatusColor,
            onClick = onNavigateToMonitoring
        )

        val spO2StatusColor = when (healthData?.spO2Status) {
            HealthStatus.LOW -> AIFDThemeExt.colors.warning
            else -> AIFDThemeExt.colors.safe
        }
        StatCard(
            icon = Icons.Default.Favorite,
            iconTint = MaterialTheme.colorScheme.primary,
            iconBackground = MaterialTheme.colorScheme.primaryContainer,
            label = strings.bloodOxygen,
            value = healthData?.spO2?.toString() ?: "--",
            unit = "%",
            statusText = healthData?.spO2Status?.name?.lowercase()?.replaceFirstChar { it.uppercase() }
                ?: strings.unknown,
            statusColor = spO2StatusColor,
            onClick = onNavigateToMonitoring
        )



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
