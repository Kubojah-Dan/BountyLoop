import 'package:flutter/material.dart';

/// BountyLoop Brand Theme Guidelines (§Brand Guide v1.0).
class AppTheme {
  // Brand color tokens
  static const Color brandGreen = Color(0xFF2D5A3D); // Primary buttons, nav, card headers
  static const Color brandAmber = Color(0xFFD98E32); // Accents, highlights, CTA, loop leaf
  static const Color neutralWhite = Color(0xFFFFFFFF);
  static const Color surfaceLight = Color(0xFFF5F8F5);
  static const Color textDark = Color(0xFF1A2E1F);
  static const Color textMuted = Color(0xFF6B8069);
  static const Color cardBorder = Color(0xFFE2EBE2);
  static const Color dangerRed = Color(0xFFC93B2B);
  static const Color warningAmber = Color(0xFFE67E22);
  static const Color successGreen = Color(0xFF2E7D32);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: brandGreen,
        primary: brandGreen,
        secondary: brandAmber,
        surface: neutralWhite,
        onSurface: textDark,
        error: dangerRed,
      ),
      scaffoldBackgroundColor: surfaceLight,
      fontFamily: 'Inter',
      appBarTheme: const AppBarTheme(
        backgroundColor: brandGreen,
        foregroundColor: neutralWhite,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: neutralWhite,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardTheme(
        color: neutralWhite,
        elevation: 1,
        shadowColor: brandGreen.withOpacity(0.08),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: cardBorder, width: 1),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: brandGreen,
          foregroundColor: neutralWhite,
          minimumSize: const Size.fromHeight(52), // Accessible >= 48px tap target
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: brandGreen,
          side: const BorderSide(color: brandGreen, width: 1.5),
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: neutralWhite,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: brandGreen, width: 2),
        ),
        labelStyle: const TextStyle(color: textMuted),
        hintStyle: const TextStyle(color: textMuted),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: neutralWhite,
        selectedItemColor: brandGreen,
        unselectedItemColor: textMuted,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 12),
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
