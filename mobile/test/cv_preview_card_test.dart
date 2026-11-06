import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/donate/cv_preview_card.dart';
import 'package:bountyloop_app/models/donation_model.dart';

void main() {
  testWidgets('CvPreviewCard renders AI prediction, confidence, and freshness badge',
      (WidgetTester tester) async {
    final donation = DonationModel(
      id: 'don_123',
      donorId: 'donor_abc',
      item: 'produce_fruit',
      itemConfidence: 0.94,
      freshness: 'grade_2_good',
      freshnessConfidence: 0.92,
      hazardFlag: 'none',
      estWeightKg: 4.5,
      expiresAt: DateTime.now().add(const Duration(hours: 48)),
      status: 'draft',
      needsReview: false,
      photoPaths: ['photos/don_123/img.jpg'],
      createdAt: DateTime.now(),
    );

    bool correctTapped = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: CvPreviewCard(
            donation: donation,
            onCorrect: () => correctTapped = true,
          ),
        ),
      ),
    );

    // Verify item title and confidence percentage
    expect(find.text('Fresh Fruit'), findsOneWidget);
    expect(find.text('94% AI match'), findsOneWidget);
    expect(find.text('Grade 2: Good'), findsOneWidget);
    expect(find.text('Estimated weight: 4.5 kg'), findsOneWidget);

    // Verify edit button callback
    final editButton = find.text('Not accurate? Edit details');
    expect(editButton, findsOneWidget);
    await tester.tap(editButton);
    expect(correctTapped, isTrue);
  });

  testWidgets('CvPreviewCard shows quality triage indicator when review is needed',
      (WidgetTester tester) async {
    final donation = DonationModel(
      id: 'don_456',
      donorId: 'donor_xyz',
      item: 'other_unclassified',
      itemConfidence: 0.45,
      freshness: 'grade_1_poor',
      freshnessConfidence: 0.40,
      hazardFlag: 'none',
      estWeightKg: 2.0,
      expiresAt: DateTime.now().add(const Duration(hours: 24)),
      status: 'draft',
      needsReview: true,
      photoPaths: [],
      createdAt: DateTime.now(),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: CvPreviewCard(donation: donation),
        ),
      ),
    );

    expect(find.textContaining('Quality triage required'), findsOneWidget);
  });
}
