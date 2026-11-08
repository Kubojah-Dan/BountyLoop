import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/services/auth_service.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _aiRetrainingConsent = false;
  bool _isSyncing = false;

  void _handleRoleToggle() async {
    final authState = ref.read(authProvider);
    final isRecipient = authState.user?.isRecipient ?? true;

    try {
      if (isRecipient) {
        await ref.read(authProvider.notifier).signIn(
              email: 'donor@bountyloop.org',
              role: 'donor',
              displayName: 'Hearth Bakery',
            );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Switched to Donor role (Hearth Bakery)')),
        );
        context.go('/donate');
      } else {
        await ref.read(authProvider.notifier).signIn(
              email: 'recipient@bountyloop.org',
              role: 'recipient',
              displayName: 'Maya Patel',
            );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Switched to Recipient role (St Mark\'s Pantry)')),
        );
        context.go('/offers');
      }
    } catch (_) {
      // In offline/demo mode, proceed cleanly
      if (!mounted) return;
      context.go(isRecipient ? '/donate' : '/offers');
    }
  }

  void _handleSync() async {
    setState(() => _isSyncing = true);
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    setState(() => _isSyncing = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Outbox synced with server.')),
    );
  }

  void _showPurgeDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm GDPR Data Purge'),
        content: const Text(
          'Are you sure you want to request account deletion? All personal data, profile info, and uploaded photos will be permanently queued for purge.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.dangerRed),
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Data purge request submitted. Account scheduled for removal.'),
                  backgroundColor: AppTheme.dangerRed,
                ),
              );
            },
            child: const Text('Request Purge'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState.user;
    final isDonor = user?.isDonor ?? false;

    final displayName = isDonor ? 'Hearth Bakery' : 'Maya Patel';
    final roleSubtitle = isDonor ? 'Hearth Bakery • Donor' : 'St Mark\'s Pantry • Recipient';
    final email = isDonor ? 'donor@bountyloop.org' : 'maya@stmarkspantry.org';
    final avatarInitials = isDonor ? 'HB' : 'MP';

    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Profile & privacy',
              style: AppTheme.lora(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 2),
            const Text(
              'YOUR ACCOUNT, YOUR CHOICES',
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
              child: Text(
                avatarInitials,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // User Profile Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.cardBorder),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppTheme.brandGreenDark,
                    child: Text(
                      avatarInitials,
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          displayName,
                          style: AppTheme.lora(
                            fontSize: 19,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textDark,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          roleSubtitle,
                          style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          email,
                          style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Role Switcher Card
            InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: _handleRoleToggle,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppTheme.cardBorder),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.swap_horiz, color: AppTheme.brandGreen, size: 22),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isDonor ? 'Using Donor (Hearth Bakery)' : 'Using Recipient Pantry',
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.textDark,
                            ),
                          ),
                          const SizedBox(height: 1),
                          Text(
                            isDonor ? 'Switch demo role to Recipient' : 'Switch demo role to Donor',
                            style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, color: AppTheme.textMuted),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Your data & AI Section
            const Text(
              'Your data & AI',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),

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
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              'Help improve food recognition',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: AppTheme.textDark,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Optional AI retraining consent',
                              style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                      Switch(
                        value: _aiRetrainingConsent,
                        activeColor: AppTheme.brandGreen,
                        onChanged: (val) => setState(() => _aiRetrainingConsent = val),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _aiRetrainingConsent
                        ? 'On. Your food photos help retrain and improve detection accuracy.'
                        : 'Off. Your photos are not used to retrain our models. Food assessment still works, and your access is unchanged.',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'You can change this choice at any time.',
                    style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Offline outbox Section
            const Text(
              'Offline outbox',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),

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
                    children: const [
                      Icon(Icons.cloud_done_outlined, size: 18, color: AppTheme.brandGreen),
                      SizedBox(width: 8),
                      Text(
                        'Everything is up to date',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textDark,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  const Padding(
                    padding: EdgeInsets.only(left: 26),
                    child: Text(
                      '0 pending • last synced today at 13:39',
                      style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Offline actions wait here and sync when you reconnect. A queued pickup is not confirmed until synced.',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.4),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.circle, size: 8, color: AppTheme.brandGreen),
                          SizedBox(width: 6),
                          Text(
                            'Online',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.brandGreen,
                            ),
                          ),
                        ],
                      ),
                      InkWell(
                        onTap: _isSyncing ? null : _handleSync,
                        child: Row(
                          children: [
                            Text(
                              _isSyncing ? 'Syncing...' : 'Sync now',
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.brandGreen,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(
                              Icons.refresh,
                              size: 14,
                              color: _isSyncing ? AppTheme.textMuted : AppTheme.brandGreen,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Delete Account & Data (GDPR Purge) Section
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.dangerRedLight,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: const [
                      Icon(Icons.shield_outlined, color: AppTheme.dangerRed, size: 18),
                      SizedBox(width: 8),
                      Text(
                        'Delete account & data',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF991B1B),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Request a GDPR data purge. This permanently removes your account, photos and personal data, except records we must retain by law.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF7F1D1D),
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton(
                    onPressed: _showPurgeDialog,
                    style: OutlinedButton.styleFrom(
                      backgroundColor: Colors.white,
                      side: const BorderSide(color: Color(0xFFFCA5A5)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 11),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.delete_outline, size: 16, color: AppTheme.dangerRed),
                        SizedBox(width: 6),
                        Text(
                          'Request data purge',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.dangerRed,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'A separate confirmation is required. No data is deleted by opening this request.',
                    style: TextStyle(fontSize: 11, color: Color(0xFF991B1B)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Footer Links
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                InkWell(
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Opening BountyLoop Privacy Policy...')),
                    );
                  },
                  child: const Row(
                    children: [
                      Text(
                        'Privacy policy',
                        style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
                      ),
                      SizedBox(width: 2),
                      Icon(Icons.north_east, size: 12, color: AppTheme.textMuted),
                    ],
                  ),
                ),
                InkWell(
                  onTap: () {
                    ref.read(authProvider.notifier).signOut();
                    context.go('/login');
                  },
                  child: const Text(
                    'Sign out',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textDark,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: 2,
        selectedItemColor: AppTheme.brandGreen,
        unselectedItemColor: AppTheme.textMuted,
        backgroundColor: Colors.white,
        onTap: (idx) {
          if (idx == 0) {
            context.go(isDonor ? '/donate' : '/offers');
          } else if (idx == 1) {
            context.go(isDonor ? '/donate/camera' : '/claims');
          } else if (idx == 2) {
            context.go('/profile');
          }
        },
        items: [
          BottomNavigationBarItem(
            icon: Icon(isDonor ? Icons.home_outlined : Icons.eco_outlined),
            label: isDonor ? 'Home' : 'Offers',
          ),
          BottomNavigationBarItem(
            icon: Icon(isDonor ? Icons.camera_alt_outlined : Icons.inventory_2_outlined),
            label: isDonor ? 'Donate' : 'Pickups',
          ),
          const BottomNavigationBarItem(
            icon: Icon(Icons.person_outline),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
