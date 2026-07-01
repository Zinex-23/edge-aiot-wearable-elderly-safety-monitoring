package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.*
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicePairingScreen(
    isScanning: Boolean,
    nearbyDevices: List<NearbyDevice>,
    currentDevice: DeviceInfo?,
    connectingDeviceId: String?,
    connectionProgress: Int,
    errorMessage: String? = null,
    onScan: () -> Unit = {},
    onConnect: (NearbyDevice) -> Unit = {},
    onBack: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = strings.back)
                }
                IconButton(onClick = onScan, enabled = !isScanning) {
                    Icon(Icons.Default.Refresh, contentDescription = strings.scan)
                }
            }
            if (isScanning) {
                // Scanning animation
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 48.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    val infiniteTransition = rememberInfiniteTransition(label = "scan")
                    val scale by infiniteTransition.animateFloat(
                        initialValue = 1f,
                        targetValue = 1.3f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(1200),
                            repeatMode = RepeatMode.Reverse
                        ),
                        label = "scanScale"
                    )
                    val alpha by infiniteTransition.animateFloat(
                        initialValue = 0.4f,
                        targetValue = 0f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(1200),
                            repeatMode = RepeatMode.Restart
                        ),
                        label = "scanAlpha"
                    )

                    Box(contentAlignment = Alignment.Center) {
                        Box(
                            modifier = Modifier
                                .size((128 * scale).dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary.copy(alpha = alpha * 0.3f))
                        )
                        Box(
                            modifier = Modifier
                                .size(128.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primaryContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Bluetooth,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(48.dp)
                            )
                        }
                    }
                    Spacer(Modifier.height(24.dp))
                    Text(strings.scanningDevices, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Medium)
                    Text(
                        strings.scanningHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                // Nearby devices list
                Text(
                    strings.nearbyDevices(nearbyDevices.size),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                if (nearbyDevices.isEmpty()) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 48.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.BluetoothDisabled,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(Modifier.height(16.dp))
                        Text(strings.noDevicesFound, style = MaterialTheme.typography.titleMedium)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = onScan) {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(strings.scanAgain)
                        }
                    }
                } else {
                    nearbyDevices.forEach { nearby ->
                        val isConnecting = connectingDeviceId == nearby.id
                        val isConnected = currentDevice?.id == nearby.id
                                && currentDevice?.connectionStatus == ConnectionStatus.CONNECTED

                        Card(
                            onClick = { if (!isConnecting && !isConnected) onConnect(nearby) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            shape = RoundedCornerShape(20.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (isConnected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.15f)
                                                else MaterialTheme.colorScheme.surface
                            ),
                            elevation = CardDefaults.cardElevation(
                                defaultElevation = if (isConnected) 0.dp else 2.dp
                            ),
                            border = if (isConnected) {
                                androidx.compose.foundation.BorderStroke(
                                    1.dp, 
                                    MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)
                                )
                            } else null
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                                ) {
                                    // Bluetooth Icon with specialized background
                                    Box(
                                        modifier = Modifier
                                            .size(52.dp)
                                            .clip(RoundedCornerShape(16.dp))
                                            .background(
                                                if (isConnected) MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                                                else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                                            ),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Bluetooth,
                                            contentDescription = null,
                                            tint = if (isConnected) MaterialTheme.colorScheme.primary
                                                   else MaterialTheme.colorScheme.onSurfaceVariant,
                                            modifier = Modifier.size(26.dp)
                                        )
                                    }

                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = nearby.name,
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                        Spacer(Modifier.height(4.dp))
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            val (signalIcon, signalColor) = when {
                                                nearby.signalStrength >= -50 -> Icons.Default.SignalWifi4Bar to AIFDThemeExt.colors.safe
                                                nearby.signalStrength >= -65 -> Icons.Default.NetworkWifi3Bar to AIFDThemeExt.colors.warning
                                                else -> Icons.Default.NetworkWifi1Bar to MaterialTheme.colorScheme.error
                                            }
                                            Icon(
                                                imageVector = signalIcon,
                                                contentDescription = null,
                                                modifier = Modifier.size(14.dp),
                                                tint = signalColor
                                            )
                                            Text(
                                                text = "${nearby.signalStrength} dBm",
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                    }

                                    // Action area
                                    Box(contentAlignment = Alignment.Center) {
                                        when {
                                            isConnecting -> {
                                                val infiniteTransition = rememberInfiniteTransition(label = "loading")
                                                val rotation by infiniteTransition.animateFloat(
                                                    initialValue = 0f,
                                                    targetValue = 360f,
                                                    animationSpec = infiniteRepeatable(
                                                        animation = tween(1000, easing = LinearEasing),
                                                        repeatMode = RepeatMode.Restart
                                                    ),
                                                    label = "rotation"
                                                )
                                                Icon(
                                                    imageVector = Icons.Default.Refresh,
                                                    contentDescription = null,
                                                    modifier = Modifier
                                                        .size(24.dp)
                                                        .graphicsLayer { rotationZ = rotation },
                                                    tint = MaterialTheme.colorScheme.primary
                                                )
                                            }
                                            isConnected -> {
                                                Surface(
                                                    shape = CircleShape,
                                                    color = AIFDThemeExt.colors.safe.copy(alpha = 0.1f),
                                                    contentColor = AIFDThemeExt.colors.safe
                                                ) {
                                                    Row(
                                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                                        verticalAlignment = Alignment.CenterVertically,
                                                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                                                    ) {
                                                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                                                        Text(strings.connected, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                                                    }
                                                }
                                            }
                                            else -> {
                                                Icon(
                                                    Icons.Default.ChevronRight,
                                                    contentDescription = null,
                                                    tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                                                )
                                            }
                                        }
                                    }
                                }

                                if (isConnecting) {
                                    Spacer(Modifier.height(16.dp))
                                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        LinearProgressIndicator(
                                            progress = connectionProgress / 100f,
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .height(6.dp)
                                                .clip(RoundedCornerShape(3.dp)),
                                            color = MaterialTheme.colorScheme.primary,
                                            trackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                                        )
                                        Text(
                                            text = when {
                                                connectionProgress < 30 -> strings.discoveringDevice
                                                connectionProgress < 60 -> strings.establishingConnection
                                                connectionProgress < 90 -> strings.syncingData
                                                else -> strings.almostDone
                                            },
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                // Error message
                if (errorMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp).fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                modifier = Modifier.weight(1f),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Icon(Icons.Default.Error, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                                Text(errorMessage, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodyMedium)
                            }
                            
                            if (errorMessage.contains("Vị trí") || errorMessage.contains("GPS")) {
                                val context = androidx.compose.ui.platform.LocalContext.current
                                TextButton(
                                    onClick = {
                                        context.startActivity(android.content.Intent(android.provider.Settings.ACTION_LOCATION_SOURCE_SETTINGS))
                                    }
                                ) {
                                    Text("Bật GPS")
                                }
                            }
                        }
                    }
                }

                // Help
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(strings.cantFindDevice, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    TextButton(onClick = { }) {
                        Text(strings.troubleshootingGuide)
                    }
                }
            }
        }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun DevicePairingScreenPreview() {
    AIFDTheme {
        DevicePairingScreen(
            isScanning = false,
            nearbyDevices = MockDataProvider.nearbyDevices,
            currentDevice = MockDataProvider.device,
            connectingDeviceId = null,
            connectionProgress = 0
        )
    }
}
