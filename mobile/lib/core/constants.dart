import 'package:flutter/material.dart';

class AppConstants {
  static const String appName = 'BountyLoop';
  static const String appTagline = 'Turn surplus into supper';

  // Configurable API Base URL (defaults to localhost:8000; can be overridden via dart-define)
  static const String defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  // 12-category taxonomy mapping
  static const Map<String, String> categoryLabels = {
    'produce_fruit': 'Fresh Fruit',
    'produce_vegetable': 'Vegetables',
    'bread_bakery': 'Bakery & Bread',
    'dairy': 'Dairy & Eggs',
    'grains_staples': 'Grains & Pantry',
    'prepared_cooked': 'Prepared Meals',
    'meat_fish': 'Meat & Seafood',
    'soup_stew': 'Soups & Stews',
    'dessert_bakery_sweet': 'Desserts & Sweets',
    'beverage': 'Beverages',
    'condiment_sauce': 'Sauces & Condiments',
    'other_unclassified': 'General Surplus',
  };

  static const Map<String, IconData> categoryIcons = {
    'produce_fruit': Icons.apple,
    'produce_vegetable': Icons.eco,
    'bread_bakery': Icons.bakery_dining,
    'dairy': Icons.egg_outlined,
    'grains_staples': Icons.rice_bowl,
    'prepared_cooked': Icons.restaurant,
    'meat_fish': Icons.kebab_dining,
    'soup_stew': Icons.soup_kitchen,
    'dessert_bakery_sweet': Icons.cake,
    'beverage': Icons.local_drink,
    'condiment_sauce': Icons.liquor,
    'other_unclassified': Icons.inventory_2_outlined,
  };

  // Freshness grade badges & colors
  static const Map<String, String> freshnessLabels = {
    'grade_3_fresh': 'Grade 3: Fresh',
    'fresh': 'Fresh',
    'grade_2_good': 'Grade 2: Good',
    'grade_1_poor': 'Grade 1: Use Soon',
    'grade_0_spoiled': 'Grade 0: Expired',
    'spoiled': 'Expired',
  };

  static Color freshnessColor(String grade) {
    switch (grade) {
      case 'grade_3_fresh':
      case 'fresh':
        return const Color(0xFF2E7D32); // Emerald Green
      case 'grade_2_good':
        return const Color(0xFF1976D2); // Trust Blue
      case 'grade_1_poor':
        return const Color(0xFFE67E22); // Amber Orange
      case 'grade_0_spoiled':
      case 'spoiled':
      default:
        return const Color(0xFFC93B2B); // Crimson Red
    }
  }
}
