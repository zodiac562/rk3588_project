import 'dart:async';
import 'comm_interface.dart';
import 'comm_protocol.dart';
import '../../../core/constants/hardware_config.dart';
import '../../../core/utils/logger.dart';

class BleCommService implements IHardwareComm {
  String? _deviceId;
  final StreamController<HardwareMessage> _statusController = StreamController<HardwareMessage>.broadcast();

  @override
  Stream<HardwareMessage> get deviceStatusStream => _statusController.stream;

  @override
  Future<bool> connect(String deviceIdOrAddress) async {
    _deviceId = deviceIdOrAddress;
    Logger.info('[BLE] Connecting to: $deviceIdOrAddress');
    // TODO: flutter_blue_plus 连接设备
    //   1. 扫描设备 → 连接 GATT
    //   2. 订阅 characteristic notify → 解析 JSON → _statusController.add()
    await Future.delayed(const Duration(seconds: 1));
    _statusController.add(const HardwareMessage(type: HardwareConfig.statusConnected, payload: {}));
    Logger.info('[BLE] Connected');
    return true;
  }

  @override
  Future<void> disconnect() async {
    Logger.info('[BLE] Disconnecting');
    // TODO: 断开 GATT
    await Future.delayed(const Duration(milliseconds: 300));
    _deviceId = null;
  }

  @override
  Future<bool> initialize() async {
    Logger.info('[BLE] Initializing device...');
    // TODO: 发送初始化指令
    await Future.delayed(const Duration(seconds: 1));
    _statusController.add(HardwareMessage(
      type: HardwareConfig.statusIdle,
      payload: {'message': '设备就绪'},
    ));
    Logger.info('[BLE] Initialized');
    return true;
  }

  @override
  Future<void> startPrint() async {
    Logger.info('[BLE] Start print');
    _write(CmdStartPrint().toJson());
  }

  @override
  Future<void> pausePrint() async {
    Logger.info('[BLE] Pause print');
    _write(CmdPausePrint().toJson());
  }

  @override
  Future<void> stopPrint() async {
    Logger.info('[BLE] Stop print');
    _write(CmdStopPrint().toJson());
  }

  @override
  Future<void> emergencyStop() async {
    Logger.info('[BLE] Emergency stop');
    _write(CmdEmergencyStop().toJson());
  }

  void _write(Map<String, dynamic> message) {
    // TODO: characteristic.write(jsonEncode(message))
    Logger.debug('[BLE] Write → ${message['type']}');
  }
}
