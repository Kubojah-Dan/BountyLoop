import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/map/route_map_strip.dart';
import 'package:bountyloop_app/models/route_model.dart';

void main() {
  group('RouteInfoModel serialization & formatting', () {
    test('parses GeoJSON LineString and formats distance & ETA properly', () {
      final json = {
        'claim_id': 'claim_abc_123',
        'donor_id': 'donor_456',
        'recipient_id': 'recip_789',
        'distance_m': 3500.0,
        'duration_s': 315.0,
        'source': 'osrm',
        'geometry': {
          'type': 'LineString',
          'coordinates': [
            [-97.7431, 30.2672],
            [-97.7400, 30.2750],
          ],
        },
      };

      final model = RouteInfoModel.fromJson(json);

      expect(model.claimId, 'claim_abc_123');
      expect(model.isOsrm, isTrue);
      expect(model.formattedDistance, '3.5 km');
      expect(model.formattedDuration, '6 min');
      expect(model.coordinates.length, 2);
      expect(model.coordinates.first, [-97.7431, 30.2672]);
    });

    test('handles straight-line estimate fallback source gracefully', () {
      final json = {
        'claim_id': 'claim_est_999',
        'distance_m': 12000.0,
        'duration_s': 1080.0,
        'route_source': 'estimate',
      };

      final model = RouteInfoModel.fromJson(json);

      expect(model.isOsrm, isFalse);
      expect(model.source, 'estimate');
      expect(model.formattedDistance, '12.0 km');
      expect(model.formattedDuration, '18 min');
      expect(model.coordinates, isEmpty);
    });
  });

  group('RouteMapStrip Widget', () {
    testWidgets('renders OSRM live route with OSM attribution and navigation trigger',
        (WidgetTester tester) async {
      const route = RouteInfoModel(
        claimId: 'claim_1',
        distanceMeters: 4800.0,
        durationSeconds: 430.0,
        source: 'osrm',
        coordinates: [
          [-97.7431, 30.2672],
          [-97.7410, 30.2700],
          [-97.7390, 30.2740],
        ],
      );

      bool navigated = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: Scaffold(
            body: SingleChildScrollView(
              child: RouteMapStrip(
                route: route,
                donorName: 'Downtown Supermarket',
                donorAddress: '500 E 7th St, Austin, TX',
                recipientName: 'Community Shelter',
                recipientAddress: '1200 San Jacinto Blvd, Austin, TX',
                onNavigate: () => navigated = true,
              ),
            ),
          ),
        ),
      );

      // Verifies Distance, Duration & Source badge
      expect(find.text('4.8 km'), findsOneWidget);
      expect(find.text('8 min'), findsOneWidget);
      expect(find.text('OSRM Live Route'), findsOneWidget);

      // Verifies stop labels
      expect(find.text('Downtown Supermarket'), findsOneWidget);
      expect(find.text('Community Shelter'), findsOneWidget);
      expect(find.text('500 E 7th St, Austin, TX'), findsOneWidget);

      // Verifies OSM Legal Attribution
      expect(find.text('© OpenStreetMap contributors'), findsOneWidget);

      // Verifies Navigation Action
      final navBtn = find.text('Start Route');
      expect(navBtn, findsOneWidget);
      await tester.tap(navBtn);
      expect(navigated, isTrue);
    });

    testWidgets('renders honest Road Estimate badge when source is estimate',
        (WidgetTester tester) async {
      const route = RouteInfoModel(
        claimId: 'claim_2',
        distanceMeters: 2500.0,
        durationSeconds: 225.0,
        source: 'estimate',
        coordinates: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SingleChildScrollView(
              child: RouteMapStrip(
                route: route,
                donorName: 'Austin Community Kitchen',
              ),
            ),
          ),
        ),
      );

      expect(find.text('2.5 km'), findsOneWidget);
      expect(find.text('4 min'), findsOneWidget);
      expect(find.text('Road Estimate'), findsOneWidget);
      expect(find.text('© OpenStreetMap contributors'), findsOneWidget);
    });
  });
}
