import 'package:flutter/foundation.dart';

import '../models/dashboard_snapshot.dart';
import '../models/editable_device_info.dart';
import '../services/health_monitor_service.dart';

class HealthProvider extends ChangeNotifier {
  HealthProvider({required HealthMonitorService service}) : _service = service;

  final HealthMonitorService _service;

  DashboardSnapshot? _snapshot;
  EditableDeviceInfo? _editableDeviceInfo;
  bool _isLoading = false;
  String? _errorMessage;

  DashboardSnapshot? get snapshot => _snapshot;
  EditableDeviceInfo? get editableDeviceInfo => _editableDeviceInfo;
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
      _editableDeviceInfo ??= EditableDeviceInfo(
        heightCm: _snapshot!.profile.heightCm,
        weightKg: _snapshot!.profile.weightKg,
        address: _snapshot!.locationLabel,
        phoneNumber: '+84 900 123 456',
      );
    } catch (_) {
      _errorMessage =
          'Unable to load wearable data right now. Please try again.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() => loadDashboard(showLoader: false);

  void updateDeviceInfo({
    required int heightCm,
    required int weightKg,
    required String address,
    required String phoneNumber,
  }) {
    if (heightCm <= 0 || weightKg <= 0) {
      return;
    }

    _editableDeviceInfo = EditableDeviceInfo(
      heightCm: heightCm,
      weightKg: weightKg,
      address: address.trim(),
      phoneNumber: phoneNumber.trim(),
    );
    notifyListeners();
  }
}
