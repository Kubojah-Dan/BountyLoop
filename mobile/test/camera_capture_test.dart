import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/features/donate/camera_capture_screen.dart';

void main() {
  testWidgets('CameraCaptureScreen renders Figma 3-step AI assessment and safety verification',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: CameraCaptureScreen(),
        ),
      ),
    );

    // Verify Title & Stepper
    expect(find.text('Photo to rescue'), findsOneWidget);
    expect(find.text('NEW DONATION • DRAFT'), findsOneWidget);
    expect(find.text('1 Photo'), findsOneWidget);
    expect(find.text('2 Review AI'), findsOneWidget);
    expect(find.text('3 Publish'), findsOneWidget);

    // Verify AI assessment card
    expect(find.text('AI assessment'), findsOneWidget);
    expect(find.text('ITEM CATEGORY'), findsOneWidget);
    expect(find.text('Bakery • mixed pastries'), findsOneWidget);
    expect(find.text('HAZARD GATE - DONOR CHECK REQUIRED'), findsOneWidget);

    // Verify actions
    expect(find.text('Confirm assessment'), findsOneWidget);
    expect(find.text('Correct AI details'), findsOneWidget);
    expect(find.byType(Checkbox), findsOneWidget);
  });
}
