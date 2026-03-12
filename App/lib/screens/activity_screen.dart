import 'package:flutter/material.dart';

import '../models/activity_hour.dart';
import '../models/dashboard_snapshot.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../theme/status_palette.dart';
import '../widgets/activity_bar_chart.dart';
import '../widgets/app_background.dart';
import '../widgets/detail_stat_tile.dart';
import '../widgets/premium_card.dart';
import '../widgets/progress_ring.dart';
import '../widgets/screen_header.dart';
import '../widgets/status_chip.dart';

class ActivityScreen extends StatelessWidget {
  const ActivityScreen({
    super.key,
    required this.snapshot,
    this.showBackButton = false,
  });

  final DashboardSnapshot snapshot;
  final bool showBackButton;

  @override
  Widget build(BuildContext context) {
    final activityColor = StatusPalette.colorForActivity(
      snapshot.activityRating,
    );
    final activityLabel = StatusPalette.labelForActivity(
      snapshot.activityRating,
    );

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
                title: 'Activity',
                subtitle: 'Steps, movement, calories, and hourly rhythm',
                showBackButton: showBackButton,
              ),
              const SizedBox(height: AppSpacing.xl),
              PremiumCard(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 560;
                    final summaryTiles = Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.md,
                      children: [
                        SizedBox(
                          width: isWide
                              ? (constraints.maxWidth -
                                        188 -
                                        AppSpacing.lg * 3) /
                                    2
                              : (constraints.maxWidth - AppSpacing.md) / 2,
                          child: DetailStatTile(
                            label: 'Active Time',
                            value: '${snapshot.activeMinutes} min',
                            footnote: 'Goal 45 min',
                          ),
                        ),
                        SizedBox(
                          width: isWide
                              ? (constraints.maxWidth -
                                        188 -
                                        AppSpacing.lg * 3) /
                                    2
                              : (constraints.maxWidth - AppSpacing.md) / 2,
                          child: DetailStatTile(
                            label: 'Calories',
                            value: '${snapshot.calories} kcal',
                            footnote: 'Estimated burn',
                          ),
                        ),
                        SizedBox(
                          width: isWide
                              ? (constraints.maxWidth -
                                        188 -
                                        AppSpacing.lg * 3) /
                                    2
                              : (constraints.maxWidth - AppSpacing.md) / 2,
                          child: DetailStatTile(
                            label: 'Distance',
                            value:
                                '${snapshot.distanceKm.toStringAsFixed(1)} km',
                            footnote: 'Walking equivalent',
                          ),
                        ),
                        SizedBox(
                          width: isWide
                              ? (constraints.maxWidth -
                                        188 -
                                        AppSpacing.lg * 3) /
                                    2
                              : (constraints.maxWidth - AppSpacing.md) / 2,
                          child: DetailStatTile(
                            label: 'Peak Window',
                            value: _peakActivityWindow(snapshot.activityByHour),
                            footnote: 'Highest movement block',
                          ),
                        ),
                      ],
                    );

                    if (isWide) {
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          ProgressRing(
                            progress: snapshot.dailySteps / 6500,
                            centerValue: '${snapshot.dailySteps}',
                            centerLabel: 'steps',
                            caption: activityLabel,
                            color: activityColor,
                            size: 168,
                          ),
                          const SizedBox(width: AppSpacing.xl),
                          Expanded(child: summaryTiles),
                        ],
                      );
                    }

                    return Column(
                      children: [
                        ProgressRing(
                          progress: snapshot.dailySteps / 6500,
                          centerValue: '${snapshot.dailySteps}',
                          centerLabel: 'steps',
                          caption: activityLabel,
                          color: activityColor,
                          size: 156,
                        ),
                        const SizedBox(height: AppSpacing.xl),
                        summaryTiles,
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              PremiumCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Hourly activity', style: AppTextStyles.title),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      'A calm morning followed by stronger movement in the late afternoon.',
                      style: AppTextStyles.body,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    SizedBox(
                      height: 260,
                      child: ActivityBarChart(
                        activityByHour: snapshot.activityByHour,
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
                    Row(
                      children: [
                        Text('Daily assessment', style: AppTextStyles.title),
                        const Spacer(),
                        StatusChip(label: activityLabel, color: activityColor),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      _assessmentText(
                        snapshot.dailySteps,
                        snapshot.activeMinutes,
                      ),
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

  static String _peakActivityWindow(List<ActivityHour> activityByHour) {
    final peak = activityByHour.reduce(
      (current, next) => current.steps >= next.steps ? current : next,
    );
    return peak.label;
  }

  static String _assessmentText(int steps, int activeMinutes) {
    if (steps >= 7000 && activeMinutes >= 45) {
      return 'Activity is strong today with healthy movement spread across the day.';
    }
    if (steps >= 4000 || activeMinutes >= 30) {
      return 'Movement is moderate today. A short evening walk would improve the total load.';
    }
    return 'Activity is light today. Consider a safe guided walk or stretching session.';
  }
}
