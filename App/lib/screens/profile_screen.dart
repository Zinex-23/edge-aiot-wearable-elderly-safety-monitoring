import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/dashboard_snapshot.dart';
import '../providers/theme_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../theme/status_palette.dart';
import '../widgets/app_background.dart';
import '../widgets/detail_stat_tile.dart';
import '../widgets/premium_card.dart';
import '../widgets/screen_header.dart';
import '../widgets/status_chip.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({
    super.key,
    required this.snapshot,
    this.showBackButton = false,
  });

  final DashboardSnapshot snapshot;
  final bool showBackButton;

  @override
  Widget build(BuildContext context) {
    final statusColor = StatusPalette.colorForHealthStatus(
      snapshot.profile.status,
    );

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
            ScreenHeader(
              title: 'Profile',
              subtitle: 'Elder profile, health background, and wearable status',
              showBackButton: showBackButton,
            ),
            const SizedBox(height: AppSpacing.xl),
            PremiumCard(
              child: Row(
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppColors.accent.withValues(alpha: 0.88),
                          AppColors.accentSecondary.withValues(alpha: 0.88),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(24),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      'NL',
                      style: AppTextStyles.title.copyWith(
                        color: AppColors.background,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.lg),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          snapshot.profile.name,
                          style: AppTextStyles.headline,
                        ),
                        const SizedBox(height: AppSpacing.xxs),
                        Text(
                          '${snapshot.profile.age} years old',
                          style: AppTextStyles.body,
                        ),
                        const SizedBox(height: AppSpacing.md),
                        StatusChip(
                          label: StatusPalette.labelForHealthStatus(
                            snapshot.profile.status,
                          ),
                          color: statusColor,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),
            Text('Personal details', style: AppTextStyles.title),
            const SizedBox(height: AppSpacing.md),
            LayoutBuilder(
              builder: (context, constraints) {
                final tileWidth = (constraints.maxWidth - AppSpacing.md) / 2;

                return Wrap(
                  spacing: AppSpacing.md,
                  runSpacing: AppSpacing.md,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: DetailStatTile(
                        label: 'Height',
                        value: '${snapshot.profile.heightCm} cm',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: DetailStatTile(
                        label: 'Weight',
                        value: '${snapshot.profile.weightKg} kg',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: DetailStatTile(
                        label: 'Location',
                        value: 'District 7',
                        footnote: 'Ho Chi Minh City',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: DetailStatTile(
                        label: 'Last Sync',
                        value: DateFormat(
                          'h:mm a',
                        ).format(snapshot.profile.lastSync),
                        footnote: DateFormat(
                          'MMM d',
                        ).format(snapshot.profile.lastSync),
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: AppSpacing.xxl),
            PremiumCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Medical history', style: AppTextStyles.title),
                  const SizedBox(height: AppSpacing.md),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.sm,
                    children: snapshot.profile.medicalHistory.map((item) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.md,
                          vertical: AppSpacing.sm,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceMuted.withValues(alpha: 0.78),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(item, style: AppTextStyles.bodyStrong),
                      );
                    }).toList(),
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
                      Icon(Icons.watch_rounded, color: AppColors.accent),
                      const SizedBox(width: AppSpacing.sm),
                      Text('Wearable Device', style: AppTextStyles.title),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  _DeviceRow(
                    label: 'Connection',
                    value: snapshot.profile.deviceConnected
                        ? 'Connected'
                        : 'Disconnected',
                    color: snapshot.profile.deviceConnected
                        ? AppColors.success
                        : AppColors.danger,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(
                    label: 'Battery',
                    value: '${snapshot.profile.batteryLevel}%',
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      value: snapshot.profile.batteryLevel / 100,
                      minHeight: 8,
                      backgroundColor: AppColors.track,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        snapshot.profile.batteryLevel > 30
                            ? AppColors.accent
                            : AppColors.warning,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(
                    label: 'Last sync time',
                    value: DateFormat(
                      'MMM d, h:mm a',
                    ).format(snapshot.profile.lastSync),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(label: 'Location', value: snapshot.locationLabel),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),
            Consumer<ThemeProvider>(
              builder: (context, themeProvider, _) {
                return PremiumCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Appearance', style: AppTextStyles.title),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        'Light mode is the default view for a brighter caregiver dashboard.',
                        style: AppTextStyles.body,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      SegmentedButton<ThemeMode>(
                        showSelectedIcon: false,
                        segments: const [
                          ButtonSegment<ThemeMode>(
                            value: ThemeMode.light,
                            icon: Icon(Icons.light_mode_rounded),
                            label: Text('Light'),
                          ),
                          ButtonSegment<ThemeMode>(
                            value: ThemeMode.dark,
                            icon: Icon(Icons.dark_mode_rounded),
                            label: Text('Dark'),
                          ),
                        ],
                        selected: {themeProvider.themeMode},
                        onSelectionChanged: (selection) {
                          context.read<ThemeProvider>().setThemeMode(
                            selection.first,
                          );
                        },
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _DeviceRow extends StatelessWidget {
  const _DeviceRow({required this.label, required this.value, this.color});

  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: AppTextStyles.body.copyWith(color: AppColors.textMuted),
          ),
        ),
        Text(
          value,
          style: AppTextStyles.bodyStrong.copyWith(
            color: color ?? AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
