import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/donate/cv_preview_card.dart';
import 'package:bountyloop_app/models/donation_model.dart';
import 'package:bountyloop_app/services/donation_service.dart';

class DonationConfirmScreen extends ConsumerStatefulWidget {
  final DonationModel initialDonation;

  const DonationConfirmScreen({
    super.key,
    required this.initialDonation,
  });

  @override
  ConsumerState<DonationConfirmScreen> createState() => _DonationConfirmScreenState();
}

class _DonationConfirmScreenState extends ConsumerState<DonationConfirmScreen> {
  late DonationModel _donation;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _donation = widget.initialDonation;
  }

  Future<void> _handleConfirm() async {
    setState(() => _isSubmitting = true);
    try {
      final confirmed = await ref.read(donationServiceProvider).confirmDonation(
            donationId: _donation.id,
            item: _donation.item,
            freshness: _donation.freshness,
            estWeightKg: _donation.estWeightKg,
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Donation published successfully! Live for recipient matching.'),
          backgroundColor: AppTheme.successGreen,
        ),
      );
      context.go('/donate/timeline/${confirmed.id}');
    } catch (e) {
      if (!mounted) return;
      setState(() => _isSubmitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to confirm donation: $e'),
          backgroundColor: AppTheme.dangerRed,
        ),
      );
    }
  }

  void _openCorrectionSheet() {
    String selectedItem = _donation.item;
    String selectedFreshness = _donation.freshness;
    double selectedWeight = _donation.estWeightKg;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Correct Donation Details',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Category dropdown
                  DropdownButtonFormField<String>(
                    value: selectedItem,
                    decoration: const InputDecoration(labelText: 'Food Category'),
                    items: AppConstants.categoryLabels.entries.map((e) {
                      return DropdownMenuItem(
                        value: e.key,
                        child: Text(e.value),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) setSheetState(() => selectedItem = val);
                    },
                  ),
                  const SizedBox(height: 12),

                  // Freshness dropdown
                  DropdownButtonFormField<String>(
                    value: selectedFreshness,
                    decoration: const InputDecoration(labelText: 'Freshness Assessment'),
                    items: AppConstants.freshnessLabels.entries.map((e) {
                      return DropdownMenuItem(
                        value: e.key,
                        child: Text(e.value),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) setSheetState(() => selectedFreshness = val);
                    },
                  ),
                  const SizedBox(height: 12),

                  // Weight field
                  TextFormField(
                    initialValue: selectedWeight.toStringAsFixed(1),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Estimated Weight (kg)',
                      suffixText: 'kg',
                    ),
                    onChanged: (val) {
                      final parsed = double.tryParse(val);
                      if (parsed != null && parsed > 0) {
                        selectedWeight = parsed;
                      }
                    },
                  ),
                  const SizedBox(height: 20),

                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _donation = DonationModel(
                          id: _donation.id,
                          donorId: _donation.donorId,
                          item: selectedItem,
                          itemConfidence: 1.0, // Donor-verified correction
                          freshness: selectedFreshness,
                          freshnessConfidence: 1.0,
                          hazardFlag: _donation.hazardFlag,
                          estWeightKg: selectedWeight,
                          expiresAt: _donation.expiresAt,
                          status: _donation.status,
                          needsReview: _donation.needsReview,
                          photoPaths: _donation.photoPaths,
                          donorName: _donation.donorName,
                          donorAddress: _donation.donorAddress,
                          createdAt: _donation.createdAt,
                        );
                      });
                      Navigator.pop(ctx);
                    },
                    child: const Text('Apply Corrections'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Confirm Donation'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Instruction header
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.brandGreen.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                children: [
                  Icon(Icons.auto_awesome, color: AppTheme.brandGreen, size: 24),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'AI Computer Vision analyzed your food photo. Verify or correct the details below before publishing.',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.textDark,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // AI Preview Card
            CvPreviewCard(
              donation: _donation,
              onCorrect: _openCorrectionSheet,
            ),
            const SizedBox(height: 24),

            // One-tap Confirm CTA
            ElevatedButton(
              onPressed: _isSubmitting ? null : _handleConfirm,
              child: _isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                    )
                  : const Text('Confirm & Publish Live'),
            ),
            const SizedBox(height: 12),

            // Correct button
            OutlinedButton.icon(
              onPressed: _isSubmitting ? null : _openCorrectionSheet,
              icon: const Icon(Icons.tune, size: 18),
              label: const Text('Edit Details / Correct AI'),
            ),
          ],
        ),
      ),
    );
  }
}

