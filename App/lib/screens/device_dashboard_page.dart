import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/device_summary.dart';
import '../providers/health_provider.dart';
import '../services/health_monitor_service.dart';
import 'main_shell.dart';

class DeviceDashboardPage extends StatelessWidget {
  const DeviceDashboardPage({super.key, required this.device});

  final DeviceSummary device;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) =>
          HealthProvider(service: HealthMonitorService(device: device))
            ..loadDashboard(),
      child: const MainShell(),
    );
  }
}
