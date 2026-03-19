import '../models/auth_user.dart';
import '../models/device_summary.dart';
import 'mongo_repository.dart';

MongoRepository createMongoRepository() => _UnsupportedMongoRepository();

class _UnsupportedMongoRepository implements MongoRepository {
  @override
  Future<List<DeviceSummary>> getAccessibleDevices(AuthUser user) {
    throw UnsupportedError(
      'Direct MongoDB access is not supported on Flutter web. Run the app on Android, iOS, or desktop.',
    );
  }

  @override
  Future<AuthUser> login({
    required String username,
    required String password,
  }) {
    throw UnsupportedError(
      'Direct MongoDB access is not supported on Flutter web. Run the app on Android, iOS, or desktop.',
    );
  }

  @override
  Future<List<AuthUser>> getManagedUsers() {
    throw UnsupportedError(
      'Direct MongoDB access is not supported on Flutter web. Run the app on Android, iOS, or desktop.',
    );
  }
}
