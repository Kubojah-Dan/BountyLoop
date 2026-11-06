import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/features/auth/login_screen.dart';

void main() {
  testWidgets('Login screen loads with BountyLoop branding and role toggles',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );

    // Verify Brand title & tagline
    expect(find.text('BountyLoop'), findsOneWidget);
    expect(find.textContaining('Turn surplus into supper'), findsOneWidget);

    // Verify Role choice chips
    expect(find.text('Donor'), findsOneWidget);
    expect(find.text('Recipient'), findsOneWidget);

    // Default button is for Food Donor
    expect(find.text('Continue as Food Donor'), findsOneWidget);

    // Tap on Recipient role
    await tester.tap(find.text('Recipient'));
    await tester.pump();

    // Button updates to Food Rescue Partner
    expect(find.text('Continue as Food Rescue Partner'), findsOneWidget);
  });
}
