import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/services/auth_service.dart';
import 'package:bountyloop_app/services/donation_service.dart';

class DonorHomeScreen extends ConsumerStatefulWidget {
  const DonorHomeScreen({super.key});

  @override
  ConsumerState<DonorHomeScreen> createState() => _DonorHomeScreenState();
}

class _DonorHomeScreenState extends ConsumerState<DonorHomeScreen> {
  @override
  void initState() {
    super.initState();
    _refreshDonations();
  }

  void _refreshDonations() {
    ref.read(donationServiceProvider).getMyDonations();
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;
    final donorName = user?.displayName ?? 'Hearth Bakery';

    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 1. Top Header with User Initials
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Hello, $donorName',
                            style: AppTheme.lora(
                              fontSize: 19,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textDark,
                              letterSpacing: -0.2,
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'DONOR • DALSTON, LONDON',
                            style: TextStyle(
                              fontSize: 10,
                              letterSpacing: 1.1,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textMuted,
                            ),
                          ),
                        ],
                      ),
                      GestureDetector(
                        onTap: () => context.push('/profile'),
                        child: Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            color: AppTheme.brandGreen.withOpacity(0.12),
                            shape: BoxShape.circle,
                            border: Border.all(color: AppTheme.brandGreen.withOpacity(0.2)),
                          ),
                          child: const Center(
                            child: Text(
                              'HB',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.brandGreen,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // 2. Headline & Subtitle with Lora italic accent
                  RichText(
                    text: TextSpan(
                      style: AppTheme.lora(
                        fontSize: 27,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textDark,
                        height: 1.12,
                        letterSpacing: -0.3,
                      ),
                      children: [
                        const TextSpan(text: 'Your surplus. Someone\'s\n'),
                        TextSpan(
                          text: 'supper.',
                          style: AppTheme.lora(
                            fontSize: 27,
                            fontWeight: FontWeight.w700,
                            fontStyle: FontStyle.italic,
                            color: AppTheme.brandGreen,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'A little less waste. A lot more possibility.',
                    style: AppTheme.nunito(
                      fontSize: 13,
                      color: AppTheme.textMuted,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 3. Impact KPI Card (Deep Forest Green)
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: BoxDecoration(
                      color: AppTheme.brandGreenDark,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.brandGreenDark.withOpacity(0.2),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.eco_rounded, color: Colors.white70, size: 14),
                            SizedBox(width: 6),
                            Text(
                              'Your impact, all time',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '186',
                                  style: AppTheme.lora(
                                    color: Colors.white,
                                    fontSize: 27,
                                    fontWeight: FontWeight.w700,
                                    fontStyle: FontStyle.italic,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'kg rescued',
                                  style: AppTheme.nunito(color: Colors.white70, fontSize: 11),
                                ),
                              ],
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '442',
                                  style: AppTheme.lora(
                                    color: Colors.white,
                                    fontSize: 27,
                                    fontWeight: FontWeight.w700,
                                    fontStyle: FontStyle.italic,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'meals shared',
                                  style: AppTheme.nunito(color: Colors.white70, fontSize: 11),
                                ),
                              ],
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '465',
                                  style: AppTheme.lora(
                                    color: Colors.white,
                                    fontSize: 27,
                                    fontWeight: FontWeight.w700,
                                    fontStyle: FontStyle.italic,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'kg CO₂ saved',
                                  style: AppTheme.nunito(color: Colors.white70, fontSize: 11),
                                ),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Container(
                          padding: const EdgeInsets.only(top: 10),
                          decoration: const BoxDecoration(
                            border: Border(top: BorderSide(color: Colors.white12)),
                          ),
                          child: const Text(
                            'Estimated from your 32 completed donations',
                            style: TextStyle(color: Colors.white60, fontSize: 10.5),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 4. Golden Amber Button (Primary CTA)
                  ElevatedButton.icon(
                    onPressed: () => context.push('/donate/camera'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.brandAmber,
                      foregroundColor: Colors.white,
                      minimumSize: const Size.fromHeight(52),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      elevation: 0,
                    ),
                    icon: const Icon(Icons.camera_alt_outlined, size: 20),
                    label: const Text(
                      'Rescue food with a photo',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // 5. In Your Loop (Active Posts)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'In your loop',
                        style: AppTheme.lora(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textDark),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.brandGreenLight,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Text(
                          '1 active post',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.brandGreen),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Active Matched Donation Card
                  InkWell(
                    onTap: () => context.push('/donate/timeline/BL-2048'),
                    borderRadius: BorderRadius.circular(20),
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.cardBorder),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.03),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          ClipRRect(
                            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                            child: Image.asset(
                              'assets/images/sourdough_loaves.jpg',
                              height: 150,
                              width: double.infinity,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) => Container(
                                height: 150,
                                color: AppTheme.brandAmberLight,
                                child: const Center(child: Icon(Icons.bakery_dining_rounded, size: 40)),
                              ),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    const Text(
                                      'Sourdough loaves',
                                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTheme.textDark),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                      decoration: BoxDecoration(
                                        color: AppTheme.brandAmberLight,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: const Text(
                                        '• Matched',
                                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.brandAmber),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                const Text(
                                  '6 kg • 12 loaves • BL-2048',
                                  style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                                ),
                                const SizedBox(height: 12),
                                Container(
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: AppTheme.brandGreenLight,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Row(
                                    children: [
                                      Icon(Icons.local_shipping_outlined, size: 16, color: AppTheme.brandGreen),
                                      SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'St Mark\'s Pantry is on the way\nArriving 14:10 • collect by 14:30',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                            color: AppTheme.brandGreen,
                                            height: 1.3,
                                          ),
                                        ),
                                      ),
                                      Icon(Icons.chevron_right, size: 16, color: AppTheme.brandGreen),
                                    ],
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

                  // 6. Recently Rescued Section
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Recently rescued',
                        style: AppTheme.lora(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textDark),
                      ),
                      TextButton(
                        onPressed: () {},
                        child: const Text('View history', style: TextStyle(fontSize: 12, color: AppTheme.brandGreen)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: const BoxDecoration(
                            color: AppTheme.brandGreenLight,
                            shape: BoxShape.circle,
                          ),
                          child: const Center(
                            child: Icon(Icons.check_rounded, color: AppTheme.brandGreen, size: 18),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Mixed pastries • 4 kg',
                                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textDark),
                              ),
                              SizedBox(height: 2),
                              Text(
                                'Yesterday • Hackney Food Bank',
                                style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'Picked up',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 0,
        onTap: (index) {
          if (index == 1) context.push('/donate/camera');
          if (index == 2) context.push('/profile');
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home_filled), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.camera_alt_outlined), label: 'Donate'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
