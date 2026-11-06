class OfferModel {
  final String id;
  final String donorId;
  final String? donorName;
  final String? donorAddress;
  final List<String> photoPaths;
  final String item;
  final String freshness;
  final double estWeightKg;
  final DateTime expiresAt;
  final double hoursRemaining;
  final double? distanceKm;
  final String status;
  final DateTime createdAt;

  const OfferModel({
    required this.id,
    required this.donorId,
    this.donorName,
    this.donorAddress,
    required this.photoPaths,
    required this.item,
    required this.freshness,
    required this.estWeightKg,
    required this.expiresAt,
    required this.hoursRemaining,
    this.distanceKm,
    required this.status,
    required this.createdAt,
  });

  factory OfferModel.fromJson(Map<String, dynamic> json) {
    return OfferModel(
      id: json['id']?.toString() ?? '',
      donorId: json['donor_id']?.toString() ?? '',
      donorName: json['donor_name']?.toString(),
      donorAddress: json['donor_address']?.toString(),
      photoPaths: (json['photo_paths'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      item: json['item']?.toString() ?? 'other_unclassified',
      freshness: json['freshness']?.toString() ?? 'grade_2_good',
      estWeightKg: (json['est_weight_kg'] as num?)?.toDouble() ?? 0.0,
      expiresAt: json['expires_at'] != null
          ? DateTime.tryParse(json['expires_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      hoursRemaining: (json['hours_remaining'] as num?)?.toDouble() ?? 0.0,
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
      status: json['status']?.toString() ?? 'open',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

