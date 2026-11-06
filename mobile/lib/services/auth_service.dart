import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/models/user_model.dart';
import 'package:bountyloop_app/services/api_client.dart';

class AuthState {
  final UserModel? user;
  final String? token;
  final bool isLoading;
  final String? error;

  const AuthState({
    this.user,
    this.token,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => user != null && token != null;
  bool get hasSelectedRole => user != null && (user!.isDonor || user!.isRecipient);

  AuthState copyWith({
    UserModel? user,
    String? token,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      user: user ?? this.user,
      token: token ?? this.token,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _apiClient;

  AuthNotifier(this._apiClient) : super(const AuthState());

  Future<void> signIn({
    required String email,
    required String role,
    String? displayName,
    String? idToken,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final token = idToken ?? 'dev_token_${email.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '_')}';
      _apiClient.setAuthToken(token);

      // Authenticate via /v1/auth/session
      final response = await _apiClient.post(
        '/v1/auth/session',
        data: {'id_token': token},
      );

      final data = response.data as Map<String, dynamic>;
      final profileData = data['profile'] as Map<String, dynamic>? ?? {};

      // If user provided a specific role, ensure role onboarding is saved
      UserModel user = UserModel(
        id: data['user_id']?.toString() ?? profileData['id']?.toString() ?? '',
        email: profileData['email']?.toString() ?? email,
        displayName: displayName ?? profileData['display_name']?.toString() ?? email.split('@').first,
        role: role,
        orgName: profileData['org_name']?.toString(),
      );

      if (profileData['role'] != role) {
        final roleRes = await _apiClient.post(
          '/v1/me/role',
          data: {'role': role, 'org_name': profileData['org_name']},
        );
        final roleData = roleRes.data as Map<String, dynamic>;
        user = UserModel(
          id: user.id,
          email: user.email,
          displayName: user.displayName,
          role: roleData['role']?.toString() ?? role,
          orgName: roleData['org_name']?.toString(),
        );
      }

      state = AuthState(user: user, token: token, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> setRole(String role, {String? orgName}) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await _apiClient.post(
        '/v1/me/role',
        data: {'role': role, 'org_name': orgName},
      );
      final data = response.data as Map<String, dynamic>;
      if (state.user != null) {
        final updatedUser = UserModel(
          id: state.user!.id,
          email: state.user!.email,
          displayName: state.user!.displayName,
          role: data['role']?.toString() ?? role,
          orgName: data['org_name']?.toString() ?? orgName,
        );
        state = state.copyWith(user: updatedUser, isLoading: false);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  void signOut() {
    _apiClient.setAuthToken(null);
    state = const AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AuthNotifier(apiClient);
});

