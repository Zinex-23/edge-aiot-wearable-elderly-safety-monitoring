import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_text_styles.dart';

class AppTheme {
  const AppTheme._();

  static ThemeData get lightTheme =>
      _buildTheme(AppColors.light, Brightness.light);

  static ThemeData get darkTheme =>
      _buildTheme(AppColors.dark, Brightness.dark);

  static ThemeData _buildTheme(AppPalette palette, Brightness brightness) {
    final onAccent = brightness == Brightness.light
        ? Colors.white
        : const Color(0xFF07120E);
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: palette.accent,
      onPrimary: onAccent,
      secondary: palette.accentSecondary,
      onSecondary: onAccent,
      error: palette.danger,
      onError: Colors.white,
      surface: palette.surface,
      onSurface: palette.textPrimary,
    );

    final base = ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: palette.background,
      dividerColor: palette.divider,
      fontFamily: 'SF Pro Display',
    );

    return base.copyWith(
      textTheme: TextTheme(
        displayLarge: AppTextStyles.display,
        headlineMedium: AppTextStyles.headline,
        titleLarge: AppTextStyles.title,
        bodyMedium: AppTextStyles.body,
        bodyLarge: AppTextStyles.bodyStrong,
        labelMedium: AppTextStyles.label,
      ),
      cardTheme: const CardThemeData(
        color: Colors.transparent,
        elevation: 0,
        margin: EdgeInsets.zero,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: palette.backgroundRaised.withValues(alpha: 0.96),
        elevation: 0,
        indicatorColor: palette.surfaceMuted,
        shadowColor: palette.shadow,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => AppTextStyles.label.copyWith(
            color: states.contains(WidgetState.selected)
                ? palette.textPrimary
                : palette.textMuted,
          ),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: palette.surfaceSoft,
        contentTextStyle: AppTextStyles.bodyStrong,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      iconTheme: IconThemeData(color: palette.textPrimary),
      chipTheme: base.chipTheme.copyWith(
        side: BorderSide.none,
        backgroundColor: palette.surfaceMuted,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: palette.accent,
          foregroundColor: onAccent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(22),
          ),
        ),
      ),
    );
  }
}
