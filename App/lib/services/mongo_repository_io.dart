import 'package:bcrypt/bcrypt.dart';
import 'package:mongo_dart/mongo_dart.dart';

import '../models/auth_user.dart';
import '../models/device_summary.dart';
import 'mongo_repository.dart';

MongoRepository createMongoRepository() => MongoAtlasRepository();

class MongoAtlasRepository implements MongoRepository {
  MongoAtlasRepository();

  static const String _mongoUri = String.fromEnvironment('MONGODB_URI');

  Db? _db;

  Future<Db> _database() async {
    if (_mongoUri.isEmpty) {
      throw StateError(
        'Missing MONGODB_URI. Start Flutter with --dart-define=MONGODB_URI=...',
      );
    }

    final db = _db;
    if (db != null && db.isConnected) {
      return db;
    }

    final next = Db(_mongoUri);
    await next.open();
    _db = next;
    return next;
  }

  Future<DbCollection> _users() async => (await _database()).collection('users');

  Future<DbCollection> _devices() async =>
      (await _database()).collection('devices');

  Future<DbCollection> _wearers() async =>
      (await _database()).collection('wearers');

  @override
  Future<AuthUser> login({
    required String username,
    required String password,
  }) async {
    final normalizedUsername = username.trim().toLowerCase();
    final users = await _users();
    final userDocument =
        await users.findOne(where.eq('username', normalizedUsername)) ??
        await users.findOne(where.eq('username', username.trim()));

    if (userDocument == null) {
      throw StateError('Username or password is incorrect.');
    }

    final status = (userDocument['status'] as String? ?? 'ACTIVE').toUpperCase();
    if (status != 'ACTIVE') {
      throw StateError('This account is disabled.');
    }

    final passwordHash = userDocument['passwordHash'] as String?;
    if (passwordHash == null || passwordHash.isEmpty) {
      throw StateError('This account is missing a password hash.');
    }

    final isValid = BCrypt.checkpw(password, passwordHash);
    if (!isValid) {
      throw StateError('Username or password is incorrect.');
    }

    return AuthUser.fromJson(userDocument);
  }

  @override
  Future<List<DeviceSummary>> getAccessibleDevices(AuthUser user) async {
    final devices = await _devices();
    final selector = user.isAdmin
        ? where.sortBy('deviceCode')
        : where.eq('assignedUserIds', ObjectId.fromHexString(user.id));

    final deviceDocuments = await devices.find(selector).toList();
    return _hydrateDevices(deviceDocuments);
  }

  @override
  Future<List<AuthUser>> getManagedUsers() async {
    final users = await _users();
    final documents = await users.find({
      'role': {'\$ne': 'ADMIN'},
    }).toList();

    documents.sort((left, right) {
      final leftName = (left['username'] as String? ?? '').toLowerCase();
      final rightName = (right['username'] as String? ?? '').toLowerCase();
      return leftName.compareTo(rightName);
    });

    return documents.map(AuthUser.fromJson).toList(growable: false);
  }

  Future<List<DeviceSummary>> _hydrateDevices(
    List<Map<String, dynamic>> deviceDocuments,
  ) async {
    final wearerIds = deviceDocuments
        .map((device) => device['wearerId'])
        .whereType<ObjectId>()
        .toSet()
        .toList(growable: false);

    final wearersById = <String, Map<String, dynamic>>{};
    if (wearerIds.isNotEmpty) {
      final wearers = await _wearers();
      final wearerDocuments = await wearers.find({
        '_id': {'\$in': wearerIds},
      }).toList();
      for (final wearer in wearerDocuments) {
        final id = wearer['_id'];
        if (id is ObjectId) {
          wearersById[id.oid] = wearer;
        }
      }
    }

    return deviceDocuments.map((device) {
      final wearerId = device['wearerId'];
      final wearerDocument = wearerId is ObjectId ? wearersById[wearerId.oid] : null;

      return DeviceSummary.fromJson({
        '_id': device['_id'],
        'deviceCode': device['deviceCode'],
        'serialNumber': device['serialNumber'],
        'model': device['model'] ?? '',
        'firmwareVersion': device['firmwareVersion'] ?? '',
        'status': device['status'] ?? 'UNKNOWN',
        'assignedUserIds': device['assignedUserIds'] ?? const [],
        'primaryAssignedUserId': device['primaryAssignedUserId'],
        'currentState': device['currentState'] ?? const {},
        'wearer': wearerDocument == null
            ? null
            : {
                '_id': wearerDocument['_id'],
                'fullName': wearerDocument['fullName'] ?? '',
                'gender': wearerDocument['gender'] ?? '',
                'dateOfBirth': wearerDocument['dateOfBirth'],
                'phone': wearerDocument['phone'] ?? '',
              },
      });
    }).toList(growable: false);
  }
}
