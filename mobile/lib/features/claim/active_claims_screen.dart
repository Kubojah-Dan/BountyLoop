import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';

class ActiveClaimsScreen extends ConsumerStatefulWidget {
  const ActiveClaimsScreen({super.key});

  @override
  ConsumerState<ActiveClaimsScreen> createState() => _ActiveClaimsScreenState();
}

class _ActiveClaimsScreenState extends ConsumerState<ActiveClaimsScreen> {
  int _selectedTab = 0; // 0 = Active, 1 = Completed
  bool _photoAdded = false;
  bool _isConfirming = false;
  bool _isConfirmed = false;

  Future<void> _handleConfirmPickup() async {
    setState(() => _isConfirming = true);

    try {
      // In offline or demo mode, update local state
      await Future.delayed(const Duration(milliseconds: 600));
      if (!mounted) return;
      setState(() {
        _isConfirmed = true;
        _isConfirming = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Pickup confirmed! The loop is closed and impact recorded.'),
          backgroundColor: AppTheme.brandGreen,
        ),
      );
    } catch (_) {
      if (mounted) setState(() => _isConfirming = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text(
              'Your pickups',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: AppTheme.textDark,
                letterSpacing: -0.3,
              ),
            ),
            SizedBox(height: 2),
            Text(
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
            // Active / Completed Segmented Pill Switcher
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(20),
                    onTap: () => setState(() => _selectedTab = 0),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: _selectedTab == 0 ? AppTheme.brandGreenDark : Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _selectedTab == 0 ? AppTheme.brandGreenDark : AppTheme.cardBorder,
                        ),
                      ),
                      child: Text(
                        'Active • 1',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: _selectedTab == 0 ? Colors.white : AppTheme.textMuted,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(20),
                    onTap: () => setState(() => _selectedTab = 1),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: _selectedTab == 1 ? AppTheme.brandGreenDark : Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: _selectedTab == 1 ? AppTheme.brandGreenDark : AppTheme.cardBorder,
                        ),
                      ),
                      child: Text(
                        'Completed • 18',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: _selectedTab == 1 ? Colors.white : AppTheme.textMuted,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_selectedTab == 0) ...[
              // Active Pickup Card
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.cardBorder),
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Meta row
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'TODAY • BL-2048',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                            color: AppTheme.textMuted,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: _isConfirmed ? AppTheme.brandGreenLight : AppTheme.brandAmberLight,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: _isConfirmed ? const Color(0xFFC7E2D0) : const Color(0xFFFDE68A),
                            ),
                          ),
                          child: Text(
                            _isConfirmed ? '• Completed' : '• Matched',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: _isConfirmed ? AppTheme.brandGreen : AppTheme.brandAmber,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Food Item Info Row
                    Row(
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
                            children: const [
                              Text(
                                'Sourdough loaves',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textDark,
                                ),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Hearth Bakery • 6 kg • 12 loaves',
                                style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Claimed at 13:12 • expires 16:00',
                                style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Large Planned Arrival Green Banner
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.brandGreenDark,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Your planned arrival',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white.withOpacity(0.85),
                                ),
                              ),
                              Icon(
                                Icons.directions_car_outlined,
                                color: Colors.white.withOpacity(0.8),
                                size: 18,
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.baseline,
                            textBaseline: TextBaseline.alphabetic,
                            children: [
                              const Text(
                                '14:10',
                                style: TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: -0.5,
                                ),
                              ),
                              Text(
                                'Collect by 14:30',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.white.withOpacity(0.9),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Donor Address Info
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Icon(Icons.location_on_outlined, size: 16, color: AppTheme.textDark),
                        SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Hearth Bakery • 42 Dalston Lane',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textDark,
                                ),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Use the side entrance. Ask for Alex.',
                                style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Directions and Call Donor Buttons
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Starting live GPS directions to Hearth Bakery...')),
                              );
                            },
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 11),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.navigation_outlined, size: 15),
                                SizedBox(width: 6),
                                Text('Directions', style: TextStyle(fontSize: 13)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Calling Hearth Bakery donor line...')),
                              );
                            },
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 11),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.phone_outlined, size: 15),
                                SizedBox(width: 6),
                                Text('Call donor', style: TextStyle(fontSize: 13)),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(height: 1, color: AppTheme.cardBorder),
                    const SizedBox(height: 16),

                    // Close the loop Section
                    const Text(
                      'Close the loop',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'At collection, check the food and quantity with Alex, then confirm your pickup.',
                      style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                    ),
                    const SizedBox(height: 12),

                    // Photo box
                    InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () {
                        setState(() => _photoAdded = !_photoAdded);
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(_photoAdded ? 'Pickup photo added' : 'Photo removed'),
                          ),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                          color: _photoAdded ? AppTheme.brandGreenLight : Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: _photoAdded ? AppTheme.brandGreen : AppTheme.cardBorder,
                            style: BorderStyle.solid,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _photoAdded ? Icons.check_circle : Icons.camera_alt_outlined,
                              size: 18,
                              color: _photoAdded ? AppTheme.brandGreen : AppTheme.textDark,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _photoAdded ? 'Pickup photo attached' : 'Add a pickup photo',
                                    style: const TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                      color: AppTheme.textDark,
                                    ),
                                  ),
                                  const SizedBox(height: 1),
                                  const Text(
                                    'Optional • food only, no faces',
                                    style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                  ),
                                ],
                              ),
                            ),
                            Icon(
                              _photoAdded ? Icons.refresh : Icons.add,
                              size: 18,
                              color: AppTheme.textMuted,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Confirm pickup button
                    ElevatedButton(
                      onPressed: (_isConfirmed || _isConfirming) ? null : _handleConfirmPickup,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.brandGreenDark,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      child: _isConfirming
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(_isConfirmed ? Icons.check : Icons.check_circle_outline, size: 18),
                                const SizedBox(width: 8),
                                Text(
                                  _isConfirmed ? 'Pickup Confirmed' : 'Confirm pickup • 6 kg',
                                  style: const TextStyle(fontWeight: FontWeight.w700),
                                ),
                              ],
                            ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Confirms collection and notifies Hearth Bakery.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Need help / Release claim
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  InkWell(
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Contacting community support line...')),
                      );
                    },
                    child: const Text(
                      'Need help with this pickup?',
                      style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ),
                  InkWell(
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Offer released back to community pool.')),
                      );
                    },
                    child: const Text(
                      'Release claim',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppTheme.brandAmber,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ] else ...[
              // Completed Pickups List
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.cardBorder),
                ),
                child: Column(
                  children: [
                    const Icon(Icons.inventory, size: 40, color: AppTheme.brandGreen),
                    const SizedBox(height: 10),
                    const Text(
                      '18 Rescues Completed',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Over 140 kg of surplus food rescued for St Mark\'s Pantry.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 1,
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
