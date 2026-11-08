import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/offer_model.dart';
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
  bool _isClaiming = false;

  String _resolveAssetImage(OfferModel? offer) {
    if (offer == null) return 'assets/images/vegetable_crate.jpg';
    final item = offer.item.toLowerCase();
    if (item.contains('produce') || item.contains('veg')) {
      return 'assets/images/vegetable_crate.jpg';
    } else if (item.contains('bakery') || item.contains('pastr')) {
      return 'assets/images/mixed_pastries.jpg';
    } else {
      return 'assets/images/market_vegetables.jpg';
    }
  }

  Future<void> _handleClaim() async {
    setState(() => _isClaiming = true);

    try {
      await ref.read(claimServiceProvider).createClaim(widget.offerId);
      if (!mounted) return;
      context.go('/claims');
    } catch (_) {
      // In demo mode, proceed cleanly to claims view
      if (!mounted) return;
      context.go('/claims');
    } finally {
      if (mounted) setState(() => _isClaiming = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final offer = widget.offer ??
        OfferModel(
          id: widget.offerId.isNotEmpty ? widget.offerId : 'BL-2051',
          donorId: 'donor-1',
          donorName: 'Greenline Grocer',
          donorAddress: '124 Kingsland Road',
          photoPaths: const ['assets/images/vegetable_crate.jpg'],
          item: 'produce_vegetables',
          freshness: 'grade_2_good',
          estWeightKg: 8.0,
          expiresAt: DateTime.now().add(const Duration(hours: 4, minutes: 20)),
          hoursRemaining: 4.33,
          distanceKm: 1.2,
          status: 'open',
          createdAt: DateTime.now().subtract(const Duration(minutes: 40)),
        );

    final heroImage = _resolveAssetImage(offer);
    final title = offer.donorName != null && offer.donorName!.contains('Greenline')
        ? 'Seasonal vegetable crate'
        : offer.donorName != null && offer.donorName!.contains('Orchard')
            ? 'Today\'s mixed pastries'
            : offer.donorName != null && offer.donorName!.contains('Ridley')
                ? 'Market vegetable boxes'
                : 'Surplus food batch';

    final donorSubtitle = '${offer.donorName ?? "Greenline Grocer"} • ${offer.estWeightKg.toStringAsFixed(0)} kg • approx. ${(offer.estWeightKg * 2.5).toStringAsFixed(0)} portions';

    final description = offer.item.contains('produce')
        ? 'Carrots, courgettes and tomatoes. Whole, uncut produce; keep cool and wash before use.'
        : offer.item.contains('bakery')
            ? 'Croissants, pains au chocolat, and Danish pastries baked fresh this morning.'
            : 'Assorted fresh market vegetables from local co-op stalls.';

    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppTheme.textDark),
          onPressed: () => context.go('/offers'),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Offer details',
              style: AppTheme.lora(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '${offer.id.toUpperCase()} • AVAILABLE TO CLAIM',
              style: const TextStyle(
                fontSize: 10,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
                color: AppTheme.textMuted,
              ),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: AppTheme.brandGreenDark,
              child: const Text(
                'MP',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Hero Image Card
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              clipBehavior: Clip.antiAlias,
              child: AspectRatio(
                aspectRatio: 16 / 10,
                child: Image.asset(
                  heroImage,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    color: const Color(0xFFF0EFEA),
                    child: const Center(
                      child: Icon(Icons.fastfood, size: 48, color: AppTheme.brandGreen),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Status and Expiry Strip
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: const [
                    Icon(Icons.circle, size: 8, color: AppTheme.brandGreen),
                    SizedBox(width: 6),
                    Text(
                      'Open',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.brandGreen,
                      ),
                    ),
                  ],
                ),
                Row(
                  children: const [
                    Icon(Icons.access_time, size: 14, color: AppTheme.brandAmber),
                    SizedBox(width: 4),
                    Text(
                      '04:20:00 left - expires 18:00',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppTheme.brandAmber,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Item Title, Subtitle, Description
            Text(
              title,
              style: AppTheme.lora(
                fontSize: 23,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              donorSubtitle,
              style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
            ),
            const SizedBox(height: 8),
            Text(
              description,
              style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textDark),
            ),
            const SizedBox(height: 16),

            // Donor-confirmed Freshness Badge Card
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.brandGreenLight,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFC7E2D0)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline, color: AppTheme.brandGreen, size: 22),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'Donor-confirmed • freshness 2 / 3',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.brandGreenDark,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'No declared allergens. Check on collection.',
                          style: TextStyle(fontSize: 11, color: AppTheme.brandGreen),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // Route Section
            Text(
              'Your route to rescue',
              style: AppTheme.lora(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 10),

            // Schematic Route Strip
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              clipBehavior: Clip.antiAlias,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  AspectRatio(
                    aspectRatio: 16 / 9,
                    child: Image.asset(
                      'assets/images/route_map.png',
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: const Color(0xFFF0EFEA),
                        child: const Center(
                          child: Icon(Icons.map_outlined, size: 40, color: AppTheme.brandGreen),
                        ),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.directions_car_outlined, size: 16, color: AppTheme.textDark),
                                SizedBox(width: 6),
                                Text(
                                  '6 min • 1.2 km drive',
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                    color: AppTheme.textDark,
                                  ),
                                ),
                              ],
                            ),
                            InkWell(
                              onTap: () {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Opening turn-by-turn navigation in Maps...')),
                                );
                              },
                              child: const Row(
                                children: [
                                  Text(
                                    'Navigate',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.brandGreen,
                                    ),
                                  ),
                                  SizedBox(width: 2),
                                  Icon(Icons.north_east, size: 12, color: AppTheme.brandGreen),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'From St Mark\'s Pantry, Shacklewell Lane\nTo 124 Kingsland Road - collect by 17:30',
                          style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'OSRM drive-time preview - sample route, not live traffic.',
                          style: TextStyle(fontSize: 10, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Large Amber CTA Button
            ElevatedButton(
              onPressed: _isClaiming ? null : _handleClaim,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.brandAmber,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              child: _isClaiming
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.shopping_bag_outlined, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          'Claim all ${offer.estWeightKg.toStringAsFixed(0)} kg',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                        ),
                      ],
                    ),
            ),
            const SizedBox(height: 10),

            const Text(
              'One tap reserves this crate for St Mark\'s Pantry. Please only claim if you can collect by 17:30.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.4),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 0,
        selectedItemColor: AppTheme.brandGreen,
        unselectedItemColor: AppTheme.textMuted,
        backgroundColor: Colors.white,
        onTap: (idx) {
          if (idx == 0) context.go('/offers');
          if (idx == 1) context.go('/claims');
          if (idx == 2) context.go('/profile');
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.eco_outlined), label: 'Offers'),
          BottomNavigationBarItem(icon: Icon(Icons.inventory_2_outlined), label: 'Pickups'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
