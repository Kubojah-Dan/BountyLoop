class RouteCoordinates {
  final double lat;
  final double lon;

  const RouteCoordinates({required this.lat, required this.lon});

  factory RouteCoordinates.fromJson(Map<String, dynamic> json) {
    return RouteCoordinates(
      lat: (json['lat'] as num).toDouble(),
      lon: (json['lon'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {'lat': lat, 'lon': lon};
}

class RouteInfoModel {
  final String claimId;
  final String? donorId;
  final String? recipientId;
  final RouteCoordinates? donorCoordinates;
  final RouteCoordinates? recipientCoordinates;
  final double distanceMeters;
  final double durationSeconds;
  final String source; // "osrm" or "estimate"
  final List<List<double>> coordinates; // [ [lon, lat], ... ]

  const RouteInfoModel({
    required this.claimId,
    this.donorId,
    this.recipientId,
    this.donorCoordinates,
    this.recipientCoordinates,
    required this.distanceMeters,
    required this.durationSeconds,
    required this.source,
    required this.coordinates,
  });

  factory RouteInfoModel.fromJson(Map<String, dynamic> json) {
    List<List<double>> parsedCoords = [];
    if (json['geometry'] != null && json['geometry']['coordinates'] != null) {
      final rawCoords = json['geometry']['coordinates'] as List;
      for (final item in rawCoords) {
        if (item is List && item.length >= 2) {
          parsedCoords.add([
            (item[0] as num).toDouble(),
            (item[1] as num).toDouble(),
          ]);
        }
      }
    }

    return RouteInfoModel(
      claimId: json['claim_id'] ?? '',
      donorId: json['donor_id'],
      recipientId: json['recipient_id'],
      donorCoordinates: json['donor_coordinates'] != null
          ? RouteCoordinates.fromJson(json['donor_coordinates'])
          : null,
      recipientCoordinates: json['recipient_coordinates'] != null
          ? RouteCoordinates.fromJson(json['recipient_coordinates'])
          : null,
      distanceMeters: (json['distance_m'] as num?)?.toDouble() ?? 0.0,
      durationSeconds: (json['duration_s'] as num?)?.toDouble() ?? 0.0,
      source: json['source'] ?? json['route_source'] ?? 'estimate',
      coordinates: parsedCoords,
    );
  }

  bool get isOsrm => source.toLowerCase() == 'osrm';

  String get formattedDistance {
    final km = distanceMeters / 1000.0;
    return '${km.toStringAsFixed(1)} km';
  }

  String get formattedDuration {
    final minutes = (durationSeconds / 60.0).ceil();
    if (minutes < 60) {
      return '$minutes min';
    }
    final hours = minutes ~/ 60;
    final remMins = minutes % 60;
    return '${hours}h ${remMins}m';
  }
}
