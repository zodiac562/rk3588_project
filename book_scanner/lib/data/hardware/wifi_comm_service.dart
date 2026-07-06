import 'dart:async';
import 'comm_interface.dart';
import 'comm_protocol.dart';
import '../../../core/constants/hardware_config.dart';
import '../../../core/utils/logger.dart';

class WifiCommService implements IHardwareComm {
  String? _ip;
  final StreamController<HardwareMessage> _statusController = StreamController<HardwareMessage>.broadcast();

  @override
  Stream<HardwareMessage> get deviceStatusStream => _statusController.stream;

  @override
  Future<bool> connect(String deviceIdOrIp) async {
    _ip = deviceIdOrIp;
    Logger.info('[WiFi] Connecting to: $deviceIdOrIp');
    // TODO: Socket.connect(ip, port), 启动 listen 接收数据
    //   收到数据后解析 JSON → HardwareMessage → _statusController.add()
    await Future.delayed(const Duration(seconds: 1));
    _statusController.add(const HardwareMessage(type: HardwareConfig.statusConnected, payload: {}));
    Logger.info('[WiFi] Connected');
    return true;
  }

  @override
  Future<void> disconnect() async {
    Logger.info('[WiFi] Disconnecting');
    // TODO: socket.close()
    await Future.delayed(const Duration(milliseconds: 300));
    _ip = null;
  }

  @override
  Future<bool> initialize() async {
    Logger.info('[WiFi] Initializing device...');
    await Future.delayed(const Duration(seconds: 1));
    _statusController.add(HardwareMessage(
      type: HardwareConfig.statusIdle,
      payload: {'message': '设备就绪'},
    ));
    Logger.info('[WiFi] Initialized');
    return true;
  }

  @override
  Future<void> startPrint() async {
    Logger.info('[WiFi] Start print');
    _send(CmdStartPrint().toJson());
  }

  @override
  Future<void> pausePrint() async {
    Logger.info('[WiFi] Pause print');
    _send(CmdPausePrint().toJson());
  }

  @override
  Future<void> stopPrint() async {
    Logger.info('[WiFi] Stop print');
    _send(CmdStopPrint().toJson());
  }

  @override
  Future<void> emergencyStop() async {
    Logger.info('[WiFi] Emergency stop');
    _send(CmdEmergencyStop().toJson());
  }

  void _send(Map<String, dynamic> message) {
    // TODO: socket.write(jsonEncode(message))
    Logger.debug('[WiFi] Send → ${message['type']}');
  }
}
