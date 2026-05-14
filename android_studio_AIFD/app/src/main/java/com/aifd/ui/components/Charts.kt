package com.aifd.ui.components

import android.graphics.Paint as NativePaint
import android.graphics.RectF
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aifd.ui.theme.AIFDTheme
import com.aifd.viewmodel.TimeRange
import java.util.Calendar
import kotlin.math.pow

/**
 * Line chart with:
 *  - Y-axis max label at top-left
 *  - Dots at every data point
 *  - Tap a dot → tooltip showing value + bucket timestamp
 *  - X-axis time labels (real HH:mm, only for ONE_HOUR and TWENTY_FOUR_HOURS)
 *  - Skips zero-value buckets (gaps in data rendered as breaks in the line)
 */
@Composable
fun LineChart(
    data: List<Int>,
    modifier: Modifier = Modifier,
    lineColor: Color = Color.Blue,
    fillColor: Color = Color.Blue.copy(alpha = 0.1f),
    showArea: Boolean = true,
    timeRange: TimeRange? = null,
    unit: String = ""
) {
    if (data.isEmpty()) return

    val density = LocalDensity.current
    val leftPad       = with(density) { 42.dp.toPx() }
    val rightPad      = with(density) { 8.dp.toPx() }
    val topPad        = with(density) { 22.dp.toPx() }
    val bottomPad     = with(density) { if (timeRange != null) 34.dp.toPx() else 8.dp.toPx() }
    val axisTextSz    = with(density) { 10.sp.toPx() }
    val ttValueSz     = with(density) { 13.sp.toPx() }
    val ttTimeSz      = with(density) { 10.sp.toPx() }
    val ttBoxW        = with(density) { 86.dp.toPx() }
    val ttBoxH        = with(density) { 50.dp.toPx() }
    val ttCornerR     = with(density) { 9.dp.toPx() }
    val ttAboveGap    = with(density) { 10.dp.toPx() }
    val dotR          = with(density) { 3.dp.toPx() }
    val dotSelR       = with(density) { 6.dp.toPx() }
    val tapRadius     = with(density) { 40.dp.toPx() }

    var selectedIndex by remember { mutableStateOf<Int?>(null) }
    var canvasSize    by remember { mutableStateOf(Size.Zero) }

    // Reset selection whenever the dataset changes
    LaunchedEffect(data) { selectedIndex = null }

    // Y scale: round to nearest step so scale stays stable as data fluctuates
    val positives = data.filter { it > 0 }
    val rawMax    = positives.maxOrNull() ?: 100
    val rawMin    = positives.minOrNull() ?: 0
    val step      = if (rawMax > 20) 5 else 1
    val yMax      = (((rawMax + step - 1) / step) * step).toFloat()   // ceil to step
    val yMin      = ((rawMin / step) * step).toFloat().coerceAtLeast(0f) // floor to step
    val yRange    = (yMax - yMin).coerceAtLeast(step.toFloat())

    // Pixel positions of each data point; null = zero-value bucket (gap)
    val points: List<Offset?> = remember(data, canvasSize, bottomPad) {
        if (canvasSize == Size.Zero) return@remember emptyList()
        val w = canvasSize.width - leftPad - rightPad
        val h = canvasSize.height - topPad - bottomPad
        data.mapIndexed { i, v ->
            if (v <= 0) null
            else Offset(
                x = leftPad + (i.toFloat() / (data.size - 1).coerceAtLeast(1)) * w,
                y = topPad + h - ((v.toFloat() - yMin) / yRange) * h
            )
        }
    }

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(200.dp)
            .onSizeChanged { sz -> canvasSize = Size(sz.width.toFloat(), sz.height.toFloat()) }
            .pointerInput(points) {
                detectTapGestures { tap ->
                    val hit = points.indices
                        .filter { points[it] != null }
                        .minByOrNull { i ->
                            val p = points[i]!!
                            (p.x - tap.x).pow(2) + (p.y - tap.y).pow(2)
                        }
                    selectedIndex = if (hit != null) {
                        val p = points[hit]!!
                        val d2 = (p.x - tap.x).pow(2) + (p.y - tap.y).pow(2)
                        if (d2 < tapRadius.pow(2)) (if (selectedIndex == hit) null else hit) else null
                    } else null
                }
            }
    ) {
        if (canvasSize == Size.Zero || points.isEmpty()) return@Canvas

        val chartW  = size.width - leftPad - rightPad
        val chartH  = size.height - topPad - bottomPad
        val nc      = drawContext.canvas.nativeCanvas
        val nowMs   = System.currentTimeMillis()
        val cal     = Calendar.getInstance()
        val axisClr = android.graphics.Color.argb(155, 120, 120, 120)

        // ── Y-axis: max label aligned with the actual data point Y ───────
        val axisPaint = NativePaint().apply {
            color     = axisClr
            textSize  = axisTextSz
            isAntiAlias = true
            textAlign = NativePaint.Align.LEFT
        }
        // Y position where rawMax sits on the chart (same formula as point computation)
        val maxDataY = topPad + chartH - ((rawMax.toFloat() - yMin) / yRange) * chartH
        // Faint guide line so the horizontal alignment is visible
        drawLine(
            color       = lineColor.copy(alpha = 0.13f),
            start       = Offset(leftPad, maxDataY),
            end         = Offset(size.width - rightPad, maxDataY),
            strokeWidth = 1.5f
        )
        // Label sits exactly at maxDataY (baseline offset ≈ half text height)
        nc.drawText(rawMax.toString(), 2f, maxDataY + axisTextSz * 0.38f, axisPaint)

        // ── X-axis: real-time labels (5 evenly spaced) ────────────────────
        if (timeRange != null) {
            val xPaint = NativePaint().apply {
                color     = axisClr
                textSize  = axisTextSz
                isAntiAlias = true
                textAlign = NativePaint.Align.CENTER
            }
            val spanMs = when (timeRange) {
                TimeRange.ONE_HOUR          -> 60L * 60_000L
                TimeRange.TWENTY_FOUR_HOURS -> 24L * 3_600_000L
                else                        -> 0L
            }
            val labelCount = if (timeRange == TimeRange.TWENTY_FOUR_HOURS) 5 else 5
            repeat(labelCount) { i ->
                val frac     = i.toFloat() / (labelCount - 1)
                val offsetMs = ((1f - frac) * spanMs).toLong()
                cal.timeInMillis = nowMs - offsetMs
                val text = "%02d:%02d".format(
                    cal.get(Calendar.HOUR_OF_DAY),
                    cal.get(Calendar.MINUTE)
                )
                nc.drawText(text, leftPad + frac * chartW, size.height - 2f, xPaint)
            }
        }

        // ── Group consecutive non-null points (skip zero-value gaps) ──────
        val segments = mutableListOf<List<Offset>>()
        var buf      = mutableListOf<Offset>()
        var prevIdx  = -2
        points.forEachIndexed { i, p ->
            if (p != null) {
                if (i == prevIdx + 1) buf.add(p)
                else {
                    if (buf.isNotEmpty()) segments.add(buf.toList())
                    buf = mutableListOf(p)
                }
                prevIdx = i
            }
        }
        if (buf.isNotEmpty()) segments.add(buf)

        // ── Area fill ─────────────────────────────────────────────────────
        if (showArea) {
            segments.forEach { seg ->
                if (seg.size < 2) return@forEach
                val path = Path()
                path.moveTo(seg[0].x, seg[0].y)
                for (k in 1 until seg.size) {
                    val cpX = (seg[k - 1].x + seg[k].x) / 2f
                    path.cubicTo(cpX, seg[k - 1].y, cpX, seg[k].y, seg[k].x, seg[k].y)
                }
                path.lineTo(seg.last().x, topPad + chartH)
                path.lineTo(seg.first().x, topPad + chartH)
                path.close()
                drawPath(
                    path  = path,
                    brush = Brush.verticalGradient(
                        colors = listOf(lineColor.copy(alpha = 0.40f), Color.Transparent),
                        startY = topPad, endY = topPad + chartH
                    )
                )
            }
        }

        // ── Lines ─────────────────────────────────────────────────────────
        segments.forEach { seg ->
            if (seg.size < 2) return@forEach
            val path = Path()
            path.moveTo(seg[0].x, seg[0].y)
            for (k in 1 until seg.size) {
                val cpX = (seg[k - 1].x + seg[k].x) / 2f
                path.cubicTo(cpX, seg[k - 1].y, cpX, seg[k].y, seg[k].x, seg[k].y)
            }
            drawPath(path, color = lineColor, style = Stroke(width = 3f))
        }

        // ── Dots ──────────────────────────────────────────────────────────
        points.forEachIndexed { i, p ->
            if (p == null) return@forEachIndexed
            if (i == selectedIndex) {
                // Halo + filled dot + white core
                drawCircle(lineColor.copy(alpha = 0.18f), dotSelR * 2.6f, p)
                drawCircle(lineColor,                      dotSelR,         p)
                drawCircle(Color.White,                    dotSelR * 0.45f, p)
            } else {
                drawCircle(lineColor.copy(alpha = 0.70f), dotR,         p)
                drawCircle(Color.White,                   dotR * 0.45f, p)
            }
        }

        // ── Tooltip ───────────────────────────────────────────────────────
        val si = selectedIndex
        if (si != null && si < points.size && points[si] != null) {
            val p     = points[si]!!
            val value = data[si]

            // Bucket start time for this data index
            val bucketMs = when (timeRange) {
                TimeRange.ONE_HOUR -> {
                    val cb = (nowMs / 300_000L) * 300_000L
                    cb - (data.size - 1 - si) * 300_000L
                }
                TimeRange.TWENTY_FOUR_HOURS -> {
                    val cb = (nowMs / 3_600_000L) * 3_600_000L
                    cb - (data.size - 1 - si) * 3_600_000L
                }
                else -> nowMs
            }
            cal.timeInMillis = bucketMs
            val timeText = "%02d:%02d".format(cal.get(Calendar.HOUR_OF_DAY), cal.get(Calendar.MINUTE))
            val valText  = if (unit.isNotEmpty()) "$value $unit" else "$value"

            // Position tooltip above the dot; keep it within canvas bounds
            val bx = (p.x - ttBoxW / 2f).coerceIn(leftPad, size.width - rightPad - ttBoxW)
            val by = (p.y - ttBoxH - ttAboveGap).coerceAtLeast(topPad - 4f)

            val bgPaint = NativePaint().apply {
                color       = android.graphics.Color.argb(235, 32, 32, 32)
                isAntiAlias = true
            }
            nc.drawRoundRect(RectF(bx, by, bx + ttBoxW, by + ttBoxH), ttCornerR, ttCornerR, bgPaint)

            val vPaint = NativePaint().apply {
                color         = android.graphics.Color.WHITE
                textSize      = ttValueSz
                isFakeBoldText = true
                isAntiAlias   = true
                textAlign     = NativePaint.Align.CENTER
            }
            val tPaint = NativePaint().apply {
                color       = android.graphics.Color.argb(210, 180, 180, 180)
                textSize    = ttTimeSz
                isAntiAlias = true
                textAlign   = NativePaint.Align.CENTER
            }
            val cx = bx + ttBoxW / 2f
            nc.drawText(valText,  cx, by + ttBoxH * 0.46f, vPaint)
            nc.drawText(timeText, cx, by + ttBoxH * 0.82f, tPaint)
        }
    }
}

