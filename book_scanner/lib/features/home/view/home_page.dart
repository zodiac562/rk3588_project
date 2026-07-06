import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/constants/app_enums.dart';
import '../../../../core/providers/device_provider.dart';
import '../../../../shared/widgets/device_status_bar.dart';
import '../../../../data/local_db/database_helper.dart';
import '../../../../data/models/braille_record.dart';
import '../providers/home_provider.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final ScrollController _logScrollCtrl = ScrollController();

  @override
  void dispose() {
    _logScrollCtrl.dispose();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final homeState = ref.watch(homeProvider);
    final deviceState = ref.watch(deviceProvider);
    final isInitializing = homeState.isInitializing;
    final isWorking = homeState.isWorking;

    ref.listen(homeProvider.select((s) => s.logs.length), (_, __) {
      _scrollToBottom();
    });

    ref.listen(homeProvider.select((s) => s.showReadyDialog), (_, show) {
      if (show) _showReadyDialog();
    });

    ref.listen(homeProvider.select((s) => s.showPaperDialog), (_, show) {
      if (show) _showPaperDialog();
    });

    return Scaffold(
      appBar: AppBar(
        title: const Text('毕昇微光'),
        centerTitle: true,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: DeviceStatusBar(),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.all(24),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                _greeting(theme),
                const SizedBox(height: 24),
                _modeSelector(theme, homeState, isWorking || isInitializing),
                if (homeState.selectedMode == PrintMode.localFile && !isWorking && !isInitializing) ...[
                  const SizedBox(height: 16),
                  _filePicker(theme, homeState),
                ],
                const SizedBox(height: 24),
                if (isInitializing) _initLoadingCard(theme),
                if (isWorking || homeState.currentStep != PrintStep.idle) ...[
                  const SizedBox(height: 12),
                ],
                if (!isInitializing) _actionArea(theme, homeState),
                const SizedBox(height: 32),
              ]),
            ),
          ),
          if (isWorking || homeState.currentStep != PrintStep.idle)
            _logPanel(theme, homeState),
        ]),
      ),
    );
  }

  Widget _greeting(ThemeData theme) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('下午好', style: theme.textTheme.bodyLarge?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5))),
      const SizedBox(height: 4),
      Text('今天想打印什么？', style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
    ]);
  }

  Widget _modeSelector(ThemeData theme, HomeState homeState, bool disabled) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(children: [
        Expanded(child: _modeTab(theme, homeState, '现场扫描', Icons.document_scanner_rounded, PrintMode.scanAndPrint, disabled)),
        Expanded(child: _modeTab(theme, homeState, '本地文件', Icons.folder_open_rounded, PrintMode.localFile, disabled)),
      ]),
    );
  }

  Widget _modeTab(ThemeData theme, HomeState state, String label, IconData icon, PrintMode mode, bool disabled) {
    final selected = state.selectedMode == mode;
    return Semantics(
      button: true, label: label,
      child: GestureDetector(
        onTap: disabled ? null : () => ref.read(homeProvider.notifier).setMode(mode),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: selected ? theme.colorScheme.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(icon, size: 20, color: selected ? Colors.white : theme.colorScheme.onSurface.withValues(alpha: 0.5)),
            const SizedBox(width: 8),
            Text(label, style: TextStyle(color: selected ? Colors.white : theme.colorScheme.onSurface.withValues(alpha: 0.5), fontWeight: FontWeight.w700, fontSize: 14)),
          ]),
        ),
      ),
    );
  }

  Widget _filePicker(ThemeData theme, HomeState homeState) {
    final selected = homeState.selectedRecord;
    if (selected != null) {
      return _selectedFileCard(theme, selected);
    }
    final records = DatabaseHelper().getRecords(orderByDate: true);
    if (records.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          Icon(Icons.inbox_rounded, color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
          const SizedBox(width: 12),
          Text('存储库中暂无文件', style: TextStyle(color: theme.colorScheme.onSurface.withValues(alpha: 0.5))),
        ]),
      );
    }
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text('选择存储库文件', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
        ),
        ...records.map((r) {
          final timeStr = '${r.createdAt.year}-${r.createdAt.month.toString().padLeft(2, '0')}-${r.createdAt.day.toString().padLeft(2, '0')} '
              '${r.createdAt.hour.toString().padLeft(2, '0')}:${r.createdAt.minute.toString().padLeft(2, '0')}';
          return Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () => ref.read(homeProvider.notifier).selectRecord(r),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Row(children: [
                    Icon(r.sourceType == '现场扫描' ? Icons.document_scanner_rounded : Icons.description_rounded, size: 20, color: theme.colorScheme.primary),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(r.title, style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600), maxLines: 1, overflow: TextOverflow.ellipsis),
                        Text('$timeStr · ${r.pageCount}面 · ${r.sourceType}', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5))),
                      ]),
                    ),
                  ]),
                ),
              ),
            ),
          );
        }),
      ]),
    );
  }

  Widget _selectedFileCard(ThemeData theme, BrailleRecord record) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.3)),
      ),
      child: Row(children: [
        Container(
          width: 40, height: 40,
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(Icons.description_rounded, color: theme.colorScheme.primary, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(record.title, style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700), maxLines: 1, overflow: TextOverflow.ellipsis),
            Text('${record.pageCount}面 · ${record.sourceType}', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5))),
          ]),
        ),
        IconButton(
          icon: const Icon(Icons.close_rounded, size: 18),
          onPressed: () => ref.read(homeProvider.notifier).selectRecord(null),
        ),
      ]),
    );
  }

  Widget _initLoadingCard(ThemeData theme) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.15)),
      ),
      child: Column(children: [
        SizedBox(
          width: 28, height: 28,
          child: CircularProgressIndicator(strokeWidth: 2.5, valueColor: AlwaysStoppedAnimation<Color>(theme.colorScheme.primary)),
        ),
        const SizedBox(height: 16),
        Text('正在准备机器...', style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Text('扫描头校准、纸张检测、机械臂归零', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.5))),
      ]),
    );
  }

  Widget _actionArea(ThemeData theme, HomeState homeState) {
    final canStart = homeState.selectedMode == PrintMode.scanAndPrint || homeState.selectedRecord != null;
    return Column(children: [
      SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: canStart ? () => ref.read(homeProvider.notifier).startWorking() : null,
          icon: const Icon(Icons.play_arrow_rounded, size: 20),
          label: const Text('开始工作', style: TextStyle(fontWeight: FontWeight.w600)),
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
      ),
    ]);
  }

  void _scrollToBottom() {
    if (_logScrollCtrl.hasClients) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _logScrollCtrl.animateTo(
          _logScrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      });
    }
  }

  Widget _logPanel(ThemeData theme, HomeState state) {
    final logs = state.logs;
    if (logs.isEmpty) return const SizedBox.shrink();

    return Container(
      height: 220,
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        border: Border(top: BorderSide(color: theme.colorScheme.primary.withValues(alpha: 0.2))),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          color: Colors.black26,
          child: Row(children: [
            const Icon(Icons.terminal_rounded, size: 14, color: Colors.greenAccent),
            const SizedBox(width: 8),
            Text('系统日志', style: TextStyle(color: Colors.greenAccent, fontSize: 12, fontWeight: FontWeight.w600, fontFamily: 'monospace')),
            const Spacer(),
            if (state.isWorking) ...[
              SizedBox(width: 8, height: 8, child: CircularProgressIndicator(strokeWidth: 1.5, valueColor: const AlwaysStoppedAnimation<Color>(Colors.greenAccent))),
            ] else ...[
              Container(width: 8, height: 8, decoration: const BoxDecoration(color: Colors.greenAccent, shape: BoxShape.circle)),
            ],
          ]),
        ),
        Expanded(
          child: ListView.builder(
            controller: _logScrollCtrl,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            itemCount: logs.length,
            itemBuilder: (_, i) {
              final log = logs[i];
              final isHeader = log.startsWith('---') && log.endsWith('---');
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text(
                  log,
                  style: TextStyle(
                    fontSize: 11,
                    fontFamily: 'monospace',
                    color: isHeader ? Colors.yellowAccent : Colors.greenAccent.withValues(alpha: 0.75),
                    fontWeight: isHeader ? FontWeight.w700 : FontWeight.w400,
                  ),
                ),
              );
            },
          ),
        ),
      ]),
    );
  }

  void _showReadyDialog() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          icon: Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(Icons.check_circle_outline_rounded, color: AppColors.primary, size: 36),
          ),
          title: const Text('机器已准备完毕', style: TextStyle(fontWeight: FontWeight.w800), textAlign: TextAlign.center),
          content: const Text('请放入纸张后点击确定开始打印', textAlign: TextAlign.center, style: TextStyle(fontSize: 15)),
          actions: [
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  ref.read(homeProvider.notifier).confirmReady();
                  ref.read(deviceProvider.notifier).startPrintJob();
                },
                icon: const Icon(Icons.print_rounded),
                label: const Text('确定开始打印'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
              ),
            ),
          ],
        ),
      );
    });
  }

  void _showPaperDialog() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(homeProvider.notifier).dismissPaperDialog();
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          icon: Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Icon(Icons.note_add_rounded, color: AppColors.primary, size: 32),
          ),
          title: const Text('打印完成', style: TextStyle(fontWeight: FontWeight.w800), textAlign: TextAlign.center),
          content: const Text('当前任务已完成\n已保存至存储库', textAlign: TextAlign.center, style: TextStyle(fontSize: 15)),
          actions: [
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  ref.read(homeProvider.notifier).confirmPaperReady();
                },
                icon: const Icon(Icons.check_rounded),
                label: const Text('确定'),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
              ),
            ),
          ],
        ),
      );
    });
  }
}
