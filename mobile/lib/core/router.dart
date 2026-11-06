import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/features/auth/login_screen.dart';
import 'package:bountyloop_app/features/claim/active_claims_screen.dart';
import 'package:bountyloop_app/features/claim/offer_detail_screen.dart';
import 'package:bountyloop_app/features/donate/camera_capture_screen.dart';
import 'package:bountyloop_app/features/donate/donation_timeline_screen.dart';
import 'package:bountyloop_app/features/donate/donor_home_screen.dart';
import 'package:bountyloop_app/features/offers/offers_list_screen.dart';
import 'package:bountyloop_app/features/profile/profile_screen.dart';
import 'package:bountyloop_app/models/offer_model.dart';
import 'package:bountyloop_app/services/auth_service.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/login',
    redirect: (BuildContext context, GoRouterState state) {
      final isLoggingIn = state.uri.path == '/login';
      final isAuthenticated = authState.isAuthenticated;

      if (!isAuthenticated) {
        return isLoggingIn ? null : '/login';
      }

      // If already logged in and at /login, route according to role (§Master Plan §6.7)
      if (isLoggingIn) {
        if (authState.user?.isRecipient == true) {
          return '/offers';
        }
        return '/donate';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/donate',
        builder: (context, state) => const DonorHomeScreen(),
      ),
      GoRoute(
        path: '/donate/camera',
        builder: (context, state) => const CameraCaptureScreen(),
      ),
      GoRoute(
        path: '/donate/timeline/:id',
        builder: (context, state) {
          final id = state.pathParameters['id'] ?? '';
          return DonationTimelineScreen(donationId: id);
        },
      ),
      GoRoute(
        path: '/offers',
        builder: (context, state) => const OffersListScreen(),
      ),
      GoRoute(
        path: '/offers/:id',
        builder: (context, state) {
          final id = state.pathParameters['id'] ?? '';
          final offer = state.extra as OfferModel?;
          return OfferDetailScreen(offerId: id, offer: offer);
        },
      ),
      GoRoute(
        path: '/claims',
        builder: (context, state) => const ActiveClaimsScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
    ],
  );
});
