import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/features/auth/login_screen.dart';

void main() {
  testWidgets('Login screen loads with BountyLoop branding and demo role switchers',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: LoginScreen(),
        ),
      ),
    );

    // Verify Brand title & Figma tagline
    expect(find.text('BountyLoop'), findsOneWidget);
    expect(find.textContaining('More shared. Less wasted.'), findsOneWidget);

    // Verify Email and Password input labels
    expect(find.text('Email address'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);

    // Verify 1-tap demo cards
    expect(find.text('Donor'), findsOneWidget);
    expect(find.text('Recipient Pantry'), findsOneWidget);
  });
}
