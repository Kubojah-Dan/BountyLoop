import 'package:flutter/material.dart';

/// BountyLoop Brand Theme Tokens matching Figma AI Design System.
class AppTheme {
  // Brand color tokens
  static const Color brandGreen = Color(0xFF2D5A3D); // Primary brand green
  static const Color brandGreenDark = Color(0xFF1E3F2B); // Deep card green
  static const Color brandGreenLight = Color(0xFFE8F3EB); // Soft sage/green highlight
  static const Color brandAmber = Color(0xFFD98E32); // Secondary golden amber CTA
  static const Color brandAmberLight = Color(0xFFFEF7ED); // Light amber callout

  static const Color neutralWhite = Color(0xFFFFFFFF);
  static const Color surfaceLight = Color(0xFFF7F9F6); // Soft warm off-white
  static const Color textDark = Color(0xFF1C2B1E); // High-contrast charcoal green
  static const Color textMuted = Color(0xFF6C7D6E); // Subtle label grey/sage
  static const Color cardBorder = Color(0xFFE5EDE6); // Refined card border
  static const Color dangerRed = Color(0xFFDC2626);
  static const Color dangerRedLight = Color(0xFFFEF2F2);
  static const Color warningAmber = Color(0xFFD97706);
  static const Color successGreen = Color(0xFF16A34A);

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
        backgroundColor: surfaceLight,
        foregroundColor: textDark,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textDark,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardTheme(
        color: neutralWhite,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: cardBorder, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: brandGreen,
          foregroundColor: neutralWhite,
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.1,
          ),
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textDark,
          side: const BorderSide(color: cardBorder, width: 1.2),
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: neutralWhite,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: cardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: cardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: brandGreen, width: 1.8),
        ),
        labelStyle: const TextStyle(color: textMuted, fontSize: 13),
        hintStyle: const TextStyle(color: textMuted, fontSize: 13),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: neutralWhite,
        selectedItemColor: brandGreen,
        unselectedItemColor: textMuted,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 11),
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
