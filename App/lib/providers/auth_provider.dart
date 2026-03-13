import 'package:flutter/foundation.dart';

import '../models/auth_user.dart';
import '../models/device_summary.dart';
import '../services/mongo_repository.dart';
import '../services/mongo_repository_factory.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider({MongoRepository? repository})
    : _repository = repository ?? createMongoRepository();

  final MongoRepository _repository;

  AuthUser? _currentUser;
  List<DeviceSummary> _devices = const [];
  List<AuthUser> _managedUsers = const [];
  bool _isInitialized = false;
  bool _isLoading = false;
  String? _errorMessage;

  AuthUser? get currentUser => _currentUser;
  List<DeviceSummary> get devices => _devices;
  List<AuthUser> get managedUsers => _managedUsers;
  bool get isInitialized => _isInitialized;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _currentUser != null;
  bool get isAdmin => _currentUser?.isAdmin ?? false;

  Future<void> initialize() async {
    _isInitialized = true;
    notifyListeners();
  }

  Future<bool> login({
    required String username,
    required String password,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final user = await _repository.login(
        username: username,
        password: password,
      );
      _currentUser = user;
      _devices = await _repository.getAccessibleDevices(user);
      _managedUsers = user.isAdmin
          ? await _repository.getManagedUsers()
          : const [];
      return true;
    } on UnsupportedError catch (error) {
      _errorMessage = error.message ?? 'Unsupported platform.';
      return false;
    } on StateError catch (error) {
      _errorMessage = error.message;
      return false;
    } catch (_) {
      _errorMessage = 'Unable to sign in to MongoDB right now.';
      return false;
    } finally {
      _isLoading = false;
      _isInitialized = true;
      notifyListeners();
    }
  }

  Future<void> refreshData({bool showLoader = true}) async {
    final user = _currentUser;
    if (user == null || _isLoading) {
      return;
    }

    _isLoading = showLoader;
    _errorMessage = null;
    notifyListeners();

    try {
      _devices = await _repository.getAccessibleDevices(user);
      _managedUsers = user.isAdmin
          ? await _repository.getManagedUsers()
          : const [];
    } on UnsupportedError catch (error) {
      _errorMessage = error.message ?? 'Unsupported platform.';
    } on StateError catch (error) {
      _errorMessage = error.message;
    } catch (_) {
      _errorMessage = 'Unable to reload MongoDB data right now.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    _currentUser = null;
    _devices = const [];
    _managedUsers = const [];
    _errorMessage = null;
    notifyListeners();
  }
}
