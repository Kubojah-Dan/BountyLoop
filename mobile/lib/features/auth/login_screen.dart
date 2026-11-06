import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:bountyloop_app/core/theme.dart';
import 'package:bountyloop_app/services/auth_service.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailController = TextEditingController(text: 'donor@bountyloop.org');
  String _selectedRole = 'donor';
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      setState(() => _errorMessage = 'Please enter an email');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await ref.read(authProvider.notifier).signIn(
            email: email,
            role: _selectedRole,
            displayName: email.split('@').first,
          );

      if (!mounted) return;
      if (_selectedRole == 'donor') {
        context.go('/donate');
      } else {
        context.go('/offers');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString();
      });
    }
  }

  void _quickFill(String email, String role) {
    setState(() {
      _emailController.text = email;
      _selectedRole = role;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Brand Header
                Container(
                  width: 90,
                  height: 90,
                  decoration: BoxDecoration(
                    color: AppTheme.brandGreen.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.recycling_rounded,
                      size: 54,
                      color: AppTheme.brandGreen,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'BountyLoop',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.brandGreen,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Turn surplus into supper — the AI food rescue loop',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: AppTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 36),

                // Role selection chips
                const Text(
                  'Select Your Account Type',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textDark,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: ChoiceChip(
                        label: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.storefront_outlined, size: 18),
                            SizedBox(width: 6),
                            Text('Donor'),
                          ],
                        ),
                        selected: _selectedRole == 'donor',
                        selectedColor: AppTheme.brandGreen.withOpacity(0.15),
                        labelStyle: TextStyle(
                          color: _selectedRole == 'donor'
                              ? AppTheme.brandGreen
                              : AppTheme.textMuted,
                          fontWeight: FontWeight.w600,
                        ),
                        onSelected: (selected) {
                          if (selected) setState(() => _selectedRole = 'donor');
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ChoiceChip(
                        label: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.volunteer_activism_outlined, size: 18),
                            SizedBox(width: 6),
                            Text('Recipient'),
                          ],
                        ),
                        selected: _selectedRole == 'recipient',
                        selectedColor: AppTheme.brandAmber.withOpacity(0.18),
                        labelStyle: TextStyle(
                          color: _selectedRole == 'recipient'
                              ? AppTheme.brandAmber
                              : AppTheme.textMuted,
                          fontWeight: FontWeight.w600,
                        ),
                        onSelected: (selected) {
                          if (selected) setState(() => _selectedRole = 'recipient');
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Email field
                TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Work Email Address',
                    prefixIcon: Icon(Icons.email_outlined, color: AppTheme.textMuted),
                  ),
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppTheme.dangerRed.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: const TextStyle(color: AppTheme.dangerRed, fontSize: 13),
                    ),
                  ),
                ],
                const SizedBox(height: 24),

                // Sign in button
                ElevatedButton(
                  onPressed: _isLoading ? null : _handleLogin,
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: Colors.white,
                          ),
                        )
                      : Text(
                          _selectedRole == 'donor'
                              ? 'Continue as Food Donor'
                              : 'Continue as Food Rescue Partner',
                        ),
                ),
                const SizedBox(height: 28),

                // Fast test accounts
                const Divider(),
                const SizedBox(height: 12),
                const Text(
                  'Quick Demo Logins (Pilot Mode)',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton.icon(
                      onPressed: () => _quickFill('donor@bountyloop.org', 'donor'),
                      icon: const Icon(Icons.apple, size: 16),
                      label: const Text('Jane\'s Bakery (Donor)'),
                    ),
                    const SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () => _quickFill('foodbank@bountyloop.org', 'recipient'),
                      icon: const Icon(Icons.food_bank_outlined, size: 16),
                      label: const Text('Austin Hub (Recipient)'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
