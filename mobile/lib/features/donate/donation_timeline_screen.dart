import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _fetchDonation();
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchDonation(silent: true));
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchDonation({bool silent = false}) async {
    try {
      final don = await ref.read(donationServiceProvider).getDonation(widget.donationId);
      if (mounted) setState(() => _donation = don);
    } catch (_) {
      // Keep demo values intact on network failure
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppTheme.textDark),
          onPressed: () => context.go('/donate'),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Donation timeline',
              style: AppTheme.lora(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '${widget.donationId.toUpperCase().contains('BL-') ? widget.donationId : 'BL-2048'} • HEARTH BAKERY',
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
                'HB',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Item Header Card
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.asset(
                      'assets/images/sourdough_loaves.jpg',
                      width: 58,
                      height: 58,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        width: 58,
                        height: 58,
                        color: const Color(0xFFF0EFEA),
                        child: const Icon(Icons.bakery_dining, color: AppTheme.brandGreen),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppTheme.brandAmberLight,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0xFFFDE68A)),
                          ),
                          child: const Text(
                            '• Matched - pickup next',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.brandAmber,
                            ),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _donation != null ? _donation!.item.replaceAll('_', ' ') : 'Sourdough loaves',
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textDark,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _donation != null ? '${_donation!.estWeightKg.toStringAsFixed(0)} kg • expires 16:00' : '6 kg • 12 loaves • expires 16:00',
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Large Green Arrival Banner
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.brandGreenDark,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        '• PICKUP IN PROGRESS',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.8,
                          color: Color(0xFF86EFAC),
                        ),
                      ),
                      Icon(
                        Icons.local_shipping_outlined,
                        color: Colors.white.withOpacity(0.8),
                        size: 20,
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Arriving at 14:10',
                    style: AppTheme.lora(
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'St Mark\'s Pantry - collect by 14:30',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.white.withOpacity(0.9),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 4-Step Vertical Timeline Card
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Column(
                children: [
                  _buildTimelineItem(
                    title: 'Draft',
                    subtitle: 'Photo reviewed and confirmed',
                    time: '12:52',
                    status: _TimelineStatus.completed,
                    showBottomLine: true,
                  ),
                  _buildTimelineItem(
                    title: 'Open',
                    subtitle: 'Shared with nearby recipients',
                    time: '13:00',
                    status: _TimelineStatus.completed,
                    showBottomLine: true,
                  ),
                  _buildTimelineItem(
                    title: 'Matched',
                    subtitle: 'Claimed by St Mark\'s Pantry',
                    time: '13:12',
                    status: _TimelineStatus.active,
                    showBottomLine: true,
                  ),
                  _buildTimelineItem(
                    title: 'Picked up',
                    subtitle: 'Waiting for recipient confirmation',
                    time: 'Pending',
                    status: _TimelineStatus.pending,
                    showBottomLine: false,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Recipient Contact Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 20,
                        backgroundColor: AppTheme.brandGreenDark,
                        child: const Text(
                          'MP',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'Maya • St Mark\'s Pantry',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textDark,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Verified community recipient',
                              style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.phone_outlined, color: AppTheme.brandGreen, size: 20),
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Calling Maya at St Mark\'s Pantry...')),
                          );
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceLight,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Text(
                      'Pickup note: use the bakery\'s side entrance.',
                      style: TextStyle(fontSize: 12, color: AppTheme.textDark),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            const Text(
              'The pantry confirms collection to close the loop. Your impact updates after pickup, not before.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
            ),
            const SizedBox(height: 14),

            // Contact Recipient Button
            OutlinedButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Opening secure messenger with recipient...')),
                );
              },
              style: OutlinedButton.styleFrom(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.chat_bubble_outline, size: 18),
                  SizedBox(width: 8),
                  Text('Contact recipient'),
                ],
              ),
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
          if (idx == 0) context.go('/donate');
          if (idx == 1) context.go('/donate/camera');
          if (idx == 2) context.go('/profile');
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.camera_alt_outlined), label: 'Donate'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }

  Widget _buildTimelineItem({
    required String title,
    required String subtitle,
    required String time,
    required _TimelineStatus status,
    required bool showBottomLine,
  }) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Step Icon & Vertical Line
          Column(
            children: [
              _buildStatusIcon(status),
              if (showBottomLine)
                Expanded(
                  child: Container(
                    width: 2,
                    color: status == _TimelineStatus.completed
                        ? AppTheme.brandGreen
                        : const Color(0xFFE2E8F0),
                    margin: const EdgeInsets.symmetric(vertical: 4),
                  ),
                ),
            ],
          ),
          const SizedBox(width: 14),
          // Content
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: status == _TimelineStatus.pending
                                ? AppTheme.textMuted
                                : AppTheme.textDark,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          subtitle,
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    time,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: status == _TimelineStatus.active
                          ? AppTheme.brandAmber
                          : AppTheme.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIcon(_TimelineStatus status) {
    switch (status) {
      case _TimelineStatus.completed:
        return Container(
          width: 22,
          height: 22,
          decoration: const BoxDecoration(
            color: AppTheme.brandGreen,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check, size: 14, color: Colors.white),
        );
      case _TimelineStatus.active:
        return Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: AppTheme.brandAmber, width: 2),
          ),
          child: Center(
            child: Container(
              width: 10,
              height: 10,
              decoration: const BoxDecoration(
                color: AppTheme.brandAmber,
                shape: BoxShape.circle,
              ),
            ),
          ),
        );
      case _TimelineStatus.pending:
        return Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: const Color(0xFFCBD5E1), width: 2),
          ),
        );
    }
  }
}

enum _TimelineStatus { completed, active, pending }
