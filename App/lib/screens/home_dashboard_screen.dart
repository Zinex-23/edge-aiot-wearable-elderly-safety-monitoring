import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/dashboard_snapshot.dart';
import '../providers/health_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../theme/status_palette.dart';
import '../widgets/alert_tile.dart';
import '../widgets/app_background.dart';
import '../widgets/metric_card.dart';
import '../widgets/premium_card.dart';
import '../widgets/progress_ring.dart';
import '../widgets/screen_header.dart';
import '../widgets/status_chip.dart';
import 'activity_screen.dart';
import 'alerts_screen.dart';
import 'emergency_screen.dart';
import 'metrics/hrv_screen.dart';
import 'metrics/resting_heart_rate_screen.dart';
import 'metrics/spo2_screen.dart';

class HomeDashboardScreen extends StatelessWidget {
  const HomeDashboardScreen({super.key, required this.snapshot});

  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final overallColor = StatusPalette.colorForHealthStatus(
      snapshot.profile.status,
    );
    final overallLabel = StatusPalette.labelForHealthStatus(
      snapshot.profile.status,
    );

    return AppBackground(
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: context.read<HealthProvider>().refresh,
          color: AppColors.accent,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(
              parent: BouncingScrollPhysics(),
            ),
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              120,
            ),
            children: [
              ScreenHeader(
                title: 'Care Dashboard',
                subtitle: 'Premium health view for today',
                trailing: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.surface.withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: IconButton(
                    onPressed: () => context.read<HealthProvider>().refresh(),
                    icon: const Icon(Icons.sync_rounded, size: 20),
                  ),
                ),
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
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 520;
                    final scoreRing = ProgressRing(
                      progress: snapshot.healthScore / 100,
                      centerValue: '${snapshot.healthScore}',
                      centerLabel: 'health score',
                      caption: 'Stable today',
                      color: AppColors.accent,
                      size: isWide ? 144 : 132,
                    );

                    final profileInfo = Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          snapshot.profile.name,
                          style: AppTextStyles.headline,
                        ),
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          '${snapshot.profile.age} years old',
                          style: AppTextStyles.body,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        StatusChip(label: overallLabel, color: overallColor),
                        const SizedBox(height: AppSpacing.md),
                        Text(
                          'Health score remains strong while recovery and oxygen readings need light attention.',
                          style: AppTextStyles.body,
                        ),
                      ],
                    );

                    return Column(
                      children: [
                        if (isWide)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(child: profileInfo),
                              const SizedBox(width: AppSpacing.lg),
                              scoreRing,
                            ],
                          )
                        else ...[
                          profileInfo,
                          const SizedBox(height: AppSpacing.xl),
                          Center(child: scoreRing),
                        ],
                        const SizedBox(height: AppSpacing.lg),
                        Wrap(
                          spacing: AppSpacing.sm,
                          runSpacing: AppSpacing.sm,
                          children: [
                            _QuickInfoPill(
                              label: 'Last sync',
                              value: _timeAgo(snapshot.profile.lastSync),
                            ),
                            _QuickInfoPill(
                              label: 'Device',
                              value: snapshot.profile.deviceConnected
                                  ? 'Connected'
                                  : 'Offline',
                            ),
                            _QuickInfoPill(
                              label: 'Battery',
                              value: '${snapshot.profile.batteryLevel}%',
                            ),
                          ],
                        ),
                        if (snapshot.hasEmergencyAlert) ...[
                          const SizedBox(height: AppSpacing.lg),
                          _EmergencyBanner(
                            onTap: () => _push(
                              context,
                              EmergencyScreen(
                                alert: snapshot.emergencyAlert!,
                                locationLabel: snapshot.locationLabel,
                              ),
                            ),
                          ),
                        ],
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
              _SectionTitle(
                title: 'Today\'s Metrics',
                subtitle: 'Tap any card for a deeper production-style view.',
              ),
              const SizedBox(height: AppSpacing.md),
              LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth > 700 ? 4 : 2;
                  final aspectRatio = constraints.maxWidth > 700 ? 1.14 : 0.92;

                  return GridView.count(
                    shrinkWrap: true,
                    crossAxisCount: columns,
                    childAspectRatio: aspectRatio,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: AppSpacing.md,
                    crossAxisSpacing: AppSpacing.md,
                    children: [
                      MetricCard(
                        title: 'Heart Rate',
                        value: '${snapshot.restingHeartRateToday}',
                        unit: 'bpm',
                        subtitle:
                            '30-day avg ${snapshot.restingHeartRate30DayAverage.toStringAsFixed(0)} bpm',
                        icon: Icons.favorite_rounded,
                        accentColor: AppColors.danger,
                        onTap: () => _push(
                          context,
                          RestingHeartRateScreen(snapshot: snapshot),
                        ),
                      ),
                      MetricCard(
                        title: 'HRV',
                        value: '${snapshot.hrvToday}',
                        unit: 'ms',
                        subtitle:
                            '7-day avg ${snapshot.hrv7DayAverage.toStringAsFixed(0)} ms',
                        icon: Icons.insights_rounded,
                        accentColor: StatusPalette.colorForHrvStatus(
                          snapshot.hrvStatus,
                        ),
                        onTap: () =>
                            _push(context, HrvScreen(snapshot: snapshot)),
                      ),
                      MetricCard(
                        title: 'SpO2',
                        value: '${snapshot.spo2Current}',
                        unit: '%',
                        subtitle:
                            'Today range ${snapshot.spo2Min}-${snapshot.spo2Max}%',
                        icon: Icons.air_rounded,
                        accentColor: snapshot.hasSpo2Warning
                            ? AppColors.warning
                            : AppColors.info,
                        onTap: () =>
                            _push(context, Spo2Screen(snapshot: snapshot)),
                      ),
                      MetricCard(
                        title: 'Daily Activity',
                        value: _compactSteps(snapshot.dailySteps),
                        unit: 'steps',
                        subtitle: '${snapshot.activeMinutes} mins active today',
                        icon: Icons.directions_walk_rounded,
                        accentColor: StatusPalette.colorForActivity(
                          snapshot.activityRating,
                        ),
                        onTap: () => _push(
                          context,
                          ActivityScreen(
                            snapshot: snapshot,
                            showBackButton: true,
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpacing.xxl),
              _SectionTitle(
                title: 'Latest Alert',
                subtitle: 'Recent wearable notifications for the caregiver.',
              ),
              const SizedBox(height: AppSpacing.md),
              AlertTile(
                alert: snapshot.latestAlert,
                onTap: () {
                  if (snapshot.latestAlert.isEmergency) {
                    _push(
                      context,
                      EmergencyScreen(
                        alert: snapshot.latestAlert,
                        locationLabel: snapshot.locationLabel,
                      ),
                    );
                    return;
                  }

                  _push(
                    context,
                    AlertsScreen(snapshot: snapshot, showBackButton: true),
                  );
                },
              ),
              const SizedBox(height: AppSpacing.md),
              PremiumCard(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Need a full review?',
                            style: AppTextStyles.title,
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            'Open all alerts, investigate the critical event, or review activity patterns.',
                            style: AppTextStyles.body,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: AppSpacing.md),
                    FilledButton.tonal(
                      onPressed: () => _push(
                        context,
                        AlertsScreen(snapshot: snapshot, showBackButton: true),
                      ),
                      child: const Text('View all'),
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

  static void _push(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => screen));
  }

  static String _compactSteps(int steps) {
    if (steps >= 1000) {
      return '${(steps / 1000).toStringAsFixed(1)}k';
    }
    return '$steps';
  }

  static String _timeAgo(DateTime dateTime) {
    final difference = DateTime.now().difference(dateTime);
    if (difference.inMinutes < 60) {
      return '${difference.inMinutes} min ago';
    }
    if (difference.inHours < 24) {
      return '${difference.inHours} hr ago';
    }
    return '${difference.inDays} d ago';
  }
}

class _QuickInfoPill extends StatelessWidget {
  const _QuickInfoPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted.withValues(alpha: 0.76),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: AppTextStyles.label),
          const SizedBox(height: AppSpacing.xxs),
          Text(value, style: AppTextStyles.bodyStrong),
        ],
      ),
    );
  }
}

class _EmergencyBanner extends StatelessWidget {
  const _EmergencyBanner({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.danger.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.danger.withValues(alpha: 0.26)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.danger.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(Icons.emergency_rounded, color: AppColors.danger),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Possible fall detected', style: AppTextStyles.bodyStrong),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  'A critical event was detected 12 minutes ago.',
                  style: AppTextStyles.label,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.danger,
              foregroundColor: AppColors.textPrimary,
            ),
            onPressed: onTap,
            child: const Text('Open'),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppTextStyles.title),
        const SizedBox(height: AppSpacing.xxs),
        Text(subtitle, style: AppTextStyles.body),
      ],
    );
  }
}
