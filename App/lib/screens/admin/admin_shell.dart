import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/auth_user.dart';
import '../../models/device_summary.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/app_background.dart';
import '../../widgets/premium_card.dart';
import '../device_dashboard_page.dart';

class AdminShell extends StatelessWidget {
  const AdminShell({super.key});

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final currentUser = authProvider.currentUser;
    if (currentUser == null) {
      return const SizedBox.shrink();
    }

    final devices = authProvider.devices;
    final users = authProvider.managedUsers;

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
                Text('Admin Console', style: AppTextStyles.headline),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Logged in as ${currentUser.username}. Review all user accounts and every wearable device in Atlas.',
                  style: AppTextStyles.body,
                ),
                const SizedBox(height: AppSpacing.xl),
                PremiumCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('System overview', style: AppTextStyles.title),
                      const SizedBox(height: AppSpacing.lg),
                      Wrap(
                        spacing: AppSpacing.md,
                        runSpacing: AppSpacing.md,
                        children: [
                          _MetricChip(
                            label: 'Managed accounts',
                            value: '${users.length}',
                          ),
                          _MetricChip(
                            label: 'All devices',
                            value: '${devices.length}',
                          ),
                          _MetricChip(
                            label: 'Role',
                            value: currentUser.role,
                          ),
                        ],
                      ),
                      if (authProvider.errorMessage != null) ...[
                        const SizedBox(height: AppSpacing.lg),
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
                _SectionHeading(
                  title: 'Caregiver Accounts',
                  subtitle: 'Admin can inspect every non-admin account stored in MongoDB.',
                ),
                const SizedBox(height: AppSpacing.md),
                if (users.isEmpty)
                  const _EmptyState(message: 'No caregiver account was found.')
                else
                  ...users.map(
                    (user) => Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.md),
                      child: _UserCard(
                        user: user,
                        deviceCount: _deviceCountForUser(user, devices),
                      ),
                    ),
                  ),
                const SizedBox(height: AppSpacing.xxl),
                _SectionHeading(
                  title: 'All Devices',
                  subtitle: 'Tap a device to open the existing dashboard for that wearer.',
                ),
                const SizedBox(height: AppSpacing.md),
                if (devices.isEmpty)
                  const _EmptyState(message: 'No device exists in MongoDB yet.')
                else
                  ...devices.map(
                    (device) => Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.md),
                      child: _DeviceCard(
                        device: device,
                        onTap: () => _openDashboard(context, device),
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

  int _deviceCountForUser(AuthUser user, List<DeviceSummary> devices) {
    return devices
        .where((device) => device.assignedUserIds.contains(user.id))
        .length;
  }

  void _openDashboard(BuildContext context, DeviceSummary device) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DeviceDashboardPage(device: device),
      ),
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.subtitle});

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

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

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

class _UserCard extends StatelessWidget {
  const _UserCard({required this.user, required this.deviceCount});

  final AuthUser user;
  final int deviceCount;

  @override
  Widget build(BuildContext context) {
    return PremiumCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(user.displayName, style: AppTextStyles.title),
          const SizedBox(height: AppSpacing.xs),
          Text('@${user.username}', style: AppTextStyles.body),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: [
              _MetricChip(label: 'Role', value: user.role),
              _MetricChip(label: 'Status', value: user.status),
              _MetricChip(label: 'Devices', value: '$deviceCount'),
            ],
          ),
        ],
      ),
    );
  }
}

class _DeviceCard extends StatelessWidget {
  const _DeviceCard({required this.device, required this.onTap});

  final DeviceSummary device;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final wearer = device.wearer;
    final battery = device.currentState?.batteryLevel ?? 0;
    final location = device.currentState?.latestLocation?.label ?? 'Unknown location';

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
                    : device.serialNumber,
                style: AppTextStyles.bodyStrong,
              ),
              const SizedBox(height: AppSpacing.xxs),
              Text(location, style: AppTextStyles.body),
              const SizedBox(height: AppSpacing.md),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  _MetricChip(label: 'Status', value: device.status),
                  _MetricChip(label: 'Battery', value: '$battery%'),
                  _MetricChip(
                    label: 'Assigned users',
                    value: '${device.assignedUserIds.length}',
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

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return PremiumCard(
      child: Text(message, style: AppTextStyles.body),
    );
  }
}
