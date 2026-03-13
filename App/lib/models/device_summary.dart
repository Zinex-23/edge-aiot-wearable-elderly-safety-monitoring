class DeviceSummary {
  const DeviceSummary({
    required this.id,
    required this.deviceCode,
    required this.serialNumber,
    required this.model,
    required this.firmwareVersion,
    required this.status,
    required this.wearer,
    required this.assignedUserIds,
    required this.primaryAssignedUserId,
    required this.currentState,
  });

  final String id;
  final String deviceCode;
  final String serialNumber;
  final String model;
  final String firmwareVersion;
  final String status;
  final WearerSummary? wearer;
  final List<String> assignedUserIds;
  final String? primaryAssignedUserId;
  final DeviceCurrentState? currentState;

  factory DeviceSummary.fromJson(Map<String, dynamic> json) {
    return DeviceSummary(
      id: _stringValue(json['id'] ?? json['_id']),
      deviceCode: json['deviceCode'] as String? ?? '',
      serialNumber: json['serialNumber'] as String? ?? '',
      model: json['model'] as String? ?? '',
      firmwareVersion: json['firmwareVersion'] as String? ?? '',
      status: json['status'] as String? ?? '',
      wearer: json['wearer'] is Map<String, dynamic>
          ? WearerSummary.fromJson(json['wearer'] as Map<String, dynamic>)
          : null,
      assignedUserIds:
          (json['assignedUserIds'] as List<dynamic>? ?? const [])
              .map(_stringValue)
              .toList(),
      primaryAssignedUserId: json['primaryAssignedUserId'] == null
          ? null
          : _stringValue(json['primaryAssignedUserId']),
      currentState: json['currentState'] is Map<String, dynamic>
          ? DeviceCurrentState.fromJson(
              json['currentState'] as Map<String, dynamic>,
            )
          : null,
    );
  }
}

class WearerSummary {
  const WearerSummary({
    required this.id,
    required this.fullName,
    required this.gender,
    required this.dateOfBirth,
    required this.phone,
  });

  final String id;
  final String fullName;
  final String gender;
  final DateTime? dateOfBirth;
  final String phone;

  factory WearerSummary.fromJson(Map<String, dynamic> json) {
    return WearerSummary(
      id: _stringValue(json['id'] ?? json['_id']),
      fullName: json['fullName'] as String? ?? '',
      gender: json['gender'] as String? ?? '',
      dateOfBirth: _tryParseDateTime(json['dateOfBirth']),
      phone: json['phone'] as String? ?? '',
    );
  }
}

class DeviceCurrentState {
  const DeviceCurrentState({
    required this.connectionStatus,
    required this.batteryLevel,
    required this.lastSeenAt,
    required this.latestHealth,
    required this.latestLocation,
  });

  final String connectionStatus;
  final int batteryLevel;
  final DateTime? lastSeenAt;
  final LatestHealth? latestHealth;
  final LatestLocation? latestLocation;

  factory DeviceCurrentState.fromJson(Map<String, dynamic> json) {
    return DeviceCurrentState(
      connectionStatus: json['connectionStatus'] as String? ?? 'OFFLINE',
      batteryLevel: (json['batteryLevel'] as num?)?.round() ?? 0,
      lastSeenAt: _tryParseDateTime(json['lastSeenAt']),
      latestHealth: json['latestHealth'] is Map<String, dynamic>
          ? LatestHealth.fromJson(json['latestHealth'] as Map<String, dynamic>)
          : null,
      latestLocation: json['latestLocation'] is Map<String, dynamic>
          ? LatestLocation.fromJson(
              json['latestLocation'] as Map<String, dynamic>,
            )
          : null,
    );
  }
}

class LatestHealth {
  const LatestHealth({
    required this.heartRate,
    required this.spo2,
    required this.hrv,
    required this.capturedAt,
  });

  final int? heartRate;
  final int? spo2;
  final int? hrv;
  final DateTime? capturedAt;

  factory LatestHealth.fromJson(Map<String, dynamic> json) {
    return LatestHealth(
      heartRate: (json['heartRate'] as num?)?.round(),
      spo2: (json['spo2'] as num?)?.round(),
      hrv: (json['hrv'] as num?)?.round(),
      capturedAt: _tryParseDateTime(json['capturedAt']),
    );
  }
}

class LatestLocation {
  const LatestLocation({
    required this.label,
    required this.lat,
    required this.lng,
    required this.capturedAt,
  });

  final String label;
  final double? lat;
  final double? lng;
  final DateTime? capturedAt;

  factory LatestLocation.fromJson(Map<String, dynamic> json) {
    return LatestLocation(
      label: json['label'] as String? ?? '',
      lat: (json['lat'] as num?)?.toDouble(),
      lng: (json['lng'] as num?)?.toDouble(),
      capturedAt: _tryParseDateTime(json['capturedAt']),
    );
  }
}

DateTime? _tryParseDateTime(dynamic value) {
  if (value is DateTime) {
    return value;
  }
  if (value is String && value.isNotEmpty) {
    return DateTime.tryParse(value);
  }
  return null;
}

String _stringValue(dynamic value) {
  if (value == null) {
    return '';
  }
  if (value is String) {
    return value;
  }
  final text = value.toString();
  if (text.startsWith('ObjectId("') && text.endsWith('")')) {
    return text.substring(10, text.length - 2);
  }
  return text;
}
