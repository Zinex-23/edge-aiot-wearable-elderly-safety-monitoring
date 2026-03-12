import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/health_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';
import '../widgets/app_background.dart';
import 'activity_screen.dart';
import 'alerts_screen.dart';
import 'health_screen.dart';
import 'home_dashboard_screen.dart';
import 'profile_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<HealthProvider>();
    final snapshot = provider.snapshot;

    if (provider.isLoading && snapshot == null) {
      return const _LoadingView();
    }

    if (snapshot == null) {
      return _ErrorView(
        message:
            provider.errorMessage ??
            'Unable to connect to the wearable stream right now.',
        onRetry: () => context.read<HealthProvider>().loadDashboard(),
      );
    }

    final screens = [
      HomeDashboardScreen(snapshot: snapshot),
      HealthScreen(snapshot: snapshot),
      ActivityScreen(snapshot: snapshot),
      AlertsScreen(snapshot: snapshot),
      ProfileScreen(snapshot: snapshot),
    ];

    return Scaffold(
      extendBody: true,
      body: IndexedStack(index: _currentIndex, children: screens),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(
          AppSpacing.md,
          0,
          AppSpacing.md,
          AppSpacing.md,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(28),
          child: NavigationBar(
            selectedIndex: _currentIndex,
            onDestinationSelected: (index) {
              setState(() => _currentIndex = index);
            },
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home_rounded),
                label: 'Home',
              ),
              NavigationDestination(
                icon: Icon(Icons.favorite_outline_rounded),
                selectedIcon: Icon(Icons.favorite_rounded),
                label: 'Health',
              ),
              NavigationDestination(
                icon: Icon(Icons.directions_walk_outlined),
                selectedIcon: Icon(Icons.directions_walk_rounded),
                label: 'Activity',
              ),
              NavigationDestination(
                icon: Icon(Icons.notifications_outlined),
                selectedIcon: Icon(Icons.notifications_active_rounded),
                label: 'Alerts',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: 'Profile',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 88,
                  height: 88,
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Padding(
                    padding: EdgeInsets.all(22),
                    child: CircularProgressIndicator(
                      strokeWidth: 4,
                      color: AppColors.accent,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.xl),
                Text('Syncing wearable data', style: AppTextStyles.title),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  'Preparing dashboard, trends, and recent alerts.',
                  style: AppTextStyles.body,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppBackground(
        child: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.wifi_tethering_error_rounded,
                    size: 54,
                    color: AppColors.warning,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Data stream interrupted',
                    style: AppTextStyles.headline,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    message,
                    style: AppTextStyles.body,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.xl),
                  FilledButton(onPressed: onRetry, child: const Text('Retry')),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
