import 'package:flutter/material.dart';

import '../models/health_enums.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

class ChartPeriodSelector extends StatelessWidget {
  const ChartPeriodSelector({
    super.key,
    required this.selectedPeriod,
    required this.onChanged,
  });

  final ChartPeriod selectedPeriod;
  final ValueChanged<ChartPeriod> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.84),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: ChartPeriod.values.map((period) {
          final selected = period == selectedPeriod;
          return Expanded(
            child: GestureDetector(
              onTap: () => onChanged(period),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                decoration: BoxDecoration(
                  color: selected ? AppColors.surfaceMuted : Colors.transparent,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Text(
                  period.label,
                  textAlign: TextAlign.center,
                  style: AppTextStyles.label.copyWith(
                    color: selected
                        ? AppColors.textPrimary
                        : AppColors.textMuted,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
