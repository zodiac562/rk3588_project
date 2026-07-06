import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/braille_record.dart';
import '../providers/repo_provider.dart';

class RepoListPage extends ConsumerWidget {
  const RepoListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final state = ref.watch(repoProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('存储库'), centerTitle: true),
      body: SafeArea(
        child: Column(children: [
          _searchBar(theme, ref),
          Expanded(child: state.records.isEmpty
            ? _emptyState(theme)
            : ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                itemCount: state.records.length,
                itemBuilder: (_, i) => _recordTile(theme, ref, state.records[i], context),
              ),
          ),
        ]),
      ),
    );
  }

  Widget _searchBar(ThemeData theme, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      child: Semantics(
        label: '搜索盲文记录',
        child: TextField(
          onChanged: (v) => ref.read(repoProvider.notifier).loadRecords(search: v),
          decoration: InputDecoration(
            hintText: '搜索记录...',
            prefixIcon: const Icon(Icons.search_rounded, size: 22),
            filled: true,
            fillColor: theme.colorScheme.surfaceContainerHighest,
            contentPadding: const EdgeInsets.symmetric(vertical: 14),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
          ),
        ),
      ),
    );
  }

  Widget _emptyState(ThemeData theme) {
    return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      Icon(Icons.inventory_2_outlined, size: 64, color: theme.colorScheme.onSurface.withValues(alpha: 0.2)),
      const SizedBox(height: 12),
      Text('暂无记录', style: theme.textTheme.titleMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.4))),
    ]));
  }

  Widget _recordTile(ThemeData theme, WidgetRef ref, BrailleRecord record, BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          onTap: () => context.go('/preview?id=${record.id}'),
          borderRadius: BorderRadius.circular(18),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(children: [
              Container(
                width: 48, height: 48,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  record.sourceType == '现场扫描' ? Icons.document_scanner_rounded : Icons.folder_open_rounded,
                  color: AppColors.primary, size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(record.title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text('${record.sourceType} / ${record.pageCount}页 / ${_timeAgo(record.createdAt)}', style: theme.textTheme.bodySmall),
              ])),
              PopupMenuButton<String>(
                onSelected: (action) {
                  if (action == 'rename') _showRenameDialog(context, ref, record);
                  if (action == 'delete') ref.read(repoProvider.notifier).deleteRecord(record.id);
                },
                itemBuilder: (_) => [
                  const PopupMenuItem(value: 'rename', child: Row(children: [Icon(Icons.edit_rounded, size: 18), SizedBox(width: 8), Text('重命名')])),
                  const PopupMenuItem(value: 'delete', child: Row(children: [Icon(Icons.delete_outline_rounded, size: 18, color: AppColors.error), SizedBox(width: 8), Text('删除', style: TextStyle(color: AppColors.error))])),
                ],
              ),
            ]),
          ),
        ),
      ),
    );
  }

  void _showRenameDialog(BuildContext context, WidgetRef ref, BrailleRecord record) {
    final ctrl = TextEditingController(text: record.title);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: const Text('重命名'),
        content: TextField(controller: ctrl, autofocus: true, decoration: const InputDecoration(hintText: '输入新名称')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () {
              if (ctrl.text.trim().isNotEmpty) {
                ref.read(repoProvider.notifier).renameRecord(record.id, ctrl.text.trim());
              }
              Navigator.pop(ctx);
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }

  String _timeAgo(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
        '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
