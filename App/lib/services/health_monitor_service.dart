import '../data/mock_health_data.dart';
import '../models/dashboard_snapshot.dart';
import '../models/device_summary.dart';
import '../models/elderly_profile.dart';
import '../models/health_enums.dart';
import '../models/health_metric_point.dart';

class HealthMonitorService {
  HealthMonitorService({required DeviceSummary device}) : _device = device;

  final DeviceSummary _device;

  Future<DashboardSnapshot> fetchDashboard() async {
    return _buildSnapshotFromDevice(_device);
  }

  DashboardSnapshot _buildSnapshotFromDevice(DeviceSummary device) {
    final base = MockHealthData.buildSnapshot();
    final latestHealth = device.currentState?.latestHealth;
    final latestLocation = device.currentState?.latestLocation;
    final lastSeenAt = device.currentState?.lastSeenAt ?? base.profile.lastSync;
    final heartRate = (latestHealth?.heartRate ?? base.restingHeartRateToday)
        .toDouble();
    final hrv = (latestHealth?.hrv ?? base.hrvToday).toDouble();
    final spo2 = (latestHealth?.spo2 ?? base.spo2Current).toDouble();
    final age = _calculateAge(device.wearer?.dateOfBirth) ?? base.profile.age;
    final locationLabel = latestLocation != null && latestLocation.label.isNotEmpty
        ? latestLocation.label
        : base.locationLabel;

    return DashboardSnapshot(
      profile: ElderlyProfile(
        name: device.wearer?.fullName ?? base.profile.name,
        age: age,
        heightCm: base.profile.heightCm,
        weightKg: base.profile.weightKg,
        medicalHistory: base.profile.medicalHistory,
        deviceConnected: device.currentState?.connectionStatus == 'ONLINE',
        batteryLevel: device.currentState?.batteryLevel ?? base.profile.batteryLevel,
        lastSync: lastSeenAt,
        status: _profileStatusFor(heartRate: heartRate, spo2: spo2),
      ),
      restingHeartRateHistory: _replaceLatestValue(
        base.restingHeartRateHistory,
        heartRate,
      ),
      hrvHistory: _replaceLatestValue(base.hrvHistory, hrv),
      spo2DailyHistory: _replaceLatestValue(base.spo2DailyHistory, spo2),
      spo2IntradayHistory: _replaceLatestValue(base.spo2IntradayHistory, spo2),
      activityByHour: base.activityByHour,
      alerts: base.alerts,
      healthScore: _healthScoreFor(
        heartRate: heartRate.round(),
        spo2: spo2.round(),
        hrv: hrv.round(),
      ),
      calories: base.calories,
      distanceKm: base.distanceKm,
      locationLabel: locationLabel,
    );
  }

  static List<HealthMetricPoint> _replaceLatestValue(
    List<HealthMetricPoint> points,
    double latestValue,
  ) {
    if (points.isEmpty) {
      return points;
    }

    return [
      ...points.take(points.length - 1),
      HealthMetricPoint(
        timestamp: points.last.timestamp,
        value: latestValue,
      ),
    ];
  }

  static int? _calculateAge(DateTime? dateOfBirth) {
    if (dateOfBirth == null) {
      return null;
    }

    final now = DateTime.now();
    var age = now.year - dateOfBirth.year;
    final hasBirthdayPassed =
        now.month > dateOfBirth.month ||
        (now.month == dateOfBirth.month && now.day >= dateOfBirth.day);
    if (!hasBirthdayPassed) {
      age -= 1;
    }
    return age;
  }

  static HealthStatus _profileStatusFor({
    required double heartRate,
    required double spo2,
  }) {
    if (spo2 < 94 || heartRate > 72) {
      return HealthStatus.warning;
    }
    return HealthStatus.normal;
  }

  static int _healthScoreFor({
    required int heartRate,
    required int spo2,
    required int hrv,
  }) {
    var score = 84;

    if (spo2 < 94) {
      score -= 10;
    }
    if (heartRate > 72) {
      score -= 5;
    }
    if (hrv < 40) {
      score -= 4;
    }

    return score.clamp(0, 100);
  }
}
