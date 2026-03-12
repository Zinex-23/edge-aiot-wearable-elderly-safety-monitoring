import 'package:flutter/material.dart';

import '../models/health_enums.dart';
import 'app_colors.dart';

class StatusPalette {
  const StatusPalette._();

  static Color colorForHealthStatus(HealthStatus status) {
    switch (status) {
      case HealthStatus.normal:
        return AppColors.success;
      case HealthStatus.warning:
        return AppColors.warning;
      case HealthStatus.critical:
        return AppColors.danger;
    }
  }

  static String labelForHealthStatus(HealthStatus status) {
    switch (status) {
      case HealthStatus.normal:
        return 'Normal';
      case HealthStatus.warning:
        return 'Warning';
      case HealthStatus.critical:
        return 'Critical';
    }
  }

  static HealthStatus restingHeartRateStatus(int bpm) {
    if (bpm <= 68) {
      return HealthStatus.normal;
    }
    if (bpm <= 72) {
      return HealthStatus.warning;
    }
    return HealthStatus.critical;
  }

  static Color colorForHrvStatus(HrvStatus status) {
    switch (status) {
      case HrvStatus.good:
        return AppColors.success;
      case HrvStatus.moderate:
        return AppColors.warning;
      case HrvStatus.low:
        return AppColors.danger;
    }
  }

  static String labelForHrvStatus(HrvStatus status) {
    switch (status) {
      case HrvStatus.good:
        return 'Good';
      case HrvStatus.moderate:
        return 'Moderate';
      case HrvStatus.low:
        return 'Low';
    }
  }

  static Color colorForActivity(ActivityRating rating) {
    switch (rating) {
      case ActivityRating.low:
        return AppColors.danger;
      case ActivityRating.moderate:
        return AppColors.warning;
      case ActivityRating.good:
        return AppColors.success;
    }
  }

  static String labelForActivity(ActivityRating rating) {
    switch (rating) {
      case ActivityRating.low:
        return 'Low activity';
      case ActivityRating.moderate:
        return 'Moderate';
      case ActivityRating.good:
        return 'Good';
    }
  }
}
