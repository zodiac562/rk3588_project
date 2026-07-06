class HardwareConfig {
  // ─── MQTT ─────────────────────────────────────
  static const String mqttBrokerHost = '192.168.xx.xx'; // 待定，按实际填写
  static const int mqttPort = 1883;
  static const int mqttQos = 1; // QoS 等级，可自定义
  static const String mqttClientId = 'bisheng_app';

  // ─── MQTT Topic ───────────────────────────────
  static const String topicAppToDevice = 'bisheng/cmd';
  static const String topicDeviceToApp = 'bisheng/status';

  // ─── BLE (备用) ──────────────────────────────
  static const String bleServiceUuid = '0000ffe0-0000-1000-8000-00805f9b34fb';
  static const String bleCharacteristicUuid = '0000ffe1-0000-1000-8000-00805f9b34fb';

  // ─── 命令类型 (APP → 板子) ─────────────────────
  static const String cmdStartPrint = 'CMD_START_PRINT';
  static const String cmdPausePrint = 'CMD_PAUSE_PRINT';
  static const String cmdStopPrint = 'CMD_STOP_PRINT';
  static const String cmdEmergencyStop = 'CMD_EMERGENCY_STOP';

  // ─── 状态类型 (板子 → APP) ─────────────────────
  static const String statusProgress = 'STATUS_PROGRESS';
  static const String statusError = 'STATUS_ERROR';
  static const String statusIdle = 'STATUS_IDLE';
  static const String statusConnected = 'STATUS_CONNECTED';

  // ─── 超时 ─────────────────────────────────────
  static const int connectionTimeout = 5000;
  static const int commandTimeout = 3000;
}
