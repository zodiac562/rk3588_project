import 'dart:async';
import 'comm_interface.dart';
import 'comm_protocol.dart';
import 'mqtt_comm_service.dart';
import 'ble_comm_service.dart';
import 'wifi_comm_service.dart';
import '../../../core/utils/logger.dart';

enum CommMode { mqtt, ble, wifi }

class HardwareManager {
  static final HardwareManager _instance = HardwareManager._();
  factory HardwareManager() => _instance;
  HardwareManager._();

  IHardwareComm? _currentComm;
  CommMode _mode = CommMode.mqtt;

  IHardwareComm? get currentComm => _currentComm;
  CommMode get mode => _mode;
  Stream<HardwareMessage>? get deviceStatusStream => _currentComm?.deviceStatusStream;

  void switchMode(CommMode mode) {
    if (_mode == mode && _currentComm != null) return;
    _mode = mode;
    _currentComm?.disconnect();
    switch (mode) {
      case CommMode.mqtt:
        _currentComm = MqttCommService();
      case CommMode.ble:
        _currentComm = BleCommService();
      case CommMode.wifi:
        _currentComm = WifiCommService();
    }
    Logger.info('[HardwareManager] Switched to ${mode.name} mode');
  }

  Future<void> initialize() async {
    await _currentComm?.initialize();
  }

  Future<bool> connect(String deviceIdOrAddress) async {
    switchMode(_mode);
    return await _currentComm!.connect(deviceIdOrAddress);
  }

  Future<void> disconnect() async {
    await _currentComm?.disconnect();
    _currentComm = null;
  }

  Future<void> startPrint() async {
    await _currentComm?.startPrint();
  }

  Future<void> pausePrint() async {
    await _currentComm?.pausePrint();
  }

  Future<void> stopPrint() async {
    await _currentComm?.stopPrint();
  }

  Future<void> emergencyStop() async {
    await _currentComm?.emergencyStop();
  }
}
