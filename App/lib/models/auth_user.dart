class AuthUser {
  const AuthUser({
    required this.id,
    required this.username,
    required this.displayName,
    required this.role,
    required this.status,
    required this.mustChangePassword,
  });

  final String id;
  final String username;
  final String displayName;
  final String role;
  final String status;
  final bool mustChangePassword;

  bool get isAdmin => role == 'ADMIN';
  bool get isCaregiver => role == 'CAREGIVER';

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: _stringValue(json['id'] ?? json['_id']),
      username: (json['username'] as String? ?? '').trim(),
      displayName:
          (json['displayName'] as String? ?? json['username'] as String? ?? '')
              .trim(),
      role: json['role'] as String? ?? 'CAREGIVER',
      status: json['status'] as String? ?? 'ACTIVE',
      mustChangePassword: json['mustChangePassword'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'displayName': displayName,
      'role': role,
      'status': status,
      'mustChangePassword': mustChangePassword,
    };
  }
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
