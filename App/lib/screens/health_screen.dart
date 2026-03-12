import 'package:flutter/material.dart';

import '../models/dashboard_snapshot.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../theme/status_palette.dart';
import '../widgets/app_background.dart';
import '../widgets/detail_stat_tile.dart';
import '../widgets/metric_card.dart';
import '../widgets/premium_card.dart';
import '../widgets/screen_header.dart';
import '../widgets/status_chip.dart';
import 'emergency_screen.dart';
import 'metrics/hrv_screen.dart';
import 'metrics/resting_heart_rate_screen.dart';
import 'metrics/spo2_screen.dart';

class HealthScreen extends StatelessWidget {
  const HealthScreen({super.key, required this.snapshot});

  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final hrvColor = StatusPalette.colorForHrvStatus(snapshot.hrvStatus);

    return AppBackground(
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
            const ScreenHeader(
              title: 'Health',
              subtitle: 'Recovery, heart efficiency, and oxygen trends',
            ),
            const SizedBox(height: AppSpacing.xl),
            PremiumCard(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppColors.surfaceSoft.withValues(alpha: 0.96),
                  AppColors.surface.withValues(alpha: 0.90),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Daily readiness is stable.',
                              style: AppTextStyles.headline,
                            ),
                            const SizedBox(height: AppSpacing.xs),
                            Text(
                              'Resting heart rate remains in the optimal band, while HRV has softened slightly over the past few days.',
                              style: AppTextStyles.body,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      StatusChip(
                        label: StatusPalette.labelForHealthStatus(
                          snapshot.profile.status,
                        ),
                        color: StatusPalette.colorForHealthStatus(
                          snapshot.profile.status,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  LayoutBuilder(
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
                              label: 'Health Score',
                              value: '${snapshot.healthScore}/100',
                              footnote: 'Premium recovery estimate',
                              valueColor: AppColors.accent,
                            ),
                          ),
                          SizedBox(
                            width: tileWidth,
                            child: DetailStatTile(
                              label: 'Today HRV',
                              value: '${snapshot.hrvToday} ms',
                              footnote: StatusPalette.labelForHrvStatus(
                                snapshot.hrvStatus,
                              ),
                              valueColor: hrvColor,
                            ),
                          ),
                          SizedBox(
                            width: tileWidth,
                            child: DetailStatTile(
                              label: 'Today SpO2',
                              value: '${snapshot.spo2Current}%',
                              footnote: snapshot.hasSpo2Warning
                                  ? 'Low episode detected'
                                  : 'Within normal range',
                              valueColor: snapshot.hasSpo2Warning
                                  ? AppColors.warning
                                  : AppColors.info,
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),
            Text('Detailed metrics', style: AppTextStyles.title),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'Each view is tuned for a caregiver-friendly readout with clear charts.',
              style: AppTextStyles.body,
            ),
            const SizedBox(height: AppSpacing.md),
            MetricCard(
              title: 'Resting Heart Rate',
              value: '${snapshot.restingHeartRateToday}',
              unit: 'bpm',
              subtitle:
                  'Optimal band 58-68 bpm • avg ${snapshot.restingHeartRate30DayAverage.toStringAsFixed(0)}',
              icon: Icons.favorite_rounded,
              accentColor: AppColors.danger,
              onTap: () =>
                  _push(context, RestingHeartRateScreen(snapshot: snapshot)),
            ),
            const SizedBox(height: AppSpacing.md),
            MetricCard(
              title: 'Heart Rate Variability',
              value: '${snapshot.hrvToday}',
              unit: 'ms',
              subtitle:
                  '7-day avg ${snapshot.hrv7DayAverage.toStringAsFixed(0)} • ${StatusPalette.labelForHrvStatus(snapshot.hrvStatus)}',
              icon: Icons.insights_rounded,
              accentColor: hrvColor,
              onTap: () => _push(context, HrvScreen(snapshot: snapshot)),
            ),
            const SizedBox(height: AppSpacing.md),
            MetricCard(
              title: 'Blood Oxygen',
              value: '${snapshot.spo2Current}',
              unit: '%',
              subtitle:
                  'Intraday range ${snapshot.spo2Min}-${snapshot.spo2Max}%',
              icon: Icons.air_rounded,
              accentColor: snapshot.hasSpo2Warning
                  ? AppColors.warning
                  : AppColors.info,
              onTap: () => _push(context, Spo2Screen(snapshot: snapshot)),
            ),
            const SizedBox(height: AppSpacing.xxl),
            PremiumCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('AI insight', style: AppTextStyles.title),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    '${snapshot.hrvInsight} Keep hydration and sleep consistent to support recovery.',
                    style: AppTextStyles.body,
                  ),
                  if (snapshot.hasEmergencyAlert) ...[
                    const SizedBox(height: AppSpacing.lg),
                    FilledButton.tonalIcon(
                      onPressed: () => _push(
                        context,
                        EmergencyScreen(
                          alert: snapshot.emergencyAlert!,
                          locationLabel: snapshot.locationLabel,
                        ),
                      ),
                      icon: const Icon(Icons.emergency_rounded),
                      label: const Text('Open emergency alert'),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static void _push(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));
  }
}
