import 'package:flutter/material.dart';

import '../models/dashboard_snapshot.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../widgets/alert_tile.dart';
import '../widgets/app_background.dart';
import '../widgets/detail_stat_tile.dart';
import '../widgets/premium_card.dart';
import '../widgets/screen_header.dart';
import 'emergency_screen.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({
    super.key,
    required this.snapshot,
    this.showBackButton = false,
  });

  final DashboardSnapshot snapshot;
  final bool showBackButton;

  @override
  Widget build(BuildContext context) {
    final criticalCount = snapshot.alerts
        .where((alert) => alert.severity.name == 'critical')
        .length;
    final warningCount = snapshot.alerts
        .where((alert) => alert.severity.name == 'warning')
        .length;
    final infoCount = snapshot.alerts
        .where((alert) => alert.severity.name == 'info')
        .length;

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
              120,
            ),
            children: [
              ScreenHeader(
                title: 'Alerts',
                subtitle: 'Recent warnings and caregiver-facing incidents',
                showBackButton: showBackButton,
              ),
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final tileWidth = constraints.maxWidth > 620
                        ? (constraints.maxWidth - AppSpacing.md * 2) / 3
                        : (constraints.maxWidth - AppSpacing.md) / 2;

                    return Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.md,
                      children: [
                        SizedBox(
                          width: tileWidth,
                          child: DetailStatTile(
                            label: 'Critical',
                            value: '$criticalCount',
                            footnote: 'Immediate review',
                            valueColor: AppColors.danger,
                          ),
                        ),
                        SizedBox(
                          width: tileWidth,
                          child: DetailStatTile(
                            label: 'Warnings',
                            value: '$warningCount',
                            footnote: 'Needs attention',
                            valueColor: AppColors.warning,
                          ),
                        ),
                        SizedBox(
                          width: tileWidth,
                          child: DetailStatTile(
                            label: 'Info',
                            value: '$infoCount',
                            footnote: 'Context updates',
                            valueColor: AppColors.info,
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              ...snapshot.alerts.map((alert) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.md),
                  child: AlertTile(
                    alert: alert,
                    onTap: alert.isEmergency
                        ? () => Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => EmergencyScreen(
                                alert: alert,
                                locationLabel: snapshot.locationLabel,
                              ),
                            ),
                          )
                        : null,
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }
}
