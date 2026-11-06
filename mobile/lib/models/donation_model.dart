class DonationModel {
  final String id;
  final String donorId;
  final String item;
  final double itemConfidence;
  final String freshness;
  final double freshnessConfidence;
  final String hazardFlag;
  final double estWeightKg;
  final DateTime expiresAt;
  final String status; // 'draft', 'open', 'matched', 'completed', 'cancelled'
  final bool needsReview;
  final List<String> photoPaths;
  final String? donorName;
  final String? donorAddress;
  final DateTime createdAt;

  const DonationModel({
    required this.id,
    required this.donorId,
    required this.item,
    required this.itemConfidence,
    required this.freshness,
    required this.freshnessConfidence,
    required this.hazardFlag,
    required this.estWeightKg,
    required this.expiresAt,
    required this.status,
    required this.needsReview,
    required this.photoPaths,
    this.donorName,
    this.donorAddress,
    required this.createdAt,
  });

  bool get isOpen => status == 'open';
  bool get isDraft => status == 'draft';
  bool get isMatched => status == 'matched';
  bool get isCompleted => status == 'completed';

  factory DonationModel.fromJson(Map<String, dynamic> json) {
    return DonationModel(
      id: json['id']?.toString() ?? '',
      donorId: json['donor_id']?.toString() ?? '',
      item: json['item']?.toString() ?? 'other_unclassified',
      itemConfidence: (json['item_confidence'] as num?)?.toDouble() ?? 0.0,
      freshness: json['freshness']?.toString() ?? 'grade_2_good',
      freshnessConfidence: (json['freshness_confidence'] as num?)?.toDouble() ?? 0.0,
      hazardFlag: json['hazard_flag']?.toString() ?? 'none',
      estWeightKg: (json['est_weight_kg'] as num?)?.toDouble() ?? 0.0,
      expiresAt: json['expires_at'] != null
          ? DateTime.tryParse(json['expires_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      status: json['status']?.toString() ?? 'draft',
      needsReview: json['needs_review'] == true,
      photoPaths: (json['photo_paths'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      donorName: json['donor_name']?.toString(),
      donorAddress: json['donor_address']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}
