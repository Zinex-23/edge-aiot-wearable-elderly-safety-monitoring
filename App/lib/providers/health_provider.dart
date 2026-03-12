import 'package:flutter/foundation.dart';

import '../models/dashboard_snapshot.dart';
import '../services/health_monitor_service.dart';

class HealthProvider extends ChangeNotifier {
  HealthProvider({required HealthMonitorService service}) : _service = service;

  final HealthMonitorService _service;

  DashboardSnapshot? _snapshot;
  bool _isLoading = false;
  String? _errorMessage;

  DashboardSnapshot? get snapshot => _snapshot;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadDashboard({bool showLoader = true}) async {
    if (_isLoading) {
      return;
    }

    _isLoading = showLoader || _snapshot == null;
    _errorMessage = null;
    notifyListeners();

    try {
      _snapshot = await _service.fetchDashboard();
    } catch (_) {
      _errorMessage =
          'Unable to load wearable data right now. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() => loadDashboard(showLoader: false);
}
