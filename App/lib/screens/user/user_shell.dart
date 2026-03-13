import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/device_summary.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/app_background.dart';
import '../../widgets/premium_card.dart';
import '../device_dashboard_page.dart';

class UserShell extends StatelessWidget {
  const UserShell({super.key});

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final currentUser = authProvider.currentUser;
    if (currentUser == null) {
      return const SizedBox.shrink();
    }

    final devices = authProvider.devices;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackground(
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: () => context.read<AuthProvider>().refreshData(),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(
                parent: BouncingScrollPhysics(),
              ),
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.lg,
                AppSpacing.lg,
                AppSpacing.lg,
                AppSpacing.xxl,
              ),
              children: [
                Text('My Devices', style: AppTextStyles.headline),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Logged in as ${currentUser.displayName}. Select one device to open the existing monitoring dashboard.',
                  style: AppTextStyles.body,
                ),
                const SizedBox(height: AppSpacing.xl),
                PremiumCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Account', style: AppTextStyles.title),
                      const SizedBox(height: AppSpacing.md),
                      _QuickRow(label: 'Username', value: currentUser.username),
                      const SizedBox(height: AppSpacing.sm),
                      _QuickRow(label: 'Role', value: currentUser.role),
                      const SizedBox(height: AppSpacing.sm),
                      _QuickRow(label: 'Assigned devices', value: '${devices.length}'),
                      if (authProvider.errorMessage != null) ...[
                        const SizedBox(height: AppSpacing.md),
                        Text(
                          authProvider.errorMessage!,
                          style: AppTextStyles.bodyStrong.copyWith(
                            color: AppColors.warning,
                          ),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.lg),
                      Row(
                        children: [
                          FilledButton.tonalIcon(
                            onPressed: authProvider.isLoading
                                ? null
                                : () => context.read<AuthProvider>().refreshData(),
                            icon: const Icon(Icons.sync_rounded),
                            label: const Text('Refresh'),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          FilledButton.tonalIcon(
                            onPressed: () => context.read<AuthProvider>().logout(),
                            icon: const Icon(Icons.logout_rounded),
                            label: const Text('Logout'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.xxl),
                Text('Assigned Wearables', style: AppTextStyles.title),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'A caregiver account can manage multiple devices. Tap any card to drill into the old dashboard.',
                  style: AppTextStyles.body,
                ),
                const SizedBox(height: AppSpacing.md),
                if (devices.isEmpty)
                  PremiumCard(
                    child: Text(
                      'No device has been assigned to this account yet.',
                      style: AppTextStyles.body,
                    ),
                  )
                else
                  ...devices.map(
                    (device) => Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.md),
                      child: _AssignedDeviceCard(
                        device: device,
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => DeviceDashboardPage(device: device),
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickRow extends StatelessWidget {
  const _QuickRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Text(label, style: AppTextStyles.body)),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: AppTextStyles.bodyStrong,
          ),
        ),
      ],
    );
  }
}

class _AssignedDeviceCard extends StatelessWidget {
  const _AssignedDeviceCard({required this.device, required this.onTap});

  final DeviceSummary device;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final wearer = device.wearer;
    final latestHealth = device.currentState?.latestHealth;

    return PremiumCard(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(24),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xs),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(device.deviceCode, style: AppTextStyles.title),
              const SizedBox(height: AppSpacing.xs),
              Text(
                wearer?.fullName.isNotEmpty == true
                    ? wearer!.fullName
                    : 'Wearer not linked',
                style: AppTextStyles.bodyStrong,
              ),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                device.currentState?.latestLocation?.label ?? 'Unknown location',
                style: AppTextStyles.body,
              ),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  _Pill(label: 'Status', value: device.status),
                  _Pill(
                    label: 'Heart rate',
                    value: latestHealth?.heartRate == null
                        ? '--'
                        : '${latestHealth!.heartRate} bpm',
                  ),
                  _Pill(
                    label: 'Battery',
                    value: '${device.currentState?.batteryLevel ?? 0}%',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.value});

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
        border: Border.all(color: AppColors.border),
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
