import 'package:flutter/material.dart';

import 'app_colors.dart';

class AppTextStyles {
  const AppTextStyles._();

  static TextStyle get display => TextStyle(
    fontSize: 34,
    height: 1.08,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.8,
    color: AppColors.textPrimary,
  );

  static TextStyle get headline => TextStyle(
    fontSize: 24,
    height: 1.18,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.4,
    color: AppColors.textPrimary,
  );

  static TextStyle get title => TextStyle(
    fontSize: 18,
    height: 1.25,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static TextStyle get body => TextStyle(
    fontSize: 14,
    height: 1.5,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
  );

  static TextStyle get bodyStrong => TextStyle(
    fontSize: 14,
    height: 1.45,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static TextStyle get label => TextStyle(
    fontSize: 12,
    height: 1.35,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.2,
    color: AppColors.textMuted,
  );

  static TextStyle get metric => TextStyle(
    fontSize: 30,
    height: 1.0,
    fontWeight: FontWeight.w700,
    letterSpacing: -1,
    color: AppColors.textPrimary,
  );
}
