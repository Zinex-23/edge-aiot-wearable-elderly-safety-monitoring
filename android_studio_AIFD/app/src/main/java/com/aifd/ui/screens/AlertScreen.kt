package com.aifd.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aifd.ui.localization.AppLocalizations
import com.aifd.ui.theme.AIFDTheme
import com.aifd.ui.theme.AIFDThemeExt

private const val COUNTDOWN_SECONDS = 15

/**
 * Full-screen fall alert with countdown, "I'm Safe", and "Call for Help" actions.
 */
@Composable
fun FallAlertScreen(
    onDismissAsSafe: () -> Unit = {},
    onCallForHelp: () -> Unit = {},
    deviceName: String = "AIFD Wearable Pro"
) {
    val strings = AppLocalizations.strings
    var countdown by remember { mutableIntStateOf(COUNTDOWN_SECONDS) }
    var isCallingHelp by remember { mutableStateOf(false) }

    // Countdown timer
    LaunchedEffect(countdown) {
        if (countdown > 0 && !isCallingHelp) {
            kotlinx.coroutines.delay(1000L)
            countdown--
        } else if (countdown <= 0 && !isCallingHelp) {
            isCallingHelp = true
            onCallForHelp()
        }
    }

    if (isCallingHelp) {
        // Calling for help state
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f)),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                val alpha by infiniteTransition.animateFloat(
                    initialValue = 0.3f,
                    targetValue = 1f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(800),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "pulseAlpha"
                )
                Box(
                    modifier = Modifier
                        .size(96.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.errorContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.Phone,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error,
                        modifier = Modifier.size(48.dp)
                    )
                }
                Spacer(Modifier.height(24.dp))
                Text(
                    strings.callingForHelp,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    strings.notifyingContacts,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        return
    }

    // Main fall alert UI
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.15f))
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        // Top: alert content
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Animated alert icon with pulse rings
            Box(contentAlignment = Alignment.Center) {
                val infiniteTransition = rememberInfiniteTransition(label = "rings")
                val ringScale by infiniteTransition.animateFloat(
                    initialValue = 1f,
                    targetValue = 1.5f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(1500, easing = LinearEasing),
                        repeatMode = RepeatMode.Restart
                    ),
                    label = "ringScale"
                )
                val ringAlpha by infiniteTransition.animateFloat(
                    initialValue = 0.4f,
                    targetValue = 0f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(1500, easing = LinearEasing),
                        repeatMode = RepeatMode.Restart
                    ),
                    label = "ringAlpha"
                )

                // Pulse ring - use graphicsLayer to avoid layout shifts
                Box(
                    modifier = Modifier
                        .size(128.dp)
                        .graphicsLayer {
                            scaleX = ringScale
                            scaleY = ringScale
                            alpha = ringAlpha * 0.3f
                        }
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.error)
                )

                // Main circle
                Box(
                    modifier = Modifier
                        .size(128.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.error.copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.Warning,
                        contentDescription = strings.fallDetected,
                        tint = MaterialTheme.colorScheme.error,
                        modifier = Modifier.size(64.dp)
                    )
                }
            }

            Spacer(Modifier.height(32.dp))

            Text(
                text = strings.fallDetected,
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = strings.okayPrompt,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(Modifier.height(32.dp))

            // Countdown ring
            Box(
                modifier = Modifier.size(112.dp),
                contentAlignment = Alignment.Center
            ) {
                val sweepAngle = (countdown.toFloat() / COUNTDOWN_SECONDS) * 360f

                Canvas(modifier = Modifier.fillMaxSize()) {
                    // Background ring
                    drawArc(
                        color = Color.Gray.copy(alpha = 0.2f),
                        startAngle = -90f,
                        sweepAngle = 360f,
                        useCenter = false,
                        style = Stroke(width = 8f, cap = StrokeCap.Round),
                        topLeft = Offset(12f, 12f),
                        size = Size(size.width - 24f, size.height - 24f)
                    )
                    // Progress ring
                    drawArc(
                        color = Color(0xFFDE3730), // Red50
                        startAngle = -90f,
                        sweepAngle = sweepAngle,
                        useCenter = false,
                        style = Stroke(width = 8f, cap = StrokeCap.Round),
                        topLeft = Offset(12f, 12f),
                        size = Size(size.width - 24f, size.height - 24f)
                    )
                }

                Text(
                    text = "$countdown",
                    fontSize = 40.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }

            Spacer(Modifier.height(12.dp))

            Text(
                text = strings.callingContactsIn(countdown),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(Modifier.height(16.dp))

        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Button(
                onClick = onDismissAsSafe,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AIFDThemeExt.colors.safe
                )
            ) {
                Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(12.dp))
                Text(strings.imSafe, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            }

            OutlinedButton(
                onClick = {
                    isCallingHelp = true
                    onCallForHelp()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.error
                ),
                border = ButtonDefaults.outlinedButtonBorder.copy(
                    brush = androidx.compose.ui.graphics.SolidColor(MaterialTheme.colorScheme.error)
                )
            ) {
                Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(12.dp))
                Text(strings.callForHelp, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Preview(showBackground = true, showSystemUi = true)
@Composable
private fun FallAlertScreenPreview() {
    AIFDTheme {
        FallAlertScreen()
    }
}
