import 'dart:math' as math;

import 'activity_hour.dart';
import 'elderly_profile.dart';
import 'health_alert.dart';
import 'health_enums.dart';
import 'health_metric_point.dart';

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.profile,
    required this.restingHeartRateHistory,
    required this.hrvHistory,
    required this.spo2DailyHistory,
    required this.spo2IntradayHistory,
    required this.activityByHour,
    required this.alerts,
    required this.healthScore,
    required this.calories,
    required this.distanceKm,
    required this.locationLabel,
  });

  final ElderlyProfile profile;
  final List<HealthMetricPoint> restingHeartRateHistory;
  final List<HealthMetricPoint> hrvHistory;
  final List<HealthMetricPoint> spo2DailyHistory;
  final List<HealthMetricPoint> spo2IntradayHistory;
  final List<ActivityHour> activityByHour;
  final List<HealthAlert> alerts;
  final int healthScore;
  final int calories;
  final double distanceKm;
  final String locationLabel;

  int get restingHeartRateToday => restingHeartRateHistory.last.value.round();

  double get restingHeartRate30DayAverage => _average(restingHeartRateHistory);

  int get hrvToday => hrvHistory.last.value.round();

  double get hrv7DayAverage =>
      _average(hrvHistory.sublist(math.max(hrvHistory.length - 7, 0)));

  double get hrv30DayAverage => _average(hrvHistory);

  int get spo2Current => spo2IntradayHistory.last.value.round();

  int get spo2Min =>
      spo2IntradayHistory.map((point) => point.value.round()).reduce(math.min);

  int get spo2Max =>
      spo2IntradayHistory.map((point) => point.value.round()).reduce(math.max);

  int get dailySteps =>
      activityByHour.fold<int>(0, (sum, item) => sum + item.steps);

  int get activeMinutes =>
      activityByHour.fold<int>(0, (sum, item) => sum + item.activeMinutes);

  HealthAlert get latestAlert => alerts.first;

  HealthAlert? get emergencyAlert {
    for (final alert in alerts) {
      if (alert.isEmergency) {
        return alert;
      }
    }
    return null;
  }

  bool get hasEmergencyAlert => emergencyAlert != null;

  bool get hasSpo2Warning => spo2Current < 94 || spo2Min < 94;

  HrvStatus get hrvStatus {
    if (hrvToday >= 48) {
      return HrvStatus.good;
    }
    if (hrvToday >= 40) {
      return HrvStatus.moderate;
    }
    return HrvStatus.low;
  }

  ActivityRating get activityRating {
    if (dailySteps >= 7000 && activeMinutes >= 45) {
      return ActivityRating.good;
    }
    if (dailySteps >= 4000 || activeMinutes >= 30) {
      return ActivityRating.moderate;
    }
    return ActivityRating.low;
  }

  String get hrvInsight {
    if (hrvHistory.length < 4) {
      return 'HRV is stable over the last few days.';
    }

    final latest = hrvHistory.last.value;
    final threeDaysAgo = hrvHistory[hrvHistory.length - 4].value;
    if (latest < threeDaysAgo) {
      return 'HRV has been slightly decreasing over the last 3 days.';
    }
    return 'HRV is holding steady and recovery looks balanced.';
  }

  static double _average(List<HealthMetricPoint> points) {
    if (points.isEmpty) {
      return 0;
    }

    final total = points.fold<double>(0, (sum, point) => sum + point.value);
    return total / points.length;
  }
}
