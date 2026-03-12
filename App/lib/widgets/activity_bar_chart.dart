import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/activity_hour.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class ActivityBarChart extends StatelessWidget {
  const ActivityBarChart({super.key, required this.activityByHour});

  final List<ActivityHour> activityByHour;

  @override
  Widget build(BuildContext context) {
    final maxSteps =
        activityByHour
            .map((hour) => hour.steps)
            .reduce((current, next) => current > next ? current : next)
            .toDouble() +
        100;

    return BarChart(
      BarChartData(
        minY: 0,
        maxY: maxSteps,
        borderData: FlBorderData(show: false),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: maxSteps / 4,
          getDrawingHorizontalLine: (value) => FlLine(
            color: AppColors.border.withValues(alpha: 0.55),
            strokeWidth: 1,
          ),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 34,
              interval: maxSteps / 4,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    value.toInt().toString(),
                    style: AppTextStyles.label.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 28,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= activityByHour.length) {
                  return const SizedBox.shrink();
                }

                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    activityByHour[index].label,
                    style: AppTextStyles.label.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        barGroups: List.generate(activityByHour.length, (index) {
          final hour = activityByHour[index];
          final isPeak = hour.steps >= 700;
          return BarChartGroupData(
            x: index,
            barRods: [
              BarChartRodData(
                toY: hour.steps.toDouble(),
                width: 16,
                color: isPeak ? AppColors.accent : AppColors.accentSecondary,
                borderRadius: BorderRadius.circular(8),
                backDrawRodData: BackgroundBarChartRodData(
                  show: true,
                  toY: maxSteps,
                  color: AppColors.track,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}
