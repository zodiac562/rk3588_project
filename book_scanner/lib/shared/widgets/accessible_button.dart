import 'package:flutter/material.dart';

class AccessibleButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final Color? color;
  final Color? textColor;
  final bool outlined;
  final bool fullWidth;
  final double? height;

  const AccessibleButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.color,
    this.textColor,
    this.outlined = false,
    this.fullWidth = false,
    this.height,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bgColor = color ?? theme.colorScheme.primary;
    final fgColor = textColor ?? (outlined ? bgColor : Colors.white);

    if (outlined) {
      return Semantics(
        button: true,
        label: label,
        child: SizedBox(
          width: fullWidth ? double.infinity : null,
          height: height ?? 56,
          child: OutlinedButton.icon(
            onPressed: onPressed,
            icon: icon != null ? Icon(icon, size: 22) : const SizedBox.shrink(),
            label: Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            style: OutlinedButton.styleFrom(
              foregroundColor: fgColor,
              side: BorderSide(color: bgColor, width: 2),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
        ),
      );
    }

    return Semantics(
      button: true,
      label: label,
      child: SizedBox(
        width: fullWidth ? double.infinity : null,
        height: height ?? 56,
        child: ElevatedButton.icon(
          onPressed: onPressed,
          icon: icon != null ? Icon(icon, size: 22) : const SizedBox.shrink(),
          label: Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          style: ElevatedButton.styleFrom(
            backgroundColor: bgColor,
            foregroundColor: fgColor,
            elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
        ),
      ),
    );
  }
}
