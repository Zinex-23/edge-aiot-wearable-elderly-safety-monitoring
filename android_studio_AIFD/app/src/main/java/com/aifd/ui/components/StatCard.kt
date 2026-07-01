package com.aifd.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt

/**
 * A summary card displaying a single health metric with icon, value, unit, status badge,
 * and optional chevron for navigation.
 */
@Composable
fun StatCard(
    icon: ImageVector,
    iconTint: Color,
    iconBackground: Color,
    label: String,
    value: String,
    unit: String,
    statusText: String? = null,
    statusColor: Color? = null,
    onClick: () -> Unit = {},
    modifier: Modifier = Modifier,
    bottomContent: @Composable (() -> Unit)? = null
) {
    val strings = AppLocalizations.strings
    ElevatedCard(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        )
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    modifier = Modifier.weight(1f),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Icon container
                    Box(
                        modifier = Modifier
                            .size(56.dp)
                            .clip(RoundedCornerShape(16.dp))
                            .background(iconBackground),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = icon,
                            contentDescription = label,
                            tint = iconTint,
                            modifier = Modifier.size(28.dp)
                        )
                    }

                    // Value
                    Column {
                        Text(
                            text = label,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            verticalAlignment = Alignment.Bottom,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Text(
                                text = value,
                                fontSize = 36.sp,
                                fontWeight = FontWeight.Bold,
                                color = statusColor ?: MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = unit,
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(bottom = 4.dp)
                            )
                        }
                    }
                }

                Column(
                    horizontalAlignment = Alignment.End,
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    statusText?.let { text ->
                        val bg = statusColor?.copy(alpha = 0.12f)
                            ?: MaterialTheme.colorScheme.primaryContainer
                        val fg = statusColor ?: MaterialTheme.colorScheme.primary
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = bg
                        ) {
                            Text(
                                text = text,
                                color = fg,
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                    Icon(
                        imageVector = Icons.Default.ChevronRight,
                        contentDescription = strings.viewDetails,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }

            bottomContent?.invoke()
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StatCardPreview() {
    AIFDTheme {
        StatCard(
            icon = Icons.Default.ChevronRight,
            iconTint = MaterialTheme.colorScheme.error,
            iconBackground = MaterialTheme.colorScheme.errorContainer,
            label = "Heart Rate",
            value = "72",
            unit = "bpm",
            statusText = "Normal",
            statusColor = AIFDThemeExt.colors.safe
        )
    }
}
