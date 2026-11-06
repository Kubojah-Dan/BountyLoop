import 'package:bountyloop_app/models/donation_model.dart';

class ClaimModel {
  final String id;
  final String donationId;
  final String recipientId;
  final String? recipientName;
  final String? donorName;
  final String status; // 'offered', 'accepted', 'declined', 'picked_up', 'failed'
  final double score;
  final DateTime offeredAt;
  final DateTime? respondedAt;
  final DateTime? pickedUpAt;
  final String? proofPhotoPath;
  final DonationModel? donation;
  final Map<String, dynamic>? impact;

  const ClaimModel({
    required this.id,
    required this.donationId,
    required this.recipientId,
    this.recipientName,
    this.donorName,
    required this.status,
    required this.score,
    required this.offeredAt,
    this.respondedAt,
    this.pickedUpAt,
    this.proofPhotoPath,
    this.donation,
    this.impact,
  });

  bool get isPickedUp => status == 'picked_up';
  bool get isAccepted => status == 'accepted';
  bool get isDeclined => status == 'declined';

  factory ClaimModel.fromJson(Map<String, dynamic> json) {
    return ClaimModel(
      id: json['id']?.toString() ?? '',
      donationId: json['donation_id']?.toString() ?? '',
      recipientId: json['recipient_id']?.toString() ?? '',
      recipientName: json['recipient_name']?.toString(),
      donorName: json['donor_name']?.toString(),
      status: json['status']?.toString() ?? 'accepted',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      offeredAt: json['offered_at'] != null
          ? DateTime.tryParse(json['offered_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      respondedAt: json['responded_at'] != null
          ? DateTime.tryParse(json['responded_at'].toString())
          : null,
      pickedUpAt: json['picked_up_at'] != null
          ? DateTime.tryParse(json['picked_up_at'].toString())
          : null,
      proofPhotoPath: json['proof_photo_path']?.toString(),
      donation: json['donation'] != null && json['donation'] is Map<String, dynamic>
          ? DonationModel.fromJson(json['donation'] as Map<String, dynamic>)
          : null,
      impact: json['impact'] != null && json['impact'] is Map<String, dynamic>
          ? json['impact'] as Map<String, dynamic>
          : null,
    );
  }
}
