import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/models/donation_model.dart';
import 'package:bountyloop_app/services/api_client.dart';

final donationServiceProvider = Provider<DonationService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return DonationService(apiClient);
});

class DonationService {
  final ApiClient _client;

  DonationService(this._client);

  /// Create draft donation with multipart photo uploads.
  Future<DonationModel> createDonation({
    required List<List<int>> imageBytesList,
    required List<String> fileNames,
    double? estWeightKg,
    double? latitude,
    double? longitude,
    String? address,
  }) async {
    final formData = FormData();

    for (int i = 0; i < imageBytesList.length; i++) {
      formData.files.add(
        MapEntry(
          'files',
          MultipartFile.fromBytes(
            imageBytesList[i],
            filename: fileNames[i],
          ),
        ),
      );
    }

    if (estWeightKg != null) {
      formData.fields.add(MapEntry('est_weight_kg', estWeightKg.toString()));
    }
    if (latitude != null) {
      formData.fields.add(MapEntry('latitude', latitude.toString()));
    }
    if (longitude != null) {
      formData.fields.add(MapEntry('longitude', longitude.toString()));
    }
    if (address != null) {
      formData.fields.add(MapEntry('address', address));
    }

    final response = await _client.dio.post(
      '/v1/donations',
      data: formData,
    );

    return DonationModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// One-tap confirm or correct AI classification, making donation open and live.
  Future<DonationModel> confirmDonation({
    required String donationId,
    String? item,
    String? freshness,
    double? estWeightKg,
  }) async {
    final payload = <String, dynamic>{};
    if (item != null) payload['item'] = item;
    if (freshness != null) payload['freshness'] = freshness;
    if (estWeightKg != null) payload['est_weight_kg'] = estWeightKg;

    final response = await _client.patch(
      '/v1/donations/$donationId/confirm',
      data: payload,
    );

    return DonationModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Fetch real-time status of a donation.
  Future<DonationModel> getDonation(String donationId) async {
    final response = await _client.get('/v1/donations/$donationId');
    return DonationModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// List donor's donations.
  Future<List<DonationModel>> getMyDonations() async {
    final response = await _client.get('/v1/donations');
    final data = response.data as Map<String, dynamic>;
    final items = data['items'] as List<dynamic>? ?? [];
    return items
        .map((e) => DonationModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

