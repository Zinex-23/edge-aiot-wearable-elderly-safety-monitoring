import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/health_metric_point.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class MetricLineChart extends StatelessWidget {
  const MetricLineChart({
    super.key,
    required this.points,
    required this.lineColor,
    required this.minY,
    required this.maxY,
    this.averageLine,
    this.optimalMin,
    this.optimalMax,
    this.showArea = true,
    this.isIntraday = false,
    this.labelStep = 5,
  });

  final List<HealthMetricPoint> points;
  final Color lineColor;
  final double minY;
  final double maxY;
  final double? averageLine;
  final double? optimalMin;
  final double? optimalMax;
  final bool showArea;
  final bool isIntraday;
  final int labelStep;

  @override
  Widget build(BuildContext context) {
    final spots = List.generate(
      points.length,
      (index) => FlSpot(index.toDouble(), points[index].value),
    );

    return LineChart(
      LineChartData(
        minX: 0,
        maxX: (points.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: ((maxY - minY) / 4).clamp(1, 100),
          getDrawingHorizontalLine: (value) {
            return FlLine(
              color: AppColors.border.withValues(alpha: 0.55),
              strokeWidth: 1,
            );
          },
        ),
        borderData: FlBorderData(show: false),
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
              interval: ((maxY - minY) / 4).clamp(1, 100),
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
              interval: labelStep.toDouble(),
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 ||
                    index >= points.length ||
                    index % labelStep != 0) {
                  return const SizedBox.shrink();
                }

                final label = isIntraday
                    ? DateFormat('ha').format(points[index].timestamp)
                    : DateFormat('d').format(points[index].timestamp);

                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    label,
                    style: AppTextStyles.label.copyWith(
                      color: AppColors.textMuted,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        rangeAnnotations: RangeAnnotations(
          horizontalRangeAnnotations: [
            if (optimalMin != null && optimalMax != null)
              HorizontalRangeAnnotation(
                y1: optimalMin!,
                y2: optimalMax!,
                color: AppColors.success.withValues(alpha: 0.10),
              ),
          ],
        ),
        extraLinesData: ExtraLinesData(
          horizontalLines: [
            if (averageLine != null)
              HorizontalLine(
                y: averageLine!,
                color: AppColors.info.withValues(alpha: 0.65),
                strokeWidth: 1.4,
                dashArray: const [6, 6],
              ),
          ],
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            color: lineColor,
            barWidth: 3.2,
            isCurved: true,
            isStrokeCapRound: true,
            preventCurveOverShooting: true,
            belowBarData: BarAreaData(
              show: showArea,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  lineColor.withValues(alpha: 0.34),
                  lineColor.withValues(alpha: 0.02),
                ],
              ),
            ),
            dotData: FlDotData(
              show: true,
              getDotPainter: (spot, percent, bar, index) {
                final isLatest = index == spots.length - 1;
                return FlDotCirclePainter(
                  radius: isLatest ? 4.2 : 0,
                  color: lineColor,
                  strokeWidth: isLatest ? 2.5 : 0,
                  strokeColor: AppColors.background,
                );
              },
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          handleBuiltInTouches: true,
          touchTooltipData: LineTouchTooltipData(
            tooltipBorderRadius: BorderRadius.circular(16),
            tooltipPadding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 10,
            ),
            getTooltipItems: (spots) {
              return spots.map((spot) {
                final value = points[spot.x.toInt()].value.toStringAsFixed(0);
                return LineTooltipItem(
                  value,
                  AppTextStyles.bodyStrong.copyWith(
                    color: AppColors.textPrimary,
                  ),
                );
              }).toList();
            },
          ),
        ),
      ),
    );
  }
}
