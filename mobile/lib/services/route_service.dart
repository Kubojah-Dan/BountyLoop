import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/models/route_model.dart';
import 'package:bountyloop_app/services/api_client.dart';

final routeServiceProvider = Provider<RouteService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return RouteService(apiClient);
});

class RouteService {
  final ApiClient _client;

  RouteService(this._client);

  /// Fetch navigation route, distance, duration, and geometry for a claim.
  Future<RouteInfoModel> getClaimRoute(String claimId) async {
    final response = await _client.get('/v1/routes/$claimId');
    return RouteInfoModel.fromJson(response.data as Map<String, dynamic>);
  }
}
