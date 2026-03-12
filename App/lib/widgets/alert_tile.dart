import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/health_alert.dart';
import '../models/health_enums.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import 'premium_card.dart';
import 'status_chip.dart';

class AlertTile extends StatelessWidget {
  const AlertTile({super.key, required this.alert, this.onTap});

  final HealthAlert alert;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(alert.severity);

    return PremiumCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(_iconForType(alert.type), color: color),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(alert.title, style: AppTextStyles.bodyStrong),
                    const SizedBox(height: AppSpacing.xxs),
                    Text(
                      DateFormat('MMM d, h:mm a').format(alert.time),
                      style: AppTextStyles.label,
                    ),
                  ],
                ),
              ),
              StatusChip(label: _severityLabel(alert.severity), color: color),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            alert.description,
            style: AppTextStyles.body.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  static IconData _iconForType(AlertType type) {
    switch (type) {
      case AlertType.heartRate:
        return Icons.favorite_rounded;
      case AlertType.hrv:
        return Icons.insights_rounded;
      case AlertType.spo2:
        return Icons.air_rounded;
      case AlertType.inactivity:
        return Icons.directions_walk_rounded;
      case AlertType.fall:
        return Icons.emergency_rounded;
    }
  }

  static Color _severityColor(AlertSeverity severity) {
    switch (severity) {
      case AlertSeverity.info:
        return AppColors.info;
      case AlertSeverity.warning:
        return AppColors.warning;
      case AlertSeverity.critical:
        return AppColors.danger;
    }
  }

  static String _severityLabel(AlertSeverity severity) {
    switch (severity) {
      case AlertSeverity.info:
        return 'Info';
      case AlertSeverity.warning:
        return 'Warning';
      case AlertSeverity.critical:
        return 'Critical';
    }
  }
}
