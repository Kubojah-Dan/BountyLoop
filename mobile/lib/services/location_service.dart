import 'package:flutter_riverpod/flutter_riverpod.dart';

class UserLocation {
  final double latitude;
  final double longitude;
  final String label;

  const UserLocation({
    required this.latitude,
    required this.longitude,
    required this.label,
  });
}

final locationProvider = StateProvider<UserLocation>((ref) {
  // Default to Austin pilot city coordinates
  return const UserLocation(
    latitude: 30.2672,
    longitude: -97.7431,
    label: 'Downtown Austin, TX',
  );
});
