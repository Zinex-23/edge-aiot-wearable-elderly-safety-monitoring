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

                        ElevatedCard(
                            shape = RoundedCornerShape(12.dp),
                            colors = if (isConnected) CardDefaults.elevatedCardColors(
                                containerColor = AIFDThemeExt.colors.safeContainer.copy(alpha = 0.3f)
                            ) else CardDefaults.elevatedCardColors()
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(48.dp)
                                            .clip(RoundedCornerShape(12.dp))
                                            .background(
                                                if (isConnected) AIFDThemeExt.colors.safeContainer
                                                else MaterialTheme.colorScheme.primaryContainer
                                            ),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            Icons.Default.Bluetooth,
                                            contentDescription = null,
                                            tint = if (isConnected) AIFDThemeExt.colors.safe
                                                   else MaterialTheme.colorScheme.primary
                                        )
                                    }

                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(nearby.name, fontWeight = FontWeight.Medium)
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            val signalIcon = when {
                                                nearby.signalStrength >= -50 -> Icons.Default.SignalWifi4Bar
                                                nearby.signalStrength >= -65 -> Icons.Default.NetworkWifi3Bar
                                                else -> Icons.Default.NetworkWifi1Bar
                                            }
                                            val signalLabel = when {
                                                nearby.signalStrength >= -50 -> strings.excellent
                                                nearby.signalStrength >= -60 -> strings.good
                                                nearby.signalStrength >= -70 -> strings.fair
                                                else -> strings.weak
                                            }
                                            Icon(signalIcon, contentDescription = null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(signalLabel, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }

                                    when {
                                        isConnecting -> {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                                            ) {
                                                Icon(Icons.Default.Sync, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                                Text(strings.connecting, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Medium)
                                            }
                                        }
                                        isConnected -> {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                                            ) {
                                                Icon(Icons.Default.Check, contentDescription = null, tint = AIFDThemeExt.colors.safe, modifier = Modifier.size(20.dp))
                                                Text(strings.connected, style = MaterialTheme.typography.labelMedium, color = AIFDThemeExt.colors.safe, fontWeight = FontWeight.Medium)
                                            }
                                        }
                                        else -> {
                                            Button(
                                                onClick = { onConnect(nearby) },
                                                enabled = connectingDeviceId == null,
                                                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                                            ) {
                                                Text(strings.connect)
                                            }
                                        }
                                    }
                                }

                                if (isConnecting) {
                                    Spacer(Modifier.height(12.dp))
                                    LinearProgressIndicator(
                                        progress = connectionProgress / 100f,
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(4.dp)
                                            .clip(RoundedCornerShape(2.dp))
                                    )
                                    Spacer(Modifier.height(4.dp))
                                    Text(
                                        text = when {
                                            connectionProgress < 30 -> strings.discoveringDevice
                                            connectionProgress < 60 -> strings.establishingConnection
                                            connectionProgress < 90 -> strings.syncingData
                                            else -> strings.almostDone
                                        },
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
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
