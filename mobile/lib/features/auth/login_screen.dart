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
  final _emailController = TextEditingController(text: 'hearth.bakery@bountyloop.org');
  final _passwordController = TextEditingController(text: '••••••••');
  bool _obscurePassword = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin({String? overrideEmail, String? role, String? displayName}) async {
    final email = (overrideEmail ?? _emailController.text).trim();
    if (email.isEmpty) {
      setState(() => _errorMessage = 'Please enter an email');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final userRole = role ?? (email.contains('pantry') ? 'recipient' : 'donor');
      await ref.read(authProvider.notifier).signIn(
            email: email,
            role: userRole,
            displayName: displayName ?? (userRole == 'donor' ? 'Hearth Bakery' : 'St Mark\'s Pantry'),
          );

      if (!mounted) return;
      if (userRole == 'donor') {
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceLight,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 1. Top Branding Header
                  Row(
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: AppTheme.brandGreen,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Center(
                          child: Icon(
                            Icons.eco_rounded,
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'BountyLoop',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.textDark,
                          letterSpacing: -0.3,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // 2. Hero Image with Tag
                  Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: Image.asset(
                          'assets/images/vegetable_crate.jpg',
                          height: 180,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) {
                            return Container(
                              height: 180,
                              color: AppTheme.brandGreenLight,
                              child: const Center(
                                child: Icon(Icons.shopping_basket_rounded, size: 48, color: AppTheme.brandGreen),
                              ),
                            );
                          },
                        ),
                      ),
                      Positioned(
                        bottom: 12,
                        left: 12,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.92),
                            borderRadius: BorderRadius.circular(30),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.08),
                                blurRadius: 6,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.eco_outlined, size: 14, color: AppTheme.brandGreen),
                              SizedBox(width: 6),
                              Text(
                                'Good food. A better next chapter.',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.textDark,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // 3. Headline & Description
                  const Text(
                    'More shared. Less wasted.',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textDark,
                      letterSpacing: -0.5,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Connect surplus food with the people who can use it. Welcome to your local loop.',
                    style: TextStyle(
                      fontSize: 13,
                      color: AppTheme.textMuted,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 20),

                  if (_errorMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.dangerRedLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.dangerRed.withOpacity(0.3)),
                      ),
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: AppTheme.dangerRed, fontSize: 12),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // 4. Form Fields
                  const Text(
                    'Email address',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textDark),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _emailController,
                    decoration: const InputDecoration(
                      hintText: 'you@organisation.org',
                    ),
                  ),
                  const SizedBox(height: 14),

                  const Text(
                    'Password',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textDark),
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      hintText: 'Enter your password',
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                          size: 18,
                          color: AppTheme.textMuted,
                        ),
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),

                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () {},
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Text(
                        'Forgot password?',
                        style: TextStyle(color: AppTheme.brandGreen, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 5. Sign In Button
                  ElevatedButton(
                    onPressed: _isLoading ? null : () => _handleLogin(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.brandGreen,
                    ),
                    child: _isLoading
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text('Sign in'),
                              SizedBox(width: 8),
                              Icon(Icons.arrow_forward_rounded, size: 16),
                            ],
                          ),
                  ),
                  const SizedBox(height: 24),

                  // 6. Demo Explorer Divider
                  const Row(
                    children: [
                      Expanded(child: Divider(color: AppTheme.cardBorder)),
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 12),
                        child: Text(
                          'OR EXPLORE A DEMO',
                          style: TextStyle(
                            fontSize: 10,
                            letterSpacing: 1.2,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textMuted,
                          ),
                        ),
                      ),
                      Expanded(child: Divider(color: AppTheme.cardBorder)),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // 7. Side-by-Side Demo Cards
                  Row(
                    children: [
                      Expanded(
                        child: InkWell(
                          onTap: () => _handleLogin(
                            overrideEmail: 'hearth.bakery@bountyloop.org',
                            role: 'donor',
                            displayName: 'Hearth Bakery',
                          ),
                          borderRadius: BorderRadius.circular(16),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppTheme.brandGreenLight.withOpacity(0.6),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: AppTheme.cardBorder),
                            ),
                            child: const Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Icon(Icons.storefront_outlined, size: 20, color: AppTheme.brandGreen),
                                    Icon(Icons.north_east_rounded, size: 14, color: AppTheme.brandGreen),
                                  ],
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Donor',
                                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.brandGreen),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'Hearth Bakery',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppTheme.textDark),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: InkWell(
                          onTap: () => _handleLogin(
                            overrideEmail: 'maya@stmarkspantry.org',
                            role: 'recipient',
                            displayName: 'St Mark\'s Pantry',
                          ),
                          borderRadius: BorderRadius.circular(16),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppTheme.brandAmberLight,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: AppTheme.cardBorder),
                            ),
                            child: const Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Icon(Icons.volunteer_activism_outlined, size: 20, color: AppTheme.brandAmber),
                                    Icon(Icons.north_east_rounded, size: 14, color: AppTheme.brandAmber),
                                  ],
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Recipient Pantry',
                                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.brandAmber),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'St Mark\'s Pantry',
                                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppTheme.textDark),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // 8. Footer
                  const Text(
                    'By continuing, you agree to our Terms & Privacy Policy. Demo roles use sample data.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.3),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
