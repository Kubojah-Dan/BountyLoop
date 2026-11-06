import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/claim/pickup_confirmation_screen.dart';
import 'package:bountyloop_app/models/claim_model.dart';
import 'package:bountyloop_app/services/claim_service.dart';

class ActiveClaimsScreen extends ConsumerStatefulWidget {
  const ActiveClaimsScreen({super.key});

  @override
  ConsumerState<ActiveClaimsScreen> createState() => _ActiveClaimsScreenState();
}

class _ActiveClaimsScreenState extends ConsumerState<ActiveClaimsScreen> {
  late Future<List<ClaimModel>> _claimsFuture;

  @override
  void initState() {
    super.initState();
    _fetchClaims();
  }

  void _fetchClaims() {
    setState(() {
      _claimsFuture = ref.read(claimServiceProvider).listMyClaims();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Food Claims'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _fetchClaims(),
        child: FutureBuilder<List<ClaimModel>>(
          future: _claimsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator(color: AppTheme.brandGreen));
            }

            if (snapshot.hasError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Error loading claims: ${snapshot.error}'),
                    const SizedBox(height: 12),
                    ElevatedButton(
                      onPressed: _fetchClaims,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }

            final claims = snapshot.data ?? [];
            if (claims.isEmpty) {
              return ListView(
                children: [
                  const SizedBox(height: 80),
                  Center(
                    child: Column(
                      children: [
                        Icon(
                          Icons.inbox_outlined,
                          size: 52,
                          color: AppTheme.brandGreen.withOpacity(0.4),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'No Active Food Claims',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textDark,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Claimed surplus food batches will appear here for pickup verification.',
                          style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            }

            return ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 12),
              itemCount: claims.length,
              itemBuilder: (context, index) {
                final claim = claims[index];
                final item = claim.donation?.item ?? 'other_unclassified';
                final itemLabel = AppConstants.categoryLabels[item] ?? item;
                final weight = claim.donation?.estWeightKg ?? 0.0;
                final isPendingPickup = claim.status == 'accepted';

                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    itemLabel,
                                    style: const TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.w700,
                                      color: AppTheme.textDark,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '${weight.toStringAsFixed(1)} kg • From: ${claim.donorName ?? "Donor"}',
                                    style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                                  ),
                                ],
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: isPendingPickup
                                    ? AppTheme.brandAmber.withOpacity(0.15)
                                    : AppTheme.successGreen.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                claim.status.toUpperCase(),
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: isPendingPickup
                                      ? AppTheme.brandAmber
                                      : AppTheme.successGreen,
                                ),
                              ),
                            ),
                          ],
                        ),
                        if (isPendingPickup) ...[
                          const SizedBox(height: 16),
                          ElevatedButton.icon(
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => PickupConfirmationScreen(claim: claim),
                                ),
                              ).then((_) => _fetchClaims());
                            },
                            icon: const Icon(Icons.qr_code_scanner, size: 18),
                            label: const Text('Confirm Food Pickup'),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
