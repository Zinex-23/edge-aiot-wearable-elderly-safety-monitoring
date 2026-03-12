import '../models/activity_hour.dart';
import '../models/dashboard_snapshot.dart';
import '../models/elderly_profile.dart';
import '../models/health_alert.dart';
import '../models/health_enums.dart';
import '../models/health_metric_point.dart';

class MockHealthData {
  const MockHealthData._();

  static DashboardSnapshot buildSnapshot() {
    final now = DateTime.now();

    return DashboardSnapshot(
      profile: ElderlyProfile(
        name: 'Nguyen Thi Lan',
        age: 78,
        heightCm: 158,
        weightKg: 54,
        medicalHistory: const [
          'Hypertension',
          'Type 2 Diabetes',
          'Mild arthritis',
        ],
        deviceConnected: true,
        batteryLevel: 76,
        lastSync: now.subtract(const Duration(minutes: 3)),
        status: HealthStatus.warning,
      ),
      restingHeartRateHistory: _dailySeries(now, const [
        64,
        63,
        64,
        65,
        62,
        61,
        63,
        64,
        62,
        61,
        60,
        62,
        63,
        64,
        65,
        63,
        62,
        61,
        62,
        64,
        65,
        66,
        65,
        64,
        63,
        62,
        64,
        65,
        67,
        66,
      ]),
      hrvHistory: _dailySeries(now, const [
        52,
        54,
        51,
        55,
        53,
        50,
        49,
        52,
        51,
        48,
        47,
        49,
        50,
        48,
        46,
        47,
        49,
        50,
        48,
        46,
        45,
        47,
        48,
        46,
        44,
        45,
        44,
        43,
        42,
        41,
      ]),
      spo2DailyHistory: _dailySeries(now, const [
        97,
        97,
        98,
        97,
        96,
        97,
        97,
        96,
        96,
        97,
        98,
        97,
        96,
        95,
        96,
        97,
        96,
        95,
        96,
        97,
        98,
        96,
        95,
        94,
        95,
        96,
        95,
        94,
        95,
        95,
      ]),
      spo2IntradayHistory: _intradaySeries(now, const [
        97,
        97,
        96,
        96,
        97,
        95,
        94,
        93,
        92,
        94,
        95,
        95,
      ]),
      activityByHour: const [
        ActivityHour(label: '6A', steps: 120, activeMinutes: 0),
        ActivityHour(label: '8A', steps: 180, activeMinutes: 2),
        ActivityHour(label: '10A', steps: 260, activeMinutes: 4),
        ActivityHour(label: '12P', steps: 360, activeMinutes: 5),
        ActivityHour(label: '2P', steps: 540, activeMinutes: 7),
        ActivityHour(label: '4P', steps: 720, activeMinutes: 8),
        ActivityHour(label: '6P', steps: 860, activeMinutes: 10),
        ActivityHour(label: '8P', steps: 760, activeMinutes: 8),
        ActivityHour(label: '10P', steps: 620, activeMinutes: 6),
        ActivityHour(label: '12A', steps: 460, activeMinutes: 4),
        ActivityHour(label: '2A', steps: 360, activeMinutes: 3),
        ActivityHour(label: '4A', steps: 240, activeMinutes: 1),
      ],
      alerts: [
        HealthAlert(
          id: 'alert_fall',
          title: 'Possible fall detected',
          description:
              'Sudden impact and posture change detected in the living room.',
          severity: AlertSeverity.critical,
          type: AlertType.fall,
          time: now.subtract(const Duration(minutes: 12)),
          isEmergency: true,
        ),
        HealthAlert(
          id: 'alert_spo2',
          title: 'Low SpO2 detected',
          description: 'SpO2 dropped to 92% for 8 minutes during rest.',
          severity: AlertSeverity.warning,
          type: AlertType.spo2,
          time: now.subtract(const Duration(hours: 1, minutes: 14)),
        ),
        HealthAlert(
          id: 'alert_rhr',
          title: 'High resting heart rate',
          description:
              'Resting heart rate stayed above 68 bpm earlier this morning.',
          severity: AlertSeverity.warning,
          type: AlertType.heartRate,
          time: now.subtract(const Duration(hours: 4, minutes: 42)),
        ),
        HealthAlert(
          id: 'alert_inactivity',
          title: 'No movement for 3 hours',
          description:
              'No meaningful activity detected between 1:00 PM and 4:00 PM.',
          severity: AlertSeverity.info,
          type: AlertType.inactivity,
          time: now.subtract(const Duration(days: 1, hours: 2)),
        ),
      ],
      healthScore: 84,
      calories: 438,
      distanceKm: 4.2,
      locationLabel: '23 Nguyen Huu Tho, District 7, Ho Chi Minh City',
    );
  }

  static List<HealthMetricPoint> _dailySeries(
    DateTime now,
    List<double> values,
  ) {
    final anchor = DateTime(now.year, now.month, now.day);

    return List.generate(values.length, (index) {
      final daysBack = values.length - 1 - index;
      return HealthMetricPoint(
        timestamp: anchor.subtract(Duration(days: daysBack)),
        value: values[index],
      );
    });
  }

  static List<HealthMetricPoint> _intradaySeries(
    DateTime now,
    List<double> values,
  ) {
    final anchor = DateTime(now.year, now.month, now.day, 6);

    return List.generate(values.length, (index) {
      return HealthMetricPoint(
        timestamp: anchor.add(Duration(hours: index * 2)),
        value: values[index],
      );
    });
  }
}
