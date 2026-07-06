import 'dart:async';
import 'comm_interface.dart';
import 'comm_protocol.dart';
import '../../../core/constants/hardware_config.dart';
import '../../../core/utils/logger.dart';

class MqttCommService implements IHardwareComm {
  bool _connected = false;
  final StreamController<HardwareMessage> _statusController = StreamController<HardwareMessage>.broadcast();

  @override
  Stream<HardwareMessage> get deviceStatusStream => _statusController.stream;

  @override
  Future<bool> connect(String brokerAddress) async {
    Logger.info('[MQTT] Connecting to $brokerAddress:${HardwareConfig.mqttPort}');
    // TODO: 接入 mqtt_client 库，建立 MQTT 连接
    //   1. MqttServerClient.withPort(brokerAddress, clientId, port)
    //   2. 连接成功后订阅 HardwareConfig.topicDeviceToApp
    //   3. 收到消息后解析为 HardwareMessage 写入 _statusController
    await Future.delayed(const Duration(milliseconds: 500));
    _connected = true;
    _statusController.add(const HardwareMessage(type: HardwareConfig.statusConnected, payload: {}));
    Logger.info('[MQTT] Connected');
    return true;
  }

  @override
  Future<void> disconnect() async {
    Logger.info('[MQTT] Disconnecting');
    // TODO: client.disconnect()
    _connected = false;
  }

  @override
  Future<bool> initialize() async {
    Logger.info('[MQTT] Initializing device...');
    // TODO: 发送初始化指令，等待响应
    await Future.delayed(const Duration(seconds: 1));
    _statusController.add(HardwareMessage(
      type: HardwareConfig.statusIdle,
      payload: {'message': '设备就绪'},
    ));
    Logger.info('[MQTT] Initialized');
    return true;
  }

  @override
  Future<void> startPrint() async {
    Logger.info('[MQTT] Start print');
    _publish(CmdStartPrint().toJson());
  }

  @override
  Future<void> pausePrint() async {
    Logger.info('[MQTT] Pause print');
    _publish(CmdPausePrint().toJson());
  }

  @override
  Future<void> stopPrint() async {
    Logger.info('[MQTT] Stop print');
    _publish(CmdStopPrint().toJson());
  }

  @override
  Future<void> emergencyStop() async {
    Logger.info('[MQTT] Emergency stop');
    _publish(CmdEmergencyStop().toJson());
  }

  void _publish(Map<String, dynamic> message) {
    if (!_connected) return;
    // TODO: 通过 MQTT publish 发送消息到 HardwareConfig.topicAppToDevice
    // client.publishMessage(topic, MqttQos.atLeastOnce, builder.payload)
    Logger.debug('[MQTT] Publish → ${message['type']}');
  }
}
