package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import com.aifd.data.DailySteps
import com.aifd.data.MockDataProvider
import com.aifd.data.UserRole
import com.aifd.ui.components.LineChart
import com.aifd.ui.components.StepsBarChart
import com.aifd.ui.components.aifd.AifdChartCard
import com.aifd.ui.components.aifd.AifdChartEmptyState
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt
import com.aifd.viewmodel.CloudLoadState
import com.aifd.viewmodel.MetricTab
import com.aifd.viewmodel.MonitoringUiState
import com.aifd.viewmodel.MonitoringViewModel
import com.aifd.viewmodel.TimeRange

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MonitoringScreen(
    viewModel: MonitoringViewModel,
    role: UserRole
) {
    val uiState by viewModel.uiState.collectAsState()
    MonitoringScreenContent(
        uiState = uiState,
        onTabSelected = viewModel::selectTab,
        onTimeRangeSelected = viewModel::selectTimeRange,
        onRefreshCloud = viewModel::forceRefreshCloud,
        stats = viewModel.getStats(),
        isCaregiver = role == UserRole.CAREGIVER
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MonitoringScreenContent(
    uiState: MonitoringUiState,
    onTabSelected: (MetricTab) -> Unit = {},
    onTimeRangeSelected: (TimeRange) -> Unit = {},
    onRefreshCloud: () -> Unit = {},
    stats: Triple<Int, Int, Int> = Triple(0, 0, 0),
    isCaregiver: Boolean = false
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
            // ── Metric Tabs ──────────────────────────────────────
            TabRow(
                selectedTabIndex = uiState.activeTab.ordinal,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                contentColor = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.clip(RoundedCornerShape(12.dp))
            ) {
                Tab(
                    selected = uiState.activeTab == MetricTab.HEART_RATE,
                    onClick = { onTabSelected(MetricTab.HEART_RATE) }
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.Favorite,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(18.dp)
                        )
                        Text(strings.heartRate, style = MaterialTheme.typography.labelSmall)
                    }
                }
                Tab(
                    selected = uiState.activeTab == MetricTab.SPO2,
                    onClick = { onTabSelected(MetricTab.SPO2) }
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.WaterDrop,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp)
                        )
                        Text("SpO2", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }

            when (uiState.activeTab) {
                MetricTab.HEART_RATE -> HeartRateContent(uiState, onTimeRangeSelected, onRefreshCloud, stats, isCaregiver)
                MetricTab.SPO2 -> SpO2Content(uiState, onTimeRangeSelected, onRefreshCloud, stats, isCaregiver)
            }

            Spacer(modifier = Modifier.height(80.dp))
    }
}

// ── Cloud loading animation ───────────────────────────────────────────────────

