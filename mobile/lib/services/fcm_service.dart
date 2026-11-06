import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/services/api_client.dart';

final fcmServiceProvider = Provider<FcmService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return FcmService(apiClient);
});

class FcmService {
  final ApiClient _client;
  String? _currentToken;

  FcmService(this._client);

  String? get currentToken => _currentToken;

  /// Register device token with backend (/v1/devices)
  Future<void> registerDeviceToken({
    required String fcmToken,
    String platform = 'android',
  }) async {
    _currentToken = fcmToken;
    try {
      await _client.post(
        '/v1/devices',
        data: {
          'fcm_token': fcmToken,
          'platform': platform,
        },
      );
      debugPrint('FCM device token registered: $fcmToken ($platform)');
    } catch (e) {
      debugPrint('Warning: Failed to register device token: $e');
    }
  }

  /// Deep link handler for tapped push notifications
  String? resolveDeepLink(Map<String, dynamic> data) {
    final type = data['type']?.toString();
    final donationId = data['donation_id']?.toString();
    final claimId = data['claim_id']?.toString();

    switch (type) {
      case 'donation_matched':
        if (donationId != null) return '/donate/timeline/$donationId';
        break;
      case 'pickup_completed':
        if (donationId != null) return '/donate/timeline/$donationId';
        break;
      case 'new_offer':
        if (donationId != null) return '/offers/$donationId';
        return '/offers';
      case 'claim_updated':
        if (claimId != null) return '/claims';
        break;
    }
    return null;
  }
}

