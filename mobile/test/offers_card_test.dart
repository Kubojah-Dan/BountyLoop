import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/offers/offer_card.dart';
import 'package:bountyloop_app/models/offer_model.dart';

void main() {
  testWidgets('OfferCard displays food item, weight, distance, and expiry countdown',
      (WidgetTester tester) async {
    final offer = OfferModel(
      id: 'offer_789',
      donorId: 'donor_bakery',
      donorName: 'Artisan Bakery Hub',
      donorAddress: '100 Congress Ave, Austin, TX',
      photoPaths: ['photos/bread.jpg'],
      item: 'bread_bakery',
      freshness: 'grade_2_good',
      estWeightKg: 8.5,
      expiresAt: DateTime.now().add(const Duration(hours: 36)),
      hoursRemaining: 36.0,
      distanceKm: 3.4,
      status: 'open',
      createdAt: DateTime.now(),
    );

    bool tapped = false;

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.lightTheme,
        home: Scaffold(
          body: OfferCard(
            offer: offer,
            onTap: () => tapped = true,
          ),
        ),
      ),
    );

    expect(find.text('Bakery & Bread'), findsOneWidget);
    expect(find.text('Artisan Bakery Hub'), findsOneWidget);
    expect(find.text('Grade 2: Good'), findsOneWidget);
    expect(find.text('8.5 kg'), findsOneWidget);
    expect(find.text('3.4 km away'), findsOneWidget);
    expect(find.text('36h left'), findsOneWidget);

    await tester.tap(find.byType(OfferCard));
    expect(tapped, isTrue);
  });
}

