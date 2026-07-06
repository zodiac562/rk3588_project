# 板端硬件通信接口对接文档 (v2.0 — MQTT 协议)

## 通信架构

```
硬件 (elf2 主控板)
  │ MQTT (TCP 1883)
  │ JSON {"type":"CMD_XXX","payload":{...}}
  ▼
IHardwareComm (抽象接口)
  ├── MqttCommService  ← 主通道，待接入 mqtt_client 库
  ├── BleCommService   ← BLE 备用
  └── WifiCommService  ← WiFi 备用
  │
  ▼
HardwareManager (单例，管理模式切换)
  │
  ▼
DeviceNotifier (状态管理)
  │
  ▼
UI (HomePage / ControlPanel)
```

## MQTT 配置

文件: `lib/core/constants/hardware_config.dart`

```dart
static const String mqttBrokerHost = '192.168.xx.xx'; // 待定
static const int mqttPort = 1883;
static const int mqttQos = 1;
static const String mqttClientId = 'bisheng_app';

static const String topicAppToDevice = 'bisheng/cmd';
static const String topicDeviceToApp = 'bisheng/status';
```

## 消息格式

所有通信使用 JSON 字符串，结构固定为：

```json
{"type": "CMD_XXX", "payload": {...}}
```

模型定义: `lib/data/hardware/comm_protocol.dart`

### 下行命令 (APP → 硬件)

| type | payload | 说明 |
|------|---------|------|
| `CMD_START_PRINT` | `{}` | 开始打印 |
| `CMD_PAUSE_PRINT` | `{}` | 暂停打印 |
| `CMD_STOP_PRINT` | `{}` | 停止打印 |
| `CMD_EMERGENCY_STOP` | `{}` | 紧急停止 |

### 上行状态 (硬件 → APP)

| type | payload | 说明 |
|------|---------|------|
| `STATUS_PROGRESS` | `{"current":15, "total":100, "percentage":15.0}` | 打印进度 |
| `STATUS_ERROR` | `{"code":"MOTOR_FAULT", "msg":"X1 轴电机通信超时"}` | 错误信息 |
| `STATUS_IDLE` | `{"message":"设备就绪"}` | 空闲待机 |
| `STATUS_CONNECTED` | `{}` | 连接成功 |

## 接口定义

文件: `lib/data/hardware/comm_interface.dart`

```dart
abstract class IHardwareComm {
  Future<bool> connect(String deviceIdOrAddress);
  Future<void> disconnect();
  Future<bool> initialize();
  Future<void> startPrint();
  Future<void> pausePrint();
  Future<void> stopPrint();
  Future<void> emergencyStop();
  Stream<HardwareMessage> get deviceStatusStream;
}
```

`HardwareMessage` 结构：
```dart
class HardwareMessage {
  final String type;
  final Map<String, dynamic> payload;
  factory HardwareMessage.fromJsonString(String raw);
  String toJsonString();
}
```

## 需要修改的文件

只需替换以下 3 个文件的 TODO 部分为真实实现：

| 文件 | 需要做什么 |
|------|-----------|
| `mqtt_comm_service.dart` | 引入 `mqtt_client` 库，实现 MQTT connect/publish/subscribe |
| `ble_comm_service.dart` | 引入 `flutter_blue_plus`，实现 BLE scan/connect/notify/write |
| `wifi_comm_service.dart` | 引入 `dart:io` Socket，实现 TCP 连接和数据收发 |
| `hardware_config.dart` | 修改 `mqttBrokerHost` 为实际地址 |

**其余文件无需修改：**
- `comm_interface.dart` — 接口已固定
- `comm_protocol.dart` — 协议模型已固定
- `hardware_manager.dart` — 管理器已固定
- `device_provider.dart` — 状态管理已对接 `HardwareMessage` Stream

## MQTT 通信 stub 实现详情

文件: `lib/data/hardware/mqtt_comm_service.dart`

```dart
// 实际接入 mqtt_client 的步骤（已在代码中以 TODO 标注）：
// 1. import 'package:mqtt_client/mqtt_client.dart';
// 2. connect(): 创建 MqttServerClient, 连接到 broker
// 3. 订阅 topicDeviceToApp, 监听消息
// 4. 收到消息后: HardwareMessage.fromJsonString(msg) → _statusController.add()
// 5. _publish(): client.publishMessage() 发送 JSON 到 topicAppToDevice
```

## Stream 到 UI 的数据流

```
MQTT 消息 (JSON 字符串)
  → HardwareMessage.fromJsonString(raw)
  → _statusController.add(message)
  → DeviceNotifier.bindStatusStream(stream) 监听
  → 根据 message.type 分发:
    - STATUS_PROGRESS → DeviceState.applyProgress(p) → UI 显示进度条
    - STATUS_ERROR → DeviceState(status: error, statusMessage: "...") → UI 显示错误
```

## MQTT Broker 设置参考

elf2 主控板通常内置 MQTT broker，默认地址为板子 IP，端口 1883。连接方式：

```dart
// 手机连接到板子的 WiFi 热点后，MQTT broker = 板子 IP
final ip = '192.168.4.1'; // 常见默认网关
manager.switchMode(CommMode.mqtt);
await manager.connect(ip);
```

## 调试辅助

所有通信代码已内置 Logger 桩点：
```
[MQTT] Connecting to 192.168.4.1:1883
[MQTT] Connected
[MQTT] Publish → CMD_START_PRINT
[MQTT] Subscribe ← STATUS_PROGRESS {current: 15, total: 100}
```

## 对接检查清单

- [ ] `mqtt_client` 库引入并实现 MQTT 连接
- [ ] `hardware_config.dart` 中 `mqttBrokerHost` 改为实际地址
- [ ] Topic 发布/订阅与板端约定一致
- [ ] JSON 解析容错（`HardwareMessage.fromJsonString`）
- [ ] `STATUS_PROGRESS` → UI 进度条正常更新
- [ ] `STATUS_ERROR` → UI 错误提示正常显示
- [ ] `CMD_EMERGENCY_STOP` 急停优先级最高
- [ ] 连接超时和断线重连处理
- [ ] Android 真机测试（WiFi + BLE 权限）
