import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/constants/app_enums.dart';
import '../../../../core/providers/device_provider.dart';
import '../../../../shared/widgets/accessible_button.dart';
import '../../../../core/utils/permission_helper.dart';

class DeviceManagePage extends ConsumerStatefulWidget {
  const DeviceManagePage({super.key});

  @override
  ConsumerState<DeviceManagePage> createState() => _DeviceManagePageState();
}

class _DeviceManagePageState extends ConsumerState<DeviceManagePage> {
  bool _useWifi = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final deviceState = ref.watch(deviceProvider);
    final isConnected = deviceState.status == DeviceStatus.connected || deviceState.status == DeviceStatus.working || deviceState.status == DeviceStatus.printing;

    return Scaffold(
      appBar: AppBar(title: const Text('设备管理'), centerTitle: true),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _connectionStatus(theme, deviceState, isConnected),
            const SizedBox(height: 24),
            _modeSwitch(theme),
            const SizedBox(height: 20),
            if (isConnected) ...[
              AccessibleButton(label: '断开连接', icon: Icons.link_off_rounded, onPressed: () => ref.read(deviceProvider.notifier).disconnect(), color: AppColors.error, fullWidth: true),
            ] else ...[
              AccessibleButton(label: _useWifi ? '连接 Wi-Fi 设备' : '扫描蓝牙设备', icon: _useWifi ? Icons.wifi_rounded : Icons.bluetooth_rounded, onPressed: _handleConnect, fullWidth: true),
            ],
            const SizedBox(height: 32),
          ]),
        ),
      ),
    );
  }

  Widget _connectionStatus(ThemeData theme, DeviceState deviceState, bool isConnected) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 500),
          width: 80, height: 80,
          decoration: BoxDecoration(
            color: isConnected ? AppColors.success.withValues(alpha: 0.12) : theme.colorScheme.onSurface.withValues(alpha: 0.06),
            shape: BoxShape.circle,
          ),
          child: Icon(
            isConnected ? Icons.bluetooth_connected_rounded : Icons.bluetooth_disabled_rounded,
            size: 40, color: isConnected ? AppColors.success : theme.colorScheme.onSurface.withValues(alpha: 0.3),
          ),
        ),
        const SizedBox(height: 16),
        Text(isConnected ? '已连接' : '未连接', style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        Text(
          isConnected ? (deviceState.connectedDeviceId ?? '') : '点击下方按钮搜索设备',
          style: theme.textTheme.bodyMedium,
        ),
      ]),
    );
  }

  Widget _modeSwitch(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(color: theme.colorScheme.surfaceContainerHighest, borderRadius: BorderRadius.circular(18)),
      child: Row(children: [
        Expanded(child: _modeOption(theme, '蓝牙', Icons.bluetooth_rounded, !_useWifi, () => setState(() => _useWifi = false))),
        Expanded(child: _modeOption(theme, 'Wi-Fi', Icons.wifi_rounded, _useWifi, () => setState(() => _useWifi = true))),
      ]),
    );
  }

  Widget _modeOption(ThemeData theme, String label, IconData icon, bool selected, VoidCallback onTap) {
    return Semantics(
      button: true, label: label,
      child: GestureDetector(
        onTap: onTap,
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

  void _handleConnect() async {
    await PermissionHelper.requestAllForHardware();
    if (mounted) {
      final deviceId = _useWifi ? '192.168.1.100' : 'ELF2-BLE-001';
      ref.read(deviceProvider.notifier).connect(deviceId, useWifi: _useWifi);
    }
  }
}
