import 'package:flutter/material.dart';

import '../../models/dashboard_snapshot.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/app_background.dart';
import '../../widgets/detail_stat_tile.dart';
import '../../widgets/metric_line_chart.dart';
import '../../widgets/premium_card.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_chip.dart';

class Spo2Screen extends StatelessWidget {
  const Spo2Screen({super.key, required this.snapshot});

  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final statusColor = snapshot.hasSpo2Warning
        ? AppColors.warning
        : AppColors.success;
    final dailyAverage =
        snapshot.spo2DailyHistory.fold<double>(
          0,
          (sum, item) => sum + item.value,
        ) /
        snapshot.spo2DailyHistory.length;

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
                title: 'SpO2',
                subtitle: 'Blood oxygen saturation and low-threshold detection',
                showBackButton: true,
              ),
              const SizedBox(height: AppSpacing.xl),
              Row(
                children: [
                  Expanded(
                    child: DetailStatTile(
                      label: 'Current',
                      value: '${snapshot.spo2Current}%',
                      footnote: 'Latest reading',
                      valueColor: AppColors.info,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: DetailStatTile(
                      label: 'Today min / max',
                      value: '${snapshot.spo2Min}% - ${snapshot.spo2Max}%',
                      footnote: 'Intraday range',
                      valueColor: statusColor,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: DetailStatTile(
                      label: '30-day average',
                      value: '${dailyAverage.toStringAsFixed(1)}%',
                      footnote: 'Daily average trend',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Align(
                alignment: Alignment.centerLeft,
                child: StatusChip(
                  label: snapshot.hasSpo2Warning ? 'Low' : 'Normal',
                  color: statusColor,
                ),
              ),
              if (snapshot.hasSpo2Warning) ...[
                const SizedBox(height: AppSpacing.lg),
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: AppColors.warning.withValues(alpha: 0.30),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning_amber_rounded,
                        color: AppColors.warning,
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Text(
                          'SpO2 dropped below 94% today. Monitor rest, breathing comfort, and device fit.',
                          style: AppTextStyles.bodyStrong,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Today\'s oxygen curve', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      'Area chart shows intraday changes and highlights the threshold line.',
                      style: AppTextStyles.body,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    SizedBox(
                      height: 280,
                      child: MetricLineChart(
                        points: snapshot.spo2IntradayHistory,
                        lineColor: AppColors.info,
                        minY: 90,
                        maxY: 99,
                        averageLine: dailyAverage,
                        optimalMin: 95,
                        optimalMax: 99,
                        isIntraday: true,
                        labelStep: 2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('About SpO2', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'SpO2 estimates how much oxygen is carried in the blood. Persistent readings below the normal range may indicate breathing discomfort, poor sensor contact, or the need for caregiver follow-up.',
                      style: AppTextStyles.body,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
