import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:elderly_health_monitor/models/auth_user.dart';
import 'package:elderly_health_monitor/models/device_summary.dart';
import 'package:elderly_health_monitor/providers/auth_provider.dart';
import 'package:elderly_health_monitor/screens/auth/login_screen.dart';
import 'package:elderly_health_monitor/services/mongo_repository.dart';

class _FakeMongoRepository implements MongoRepository {
  @override
  Future<List<DeviceSummary>> getAccessibleDevices(AuthUser user) async =>
      const [];

  @override
  Future<List<AuthUser>> getManagedUsers() async => const [];

  @override
  Future<AuthUser> login({
    required String username,
    required String password,
  }) {
    throw UnimplementedError();
  }
}

void main() {
  testWidgets('renders the login screen', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AuthProvider(repository: _FakeMongoRepository()),
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.text('Login'), findsOneWidget);
  });
}
