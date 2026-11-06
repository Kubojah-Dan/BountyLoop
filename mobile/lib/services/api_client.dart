import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/core/constants.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

class ApiException implements Exception {
  final int? statusCode;
  final String title;
  final String detail;

  const ApiException({
    this.statusCode,
    required this.title,
    required this.detail,
  });

  @override
  String toString() => '$title ($statusCode): $detail';
}

class ApiClient {
  late final Dio dio;
  String? _authToken;

  ApiClient({String? baseUrl, Dio? customDio}) {
    dio = customDio ??
        Dio(
          BaseOptions(
            baseUrl: baseUrl ?? AppConstants.defaultApiBaseUrl,
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(seconds: 15),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) {
          final response = error.response;
          if (response != null && response.data is Map<String, dynamic>) {
            final data = response.data as Map<String, dynamic>;
            final title = data['title']?.toString() ?? 'Request Error';
            final detail = data['detail']?.toString() ?? error.message ?? 'Unknown error';
            return handler.reject(
              DioException(
                requestOptions: error.requestOptions,
                response: response,
                error: ApiException(
                  statusCode: response.statusCode,
                  title: title,
                  detail: detail,
                ),
              ),
            );
          }
          return handler.next(error);
        },
      ),
    );
  }

  void setAuthToken(String? token) {
    _authToken = token;
  }

  String? get authToken => _authToken;

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return dio.get<T>(path, queryParameters: queryParameters);
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return dio.post<T>(path, data: data, queryParameters: queryParameters);
  }

  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return dio.patch<T>(path, data: data, queryParameters: queryParameters);
  }

  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return dio.delete<T>(path, queryParameters: queryParameters);
  }
}
