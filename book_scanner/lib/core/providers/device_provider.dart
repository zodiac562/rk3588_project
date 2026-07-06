import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants/app_enums.dart';
import '../../data/services/api_client.dart';
import '../../data/hardware/comm_protocol.dart';

class DeviceState {
  final DeviceStatus status;
  final String statusMessage;
  final PrintStep currentStep;
  final String? connectedDeviceId;
  final bool useWifi;
  final int progressCurrent;
  final int progressTotal;
  final double progressPercentage;

  const DeviceState({
    this.status = DeviceStatus.connected,
    this.statusMessage = '已连接',
    this.currentStep = PrintStep.idle,
    this.connectedDeviceId = 'ELF2-BSG-001',
    this.useWifi = false,
    this.progressCurrent = 0,
    this.progressTotal = 0,
    this.progressPercentage = 0,
  });

  DeviceState copyWith({
    DeviceStatus? status,
    String? statusMessage,
    PrintStep? currentStep,
    String? connectedDeviceId,
    bool? useWifi,
    int? progressCurrent,
    int? progressTotal,
    double? progressPercentage,
  }) {
    return DeviceState(
      status: status ?? this.status,
      statusMessage: statusMessage ?? this.statusMessage,
      currentStep: currentStep ?? this.currentStep,
      connectedDeviceId: connectedDeviceId ?? this.connectedDeviceId,
      useWifi: useWifi ?? this.useWifi,
      progressCurrent: progressCurrent ?? this.progressCurrent,
      progressTotal: progressTotal ?? this.progressTotal,
      progressPercentage: progressPercentage ?? this.progressPercentage,
    );
  }

  DeviceState applyProgress(StatusProgress p) {
    return copyWith(
      progressCurrent: p.current,
      progressTotal: p.total,
      progressPercentage: p.percentage,
      currentStep: PrintStep.printing,
      status: DeviceStatus.printing,
      statusMessage: '${p.current}/${p.total}',
    );
  }
}

class DeviceNotifier extends StateNotifier<DeviceState> {
  final ApiClient _api = ApiClient();
  StreamSubscription<HardwareMessage>? _statusSub;

  DeviceNotifier() : super(const DeviceState());

  void bindStatusStream(Stream<HardwareMessage> stream) {
    _statusSub?.cancel();
    _statusSub = stream.listen((msg) {
      switch (msg.type) {
        case StatusProgress.type:
          final p = StatusProgress.fromPayload(msg.payload);
          state = state.applyProgress(p);
        case StatusError.type:
          final e = StatusError.fromPayload(msg.payload);
          state = state.copyWith(
            status: DeviceStatus.error,
            statusMessage: '${e.code}: ${e.msg}',
          );
        default:
      }
    });
  }

  Future<void> connect(String deviceId, {bool useWifi = false}) async {
    state = state.copyWith(status: DeviceStatus.connecting, statusMessage: '连接中...');
    try {
      await _api.connectDevice(deviceId, useWifi: useWifi);
      state = state.copyWith(
        status: DeviceStatus.connected,
        statusMessage: '已连接',
        connectedDeviceId: deviceId,
        useWifi: useWifi,
      );
    } catch (e) {
      state = state.copyWith(status: DeviceStatus.error, statusMessage: '连接失败');
    }
  }

  Future<void> disconnect() async {
    try {
      await _api.disconnectDevice();
    } catch (_) {}
    _statusSub?.cancel();
    state = const DeviceState();
  }

  Future<void> initialize() async {
    state = state.copyWith(status: DeviceStatus.initializing, statusMessage: '正在初始化设备...');
    try {
      final res = await _api.initializeDevice();
      if (res['success'] == true) {
        state = state.copyWith(status: DeviceStatus.initialized, statusMessage: '设备就绪，可以开始打印');
      } else {
        state = state.copyWith(status: DeviceStatus.error, statusMessage: '初始化失败');
      }
    } catch (e) {
      state = state.copyWith(status: DeviceStatus.error, statusMessage: '初始化失败，请检查网络');
    }
  }

  Future<void> startPrintJob() async {
    try {
      await _api.startPrint();
    } catch (_) {}
    state = state.copyWith(
      status: DeviceStatus.working,
      currentStep: PrintStep.turningPage,
      progressCurrent: 0,
      progressTotal: 0,
      progressPercentage: 0,
    );
  }

  Future<void> pausePrint() async {
    state = state.copyWith(status: DeviceStatus.paused, currentStep: PrintStep.paused, statusMessage: '已暂停');
  }

  Future<void> resumePrint() async {
    state = state.copyWith(status: DeviceStatus.printing, currentStep: PrintStep.printing, statusMessage: '打印中...');
  }

  Future<void> emergencyStop() async {
    try {
      await _api.stopPrint();
    } catch (_) {}
    state = state.copyWith(status: DeviceStatus.connected, currentStep: PrintStep.stopped, statusMessage: '已终止');
  }

  void setSimulatedStep(PrintStep step) {
    state = state.copyWith(currentStep: step);
  }

  void simulatePaperDone() {
    state = state.copyWith(status: DeviceStatus.connected, currentStep: PrintStep.completed, statusMessage: '请更换盲文纸');
  }

  Future<void> confirmPaperReady() async {
    try {
      await _api.paperReady();
    } catch (_) {}
    state = state.copyWith(status: DeviceStatus.working, currentStep: PrintStep.printing, statusMessage: '打印中...');
  }

  @override
  void dispose() {
    _statusSub?.cancel();
    super.dispose();
  }
}

final deviceProvider = StateNotifierProvider<DeviceNotifier, DeviceState>((ref) {
  return DeviceNotifier();
});
