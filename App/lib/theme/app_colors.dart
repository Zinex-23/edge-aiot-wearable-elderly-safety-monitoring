import 'package:flutter/material.dart';

@immutable
class AppPalette {
  const AppPalette({
    required this.background,
    required this.backgroundRaised,
    required this.surface,
    required this.surfaceSoft,
    required this.surfaceMuted,
    required this.border,
    required this.divider,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.accent,
    required this.accentSecondary,
    required this.success,
    required this.warning,
    required this.danger,
    required this.info,
    required this.track,
    required this.shadow,
  });

  final Color background;
  final Color backgroundRaised;
  final Color surface;
  final Color surfaceSoft;
  final Color surfaceMuted;
  final Color border;
  final Color divider;

  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;

  final Color accent;
  final Color accentSecondary;
  final Color success;
  final Color warning;
  final Color danger;
  final Color info;

  final Color track;
  final Color shadow;
}

class AppColors {
  const AppColors._();

  static const AppPalette light = AppPalette(
    background: Color(0xFFF6F8FB),
    backgroundRaised: Color(0xFFFFFFFF),
    surface: Color(0xFFFFFFFF),
    surfaceSoft: Color(0xFFF3F6FB),
    surfaceMuted: Color(0xFFE8EEF6),
    border: Color(0xFFD8E1EC),
    divider: Color(0xFFE5EBF3),
    textPrimary: Color(0xFF101720),
    textSecondary: Color(0xFF566577),
    textMuted: Color(0xFF8591A1),
    accent: Color(0xFF1BC68A),
    accentSecondary: Color(0xFF4CA9F4),
    success: Color(0xFF21B66F),
    warning: Color(0xFFF1B641),
    danger: Color(0xFFE76273),
    info: Color(0xFF48A8F2),
    track: Color(0xFFDCE5EF),
    shadow: Color(0x180F1720),
  );

  static const AppPalette dark = AppPalette(
    background: Color(0xFF07090D),
    backgroundRaised: Color(0xFF0F1319),
    surface: Color(0xFF141922),
    surfaceSoft: Color(0xFF1B2230),
    surfaceMuted: Color(0xFF242D3B),
    border: Color(0xFF2B3443),
    divider: Color(0xFF242C38),
    textPrimary: Color(0xFFF5F7FA),
    textSecondary: Color(0xFFA4AFBF),
    textMuted: Color(0xFF727C8A),
    accent: Color(0xFF52E5A3),
    accentSecondary: Color(0xFF77D7FF),
    success: Color(0xFF4EE28E),
    warning: Color(0xFFFFC65C),
    danger: Color(0xFFFF6178),
    info: Color(0xFF8AD8FF),
    track: Color(0xFF212938),
    shadow: Color(0x55000000),
  );

  static AppPalette _active = light;

  static void applyThemeMode(ThemeMode themeMode) {
    _active = themeMode == ThemeMode.dark ? dark : light;
  }

  static bool get isLight => identical(_active, light);

  static Color get background => _active.background;
  static Color get backgroundRaised => _active.backgroundRaised;
  static Color get surface => _active.surface;
  static Color get surfaceSoft => _active.surfaceSoft;
  static Color get surfaceMuted => _active.surfaceMuted;
  static Color get border => _active.border;
  static Color get divider => _active.divider;

  static Color get textPrimary => _active.textPrimary;
  static Color get textSecondary => _active.textSecondary;
  static Color get textMuted => _active.textMuted;

  static Color get accent => _active.accent;
  static Color get accentSecondary => _active.accentSecondary;
  static Color get success => _active.success;
  static Color get warning => _active.warning;
  static Color get danger => _active.danger;
  static Color get info => _active.info;

  static Color get track => _active.track;
  static Color get shadow => _active.shadow;
}
