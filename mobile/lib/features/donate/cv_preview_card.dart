import 'package:flutter/material.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/donation_model.dart';

class CvPreviewCard extends StatelessWidget {
  final DonationModel donation;
  final VoidCallback? onCorrect;

  const CvPreviewCard({
    super.key,
    required this.donation,
    this.onCorrect,
  });

  @override
  Widget build(BuildContext context) {
    final itemLabel = AppConstants.categoryLabels[donation.item] ?? donation.item;
    final itemIcon = AppConstants.categoryIcons[donation.item] ?? Icons.fastfood_outlined;
    final freshnessLabel = AppConstants.freshnessLabels[donation.freshness] ?? donation.freshness;
    final freshnessColor = AppConstants.freshnessColor(donation.freshness);
    final confPercent = (donation.itemConfidence * 100).toInt();

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
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
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              itemLabel,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textDark,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.brandGreen.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              '$confPercent% AI match',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.brandGreen,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Estimated weight: ${donation.estWeightKg.toStringAsFixed(1)} kg',
                        style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 24),

            // Freshness & Quality assessment
            Row(
              children: [
                const Text(
                  'Quality Assessment: ',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textMuted,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: freshnessColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: freshnessColor.withOpacity(0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.verified_outlined, size: 14, color: freshnessColor),
                      const SizedBox(width: 4),
                      Text(
                        freshnessLabel,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: freshnessColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Safety gate indicator
            if (donation.needsReview) ...[
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.warningAmber.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.info_outline, size: 18, color: AppTheme.warningAmber),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Quality triage required: donation will undergo quick operator verification before dispatch.',
                        style: TextStyle(fontSize: 12, color: AppTheme.textDark),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
            ],

            if (onCorrect != null)
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: onCorrect,
                  icon: const Icon(Icons.edit_outlined, size: 16),
                  label: const Text('Not accurate? Edit details'),
                  style: TextButton.styleFrom(foregroundColor: AppTheme.brandAmber),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

