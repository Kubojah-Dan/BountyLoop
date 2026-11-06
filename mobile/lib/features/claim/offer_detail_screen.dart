import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/map/route_map_strip.dart';
import 'package:bountyloop_app/models/offer_model.dart';
import 'package:bountyloop_app/models/route_model.dart';
import 'package:bountyloop_app/services/claim_service.dart';

class OfferDetailScreen extends ConsumerStatefulWidget {
  final String offerId;
  final OfferModel? offer;

  const OfferDetailScreen({
    super.key,
    required this.offerId,
    this.offer,
  });

  @override
  ConsumerState<OfferDetailScreen> createState() => _OfferDetailScreenState();
}

class _OfferDetailScreenState extends ConsumerState<OfferDetailScreen> {
  OfferModel? _offer;
  bool _isClaiming = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _offer = widget.offer;
  }

  Future<void> _handleClaim() async {
    setState(() {
      _isClaiming = true;
      _errorMessage = null;
    });

    try {
      await ref.read(claimServiceProvider).createClaim(widget.offerId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Offer successfully claimed! Proceed with pickup.'),
          backgroundColor: AppTheme.successGreen,
        ),
      );
      context.go('/claims');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isClaiming = false;
        _errorMessage = 'Claim failed: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_offer == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Offer Details')),
        body: const Center(child: Text('Offer information not available.')),
      );
    }

    final offer = _offer!;
    final itemLabel = AppConstants.categoryLabels[offer.item] ?? offer.item;
    final itemIcon = AppConstants.categoryIcons[offer.item] ?? Icons.fastfood_outlined;
    final freshnessLabel = AppConstants.freshnessLabels[offer.freshness] ?? offer.freshness;
    final freshnessColor = AppConstants.freshnessColor(offer.freshness);
    final mealsCount = (offer.estWeightKg / 1.2).toStringAsFixed(0);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Offer Details'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Hero Icon & Category
            Center(
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: AppTheme.brandGreen.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(itemIcon, color: AppTheme.brandGreen, size: 54),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              itemLabel,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 6),
            Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: freshnessColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: freshnessColor.withOpacity(0.3)),
                ),
                child: Text(
                  freshnessLabel,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: freshnessColor,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Key Stats Card
            Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildStat('Weight', '${offer.estWeightKg.toStringAsFixed(1)} kg'),
                        _buildStat('Meals Fit', '~$mealsCount meals'),
                        _buildStat('Expires In', '${offer.hoursRemaining.toStringAsFixed(0)}h'),
                      ],
                    ),
                    const Divider(height: 24),
                    Row(
                      children: [
                        const Icon(Icons.location_on_outlined, color: AppTheme.brandAmber),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                offer.donorName ?? 'Community Donor',
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                              ),
                              Text(
                                offer.donorAddress ?? 'Austin Metro Area',
                                style: const TextStyle(color: AppTheme.textMuted, fontSize: 13),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            if (offer.distanceKm != null) ...[
              const SizedBox(height: 20),
              RouteMapStrip(
                route: RouteInfoModel(
                  claimId: offer.id,
                  distanceMeters: offer.distanceKm! * 1000.0,
                  durationSeconds: (offer.distanceKm! / 40.0) * 3600.0,
                  source: 'estimate',
                  coordinates: const [],
                ),
                donorName: offer.donorName,
                donorAddress: offer.donorAddress,
                recipientName: 'My Rescue Facility',
              ),
            ],

            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.dangerRed.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(color: AppTheme.dangerRed, fontSize: 13),
                ),
              ),
            ],
            const SizedBox(height: 32),

            // Primary Claim CTA
            ElevatedButton(
              onPressed: _isClaiming ? null : _handleClaim,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.brandGreen,
                minimumSize: const Size.fromHeight(56),
              ),
              child: _isClaiming
                  ? const SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                    )
                  : const Text(
                      'Claim Food Rescue',
                      style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStat(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: AppTheme.textDark,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
        ),
      ],
    );
  }
}
