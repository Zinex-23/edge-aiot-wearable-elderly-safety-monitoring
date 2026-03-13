import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/dashboard_snapshot.dart';
import '../models/editable_device_info.dart';
import '../providers/auth_provider.dart';
import '../providers/health_provider.dart';
import '../providers/theme_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../theme/status_palette.dart';
import '../widgets/app_background.dart';
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
    final deviceInfo =
        context.watch<HealthProvider>().editableDeviceInfo ??
        EditableDeviceInfo(
          heightCm: snapshot.profile.heightCm,
          weightKg: snapshot.profile.weightKg,
          address: snapshot.locationLabel,
          phoneNumber: '+84 900 123 456',
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
            PremiumCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text('Device Information', style: AppTextStyles.title),
                      const Spacer(),
                      FilledButton.tonalIcon(
                        onPressed: () {
                          showDialog<void>(
                            context: context,
                            builder: (_) =>
                                _EditDeviceInfoDialog(initialInfo: deviceInfo),
                          );
                        },
                        icon: const Icon(Icons.edit_rounded),
                        label: const Text('Edit'),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  _DeviceRow(
                    label: 'Height',
                    value: '${deviceInfo.heightCm} cm',
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(
                    label: 'Weight',
                    value: '${deviceInfo.weightKg} kg',
                  ),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(label: 'Address', value: deviceInfo.address),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(label: 'Phone', value: deviceInfo.phoneNumber),
                  const SizedBox(height: AppSpacing.md),
                  _DeviceRow(
                    label: 'Last Sync',
                    value: DateFormat(
                      'MMM d, h:mm a',
                    ).format(snapshot.profile.lastSync),
                  ),
                ],
              ),
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
            const SizedBox(height: AppSpacing.xxl),
            PremiumCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Session', style: AppTextStyles.title),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Sign out to return to the login screen.',
                    style: AppTextStyles.body,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.tonalIcon(
                      onPressed: () => context.read<AuthProvider>().logout(),
                      icon: const Icon(Icons.logout_rounded),
                      label: const Text('Logout'),
                    ),
                  ),
                ],
              ),
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
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: AppTextStyles.body.copyWith(color: AppColors.textMuted),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          flex: 2,
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: AppTextStyles.bodyStrong.copyWith(
              color: color ?? AppColors.textPrimary,
            ),
          ),
        ),
      ],
    );
  }
}

class _EditDeviceInfoDialog extends StatefulWidget {
  const _EditDeviceInfoDialog({required this.initialInfo});

  final EditableDeviceInfo initialInfo;

  @override
  State<_EditDeviceInfoDialog> createState() => _EditDeviceInfoDialogState();
}

class _EditDeviceInfoDialogState extends State<_EditDeviceInfoDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _heightController;
  late final TextEditingController _weightController;
  late final TextEditingController _addressController;
  late final TextEditingController _phoneController;

  @override
  void initState() {
    super.initState();
    _heightController = TextEditingController(
      text: widget.initialInfo.heightCm.toString(),
    );
    _weightController = TextEditingController(
      text: widget.initialInfo.weightKg.toString(),
    );
    _addressController = TextEditingController(text: widget.initialInfo.address);
    _phoneController = TextEditingController(
      text: widget.initialInfo.phoneNumber,
    );
  }

  @override
  void dispose() {
    _heightController.dispose();
    _weightController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit Device Information'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _heightController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Height (cm)',
                  hintText: 'e.g. 158',
                ),
                validator: (value) {
                  final parsed = int.tryParse(value?.trim() ?? '');
                  if (parsed == null || parsed <= 0) {
                    return 'Enter a valid height';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              TextFormField(
                controller: _weightController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Weight (kg)',
                  hintText: 'e.g. 54',
                ),
                validator: (value) {
                  final parsed = int.tryParse(value?.trim() ?? '');
                  if (parsed == null || parsed <= 0) {
                    return 'Enter a valid weight';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              TextFormField(
                controller: _addressController,
                decoration: const InputDecoration(
                  labelText: 'Address',
                  hintText: 'e.g. 23 Nguyen Huu Tho, District 7',
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Address is required';
                  }
                  return null;
                },
              ),
              const SizedBox(height: AppSpacing.md),
              TextFormField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'Phone number',
                  hintText: 'e.g. +84 900 123 456',
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Phone number is required';
                  }
                  return null;
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _save,
          child: const Text('Save'),
        ),
      ],
    );
  }

  void _save() {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    final height = int.parse(_heightController.text.trim());
    final weight = int.parse(_weightController.text.trim());

    context.read<HealthProvider>().updateDeviceInfo(
      heightCm: height,
      weightKg: weight,
      address: _addressController.text,
      phoneNumber: _phoneController.text,
    );

    Navigator.of(context).pop();
  }
}
