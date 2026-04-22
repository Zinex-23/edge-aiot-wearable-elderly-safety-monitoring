package com.aifd.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.ConnectionStatus
import com.aifd.data.DeviceInfo
import com.aifd.data.MockDataProvider
import com.aifd.ui.components.StatusBadge
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceDetailScreen(
    device: DeviceInfo?,
    onRename: (String) -> Unit = {},
    onReconnect: () -> Unit = {},
    onDisconnect: () -> Unit = {},
    onNavigateToBlePairing: () -> Unit = {},
    onBack: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    var isRenaming by remember { mutableStateOf(false) }
    var newName by remember { mutableStateOf(device?.name ?: "") }
    var showDisconnectDialog by remember { mutableStateOf(false) }

    if (device == null) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(Icons.Default.Bluetooth, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(16.dp))
            Text(strings.noDeviceConnected, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Medium)
            Text(strings.connectDeviceToView, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(24.dp))
            Button(onClick = onNavigateToBlePairing) { Text(strings.pairDevice) }
        }
        return
    }

    val isConnected = device.connectionStatus == ConnectionStatus.CONNECTED

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(24.dp)
    ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = strings.back)
            }
            // Device header
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(RoundedCornerShape(20.dp))
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Default.Bluetooth, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(40.dp))
                }
                Spacer(Modifier.height(16.dp))

                if (isRenaming) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = newName,
                            onValueChange = { newName = it },
                            singleLine = true,
                            modifier = Modifier.width(200.dp)
                        )
                        IconButton(onClick = {
                            if (newName.isNotBlank()) {
                                onRename(newName)
                                isRenaming = false
                            }
                        }) {
                            Icon(Icons.Default.Check, contentDescription = strings.save)
                        }
                    }
                } else {
                    Text(device.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                }

                Spacer(Modifier.height(8.dp))
                StatusBadge(
                    text = when (device.connectionStatus) {
                        ConnectionStatus.CONNECTED -> strings.connected
                        ConnectionStatus.CONNECTING -> strings.connecting
                        ConnectionStatus.DISCONNECTED -> strings.disconnected
                    },
                    color = when (device.connectionStatus) {
                        ConnectionStatus.CONNECTED -> AIFDThemeExt.colors.safe
                        ConnectionStatus.CONNECTING -> AIFDThemeExt.colors.warning
                        ConnectionStatus.DISCONNECTED -> MaterialTheme.colorScheme.error
                    },
                    showDot = true,
                    dotAnimated = device.connectionStatus == ConnectionStatus.CONNECTED
                )
            }

            // Device info
            ElevatedCard(shape = RoundedCornerShape(16.dp)) {
                Column {
                    InfoRow(icon = Icons.Default.Bluetooth, label = strings.deviceId, value = device.id)
                    Divider()
                    InfoRow(
                        icon = Icons.Default.BatteryFull,
                        label = strings.battery,
                        value = "${device.battery}%",
                        valueColor = if (device.battery < 20) MaterialTheme.colorScheme.error else null
                    )
                    Divider()
                    InfoRow(icon = Icons.Default.SignalCellularAlt, label = strings.signalStrength, value = "${device.signalStrength} dBm")
                    Divider()
                    InfoRow(
                        icon = Icons.Default.Schedule,
                        label = strings.lastSync,
                        value = formatLastSync(device.lastSyncTime)
                    )
                    Divider()
                    InfoRow(icon = Icons.Default.Memory, label = strings.firmwareVersion, value = device.firmwareVersion)
                }
            }

            // Actions
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                if (!isConnected) {
                    Button(
                        onClick = onReconnect,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(strings.reconnect, fontWeight = FontWeight.SemiBold)
                    }
                }
                if (isConnected) {
                    OutlinedButton(
                        onClick = { showDisconnectDialog = true },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                        border = ButtonDefaults.outlinedButtonBorder.copy(
                            brush = androidx.compose.ui.graphics.SolidColor(MaterialTheme.colorScheme.error.copy(alpha = 0.3f))
                        )
                    ) {
                        Icon(Icons.Default.PowerSettingsNew, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(strings.disconnect, fontWeight = FontWeight.SemiBold)
                    }
                }
                OutlinedButton(
                    onClick = { isRenaming = true },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(strings.renameDevice, fontWeight = FontWeight.SemiBold)
                }
            }

            Spacer(Modifier.height(80.dp))
    }

    if (showDisconnectDialog) {
        AlertDialog(
            onDismissRequest = { showDisconnectDialog = false },
            title = { Text(strings.disconnectDeviceTitle) },
            text = { Text(strings.disconnectDeviceMessage(device.name)) },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDisconnectDialog = false
                        onDisconnect()
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) { Text(strings.disconnect) }
            },
            dismissButton = {
                TextButton(onClick = { showDisconnectDialog = false }) { Text(strings.cancel) }
            }
        )
    }
}

@Composable
private fun InfoRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String,
    valueColor: androidx.compose.ui.graphics.Color? = null
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(
            value,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.Medium,
            color = valueColor ?: MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
private fun formatLastSync(date: Date): String {
    val strings = AppLocalizations.strings
    val diff = System.currentTimeMillis() - date.time
    val minutes = diff / 60000
    return when {
        minutes < 1 -> strings.justNow
        minutes < 60 -> "$minutes min"
        else -> {
            val hours = minutes / 60
            if (hours < 24) strings.hoursAgo(hours)
            else SimpleDateFormat("MMM d", AppLocalizations.strings.locale).format(date)
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun DeviceDetailScreenPreview() {
    AIFDTheme {
        DeviceDetailScreen(device = MockDataProvider.device)
    }
}
