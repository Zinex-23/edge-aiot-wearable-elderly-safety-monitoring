package com.aifd.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt

/**
 * Small coloured pill badge with optional pulsing dot indicator.
 */
@Composable
fun StatusBadge(
    text: String,
    color: Color,
    modifier: Modifier = Modifier,
    showDot: Boolean = false,
    dotAnimated: Boolean = false
) {
    val infiniteTransition = rememberInfiniteTransition(label = "dot")
    val dotAlpha by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "dotAlpha"
    )

    Surface(
        shape = RoundedCornerShape(8.dp),
        color = color.copy(alpha = 0.12f),
        modifier = modifier
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            if (showDot) {
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .clip(CircleShape)
                        .background(color)
                        .then(
                            if (dotAnimated) Modifier.alpha(dotAlpha) else Modifier
                        )
                )
            }
            Text(
                text = text,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.SemiBold,
                color = color
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StatusBadgePreview() {
    AIFDTheme {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatusBadge(text = "Connected", color = AIFDThemeExt.colors.safe, showDot = true, dotAnimated = true)
            StatusBadge(text = "Normal", color = AIFDThemeExt.colors.safe)
            StatusBadge(text = "High", color = MaterialTheme.colorScheme.error)
        }
    }
}
