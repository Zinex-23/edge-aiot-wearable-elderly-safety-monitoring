package com.aifd.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.data.*
import com.aifd.ui.components.aifd.AifdEmptyState
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    events: List<FallEvent>,
    onEventClick: (String) -> Unit = {},
    onBack: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    var filter by remember { mutableStateOf("all") }

    val filteredEvents = when (filter) {
        "fall" -> events.filter { it.type == EventType.FALL }
        "disconnect" -> events.filter { it.type == EventType.DISCONNECT }
        "alert" -> events.filter { it.type == EventType.ALERT }
        else -> events
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
            // Filter chips
            Row(
                modifier = Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChipItem(strings.filterAll, filter == "all", events.size) { filter = "all" }
                FilterChipItem(strings.filterFalls, filter == "fall", events.count { it.type == EventType.FALL }) { filter = "fall" }
                FilterChipItem(strings.filterDisconnects, filter == "disconnect", events.count { it.type == EventType.DISCONNECT }) { filter = "disconnect" }
                FilterChipItem(strings.filterAlerts, filter == "alert", events.count { it.type == EventType.ALERT }) { filter = "alert" }
            }

            if (filteredEvents.isEmpty()) {
                AifdEmptyState(
                    icon = if (filter == "all") Icons.Default.Notifications else Icons.Default.FilterList,
                    title = if (filter == "all") strings.noEventsTitle else strings.noEventsFound,
                    subtitle = if (filter == "all") strings.noEventsSubtitle
                              else strings.noFilteredEvents(filter)
                )
            } else {
                filteredEvents.forEach { event ->
                    EventListItem(event = event, onClick = { onEventClick(event.id) })
                }
            }

            Spacer(Modifier.height(80.dp))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilterChipItem(label: String, isActive: Boolean, count: Int, onClick: () -> Unit) {
    FilterChip(
        selected = isActive,
        onClick = onClick,
        label = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(label)
                Surface(
                    shape = CircleShape,
                    color = if (isActive) MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.2f)
                            else MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        text = "$count",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        style = MaterialTheme.typography.labelSmall
                    )
                }
            }
        }
    )
}

@Composable
private fun EventListItem(
    event: FallEvent,
    onClick: () -> Unit
) {
    val (icon, iconColor) = getEventIconAndColor(event.type)

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp)
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
                    .clip(RoundedCornerShape(12.dp))
                    .background(iconColor.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(20.dp))
            }

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = AppLocalizations.strings.eventTitle(event.type),
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.weight(1f)
                    )
                    StatusChip(event.status)
                }
                Spacer(Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        formatEventTime(event.timestamp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text("•", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(
                        event.deviceName,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Icon(
                Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@Composable
private fun StatusChip(status: EventStatus) {
    val strings = AppLocalizations.strings
    val (text, color) = when (status) {
        EventStatus.RESOLVED -> strings.resolved to AIFDThemeExt.colors.safe
        EventStatus.PENDING -> strings.pending to AIFDThemeExt.colors.warning
        EventStatus.DISMISSED -> strings.dismissed to MaterialTheme.colorScheme.onSurfaceVariant
    }
    Surface(
        shape = RoundedCornerShape(6.dp),
        color = color.copy(alpha = 0.12f)
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
            style = MaterialTheme.typography.labelSmall,
            color = color,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun getEventIconAndColor(type: EventType): Pair<ImageVector, Color> = when (type) {
    EventType.FALL -> Icons.Default.Warning to MaterialTheme.colorScheme.error
    EventType.DISCONNECT -> Icons.Default.WifiOff to AIFDThemeExt.colors.warning
    EventType.LOW_BATTERY -> Icons.Default.BatteryAlert to AIFDThemeExt.colors.warning
    EventType.ALERT -> Icons.Default.Notifications to MaterialTheme.colorScheme.primary
}

@Composable
private fun formatEventTime(date: Date): String {
    val strings = AppLocalizations.strings
    val now = System.currentTimeMillis()
    val diff = now - date.time
    val hours = diff / (1000 * 60 * 60)
    val days = hours / 24
    return when {
        hours < 1 -> strings.justNow
        hours < 24 -> strings.hoursAgo(hours)
        days < 7 -> strings.daysAgo(days)
        else -> SimpleDateFormat("MMM d", AppLocalizations.strings.locale).format(date)
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun HistoryScreenPreview() {
    AIFDTheme {
        HistoryScreen(events = MockDataProvider.fallEvents)
    }
}
