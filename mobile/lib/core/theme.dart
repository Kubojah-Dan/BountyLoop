import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// BountyLoop Brand Theme Tokens matching Figma AI Design System and Project Template Showcase.
class AppTheme {
  // Brand color tokens derived from project template (--moss, --moss-deep, --terra, --cream, --ink)
  static const Color brandGreen = Color(0xFF385E38); // Organic moss green (--moss)
  static const Color brandGreenDark = Color(0xFF223824); // Deep forest moss green (--moss-deep)
  static const Color brandGreenLight = Color(0xFFE7EFE8); // Soft moss tint
  static const Color brandAmber = Color(0xFFC77735); // Warm terracotta amber (--terra)
  static const Color brandAmberLight = Color(0xFFFBF3EB); // Warm cream amber callout

  static const Color neutralWhite = Color(0xFFFFFFFF);
  static const Color surfaceLight = Color(0xFFF7F5EE); // Warm cream backdrop (--cream)
  static const Color surfaceCardCream = Color(0xFFECE6D8); // Card surface cream (--cream-2)
  static const Color textDark = Color(0xFF1F261C); // Deep charcoal ink (--ink)
  static const Color textMuted = Color(0xFF6B7B68); // Soft earthy sage
  static const Color cardBorder = Color(0xFFE4DFD3); // Warm border
  static const Color dangerRed = Color(0xFFC53030);
  static const Color dangerRedLight = Color(0xFFFDF2F2);
  static const Color warningAmber = Color(0xFFD97706);
  static const Color successGreen = Color(0xFF2E7D32);

  // Typography helpers from project template:
  // Lora for brand, titles, display headlines, numbers
  // Nunito for body, forms, buttons, controls, captions
  static TextStyle lora({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
    FontStyle? fontStyle,
    double? letterSpacing,
    double? height,
  }) {
    return GoogleFonts.lora(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color ?? textDark,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
      height: height,
    );
  }

  static TextStyle nunito({
    double? fontSize,
    FontWeight? fontWeight,
    Color? color,
    FontStyle? fontStyle,
    double? letterSpacing,
    double? height,
  }) {
    return GoogleFonts.nunito(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color ?? textDark,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
      height: height,
    );
  }

  static ThemeData get lightTheme {
    final nunitoTheme = GoogleFonts.nunitoTextTheme();

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
      textTheme: nunitoTheme.copyWith(
        displayLarge: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w600),
        displayMedium: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w600),
        displaySmall: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w600),
        headlineLarge: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w700),
        headlineMedium: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w700),
        headlineSmall: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w700),
        titleLarge: GoogleFonts.lora(color: textDark, fontWeight: FontWeight.w700),
        titleMedium: GoogleFonts.nunito(color: textDark, fontWeight: FontWeight.w700),
        titleSmall: GoogleFonts.nunito(color: textDark, fontWeight: FontWeight.w600),
        bodyLarge: GoogleFonts.nunito(color: textDark),
        bodyMedium: GoogleFonts.nunito(color: textDark),
        bodySmall: GoogleFonts.nunito(color: textMuted),
        labelLarge: GoogleFonts.nunito(fontWeight: FontWeight.w700),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: surfaceLight,
        foregroundColor: textDark,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.lora(
          color: textDark,
          fontSize: 20,
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
          textStyle: GoogleFonts.nunito(
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
          textStyle: GoogleFonts.nunito(
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
        labelStyle: GoogleFonts.nunito(color: textMuted, fontSize: 13),
        hintStyle: GoogleFonts.nunito(color: textMuted, fontSize: 13),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: neutralWhite,
        selectedItemColor: brandGreen,
        unselectedItemColor: textMuted,
        selectedLabelStyle: GoogleFonts.nunito(fontWeight: FontWeight.w700, fontSize: 11),
        unselectedLabelStyle: GoogleFonts.nunito(fontWeight: FontWeight.w500, fontSize: 11),
        elevation: 8,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}
