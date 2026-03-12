import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/health_provider.dart';
import 'providers/theme_provider.dart';
import 'screens/main_shell.dart';
import 'services/health_monitor_service.dart';
import 'theme/app_colors.dart';
import 'theme/app_theme.dart';

class ElderlyHealthMonitorApp extends StatelessWidget {
  const ElderlyHealthMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) =>
              HealthProvider(service: HealthMonitorService())..loadDashboard(),
        ),
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          AppColors.applyThemeMode(themeProvider.themeMode);

          return MaterialApp(
            title: 'Elderly Health Monitor',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: themeProvider.themeMode,
            home: const MainShell(),
          );
        },
      ),
    );
  }
}
