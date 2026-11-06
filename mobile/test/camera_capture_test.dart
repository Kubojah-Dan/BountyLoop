import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/features/donate/camera_capture_screen.dart';

void main() {
  testWidgets('CameraCaptureScreen allows setting weight and choosing sample photo',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: CameraCaptureScreen(),
        ),
      ),
    );

    // Verify initial UI elements
    expect(find.text('Donate Surplus Food'), findsOneWidget);
    expect(find.text('Take or Upload Food Photo'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Estimated Weight (kg)'), findsOneWidget);

    // Tap "use demo sample photo"
    await tester.tap(find.text('Or use demo sample photo'));
    await tester.pump();

    // Verify placeholder replaced by preview image with refresh button
    expect(find.byIcon(Icons.refresh), findsOneWidget);

    // Update weight
    final weightField = find.widgetWithText(TextField, '3.5');
    expect(weightField, findsOneWidget);
    await tester.enterText(weightField, '6.0');
    await tester.pump();
    expect(find.text('6.0'), findsOneWidget);
  });
}

