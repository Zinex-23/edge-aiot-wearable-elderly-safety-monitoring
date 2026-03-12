import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/health_alert.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../widgets/app_background.dart';
import '../widgets/premium_card.dart';
import '../widgets/screen_header.dart';

class EmergencyScreen extends StatelessWidget {
  const EmergencyScreen({
    super.key,
    required this.alert,
    required this.locationLabel,
  });

  final HealthAlert alert;
  final String locationLabel;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackground(
        child: SafeArea(
          child: ListView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.xl,
            ),
            children: [
              const ScreenHeader(
                title: 'Emergency',
                subtitle: 'Immediate caregiver response recommended',
                showBackButton: true,
              ),
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    AppColors.danger.withValues(alpha: 0.28),
                    AppColors.surfaceSoft.withValues(alpha: 0.96),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: AppColors.danger.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: Icon(
                        Icons.emergency_rounded,
                        color: AppColors.danger,
                        size: 34,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      'Possible fall detected',
                      style: AppTextStyles.display.copyWith(fontSize: 30),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(alert.description, style: AppTextStyles.body),
                    const SizedBox(height: AppSpacing.lg),
                    _EmergencyInfoRow(
                      label: 'Time',
                      value: DateFormat('MMM d, h:mm a').format(alert.time),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    _EmergencyInfoRow(label: 'Location', value: locationLabel),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              _EmergencyActionButton(
                label: 'Call',
                icon: Icons.call_rounded,
                backgroundColor: AppColors.danger,
                foregroundColor: AppColors.textPrimary,
                onPressed: () =>
                    _showActionFeedback(context, 'Calling caregiver'),
              ),
              const SizedBox(height: AppSpacing.md),
              _EmergencyActionButton(
                label: 'Send Help',
                icon: Icons.local_hospital_rounded,
                backgroundColor: AppColors.surfaceSoft,
                foregroundColor: AppColors.textPrimary,
                borderColor: AppColors.danger.withValues(alpha: 0.34),
                onPressed: () =>
                    _showActionFeedback(context, 'Help request sent'),
              ),
              const SizedBox(height: AppSpacing.md),
              _EmergencyActionButton(
                label: 'Open Map',
                icon: Icons.map_rounded,
                backgroundColor: AppColors.surfaceSoft,
                foregroundColor: AppColors.textPrimary,
                borderColor: AppColors.border,
                onPressed: () =>
                    _showActionFeedback(context, 'Opening map view'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static void _showActionFeedback(BuildContext context, String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}

class _EmergencyInfoRow extends StatelessWidget {
  const _EmergencyInfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(width: 74, child: Text(label, style: AppTextStyles.label)),
        Expanded(child: Text(value, style: AppTextStyles.bodyStrong)),
      ],
    );
  }
}

class _EmergencyActionButton extends StatelessWidget {
  const _EmergencyActionButton({
    required this.label,
    required this.icon,
    required this.onPressed,
    required this.backgroundColor,
    required this.foregroundColor,
    this.borderColor,
  });

  final String label;
  final IconData icon;
  final VoidCallback onPressed;
  final Color backgroundColor;
  final Color foregroundColor;
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 60,
      child: ElevatedButton.icon(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: backgroundColor,
          foregroundColor: foregroundColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
            side: BorderSide(color: borderColor ?? Colors.transparent),
          ),
        ),
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label, style: AppTextStyles.bodyStrong),
      ),
    );
  }
}
