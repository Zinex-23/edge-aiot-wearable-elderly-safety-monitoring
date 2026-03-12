enum HealthStatus { normal, warning, critical }

enum AlertSeverity { info, warning, critical }

enum AlertType { heartRate, hrv, spo2, inactivity, fall }

enum ChartPeriod { day, week, month, sixMonths, year }

enum HrvStatus { good, moderate, low }

enum ActivityRating { low, moderate, good }

extension ChartPeriodLabel on ChartPeriod {
  String get label {
    switch (this) {
      case ChartPeriod.day:
        return 'D';
      case ChartPeriod.week:
        return 'W';
      case ChartPeriod.month:
        return 'M';
      case ChartPeriod.sixMonths:
        return '6M';
      case ChartPeriod.year:
        return 'Y';
    }
  }
}
