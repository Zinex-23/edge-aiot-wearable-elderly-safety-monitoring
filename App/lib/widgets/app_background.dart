import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class AppBackground extends StatelessWidget {
  const AppBackground({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final gradientColors = AppColors.isLight
        ? const [Color(0xFFF8FAFD), Color(0xFFF1F7FF), Color(0xFFFFFFFF)]
        : const [Color(0xFF07090D), Color(0xFF0A1018), Color(0xFF0A0D12)];

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: gradientColors,
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: -90,
            right: -40,
            child: _GlowOrb(
              size: 220,
              color: AppColors.accent.withValues(
                alpha: AppColors.isLight ? 0.14 : 0.18,
              ),
            ),
          ),
          Positioned(
            top: 280,
            left: -120,
            child: _GlowOrb(
              size: 240,
              color: AppColors.accentSecondary.withValues(
                alpha: AppColors.isLight ? 0.10 : 0.10,
              ),
            ),
          ),
          Positioned(
            bottom: -140,
            right: -120,
            child: _GlowOrb(
              size: 280,
              color: AppColors.danger.withValues(
                alpha: AppColors.isLight ? 0.06 : 0.08,
              ),
            ),
          ),
          child,
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(colors: [color, color.withValues(alpha: 0)]),
        ),
      ),
    );
  }
}
