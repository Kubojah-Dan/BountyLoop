import 'package:flutter/material.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/offer_model.dart';

class OfferCard extends StatelessWidget {
  final OfferModel offer;
  final VoidCallback onTap;

  const OfferCard({
    super.key,
    required this.offer,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final itemLabel = AppConstants.categoryLabels[offer.item] ?? offer.item;
    final itemIcon = AppConstants.categoryIcons[offer.item] ?? Icons.fastfood_outlined;
    final freshnessLabel = AppConstants.freshnessLabels[offer.freshness] ?? offer.freshness;
    final freshnessColor = AppConstants.freshnessColor(offer.freshness);

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.brandGreen.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(itemIcon, color: AppTheme.brandGreen, size: 28),
                  ),
                  const SizedBox(width: 14),
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
                          offer.donorName ?? 'Community Donor',
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppTheme.textMuted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Freshness badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: freshnessColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: freshnessColor.withOpacity(0.3)),
                    ),
                    child: Text(
                      freshnessLabel,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: freshnessColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              const Divider(height: 1),
              const SizedBox(height: 12),

              // Metrics row: weight, distance, hours remaining
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.scale_outlined, size: 16, color: AppTheme.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        '${offer.estWeightKg.toStringAsFixed(1)} kg',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textDark,
                        ),
                      ),
                    ],
                  ),
                  if (offer.distanceKm != null)
                    Row(
                      children: [
                        const Icon(Icons.near_me_outlined, size: 16, color: AppTheme.brandAmber),
                        const SizedBox(width: 4),
                        Text(
                          '${offer.distanceKm!.toStringAsFixed(1)} km away',
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.brandAmber,
                          ),
                        ),
                      ],
                    ),
                  Row(
                    children: [
                      const Icon(Icons.timer_outlined, size: 16, color: AppTheme.textMuted),
                      const SizedBox(width: 4),
                      Text(
                        '${offer.hoursRemaining.toStringAsFixed(0)}h left',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
