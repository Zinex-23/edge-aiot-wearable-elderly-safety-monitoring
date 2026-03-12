import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../models/dashboard_snapshot.dart';
import '../../models/health_enums.dart';
import '../../models/health_metric_point.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../theme/status_palette.dart';
import '../../widgets/app_background.dart';
import '../../widgets/chart_period_selector.dart';
import '../../widgets/detail_stat_tile.dart';
import '../../widgets/metric_line_chart.dart';
import '../../widgets/premium_card.dart';
import '../../widgets/screen_header.dart';
import '../../widgets/status_chip.dart';

class RestingHeartRateScreen extends StatefulWidget {
  const RestingHeartRateScreen({super.key, required this.snapshot});

  final DashboardSnapshot snapshot;

  @override
  State<RestingHeartRateScreen> createState() => _RestingHeartRateScreenState();
}

class _RestingHeartRateScreenState extends State<RestingHeartRateScreen> {
  ChartPeriod _selectedPeriod = ChartPeriod.month;

  @override
  Widget build(BuildContext context) {
    final status = StatusPalette.restingHeartRateStatus(
      widget.snapshot.restingHeartRateToday,
    );
    final points = _visiblePoints(widget.snapshot.restingHeartRateHistory);
    final minValue = points
        .map((point) => point.value)
        .reduce((current, next) => current < next ? current : next);
    final maxValue = points
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
                title: 'Resting Heart Rate',
                subtitle:
                    'Lower resting heart rate often reflects better efficiency',
                showBackButton: true,
              ),
              const SizedBox(height: AppSpacing.xl),
              ChartPeriodSelector(
                selectedPeriod: _selectedPeriod,
                onChanged: (period) => setState(() => _selectedPeriod = period),
              ),
              const SizedBox(height: AppSpacing.xl),
              Row(
                children: [
                  Expanded(
                    child: DetailStatTile(
                      label: 'Today',
                      value: '${widget.snapshot.restingHeartRateToday} bpm',
                      footnote: 'Current resting baseline',
                      valueColor: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: DetailStatTile(
                      label: '30-day average',
                      value:
                          '${widget.snapshot.restingHeartRate30DayAverage.toStringAsFixed(0)} bpm',
                      footnote: 'Average line on chart',
                      valueColor: AppColors.info,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              Align(
                alignment: Alignment.centerLeft,
                child: StatusChip(
                  label: StatusPalette.labelForHealthStatus(status),
                  color: StatusPalette.colorForHealthStatus(status),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Trend', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      'Average line and optimal zone are layered directly onto the chart.',
                      style: AppTextStyles.body,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    SizedBox(
                      height: 280,
                      child: MetricLineChart(
                        points: points,
                        lineColor: AppColors.danger,
                        minY: (minValue - 4).floorToDouble(),
                        maxY: (maxValue + 4).ceilToDouble(),
                        averageLine:
                            widget.snapshot.restingHeartRate30DayAverage,
                        optimalMin: 58,
                        optimalMax: 68,
                        labelStep: points.length <= 7 ? 2 : 5,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.sm,
                      children: [
                        _LegendItem(
                          color: AppColors.danger,
                          label: 'Resting heart rate',
                        ),
                        _LegendItem(color: AppColors.info, label: 'Average'),
                        _LegendItem(
                          color: AppColors.success,
                          label: 'Optimal zone',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'About Resting Heart Rate',
                      style: AppTextStyles.title,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Resting heart rate is the number of beats per minute when the body is fully at rest. A gradual rise can point to fatigue, illness, or extra physiological stress.',
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

  List<HealthMetricPoint> _visiblePoints(List<HealthMetricPoint> points) {
    final count = switch (_selectedPeriod) {
      ChartPeriod.day => 5,
      ChartPeriod.week => 7,
      ChartPeriod.month => 30,
      ChartPeriod.sixMonths => 30,
      ChartPeriod.year => 30,
    };

    return points.sublist(math.max(points.length - count, 0));
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(999),
          ),
        ),
        const SizedBox(width: AppSpacing.xs),
        Text(label, style: AppTextStyles.label),
      ],
    );
  }
}
