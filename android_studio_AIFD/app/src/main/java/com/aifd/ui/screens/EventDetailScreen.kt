package com.aifd.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
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
import com.aifd.data.*
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EventDetailScreen(
    event: FallEvent?,
    onBack: () -> Unit = {}
) {
    val strings = AppLocalizations.strings
    if (event == null) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(strings.eventNotFound, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = strings.back)
            }
            // Event header
            ElevatedCard(shape = RoundedCornerShape(16.dp)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    val (icon, iconColor) = getEventIconAndColor(event.type)
                    Box(
                        modifier = Modifier
                            .size(56.dp)
                            .clip(RoundedCornerShape(16.dp))
                            .background(iconColor.copy(alpha = 0.12f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(24.dp))
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(strings.eventTitle(event.type), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                            EventStatusChip(event.status)
                        }
                        Spacer(Modifier.height(4.dp))
                        Text(
                            formatFullDate(event.timestamp),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Details
            ElevatedCard(shape = RoundedCornerShape(16.dp)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(strings.details, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(16.dp))
                    DetailRow(Icons.Default.Schedule, strings.time, formatTime(event.timestamp))
                    Spacer(Modifier.height(12.dp))
                    DetailRow(Icons.Default.Smartphone, strings.device, event.deviceName)
                    event.location?.let {
                        Spacer(Modifier.height(12.dp))
                        DetailRow(Icons.Default.LocationOn, strings.location, it)
                    }
                    event.userResponse?.let {
                        Spacer(Modifier.height(12.dp))
                        DetailRow(Icons.Default.Person, strings.userResponse, it)
                    }
                    event.detail?.let {
                        Spacer(Modifier.height(12.dp))
                        DetailRow(Icons.Default.Info, "Chi tiết", it)
                    }
                }
            }

            // Timeline
            ElevatedCard(shape = RoundedCornerShape(16.dp)) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(strings.timeline, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(16.dp))
                    val steps = getTimelineSteps(event)
                    steps.forEachIndexed { index, step ->
                        TimelineStepItem(
                            icon = step.icon,
                            title = step.title,
                            description = step.description,
                            time = step.time,
                            isCompleted = step.isCompleted,
                            isLast = index == steps.lastIndex
                        )
                    }
                }
            }

            Spacer(Modifier.height(80.dp))
    }
}

@Composable
private fun EventStatusChip(status: EventStatus) {
    val strings = AppLocalizations.strings
    val (text, color) = when (status) {
        EventStatus.RESOLVED -> strings.resolved to AIFDThemeExt.colors.safe
        EventStatus.PENDING -> strings.pending to AIFDThemeExt.colors.warning
        EventStatus.DISMISSED -> strings.dismissed to MaterialTheme.colorScheme.onSurfaceVariant
    }
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = color.copy(alpha = 0.12f)
    ) {
        Text(
            text, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelSmall, color = color, fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun DetailRow(icon: ImageVector, label: String, value: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Surface(
            shape = RoundedCornerShape(8.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.size(40.dp)
        ) {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Column {
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun TimelineStepItem(
    icon: ImageVector,
    title: String,
    description: String,
    time: Date,
    isCompleted: Boolean,
    isLast: Boolean
) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(32.dp)
                    .clip(CircleShape)
                    .background(
                        if (isCompleted) AIFDThemeExt.colors.safeContainer
                        else MaterialTheme.colorScheme.surfaceVariant
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    icon, contentDescription = null, modifier = Modifier.size(16.dp),
                    tint = if (isCompleted) AIFDThemeExt.colors.safe else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .width(2.dp)
                        .height(32.dp)
                        .background(
                            if (isCompleted) AIFDThemeExt.colors.safe.copy(alpha = 0.3f)
                            else MaterialTheme.colorScheme.surfaceVariant
                        )
                )
            }
        }
        Column(modifier = Modifier.padding(bottom = if (isLast) 0.dp else 16.dp)) {
            Text(title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(formatTime(time), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
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

private data class TimelineStep(
    val icon: ImageVector,
    val title: String,
    val description: String,
    val time: Date,
    val isCompleted: Boolean
)

@Composable
private fun getTimelineSteps(event: FallEvent): List<TimelineStep> {
    val strings = AppLocalizations.strings
    if (event.type == EventType.FALL) {
        return listOf(
            TimelineStep(Icons.Default.Warning, strings.fallDetected, strings.unusualMotionDetected, event.timestamp, true),
            TimelineStep(Icons.Default.Notifications, strings.alertTriggered, strings.countdownStarted, Date(event.timestamp.time + 1000), true),
            TimelineStep(
                if (event.userResponse == "I'm Safe") Icons.Default.CheckCircle else Icons.Default.Phone,
                event.userResponse ?: strings.userResponse,
                if (event.userResponse == "I'm Safe") strings.userOkay else strings.emergencyContactsNotified,
                Date(event.timestamp.time + 8000), true
            ),
            TimelineStep(Icons.Default.CheckCircle, strings.eventResolved, strings.noFurtherAction, Date(event.timestamp.time + 10000), event.status == EventStatus.RESOLVED)
        )
    }
    if (event.type == EventType.DISCONNECT) {
        return listOf(
            TimelineStep(Icons.Default.WifiOff, strings.disconnected, strings.caregiverNoBle, event.timestamp, true),
            TimelineStep(Icons.Default.Notifications, strings.notificationSettings, strings.manageAlerts, Date(event.timestamp.time + 5000), true)
        )
    }
    return listOf(
        TimelineStep(Icons.Default.Notifications, strings.eventTitle(event.type), strings.details, event.timestamp, true)
    )
}

@Composable
private fun formatFullDate(date: Date): String =
    SimpleDateFormat("EEEE, MMMM d, yyyy 'at' h:mm:ss a", AppLocalizations.strings.locale).format(date)

@Composable
private fun formatTime(date: Date): String =
    SimpleDateFormat("h:mm:ss a", AppLocalizations.strings.locale).format(date)

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun EventDetailScreenPreview() {
    AIFDTheme {
        EventDetailScreen(event = MockDataProvider.fallEvents.first())
    }
}
