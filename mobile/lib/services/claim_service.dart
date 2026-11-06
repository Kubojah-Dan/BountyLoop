import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/models/claim_model.dart';
import 'package:bountyloop_app/models/offer_model.dart';
import 'package:bountyloop_app/services/api_client.dart';

final claimServiceProvider = Provider<ClaimService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ClaimService(apiClient);
});

class ClaimService {
  final ApiClient _client;

  ClaimService(this._client);

  /// Fetch open surplus offers within radius and filters.
  Future<List<OfferModel>> listOffers({
    double radiusKm = 25.0,
    double? latitude,
    double? longitude,
    String? item,
    String? minFreshness,
  }) async {
    final query = <String, dynamic>{
      'radius_km': radiusKm,
    };
    if (latitude != null && longitude != null) {
      query['latitude'] = latitude;
      query['longitude'] = longitude;
    }
    if (item != null) query['item'] = item;
    if (minFreshness != null) query['min_freshness'] = minFreshness;

    final response = await _client.get(
      '/v1/offers',
      queryParameters: query,
    );

    final list = response.data as List<dynamic>? ?? [];
    return list
        .map((e) => OfferModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Claim an open donation offer.
  Future<ClaimModel> createClaim(String donationId) async {
    final response = await _client.post(
      '/v1/claims',
      data: {'donation_id': donationId},
    );
    return ClaimModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Decline a claim with optional rationale.
  Future<void> declineClaim(String claimId, {String? reason}) async {
    await _client.post(
      '/v1/claims/$claimId/decline',
      data: {'reason': reason},
    );
  }

  /// Confirm pickup with proof photo and close rescue loop.
  Future<ClaimModel> confirmPickup(
    String claimId, {
    String? proofPhotoPath,
    String? notes,
  }) async {
    final response = await _client.post(
      '/v1/claims/$claimId/pickup',
      data: {
        if (proofPhotoPath != null) 'proof_photo_path': proofPhotoPath,
        if (notes != null) 'notes': notes,
      },
    );
    return ClaimModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// List claims for the current user.
  Future<List<ClaimModel>> listMyClaims({String? status}) async {
    final query = <String, dynamic>{'role': 'mine'};
    if (status != null) query['status'] = status;

    final response = await _client.get(
      '/v1/claims',
      queryParameters: query,
    );
    final list = response.data as List<dynamic>? ?? [];
    return list
        .map((e) => ClaimModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

