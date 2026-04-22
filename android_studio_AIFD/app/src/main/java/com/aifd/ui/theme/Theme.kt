package com.aifd.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// ─── Extended colour slots not covered by Material 3 ─────────────
data class ExtendedColors(
    val safe: Color,
    val safeContainer: Color,
    val onSafe: Color,
    val onSafeContainer: Color,
    val warning: Color,
    val warningContainer: Color,
    val onWarning: Color,
    val onWarningContainer: Color
)

val LocalExtendedColors = staticCompositionLocalOf {
    ExtendedColors(
        safe = Green50,
        safeContainer = Green90,
        onSafe = Neutral100,
        onSafeContainer = Green10,
        warning = Amber40,
        warningContainer = Amber90,
        onWarning = Neutral100,
        onWarningContainer = Amber20
    )
}

// ─── Light colour scheme ─────────────────────────────────────────
private val LightColorScheme = lightColorScheme(
    primary = Blue40,
    onPrimary = Neutral100,
    primaryContainer = Blue90,
    onPrimaryContainer = Blue10,
    secondary = Neutral40,
    onSecondary = Neutral100,
    secondaryContainer = Neutral90,
    onSecondaryContainer = Neutral10,
    tertiary = Green40,
    onTertiary = Neutral100,
    tertiaryContainer = Green90,
    onTertiaryContainer = Green10,
    error = Red40,
    onError = Neutral100,
    errorContainer = Red90,
    onErrorContainer = Red10,
    background = Neutral98,
    onBackground = Neutral10,
    surface = Neutral100,
    onSurface = Neutral10,
    surfaceVariant = Neutral94,
    onSurfaceVariant = Neutral40,
    outline = Neutral60,
    outlineVariant = Neutral87,
    inverseSurface = Neutral20,
    inverseOnSurface = Neutral95
)

private val LightExtended = ExtendedColors(
    safe = Green50,
    safeContainer = Green90,
    onSafe = Neutral100,
    onSafeContainer = Green10,
    warning = Amber40,
    warningContainer = Amber90,
    onWarning = Neutral100,
    onWarningContainer = Amber20
)

// ─── Dark colour scheme ──────────────────────────────────────────
private val DarkColorScheme = darkColorScheme(
    primary = Blue80,
    onPrimary = Blue20,
    primaryContainer = Blue30,
    onPrimaryContainer = Blue90,
    secondary = Neutral80,
    onSecondary = Neutral20,
    secondaryContainer = Neutral30,
    onSecondaryContainer = Neutral90,
    tertiary = Green80,
    onTertiary = Green20,
    tertiaryContainer = Green30,
    onTertiaryContainer = Green90,
    error = Red80,
    onError = Red20,
    errorContainer = Red30,
    onErrorContainer = Red90,
    background = Neutral6,
    onBackground = Neutral90,
    surface = Neutral10,
    onSurface = Neutral90,
    surfaceVariant = Neutral24,
    onSurfaceVariant = Neutral80,
    outline = Neutral50,
    outlineVariant = Neutral30,
    inverseSurface = Neutral90,
    inverseOnSurface = Neutral20
)

private val DarkExtended = ExtendedColors(
    safe = Green80,
    safeContainer = Green30,
    onSafe = Green20,
    onSafeContainer = Green90,
    warning = Amber80,
    warningContainer = Amber30,
    onWarning = Amber20,
    onWarningContainer = Amber90
)

// ─── Theme Enum ──────────────────────────────────────────────────
enum class AppThemeMode {
    LIGHT, DARK, SYSTEM
}

// ─── Theme Composable ────────────────────────────────────────────
@Composable
fun AIFDTheme(
    themeMode: AppThemeMode = AppThemeMode.SYSTEM,
    content: @Composable () -> Unit
) {
    val darkTheme = when (themeMode) {
        AppThemeMode.LIGHT -> false
        AppThemeMode.DARK -> true
        AppThemeMode.SYSTEM -> isSystemInDarkTheme()
    }

    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    val extendedColors = if (darkTheme) DarkExtended else LightExtended

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    CompositionLocalProvider(LocalExtendedColors provides extendedColors) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = AppTypography,
            content = content
        )
    }
}

// Convenience accessor
object AIFDThemeExt {
    val colors: ExtendedColors
        @Composable
        get() = LocalExtendedColors.current
}
