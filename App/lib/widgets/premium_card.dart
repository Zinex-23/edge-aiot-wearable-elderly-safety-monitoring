import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';

class PremiumCard extends StatelessWidget {
  const PremiumCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
    this.onTap,
    this.gradient,
    this.backgroundColor,
    this.radius = 28,
  });

  final Widget child;
  final EdgeInsets padding;
  final VoidCallback? onTap;
  final Gradient? gradient;
  final Color? backgroundColor;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final decoration = BoxDecoration(
      color: backgroundColor ?? AppColors.surface.withValues(alpha: 0.88),
      gradient: gradient,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: AppColors.border.withValues(alpha: 0.85)),
      boxShadow: [
        BoxShadow(
          color: AppColors.shadow,
          blurRadius: 28,
          offset: Offset(0, 18),
        ),
      ],
    );

    final card = Ink(
      decoration: decoration,
      child: Padding(padding: padding, child: child),
    );

    if (onTap == null) {
      return card;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radius),
        child: card,
      ),
    );
  }
}
