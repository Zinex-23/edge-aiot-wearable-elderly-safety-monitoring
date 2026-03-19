import '../models/auth_user.dart';
import '../models/device_summary.dart';

abstract class MongoRepository {
  Future<AuthUser> login({
    required String username,
    required String password,
  });

  Future<List<DeviceSummary>> getAccessibleDevices(AuthUser user);

  Future<List<AuthUser>> getManagedUsers();
}
