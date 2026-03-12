import 'health_enums.dart';

class HealthAlert {
  const HealthAlert({
    required this.id,
    required this.title,
    required this.description,
    required this.severity,
    required this.type,
    required this.time,
    this.isEmergency = false,
  });

  final String id;
  final String title;
  final String description;
  final AlertSeverity severity;
  final AlertType type;
  final DateTime time;
  final bool isEmergency;
}
