import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../data/models/braille_record.dart';
import '../../../../shared/widgets/accessible_button.dart';
import '../providers/repo_provider.dart';

class PreviewPage extends ConsumerStatefulWidget {
  final String recordId;

  const PreviewPage({super.key, required this.recordId});

  @override
  ConsumerState<PreviewPage> createState() => _PreviewPageState();
}

class _PreviewPageState extends ConsumerState<PreviewPage> {
  BrailleRecord? _record;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final record = await ref.read(repoProvider.notifier).getRecord(widget.recordId);
    if (mounted) {
      setState(() {
        _record = record;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: const Text('预览')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_record == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('预览')),
        body: const Center(child: Text('记录不存在')),
      );
    }

    final record = _record!;

    return Scaffold(
      appBar: AppBar(title: Text(record.title), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _infoCard(theme, record),
            const SizedBox(height: 20),
            if (record.textContent != null && record.textContent!.isNotEmpty) ...[
              Text('文字内容', style: theme.textTheme.titleMedium),
              const SizedBox(height: 12),
              _textContentCard(theme, record.textContent!),
              const SizedBox(height: 24),
            ],
            AccessibleButton(
              label: '直接打印',
              icon: Icons.print_rounded,
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: const Text('已发送打印指令'), behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                );
              },
              fullWidth: true,
            ),
            const SizedBox(height: 32),
          ]),
        ),
      ),
    );
  }

  Widget _infoCard(ThemeData theme, BrailleRecord record) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(record.title, style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Row(children: [
          _infoChip(theme, Icons.source_rounded, record.sourceType),
          const SizedBox(width: 10),
          _infoChip(theme, Icons.grid_on_rounded, '${record.dotMatrixWidth}x${record.dotMatrixHeight}'),
          const SizedBox(width: 10),
          _infoChip(theme, Icons.pages_rounded, '${record.pageCount}页'),
        ]),
      ]),
    );
  }

  Widget _infoChip(ThemeData theme, IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: theme.colorScheme.primary),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 12, color: theme.colorScheme.primary, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  Widget _textContentCard(ThemeData theme, String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        text,
        style: theme.textTheme.bodyMedium?.copyWith(height: 1.8, letterSpacing: 1),
      ),
    );
  }
}
