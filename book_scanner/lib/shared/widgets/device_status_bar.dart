import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers/device_provider.dart';
import '../../core/constants/app_enums.dart';

class DeviceStatusBar extends ConsumerWidget {
  const DeviceStatusBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final deviceState = ref.watch(deviceProvider);
    final theme = Theme.of(context);

    final Color statusColor;
    final IconData statusIcon;
    final String label;

    switch (deviceState.status) {
      case DeviceStatus.connected:
        statusColor = theme.colorScheme.tertiary;
        statusIcon = Icons.bluetooth_connected_rounded;
        label = '已连接';
        break;
      case DeviceStatus.connecting:
        statusColor = Colors.orange;
        statusIcon = Icons.sync_rounded;
        label = '连接中...';
        break;
      case DeviceStatus.initializing:
        statusColor = Colors.orange;
        statusIcon = Icons.settings_rounded;
        label = '初始化中';
        break;
      case DeviceStatus.initialized:
        statusColor = theme.colorScheme.primary;
        statusIcon = Icons.check_circle_rounded;
        label = '已就绪';
        break;
      case DeviceStatus.working:
        statusColor = theme.colorScheme.tertiary;
        statusIcon = Icons.camera_alt_rounded;
        label = '工作中';
        break;
      case DeviceStatus.printing:
        statusColor = theme.colorScheme.secondary;
        statusIcon = Icons.print_rounded;
        label = '打印中';
        break;
      case DeviceStatus.paused:
        statusColor = Colors.orange;
        statusIcon = Icons.pause_circle_rounded;
        label = '已暂停';
        break;
      case DeviceStatus.stopped:
        statusColor = Colors.red;
        statusIcon = Icons.stop_circle_rounded;
        label = '已停止';
        break;
      case DeviceStatus.error:
        statusColor = theme.colorScheme.error;
        statusIcon = Icons.error_outline_rounded;
        label = '故障';
        break;
      case DeviceStatus.disconnected:
        statusColor = theme.colorScheme.onSurface.withValues(alpha: 0.4);
        statusIcon = Icons.bluetooth_disabled_rounded;
        label = '未连接';
        break;
    }

    return Semantics(
      label: '设备状态: $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: statusColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: statusColor.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: statusColor,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: statusColor.withValues(alpha: 0.5),
                    blurRadius: 6,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Icon(statusIcon, size: 18, color: statusColor),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: statusColor,
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
