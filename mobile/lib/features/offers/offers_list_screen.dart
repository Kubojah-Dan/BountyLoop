import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/constants.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/offers/offer_card.dart';
import 'package:bountyloop_app/models/offer_model.dart';
import 'package:bountyloop_app/services/claim_service.dart';

class OffersListScreen extends ConsumerStatefulWidget {
  const OffersListScreen({super.key});

  @override
  ConsumerState<OffersListScreen> createState() => _OffersListScreenState();
}

class _OffersListScreenState extends ConsumerState<OffersListScreen> {
  late Future<List<OfferModel>> _offersFuture;
  String? _selectedCategory;

  @override
  void initState() {
    super.initState();
    _fetchOffers();
  }

  void _fetchOffers() {
    setState(() {
      _offersFuture = ref.read(claimServiceProvider).listOffers(
            item: _selectedCategory,
          );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Available Surplus Offers'),
        actions: [
          IconButton(
            icon: const Icon(Icons.assignment_outlined),
            tooltip: 'My Active Claims',
            onPressed: () => context.push('/claims'),
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: 'Profile',
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter Chips
          Container(
            height: 52,
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                FilterChip(
                  label: const Text('All Categories'),
                  selected: _selectedCategory == null,
                  onSelected: (selected) {
                    if (selected) {
                      setState(() => _selectedCategory = null);
                      _fetchOffers();
                    }
                  },
                ),
                const SizedBox(width: 8),
                ...AppConstants.categoryLabels.entries.map((entry) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: FilterChip(
                      label: Text(entry.value),
                      selected: _selectedCategory == entry.key,
                      onSelected: (selected) {
                        setState(() {
                          _selectedCategory = selected ? entry.key : null;
                        });
                        _fetchOffers();
                      },
                    ),
                  );
                }),
              ],
            ),
          ),
          const Divider(height: 1),

          // Offers List
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async => _fetchOffers(),
              child: FutureBuilder<List<OfferModel>>(
                future: _offersFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(
                      child: CircularProgressIndicator(color: AppTheme.brandGreen),
                    );
                  }

                  if (snapshot.hasError) {
                    return Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.cloud_off_outlined, size: 48, color: AppTheme.textMuted),
                            const SizedBox(height: 12),
                            Text('Failed to load offers: ${snapshot.error}'),
                            const SizedBox(height: 12),
                            ElevatedButton(
                              onPressed: _fetchOffers,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  final offers = snapshot.data ?? [];
                  if (offers.isEmpty) {
                    return ListView(
                      children: [
                        const SizedBox(height: 60),
                        Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.eco_outlined,
                                size: 56,
                                color: AppTheme.brandGreen.withOpacity(0.4),
                              ),
                              const SizedBox(height: 14),
                              const Text(
                                'No open surplus offers right now',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textDark,
                                ),
                              ),
                              const SizedBox(height: 6),
                              const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 32),
                                child: Text(
                                  'Pull down to refresh or check back soon when donors post food rescue batches.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    );
                  }

                  return ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    itemCount: offers.length,
                    itemBuilder: (context, index) {
                      final offer = offers[index];
                      return OfferCard(
                        offer: offer,
                        onTap: () => context.push('/offers/${offer.id}', extra: offer),
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

