import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

class DetailStatTile extends StatelessWidget {
  const DetailStatTile({
    super.key,
    required this.label,
    required this.value,
    this.footnote,
    this.valueColor,
  });

  final String label;
  final String value;
  final String? footnote;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surfaceSoft.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.label.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            value,
            style: AppTextStyles.title.copyWith(
              color: valueColor ?? AppColors.textPrimary,
            ),
          ),
          if (footnote != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(footnote!, style: AppTextStyles.label),
          ],
        ],
      ),
    );
  }
}
