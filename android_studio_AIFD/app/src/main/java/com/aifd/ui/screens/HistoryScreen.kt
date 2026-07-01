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
    onBack: () -> Unit = {},
    onClearAll: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    var filter by remember { mutableStateOf("all") }
    var showClearDialog by remember { mutableStateOf(false) }
    var showAll by remember { mutableStateOf(false) }

    val filteredEvents = when (filter) {
        "fall"       -> events.filter { it.type == EventType.FALL }
        "safe"       -> events.filter { it.type == EventType.SAFE }
        "vitals"     -> events.filter { it.type == EventType.VITALS }
        "disconnect" -> events.filter { it.type in listOf(EventType.DISCONNECT, EventType.SYNC_FAILED) }
        "alert"      -> events.filter { it.type == EventType.ALERT }
        else         -> events
    }

    // Reset về trang đầu khi đổi filter
    LaunchedEffect(filter) { showAll = false }

    val PAGE_SIZE = 10
    val displayedEvents = if (showAll) filteredEvents else filteredEvents.take(PAGE_SIZE)
    val hiddenCount = filteredEvents.size - displayedEvents.size

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
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChipItem(strings.filterAll, filter == "all", events.size) { filter = "all" }
            FilterChipItem(strings.filterFalls, filter == "fall",
                events.count { it.type == EventType.FALL }) { filter = "fall" }
            FilterChipItem("An toàn", filter == "safe",
                events.count { it.type == EventType.SAFE }) { filter = "safe" }
            FilterChipItem("Sinh hiệu", filter == "vitals",
                events.count { it.type == EventType.VITALS }) { filter = "vitals" }
            FilterChipItem(strings.filterDisconnects, filter == "disconnect",
                events.count { it.type in listOf(EventType.DISCONNECT, EventType.SYNC_FAILED) }) { filter = "disconnect" }
            FilterChipItem(strings.filterAlerts, filter == "alert",
                events.count { it.type == EventType.ALERT }) { filter = "alert" }
        }

        // Nút xóa tất cả — bên dưới filter chips, bo viền
        if (events.isNotEmpty()) {
            OutlinedButton(
                onClick = { showClearDialog = true },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(10.dp),
                border = androidx.compose.foundation.BorderStroke(
                    1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.5f)
                ),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.error
                )
            ) {
                Icon(Icons.Default.DeleteSweep, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(6.dp))
                Text("Xóa tất cả thông báo", style = MaterialTheme.typography.labelLarge)
            }
        }

        if (filteredEvents.isEmpty()) {
                AifdEmptyState(
                    icon = if (filter == "all") Icons.Default.Notifications else Icons.Default.FilterList,
                    title = if (filter == "all") strings.noEventsTitle else strings.noEventsFound,
                    subtitle = if (filter == "all") strings.noEventsSubtitle
                              else strings.noFilteredEvents(filter)
                )
            } else {
                displayedEvents.forEach { event ->
                    EventListItem(event = event, onClick = { onEventClick(event.id) })
                }

                // Nút "Xem thêm" — chỉ hiện khi còn thông báo ẩn
                if (hiddenCount > 0) {
                    OutlinedButton(
                        onClick = { showAll = true },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(Icons.Default.ExpandMore, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Xem thêm $hiddenCount thông báo", style = MaterialTheme.typography.labelLarge)
                    }
                }
            }

        Spacer(Modifier.height(80.dp))
    }

    // Confirm clear dialog
    if (showClearDialog) {
        AlertDialog(
            onDismissRequest = { showClearDialog = false },
            icon = { Icon(Icons.Default.DeleteSweep, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Xóa tất cả thông báo?", fontWeight = FontWeight.SemiBold) },
            text  = { Text("Toàn bộ ${events.size} thông báo sẽ bị xóa vĩnh viễn.") },
            confirmButton = {
                TextButton(
                    onClick = { showClearDialog = false; onClearAll() },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) { Text("Xóa tất cả", fontWeight = FontWeight.SemiBold) }
            },
            dismissButton = {
                TextButton(onClick = { showClearDialog = false }) { Text("Hủy") }
            }
        )
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
    EventType.FALL        -> Icons.Default.Warning       to MaterialTheme.colorScheme.error
    EventType.SAFE        -> Icons.Default.CheckCircle   to AIFDThemeExt.colors.safe
    EventType.VITALS      -> Icons.Default.Favorite      to AIFDThemeExt.colors.warning
    EventType.DISCONNECT  -> Icons.Default.WifiOff       to AIFDThemeExt.colors.warning
    EventType.SYNC_FAILED -> Icons.Default.CloudOff      to MaterialTheme.colorScheme.onSurfaceVariant
    EventType.LOW_BATTERY -> Icons.Default.BatteryAlert  to AIFDThemeExt.colors.warning
    EventType.ALERT       -> Icons.Default.Notifications to MaterialTheme.colorScheme.primary
}

private fun formatEventTime(date: Date): String {
    val vn = TimeZone.getTimeZone("Asia/Ho_Chi_Minh")
    val fmt = SimpleDateFormat("HH:mm  dd/MM/yyyy", Locale("vi", "VN")).also { it.timeZone = vn }
    return fmt.format(date)
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun HistoryScreenPreview() {
    AIFDTheme {
        HistoryScreen(events = MockDataProvider.fallEvents)
    }
}
