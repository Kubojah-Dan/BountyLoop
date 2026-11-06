import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/claim/pickup_confirmation_screen.dart';
import 'package:bountyloop_app/models/claim_model.dart';
import 'package:bountyloop_app/models/donation_model.dart';

void main() {
  testWidgets('PickupConfirmationScreen renders closing loop and proof options',
      (WidgetTester tester) async {
    final donation = DonationModel(
      id: 'don_abc',
      donorId: 'donor_123',
      item: 'produce_fruit',
      itemConfidence: 0.95,
      freshness: 'grade_3_fresh',
      freshnessConfidence: 0.95,
      hazardFlag: 'none',
      estWeightKg: 10.0,
      expiresAt: DateTime.now().add(const Duration(hours: 48)),
      status: 'matched',
      needsReview: false,
      photoPaths: [],
      createdAt: DateTime.now(),
    );

    final claim = ClaimModel(
      id: 'claim_xyz',
      donationId: 'don_abc',
      recipientId: 'recip_123',
      recipientName: 'Austin Food Hub',
      donorName: 'Fresh Farms',
      status: 'accepted',
      score: 95.0,
      offeredAt: DateTime.now(),
      donation: donation,
    );

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: PickupConfirmationScreen(claim: claim),
        ),
      ),
    );

    expect(find.text('Confirm Pickup'), findsOneWidget);
    expect(find.text('Closing the Rescue Loop'), findsOneWidget);
    expect(find.textContaining('10.0 kg surplus food'), findsOneWidget);
    expect(find.text('Optional: Proof Photo'), findsOneWidget);
    expect(find.text('Confirm Food Received & Record Impact'), findsOneWidget);
  });
}

