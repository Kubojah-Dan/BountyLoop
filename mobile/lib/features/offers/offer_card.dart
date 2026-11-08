import 'package:flutter/material.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/offer_model.dart';

class OfferCard extends StatelessWidget {
  final OfferModel offer;
  final VoidCallback onTap;
  final String? customImage;
  final String? distanceLabel;

  const OfferCard({
    super.key,
    required this.offer,
    required this.onTap,
    this.customImage,
    this.distanceLabel,
  });

  String _resolveAssetImage() {
    if (customImage != null) return customImage!;
    final item = offer.item.toLowerCase();
    if (item.contains('produce') || item.contains('fruit') || item.contains('veg')) {
      return 'assets/images/vegetable_crate.jpg';
    } else if (item.contains('bakery') || item.contains('pastr')) {
      return 'assets/images/mixed_pastries.jpg';
    } else {
      return 'assets/images/market_vegetables.jpg';
    }
  }

  @override
  Widget build(BuildContext context) {
    final imageAsset = _resolveAssetImage();
    final dist = distanceLabel ??
        (offer.distanceKm != null
            ? '${offer.distanceKm!.toStringAsFixed(1)} km'
            : '1.2 km');

    final title = offer.donorName != null && offer.donorName!.contains('Greenline')
        ? 'Seasonal vegetable crate'
        : offer.donorName != null && offer.donorName!.contains('Orchard')
            ? 'Today\'s mixed pastries'
            : offer.donorName != null && offer.donorName!.contains('Ridley')
                ? 'Market vegetable boxes'
                : offer.item.replaceAll('_', ' ').split(' ').map((s) => s.isNotEmpty ? '${s[0].toUpperCase()}${s.substring(1)}' : '').join(' ');

    final subtitle = '${offer.estWeightKg.toStringAsFixed(0)} kg • approx. ${(offer.estWeightKg * 2.5).toStringAsFixed(0)} portions';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.cardBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Photographic banner with distance tag overlay
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Image.asset(
                    imageAsset,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      color: const Color(0xFFF0EFEA),
                      child: const Center(
                        child: Icon(Icons.fastfood_outlined, size: 40, color: AppTheme.brandGreen),
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: 12,
                  left: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.92),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.location_on_outlined, size: 14, color: AppTheme.textDark),
                        const SizedBox(width: 4),
                        Text(
                          dist,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textDark,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            // Card Body
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        offer.donorName ?? 'Community Donor',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textMuted,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.brandGreenLight,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'OPEN',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.5,
                            color: AppTheme.brandGreen,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    title,
                    style: AppTheme.lora(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                  ),
                  const SizedBox(height: 12),
                  const Divider(height: 1, color: AppTheme.cardBorder),
                  const SizedBox(height: 10),

                  // Bottom timer & expiry strip
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.access_time, size: 14, color: AppTheme.brandAmber),
                          SizedBox(width: 4),
                          Text(
                            '04:20:00 left',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.brandAmber,
                            ),
                          ),
                          SizedBox(width: 6),
                          Text(
                            '• Collect by 17:30',
                            style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                      const Text(
                        'Expires 18:00',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
