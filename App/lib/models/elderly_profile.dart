import 'health_enums.dart';

class ElderlyProfile {
  const ElderlyProfile({
    required this.name,
    required this.age,
    required this.heightCm,
    required this.weightKg,
    required this.medicalHistory,
    required this.deviceConnected,
    required this.batteryLevel,
    required this.lastSync,
    required this.status,
  });

  final String name;
  final int age;
  final int heightCm;
  final int weightKg;
  final List<String> medicalHistory;
  final bool deviceConnected;
  final int batteryLevel;
  final DateTime lastSync;
  final HealthStatus status;
}
