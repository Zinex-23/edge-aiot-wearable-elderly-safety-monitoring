import 'package:flutter/material.dart';

import '../../models/dashboard_snapshot.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../theme/status_palette.dart';
import '../../widgets/app_background.dart';
import '../../widgets/detail_stat_tile.dart';
import '../../widgets/metric_line_chart.dart';
import '../../widgets/premium_card.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_chip.dart';

class HrvScreen extends StatelessWidget {
  const HrvScreen({super.key, required this.snapshot});

  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final hrvColor = StatusPalette.colorForHrvStatus(snapshot.hrvStatus);
    final minValue = snapshot.hrvHistory
        .map((point) => point.value)
        .reduce((current, next) => current < next ? current : next);
    final maxValue = snapshot.hrvHistory
        .map((point) => point.value)
        .reduce((current, next) => current > next ? current : next);

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
                title: 'HRV',
                subtitle: 'Recovery readiness based on heart rhythm variation',
                showBackButton: true,
              ),
              const SizedBox(height: AppSpacing.xl),
              Row(
                children: [
                  Expanded(
                    child: DetailStatTile(
                      label: 'Today',
                      value: '${snapshot.hrvToday} ms',
                      footnote: 'Latest measurement',
                      valueColor: hrvColor,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: DetailStatTile(
                      label: '7-day average',
                      value: '${snapshot.hrv7DayAverage.toStringAsFixed(0)} ms',
                      footnote: 'Short-term recovery',
                      valueColor: AppColors.info,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: DetailStatTile(
                      label: '30-day average',
                      value:
                          '${snapshot.hrv30DayAverage.toStringAsFixed(0)} ms',
                      footnote: 'Longer baseline',
                      valueColor: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Align(
                alignment: Alignment.centerLeft,
                child: StatusChip(
                  label: StatusPalette.labelForHrvStatus(snapshot.hrvStatus),
                  color: hrvColor,
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('30-day trend', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      'Recent values show a slight dip, which can reflect accumulated stress or less recovery.',
                      style: AppTextStyles.body,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    SizedBox(
                      height: 280,
                      child: MetricLineChart(
                        points: snapshot.hrvHistory,
                        lineColor: hrvColor,
                        minY: (minValue - 5).floorToDouble(),
                        maxY: (maxValue + 5).ceilToDouble(),
                        averageLine: snapshot.hrv30DayAverage,
                        optimalMin: 46,
                        optimalMax: 58,
                        labelStep: 5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              PremiumCard(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    hrvColor.withValues(alpha: 0.18),
                    AppColors.surface.withValues(alpha: 0.92),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('AI insight', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      '${snapshot.hrvInsight} Consider prioritizing sleep and a lighter recovery day.',
                      style: AppTextStyles.body,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('What is HRV?', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Heart rate variability tracks the variation between heartbeats. Higher and more stable values often indicate better recovery and nervous system balance, while lower values can signal fatigue or strain.',
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