@Composable
private fun CloudLoadingCard() {
    val infiniteTransition = rememberInfiniteTransition(label = "cloud_load")

    // Rotating sync icon
    val angle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue  = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 900, easing = LinearEasing)
        ),
        label = "rotate"
    )

    // Shimmer bar position (0 → 1 → 0)
    val shimmerPos by infiniteTransition.animateFloat(
        initialValue = -0.4f,
        targetValue  = 1.4f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = FastOutSlowInEasing)
        ),
        label = "shimmer"
    )

    val primaryColor = MaterialTheme.colorScheme.primary
    val trackColor   = MaterialTheme.colorScheme.surfaceVariant

    ElevatedCard(
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Sync,
                contentDescription = null,
                modifier = Modifier.size(22.dp).rotate(angle),
                tint = primaryColor
            )
            Column {
                Text(
                    text = "Đang tải dữ liệu từ Cloud…",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "Vui lòng chờ trong giây lát",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Custom shimmer bar — avoids LinearProgressIndicator BOM incompatibility
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
        ) {
            // Track
            drawRect(color = trackColor, size = size)
            // Shimmer stripe
            val stripeWidth = size.width * 0.35f
            val x = shimmerPos * size.width - stripeWidth / 2
            drawRect(
                color = primaryColor,
                topLeft = Offset(x.coerceIn(0f, size.width), 0f),
                size = Size(
                    width  = (stripeWidth - (x - (size.width - stripeWidth)).coerceAtLeast(0f))
                        .coerceIn(0f, stripeWidth),
                    height = size.height
                )
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TimeRangeSelector(
    selected: TimeRange,
    onSelected: (TimeRange) -> Unit,
    showLive: Boolean = true
) {
    val strings = AppLocalizations.strings
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        TimeRange.entries.forEach { range ->
            if (range == TimeRange.LIVE && !showLive) return@forEach
            val label = when (range) {
                TimeRange.LIVE -> strings.live
                TimeRange.ONE_HOUR -> strings.oneHour
                TimeRange.TWENTY_FOUR_HOURS -> strings.twentyFourHours
            }
            FilterChip(
                selected = selected == range,
                onClick = { onSelected(range) },
                label = {
                    if (range == TimeRange.LIVE && selected == range) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.FiberManualRecord,
                                contentDescription = null,
                                tint = AIFDThemeExt.colors.safe,
                                modifier = Modifier.size(8.dp)
                            )
                            Spacer(Modifier.width(4.dp))
                            Text(label)
                        }
                    } else {
                        Text(label)
                    }
                },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun StatsRow(stats: Triple<Int, Int, Int>, unit: String = "") {
    val strings = AppLocalizations.strings
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        listOf(strings.average to stats.first, strings.min to stats.second, strings.max to stats.third).forEach { (label, value) ->
            ElevatedCard(
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("$value$unit", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun HeartRateContent(
    uiState: MonitoringUiState,
    onTimeRangeSelected: (TimeRange) -> Unit,
    onRefreshCloud: () -> Unit = {},
    stats: Triple<Int, Int, Int>,
    isCaregiver: Boolean = false
) {
    val strings = AppLocalizations.strings

    // Caregiver không xem được Live (không có BLE) → tự chuyển sang 1H
    LaunchedEffect(isCaregiver) {
        if (isCaregiver && uiState.timeRange == TimeRange.LIVE) {
            onTimeRangeSelected(TimeRange.ONE_HOUR)
        }
    }

    TimeRangeSelector(
        selected  = uiState.timeRange,
        onSelected = onTimeRangeSelected,
        showLive  = !isCaregiver
    )

    // Cloud loading indicator (only for history tabs)
    if (uiState.timeRange != TimeRange.LIVE && uiState.cloudLoadState == CloudLoadState.LOADING) {
        CloudLoadingCard()
    }

    // Current value — chỉ hiện ở Live mode (caregiver không vào được Live nên ẩn luôn)
    if (!isCaregiver || uiState.timeRange == TimeRange.LIVE) {
    ElevatedCard(shape = RoundedCornerShape(16.dp)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(strings.current, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        text = uiState.healthData?.heartRate?.toString() ?: "--",
                        style = MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("bpm", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 4.dp))
                }
            }
            val statusName = uiState.healthData?.heartRateStatus?.name?.lowercase()?.replaceFirstChar { it.uppercase() } ?: strings.unknown
            com.aifd.ui.components.StatusBadge(
                text = statusName,
                color = when (uiState.healthData?.heartRateStatus) {
                    com.aifd.data.HealthStatus.HIGH -> MaterialTheme.colorScheme.error
                    com.aifd.data.HealthStatus.LOW -> AIFDThemeExt.colors.warning
                    else -> AIFDThemeExt.colors.safe
                }
            )
        }
    }
    } // end if (!isCaregiver || LIVE)

    // Chart card — only rendered for 1h and 24h modes (LIVE focuses on current value)
    if (uiState.timeRange != TimeRange.LIVE) {
        val hasChartData = uiState.chartData.any { it > 0 }
        AifdChartCard(
            title     = strings.heartRateTrend,
            trailing  = if (uiState.timeRange == TimeRange.ONE_HOUR) "1h" else "24h",
            onRefresh = onRefreshCloud
        ) {
            if (hasChartData) {
                LineChart(
                    data      = uiState.chartData,
                    lineColor = MaterialTheme.colorScheme.error,
                    fillColor = MaterialTheme.colorScheme.error.copy(alpha = 0.1f),
                    timeRange = uiState.timeRange,
                    unit      = "bpm"
                )
            } else {
                AifdChartEmptyState(
                    title    = strings.noChartData,
                    subtitle = strings.waitingForReadings
                )
            }
        }
        if (hasChartData) {
            StatsRow(stats)
        }
    }

    // Info/connect cards — hidden entirely for caregiver
    if (!isCaregiver) if (!uiState.isConnected || uiState.healthData == null || uiState.healthData.heartRate == 0) {
        ElevatedCard(
            shape = RoundedCornerShape(24.dp),
            elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(
                modifier = Modifier
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.surfaceVariant,
                                MaterialTheme.colorScheme.surface
                            )
                        )
                    )
                    .padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Watch,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = strings.noDeviceConnected,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = strings.connectDeviceToView,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = androidx.compose.ui.unit.TextUnit.Unspecified
                        )
                    }
                }
            }
        }
    } else {
        ElevatedCard(
            shape = RoundedCornerShape(24.dp),
            elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(
                modifier = Modifier
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.8f),
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                            )
                        )
                    )
                    .padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.error.copy(alpha = 0.1f),
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = strings.normalHeartRateRange,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                        Text(
                            text = strings.heartRateWarning,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = androidx.compose.ui.unit.TextUnit.Unspecified
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SpO2Content(
    uiState: MonitoringUiState,
    onTimeRangeSelected: (TimeRange) -> Unit,
    onRefreshCloud: () -> Unit = {},
    stats: Triple<Int, Int, Int>,
    isCaregiver: Boolean = false
) {
    val strings = AppLocalizations.strings

    // Caregiver không xem được Live → tự chuyển sang 1H
    LaunchedEffect(isCaregiver) {
        if (isCaregiver && uiState.timeRange == TimeRange.LIVE) {
            onTimeRangeSelected(TimeRange.ONE_HOUR)
        }
    }

    TimeRangeSelector(
        selected   = uiState.timeRange,
        onSelected = onTimeRangeSelected,
        showLive   = !isCaregiver
    )

    // Cloud loading indicator (only for history tabs)
    if (uiState.timeRange != TimeRange.LIVE && uiState.cloudLoadState == CloudLoadState.LOADING) {
        CloudLoadingCard()
    }

    // Current value — chỉ hiện ở Live mode
    if (!isCaregiver || uiState.timeRange == TimeRange.LIVE) {
    ElevatedCard(shape = RoundedCornerShape(16.dp)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(strings.current, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        text = uiState.healthData?.spO2?.toString() ?: "--",
                        style = MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("%", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 4.dp))
                }
            }
            val statusName = uiState.healthData?.spO2Status?.name?.lowercase()?.replaceFirstChar { it.uppercase() } ?: strings.unknown
            com.aifd.ui.components.StatusBadge(
                text = statusName,
                color = when (uiState.healthData?.spO2Status) {
                    com.aifd.data.HealthStatus.LOW -> AIFDThemeExt.colors.warning
                    else -> AIFDThemeExt.colors.safe
                }
            )
        }
    }
    } // end if (!isCaregiver || LIVE)

    if (uiState.timeRange != TimeRange.LIVE) {
        val hasChartData = uiState.chartData.any { it > 0 }
        AifdChartCard(
            title     = strings.spo2Trend,
            trailing  = if (uiState.timeRange == TimeRange.ONE_HOUR) "1h" else "24h",
            onRefresh = onRefreshCloud
        ) {
            if (hasChartData) {
                LineChart(
                    data      = uiState.chartData,
                    lineColor = MaterialTheme.colorScheme.primary,
                    fillColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                    timeRange = uiState.timeRange,
                    unit      = "%"
                )
            } else {
                AifdChartEmptyState(
                    title    = strings.noChartData,
                    subtitle = strings.waitingForReadings
                )
            }
        }
        if (hasChartData) {
            StatsRow(stats, "%")
        }
    }

    // Info/connect cards — hidden entirely for caregiver
    if (!isCaregiver) if (!uiState.isConnected || uiState.healthData == null || uiState.healthData.spO2 == 0) {
        ElevatedCard(
            shape = RoundedCornerShape(24.dp),
            elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(
                modifier = Modifier
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.surfaceVariant,
                                MaterialTheme.colorScheme.surface
                            )
                        )
                    )
                    .padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Watch,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = strings.noDeviceConnected,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = strings.connectDeviceToView,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = androidx.compose.ui.unit.TextUnit.Unspecified
                        )
                    }
                }
            }
        }
    } else {
        ElevatedCard(
            shape = RoundedCornerShape(24.dp),
            elevation = CardDefaults.elevatedCardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Box(
                modifier = Modifier
                    .background(
                        Brush.linearGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.8f),
                                MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.4f)
                            )
                        )
                    )
                    .padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Surface(
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(8.dp)
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = strings.normalSpo2Range,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            text = strings.lowSpo2Warning,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = androidx.compose.ui.unit.TextUnit.Unspecified
                        )
                    }
                }
            }
        }
    }
}


@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun MonitoringScreenPreview() {
    AIFDTheme {
        MonitoringScreenContent(
            uiState = MonitoringUiState(
                chartData = MockDataProvider.generateChartData(72.0, 3.0, 55.0, 110.0, 20)
            )
        )
    }
}
