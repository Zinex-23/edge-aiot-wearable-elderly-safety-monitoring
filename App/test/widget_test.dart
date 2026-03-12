import 'package:flutter_test/flutter_test.dart';

import 'package:elderly_health_monitor/app.dart';

void main() {
  testWidgets('renders the home dashboard after loading', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const ElderlyHealthMonitorApp());
    await tester.pump(const Duration(milliseconds: 1100));

    expect(find.text('Care Dashboard'), findsOneWidget);
    expect(find.text('Nguyen Thi Lan'), findsOneWidget);
    expect(find.text('Premium health view for today'), findsOneWidget);
  });
}
