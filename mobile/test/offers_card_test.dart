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
      photoPaths: const ['assets/images/mixed_pastries.jpg'],
      item: 'bakery_pastries',
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
          body: ListView(
            children: [
              OfferCard(
                offer: offer,
                onTap: () => tapped = true,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('Artisan Bakery Hub'), findsOneWidget);
    expect(find.text('OPEN'), findsOneWidget);
    expect(find.text('3.4 km'), findsOneWidget);
    expect(find.text('04:20:00 left'), findsOneWidget);
    expect(find.text('Expires 18:00'), findsOneWidget);

    await tester.tap(find.byType(OfferCard));
    expect(tapped, isTrue);
  });
}
