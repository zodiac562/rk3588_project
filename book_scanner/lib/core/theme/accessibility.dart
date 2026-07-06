import 'package:flutter/material.dart';

class AccessibilityConfig {
  AccessibilityConfig._();

  static const double minTouchTarget = 48.0;
  static const double largeButtonHeight = 56.0;
  static const double largeButtonMinWidth = 120.0;
  static const double iconSize = 24.0;
  static const double largeIconSize = 32.0;
  static const double smallRadius = 12.0;
  static const double mediumRadius = 16.0;
  static const double largeRadius = 20.0;
  static const double xlargeRadius = 28.0;

  static const double bodyFontSize = 16.0;
  static const double smallFontSize = 14.0;
  static const double titleFontSize = 20.0;
  static const double largeTitleFontSize = 28.0;

  static const double spacingXS = 4.0;
  static const double spacingSM = 8.0;
  static const double spacingMD = 12.0;
  static const double spacingLG = 16.0;
  static const double spacingXL = 24.0;
  static const double spacing2XL = 32.0;

  static BoxDecoration accessibleButtonDecoration(ThemeData theme) {
    return BoxDecoration(
      color: theme.colorScheme.primaryContainer,
      borderRadius: BorderRadius.circular(mediumRadius),
    );
  }
}
