import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/features/offers/offer_card.dart';
import 'package:bountyloop_app/models/offer_model.dart';

class OffersListScreen extends ConsumerStatefulWidget {
  const OffersListScreen({super.key});

  @override
  ConsumerState<OffersListScreen> createState() => _OffersListScreenState();
}

class _OffersListScreenState extends ConsumerState<OffersListScreen> {
  String _selectedCategory = 'All food';
  final List<String> _categories = ['All food', 'Produce', 'Bakery', 'Prepared'];

  // Static fallback offers matching Figma Screen 5 exactly
  final List<OfferModel> _demoOffers = [
    OfferModel(
      id: 'BL-2051',
      donorId: 'donor-1',
      donorName: 'Greenline Grocer',
      donorAddress: '124 Kingsland Road, Dalston',
      photoPaths: const ['assets/images/vegetable_crate.jpg'],
      item: 'produce_vegetables',
      freshness: 'grade_2_good',
      estWeightKg: 8.0,
      expiresAt: DateTime.now().add(const Duration(hours: 4, minutes: 20)),
      hoursRemaining: 4.33,
      distanceKm: 1.2,
      status: 'open',
      createdAt: DateTime.now().subtract(const Duration(minutes: 40)),
    ),
    OfferModel(
      id: 'BL-2052',
      donorId: 'donor-2',
      donorName: 'Orchard Café',
      donorAddress: '55 Stoke Newington Rd',
      photoPaths: const ['assets/images/mixed_pastries.jpg'],
      item: 'bakery_pastries',
      freshness: 'grade_2_good',
      estWeightKg: 2.0,
      expiresAt: DateTime.now().add(const Duration(hours: 1, minutes: 50)),
      hoursRemaining: 1.83,
      distanceKm: 1.8,
      status: 'open',
      createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
    ),
    OfferModel(
      id: 'BL-2053',
      donorId: 'donor-3',
      donorName: 'Ridley Road Co-op',
      donorAddress: '12 Ridley Road Market',
      photoPaths: const ['assets/images/market_vegetables.jpg'],
      item: 'produce_boxes',
      freshness: 'grade_3_fresh',
      estWeightKg: 10.0,
      expiresAt: DateTime.now().add(const Duration(hours: 5, minutes: 20)),
      hoursRemaining: 5.33,
      distanceKm: 2.4,
      status: 'open',
      createdAt: DateTime.now().subtract(const Duration(minutes: 10)),
    ),
  ];

  @override
  Widget build(BuildContext context) {
    // Filter demo offers if a category is selected
    final filteredOffers = _demoOffers.where((offer) {
      if (_selectedCategory == 'All food') return true;
      if (_selectedCategory == 'Produce') return offer.item.contains('produce');
      if (_selectedCategory == 'Bakery') return offer.item.contains('bakery');
      return true;
    }).toList();

    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Good food, nearby',
              style: AppTheme.lora(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 2),
            const Text(
              'ST MARK\'S PANTRY • RECIPIENT',
              style: TextStyle(
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
              radius: 17,
              backgroundColor: AppTheme.brandGreenDark,
              child: const Text(
                'MP',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Location and Filter Bar
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.location_on_outlined, size: 16, color: AppTheme.textDark),
                        SizedBox(width: 6),
                        Text(
                          'Dalston • within 5 km',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textDark,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.keyboard_arrow_down, size: 16, color: AppTheme.textMuted),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppTheme.cardBorder),
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.tune, size: 20, color: AppTheme.textDark),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Showing nearby filters (radius, dietary, allergens)')),
                      );
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Horizontal Category Pills
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: _categories.map((cat) {
                  final isSelected = _selectedCategory == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: () => setState(() => _selectedCategory = cat),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: isSelected ? AppTheme.brandGreenDark : Colors.white,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: isSelected ? AppTheme.brandGreenDark : AppTheme.cardBorder,
                          ),
                        ),
                        child: Text(
                          cat,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: isSelected ? Colors.white : AppTheme.textDark,
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 16),

            // Meta line: count and update timestamp
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${filteredOffers.length} offers • sorted by distance',
                  style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                ),
                const Text(
                  'Updated 13:40',
                  style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Offer Cards
            ...filteredOffers.map((offer) {
              return OfferCard(
                offer: offer,
                onTap: () {
                  context.push('/offers/${offer.id}', extra: offer);
                },
              );
            }),

            const SizedBox(height: 8),
            const Text(
              'Demo feed - countdowns shown at 13:40 today. Check storage and allergens before claiming.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.4),
            ),
            const SizedBox(height: 16),
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
