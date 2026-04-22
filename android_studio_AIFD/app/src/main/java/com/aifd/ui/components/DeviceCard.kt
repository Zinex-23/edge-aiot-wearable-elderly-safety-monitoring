package com.aifd.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.ConnectionStatus
import com.aifd.data.DeviceInfo
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt

/**
 * Card displaying connected BLE device information with status indicator.
 */
@Composable
fun DeviceCard(
    device: DeviceInfo,
    onClick: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val strings = AppLocalizations.strings
    val isConnected = device.connectionStatus == ConnectionStatus.CONNECTED

    ElevatedCard(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                modifier = Modifier.weight(1f),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Bluetooth icon
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Bluetooth,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                }

                Column {
                    Text(
                        text = device.name,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StatusBadge(
                            text = if (isConnected) strings.connected else strings.disconnected,
                            color = if (isConnected) AIFDThemeExt.colors.safe
                                    else MaterialTheme.colorScheme.error,
                            showDot = true,
                            dotAnimated = isConnected
                        )
                        Text(
                            text = "${device.battery}% ${strings.battery}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = strings.details,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun DeviceCardPreview() {
    AIFDTheme {
        DeviceCard(
            device = DeviceInfo(
                name = "AIFD Wearable Pro",
                id = "AIFD-001",
                battery = 78,
                signalStrength = -45,
                connectionStatus = ConnectionStatus.CONNECTED
            )
        )
    }
}
