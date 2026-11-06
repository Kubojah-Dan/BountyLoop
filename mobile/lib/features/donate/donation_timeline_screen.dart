import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/donation_model.dart';
import 'package:bountyloop_app/services/donation_service.dart';

class DonationTimelineScreen extends ConsumerStatefulWidget {
  final String donationId;

  const DonationTimelineScreen({super.key, required this.donationId});

  @override
  ConsumerState<DonationTimelineScreen> createState() => _DonationTimelineScreenState();
}

class _DonationTimelineScreenState extends ConsumerState<DonationTimelineScreen> {
  DonationModel? _donation;
  bool _isLoading = true;
  String? _error;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _fetchDonation();
    // Poll status every 8 seconds for live updates
    _pollingTimer = Timer.periodic(const Duration(seconds: 8), (_) => _fetchDonation(silent: true));
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchDonation({bool silent = false}) async {
    if (!silent) setState(() => _isLoading = true);
    try {
      final don = await ref.read(donationServiceProvider).getDonation(widget.donationId);
      if (mounted) {
        setState(() {
          _donation = don;
          _isLoading = false;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = e.toString();
        });
      }
    }
  }

  int _getStatusStep(String status) {
    switch (status) {
      case 'draft':
        return 0;
      case 'open':
        return 1;
      case 'matched':
        return 2;
      case 'completed':
        return 3;
      default:
        return 1;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Donation Status'),
      ),
      body: _isLoading && _donation == null
          ? const Center(child: CircularProgressIndicator(color: AppTheme.brandGreen))
          : _error != null && _donation == null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('Error: $_error'),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: () => _fetchDonation(),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _buildTimelineContent(),
    );
  }

  Widget _buildTimelineContent() {
    final don = _donation!;
    final step = _getStatusStep(don.status);
    final itemLabel = AppConstants.categoryLabels[don.item] ?? don.item;
    final icon = AppConstants.categoryIcons[don.item] ?? Icons.fastfood_outlined;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Card
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.brandGreen.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: AppTheme.brandGreen, size: 32),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          itemLabel,
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${don.estWeightKg.toStringAsFixed(1)} kg • ${don.status.toUpperCase()}',
                          style: const TextStyle(
                            fontSize: 13,
                            color: AppTheme.brandAmber,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Visual Stepper
          const Text(
            'Rescue Loop Timeline',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppTheme.textDark,
            ),
          ),
          const SizedBox(height: 16),

          _buildStep(
            index: 0,
            currentStep: step,
            title: 'Draft Analyzed with AI',
            subtitle: 'Photo stripped of EXIF data & verified by Computer Vision cascade.',
            isLast: false,
          ),
          _buildStep(
            index: 1,
            currentStep: step,
            title: 'Offer Live in Community',
            subtitle: 'Broadcast to food banks, community fridges & shelters within radius.',
            isLast: false,
          ),
          _buildStep(
            index: 2,
            currentStep: step,
            title: 'Matched & Claimed',
            subtitle: step >= 2
                ? 'Claimed by a verified recipient partner. Transport scheduled.'
                : 'Awaiting recipient claim.',
            isLast: false,
          ),
          _buildStep(
            index: 3,
            currentStep: step,
            title: 'Rescued & Completed 🎉',
            subtitle: step >= 3
                ? 'Food received safely! Environmental impact recorded.'
                : 'Pickup confirmation will close the loop.',
            isLast: true,
          ),
          const SizedBox(height: 24),

          // Completed Celebration Box
          if (don.isCompleted) ...[
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.successGreen.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.successGreen.withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  const Icon(Icons.celebration, color: AppTheme.successGreen, size: 40),
                  const SizedBox(height: 10),
                  const Text(
                    'Food Rescue Complete!',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.successGreen,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'You provided ~${(don.estWeightKg / 1.2).toStringAsFixed(0)} meals and prevented ${(don.estWeightKg * 2.5).toStringAsFixed(1)} kg CO2e emissions.',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 14, color: AppTheme.textDark),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStep({
    required int index,
    required int currentStep,
    required String title,
    required String subtitle,
    required bool isLast,
  }) {
    final isDone = currentStep >= index;
    final isCurrent = currentStep == index;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: isDone ? AppTheme.brandGreen : Colors.grey.shade300,
                shape: BoxShape.circle,
                border: isCurrent
                    ? Border.all(color: AppTheme.brandAmber, width: 3)
                    : null,
              ),
              child: Center(
                child: isDone
                    ? const Icon(Icons.check, size: 18, color: Colors.white)
                    : Text(
                        '${index + 1}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
              ),
            ),
            if (!isLast)
              Container(
                width: 3,
                height: 48,
                color: currentStep > index ? AppTheme.brandGreen : Colors.grey.shade300,
              ),
          ],
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: isDone ? FontWeight.w700 : FontWeight.w600,
                    color: isDone ? AppTheme.textDark : AppTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDone ? AppTheme.textMuted : Colors.grey.shade400,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
