import '../data/mock_health_data.dart';
import '../models/dashboard_snapshot.dart';

class HealthMonitorService {
  Future<DashboardSnapshot> fetchDashboard() async {
    // Simulate device sync and local processing.
    await Future<void>.delayed(const Duration(milliseconds: 900));
    return MockHealthData.buildSnapshot();
  }
}
