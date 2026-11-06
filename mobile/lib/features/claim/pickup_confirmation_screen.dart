import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/claim_model.dart';
import 'package:bountyloop_app/services/claim_service.dart';

class PickupConfirmationScreen extends ConsumerStatefulWidget {
  final ClaimModel claim;

  const PickupConfirmationScreen({super.key, required this.claim});

  @override
  ConsumerState<PickupConfirmationScreen> createState() => _PickupConfirmationScreenState();
}

class _PickupConfirmationScreenState extends ConsumerState<PickupConfirmationScreen> {
  final _notesController = TextEditingController();
  bool _isConfirming = false;
  ClaimModel? _completedClaim;
  String? _errorMessage;

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _handleConfirmPickup() async {
    setState(() {
      _isConfirming = true;
      _errorMessage = null;
    });

    try {
      final updated = await ref.read(claimServiceProvider).confirmPickup(
            widget.claim.id,
            proofPhotoPath: 'photos/proofs/${widget.claim.id}.jpg',
            notes: _notesController.text.trim().isNotEmpty
                ? _notesController.text.trim()
                : 'Pickup verified by recipient partner.',
          );

      if (!mounted) return;
      setState(() {
        _isConfirming = false;
        _completedClaim = updated;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isConfirming = false;
        _errorMessage = 'Failed to confirm pickup: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_completedClaim != null) {
      return _buildCelebrationScreen(_completedClaim!);
    }

    final don = widget.claim.donation;
    final weight = don?.estWeightKg ?? 5.0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Confirm Pickup'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Instructions
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.brandGreen.withOpacity(0.08),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline, color: AppTheme.brandGreen, size: 28),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Closing the Rescue Loop',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textDark,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Confirm you have received the ${weight.toStringAsFixed(1)} kg surplus food at the pickup address.',
                          style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Proof Photo Placeholder
            Container(
              height: 180,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.camera_alt_outlined,
                      size: 40,
                      color: AppTheme.brandGreen.withOpacity(0.5),
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'Optional: Proof Photo',
                      style: TextStyle(fontWeight: FontWeight.w600, color: AppTheme.textDark),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Photo of food package or receipt upon pickup',
                      style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Notes
            TextField(
              controller: _notesController,
              decoration: const InputDecoration(
                labelText: 'Pickup Notes (Optional)',
                hintText: 'e.g. Received frozen, all crates intact',
              ),
            ),

            if (_errorMessage != null) ...[
              const SizedBox(height: 14),
              Text(_errorMessage!, style: const TextStyle(color: AppTheme.dangerRed)),
            ],
            const SizedBox(height: 28),

            // Confirm Button
            ElevatedButton(
              onPressed: _isConfirming ? null : _handleConfirmPickup,
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.brandGreen),
              child: _isConfirming
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
                    )
                  : const Text('Confirm Food Received & Record Impact'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCelebrationScreen(ClaimModel claim) {
    final impact = claim.impact;
    final meals = impact?['meals_equivalent'] ?? 10.0;
    final co2 = impact?['co2e_avoided_kg'] ?? 25.0;
    final kg = impact?['kg_rescued'] ?? 12.0;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: AppTheme.successGreen.withOpacity(0.12),
                  shape: BoxShape.circle,
                ),
                child: const Center(
                  child: Icon(Icons.celebration, color: AppTheme.successGreen, size: 48),
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'Food Rescue Completed! 🎉',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textDark,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'The food rescue loop has closed. Impact recorded on the community ledger.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: AppTheme.textMuted),
              ),
              const SizedBox(height: 28),

              // Impact metric tiles
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.cardBorder),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _buildMetricTile('${kg.toStringAsFixed(1)} kg', 'Food Rescued'),
                    _buildMetricTile('~$meals', 'Meals Provided'),
                    _buildMetricTile('${co2.toStringAsFixed(1)} kg', 'CO2e Avoided'),
                  ],
                ),
              ),
              const SizedBox(height: 36),

              ElevatedButton(
                onPressed: () => context.go('/offers'),
                child: const Text('Back to Surplus Offers'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricTile(String value, String label) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: AppTheme.brandGreen,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
        ),
      ],
    );
  }
}
