import 'package:flutter/material.dart';
import '../../../../core/constants/app_enums.dart';

class PrintProgressWidget extends StatelessWidget {
  final PrintStep step;
  final double progress;

  const PrintProgressWidget({super.key, required this.step, required this.progress});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(children: [
        _stepRow(theme, PrintStep.turningPage, '翻页中', Icons.auto_stories_rounded),
        const SizedBox(height: 8),
        _stepRow(theme, PrintStep.capturing, '拍照中', Icons.camera_alt_rounded),
        const SizedBox(height: 8),
        _stepRow(theme, PrintStep.recognizing, 'OCR 识别', Icons.text_snippet_rounded),
        const SizedBox(height: 8),
        _stepRow(theme, PrintStep.converting, '盲文转换', Icons.transform_rounded),
        const SizedBox(height: 8),
        _stepRow(theme, PrintStep.printing, '打印中', Icons.print_rounded),
        const SizedBox(height: 14),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: progress,
            minHeight: 8,
            backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.15),
            valueColor: AlwaysStoppedAnimation<Color>(theme.colorScheme.primary),
          ),
        ),
        const SizedBox(height: 8),
        Text('${(progress * 100).toInt()}%', style: theme.textTheme.bodySmall),
      ]),
    );
  }

  Widget _stepRow(ThemeData theme, PrintStep checkStep, String label, IconData icon) {
    final bool done = step.index > checkStep.index;
    final bool active = step == checkStep;

    return Semantics(
      label: '$label${done ? " 已完成" : active ? " 进行中" : " 等待中"}',
      child: Row(children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          width: 24, height: 24,
          decoration: BoxDecoration(
            color: done ? theme.colorScheme.primary : (active ? theme.colorScheme.primary.withValues(alpha: 0.2) : Colors.transparent),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: done || active ? theme.colorScheme.primary : theme.colorScheme.outline.withValues(alpha: 0.3), width: 2),
          ),
          child: done ? const Icon(Icons.check_rounded, size: 16, color: Colors.white) : (active ? Icon(icon, size: 14, color: theme.colorScheme.primary) : null),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(label, style: TextStyle(fontSize: 14, fontWeight: active ? FontWeight.w700 : FontWeight.w500, color: done ? theme.colorScheme.primary : (active ? theme.colorScheme.onSurface : theme.colorScheme.onSurface.withValues(alpha: 0.4))))),
      ]),
    );
  }
}