/**
 * Bar chart for step data.
 */
@Composable
fun StepsBarChart(
    data: List<Pair<String, Int>>,
    modifier: Modifier = Modifier,
    barColor: Color = MaterialTheme.colorScheme.tertiary,
    backgroundColor: Color = MaterialTheme.colorScheme.surfaceVariant
) {
    if (data.isEmpty()) return

    val maxVal = data.maxOfOrNull { it.second }?.toFloat()?.coerceAtLeast(1f) ?: 1f

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(150.dp)
    ) {
        val barWidth = (size.width / data.size) * 0.6f
        val gapWidth = (size.width / data.size) * 0.4f

        data.forEachIndexed { index, (_, steps) ->
            val x         = index * (barWidth + gapWidth) + gapWidth / 2
            val barHeight = (steps / maxVal) * size.height * 0.85f

            drawRoundRect(
                color        = backgroundColor,
                topLeft      = Offset(x, size.height * 0.05f),
                size         = androidx.compose.ui.geometry.Size(barWidth, size.height * 0.85f),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
            )
            drawRoundRect(
                color        = barColor,
                topLeft      = Offset(x, size.height * 0.05f + (size.height * 0.85f - barHeight)),
                size         = androidx.compose.ui.geometry.Size(barWidth, barHeight),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun LineChartPreview() {
    AIFDTheme {
        LineChart(
            data      = listOf(0, 72, 74, 71, 73, 76, 72, 70, 75, 73, 0, 71),
            timeRange = TimeRange.ONE_HOUR,
            unit      = "bpm"
        )
    }
}
