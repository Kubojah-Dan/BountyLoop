import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/models/donation_model.dart';
import 'package:bountyloop_app/services/auth_service.dart';
import 'package:bountyloop_app/services/donation_service.dart';

class DonorHomeScreen extends ConsumerStatefulWidget {
  const DonorHomeScreen({super.key});

  @override
  ConsumerState<DonorHomeScreen> createState() => _DonorHomeScreenState();
}

class _DonorHomeScreenState extends ConsumerState<DonorHomeScreen> {
  late Future<List<DonationModel>> _donationsFuture;

  @override
  void initState() {
    super.initState();
    _refreshDonations();
  }

  void _refreshDonations() {
    setState(() {
      _donationsFuture = ref.read(donationServiceProvider).getMyDonations();
    });
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('BountyLoop Donor'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _refreshDonations(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Hero Callout
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppTheme.brandGreen, Color(0xFF3B7A54)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Welcome, ${user?.displayName ?? 'Donor'}!',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Keep good food in the community. Take a photo of surplus produce, bakery items, or prepared meals to begin.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.white70,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 18),
                      ElevatedButton.icon(
                        onPressed: () => context.push('/donate/camera'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.brandAmber,
                          foregroundColor: Colors.white,
                        ),
                        icon: const Icon(Icons.camera_alt_outlined),
                        label: const Text('Donate Surplus Food'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Active Donations Section Header
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  'My Food Donations',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textDark,
                  ),
                ),
              ),
              const SizedBox(height: 8),

              FutureBuilder<List<DonationModel>>(
                future: _donationsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(
                      child: Padding(
                        padding: EdgeInsets.all(32),
                        child: CircularProgressIndicator(color: AppTheme.brandGreen),
                      ),
                    );
                  }

                  if (snapshot.hasError) {
                    return Padding(
                      padding: const EdgeInsets.all(16),
                      child: Center(
                        child: Column(
                          children: [
                            const Icon(Icons.error_outline, size: 36, color: AppTheme.textMuted),
                            const SizedBox(height: 8),
                            Text('Failed to load donations: ${snapshot.error}'),
                            TextButton(
                              onPressed: _refreshDonations,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  final donations = snapshot.data ?? [];
                  if (donations.isEmpty) {
                    return Container(
                      margin: const EdgeInsets.all(16),
                      padding: const EdgeInsets.all(28),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: AppTheme.cardBorder),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            Icons.volunteer_activism_outlined,
                            size: 48,
                            color: AppTheme.brandGreen.withOpacity(0.4),
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'No donations yet',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textDark,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'When you post food rescue items, track them live here from offer to pickup.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                    );
                  }

                  return ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: donations.length,
                    itemBuilder: (context, index) {
                      final don = donations[index];
                      final categoryLabel = AppConstants.categoryLabels[don.item] ?? don.item;
                      final icon = AppConstants.categoryIcons[don.item] ?? Icons.fastfood_outlined;

                      Color statusColor = AppTheme.brandGreen;
                      if (don.isDraft) statusColor = AppTheme.textMuted;
                      if (don.isMatched) statusColor = AppTheme.brandAmber;
                      if (don.isCompleted) statusColor = AppTheme.successGreen;

                      return Card(
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          leading: Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: AppTheme.brandGreen.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(icon, color: AppTheme.brandGreen),
                          ),
                          title: Text(
                            categoryLabel,
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          subtitle: Text(
                            '${don.estWeightKg.toStringAsFixed(1)} kg • ${don.status.toUpperCase()}',
                            style: TextStyle(
                              fontSize: 12,
                              color: statusColor,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          trailing: const Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.textMuted),
                          onTap: () => context.push('/donate/timeline/${don.id}'),
                        ),
                      );
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
