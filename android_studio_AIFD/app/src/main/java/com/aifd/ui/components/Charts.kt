package com.aifd.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.ui.theme.AIFDTheme

/**
 * A simple line chart drawn on Canvas. Supports optional area fill.
 */
@Composable
fun LineChart(
    data: List<Int>,
    modifier: Modifier = Modifier,
    lineColor: Color = MaterialTheme.colorScheme.primary,
    fillColor: Color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
    showArea: Boolean = true
) {
    if (data.isEmpty()) return

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(180.dp)
    ) {
        val padding = 8f
        val minVal = (data.minOrNull() ?: 0) - 2f
        val maxVal = (data.maxOrNull() ?: 100) + 2f
        val range = (maxVal - minVal).coerceAtLeast(1f)

        val chartWidth = size.width - padding * 2
        val chartHeight = size.height - padding * 2

        val points = data.mapIndexed { index, value ->
            val x = padding + (index.toFloat() / (data.size - 1).coerceAtLeast(1)) * chartWidth
            val y = padding + chartHeight - ((value - minVal) / range) * chartHeight
            Offset(x, y)
        }

        // Area fill
        if (showArea && points.size > 1) {
            val areaPath = Path().apply {
                moveTo(points.first().x, points.first().y)
                for (i in 1 until points.size) {
                    lineTo(points[i].x, points[i].y)
                }
                lineTo(points.last().x, size.height)
                lineTo(points.first().x, size.height)
                close()
            }
            drawPath(areaPath, color = fillColor)
        }

        // Line
        if (points.size > 1) {
            val linePath = Path().apply {
                moveTo(points.first().x, points.first().y)
                for (i in 1 until points.size) {
                    lineTo(points[i].x, points[i].y)
                }
            }
            drawPath(linePath, color = lineColor, style = Stroke(width = 3f))
        }

        // Current value dot
        if (points.isNotEmpty()) {
            val last = points.last()
            drawCircle(color = lineColor, radius = 6f, center = last)
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
            val x = index * (barWidth + gapWidth) + gapWidth / 2
            val barHeight = (steps / maxVal) * size.height * 0.85f

            // Background bar
            drawRoundRect(
                color = backgroundColor,
                topLeft = Offset(x, size.height * 0.05f),
                size = androidx.compose.ui.geometry.Size(barWidth, size.height * 0.85f),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
            )

            // Filled bar
            drawRoundRect(
                color = barColor,
                topLeft = Offset(x, size.height * 0.05f + (size.height * 0.85f - barHeight)),
                size = androidx.compose.ui.geometry.Size(barWidth, barHeight),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(6f, 6f)
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun LineChartPreview() {
    AIFDTheme {
        LineChart(data = listOf(72, 74, 71, 73, 76, 72, 70, 75, 73, 71))
    }
}
