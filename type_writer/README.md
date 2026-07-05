# TypeWriter - 基于 RK3588 NPU 的智能盲文打印系统

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-RK3588-orange.svg)](https://www.rock-chips.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**TypeWriter** 是一款运行在 RK3588 嵌入式 Linux 平台上的开源盲文打印系统。通过板载 NPU 实现摄像头 OCR 中文字符识别，自动转换为国标盲文点位，并由三轴步进电机驱动电磁铁在纸张上打印盲文。支持自动翻书、MQTT 远程控制、硬件按钮交互和急停安全保护。

---

## 功能特性

- **AI 文字识别**：基于 RK3588 NPU 的 DBNet 文字检测 + CRNN 文字识别（RKNN 模型推理）
- **中文→盲文转换**：pypinyin 拼音映射 → 6 点盲文阵（符合 2018 年国标）
- **三轴精密打印**：Y1/Y2 双轴同步走纸 + X 轴行内移动，UART 通信步进电机驱动
- **自动翻书**：GPIO 脉冲触发外接翻书机，结合 OCR 循环实现连续多页识别
- **多按钮交互**：硬件开始/拒绝/急停按钮（自锁急停，按下即全程序安全退出）
- **MQTT 远程控制**：外部设备可通过 MQTT 发送指令、接收打印状态
- **Mock 调试模式**：无硬件环境下通过模拟串口/GPIO 进行完整功能调试
- **位置持久化**：电机位置断电记忆（二进制文件 + 魔数校验）
- **看门狗监控**：独立心跳检测线程，异常自动上报
- **多页面换页确认**：用户确认机制 + 自动分页排版

---

## 系统架构

```
┌────────────────────────────────────────────────────────────┐
│                        main.py（主线程）                    │
│                 编排、确认、换页循环、资源管理              │
└────────────────────────────┬───────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    QueueBus     │  四层消息总线
                    │ text/motor/     │  (Queue + PriorityQueue)
                    │ status/cmd      │
                    └──┬──┬──┬──┬────┘
                       │  │  │  │
     ┌─────────────────┼──┤  │  ├──────────────────┐
     ▼                 │  │  │  │                  ▼
┌──────────────┐  ┌────▼──▼──▼──▼─────┐  ┌──────────────────┐
│  OCRThread   │  │ MotionPlannerThread│  │PrintWorkerThread │
│              │  │                    │  │                  │
│ 摄像头/CLI   ├──► text_q → 盲文转换  ├──► motor_q → 电机驱动│
│ → TEXT_BATCH │  │ → 动作序列生成     │  │ + 电磁铁打点      │
└──────┬───────┘  └──────────┬─────────┘  └────────┬─────────┘
       │                     │                      │
       │              status_q ◄────────────────────┘
       │                     │
       │              cmd_q (PriorityQueue, 优先级 0-9)
       │                     │
       └─────────────────────┼──────────────────────┐
                             │                      │
                  ┌──────────▼──────────┐  ┌───────▼──────────┐
                  │ HardwareListener │  │   MQTTThread    │
                  │ (开始/拒绝/急停)   │  │  (外部指令/状态)  │
                  └───────────────────┘  └──────────────────┘
                             │
                  ┌──────────▼──────────┐  ┌──────────────────┐
                  │ PageTurnerThread  │  │    Watchdog     │
                  │ (翻书机 GPIO 脉冲)  │  │   (心跳监控)     │
                  └───────────────────┘  └──────────────────┘
```

### 数据流

```
摄像头拍照 → NPU OCR → text_q → 盲文转换 → 动作规划 → motor_q
→ 电机移动 + 电磁铁打点 → 位置记录 → status_q → MQTT / 日志
```

---

## 硬件要求

| 硬件 | 接口 | 说明 |
|------|------|------|
| RK3588 | NPU/RKNN Lite | 板载 NPU，推理文字检测与识别模型 |
| 步进电机 ×3 | UART (/dev/ttyS3, /dev/ttyS8, /dev/ttyS9) | X/Y1/Y2 三轴运动控制 |
| 电磁铁 | GPIO (gpiochip3:0) | 盲文打点执行器 |
| 摄像头 | USB Video (ID=21) | 书籍页面拍照 |
| 按钮 ×3 | GPIO (gpiochip3:1,23,24) | 开始/拒绝/急停 |
| 翻书机 | GPIO (gpiochip4:144) | 100ms 脉冲触发翻书 |

---

## 软件依赖

### Python 环境
- Python ≥ 3.10

### 核心依赖（`requirements.txt`）

```
pyserial>=3.5          # 串口通信
pypinyin>=0.49.0       # 中文拼音转换
PyYAML>=6.0            # 配置文件解析
paho-mqtt>=1.6.0       # MQTT 客户端
gpiod>=2.0.0           # GPIO 控制
```

### RK3588 平台依赖

```
numpy                  # OCR 图像处理
opencv-python          # 摄像头捕获与图像处理
rknnlite               # RK3588 NPU 推理
pyclipper              # OCR 文本框扩张
shapely                # OCR 几何计算
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/type_writer.git
cd type_writer
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

在 RK3588 平台还需安装 `.whl` 格式的 `rknn_toolkit_lite2`。

### 3. 配置

编辑 `config/config.yaml`，按实际硬件环境修改串口号、GPIO 引脚等参数：

```yaml
uart:
  x_port: "/dev/ttyS3"
  y1_port: "/dev/ttyS8"
  y2_port: "/dev/ttyS9"
  baudrate: 115200

motor:
  x_paper_width: 300      # 纸张宽度（mm）
  y_page_length: 270      # 页面长度（mm）
  punch_distance: 2.5     # 打点间距（mm）

gpio:
  solenoid_chip: "gpiochip3"
  solenoid_line: 0
  button_start_chip: "gpiochip3"
  button_start_line: 1
  button_reject_line: 23
  button_estop_line: 24
```

### 4. 运行

**Mock 调试模式（无需硬件）：**

```bash
python main.py
```

**真实硬件模式：**

```bash
python main.py --real-serial
```

**跳过初始化回零（调试用，不推荐生产环境）：**

```bash
python main.py --real-serial --skip-init
```

---

## 使用说明

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--real-serial` | 启用真实串口通信（默认使用 Mock 虚拟串口） |
| `--skip-init` | 跳过系统初始化回零流程（仅调试用） |

### 操作流程

1. 启动程序，系统自动回零校准
2. 按下**开始按钮**或通过 MQTT 发送开始指令
3. OCR 自动拍照识别 → 转换为盲文 → 打印输出
4. 页面满时，系统暂停等待用户确认换页
5. 按下**开始按钮**确认换页继续，或按**拒绝按钮**取消剩余内容
6. 所有内容打印完成后自动停止

### MQTT 指令

程序支持通过 MQTT 远程控制。订阅和发布主题可在 `config/config.yaml` 中配置。

```json
{"cmd": "start"}    // 开始打印
{"cmd": "pause"}    // 暂停
{"cmd": "resume"}   // 恢复
{"cmd": "stop"}     // 停止
```

---

## 项目结构

```
type_writer/
├── main.py                        # 程序入口，主线程编排
├── requirements.txt               # Python 依赖
├── config/
│   ├── config.yaml                # 全局配置文件
│   └── loader.py                  # YAML 加载器（校验 + 单例）
├── core/
│   ├── messages.py                # 消息系统（MsgType/Msg/QueueBus）
│   ├── motion_planner.py          # 运动规划器（汉字→盲文→动作序列）
│   ├── motion_planner_thread.py   # 运动规划线程
│   └── state_machine.py           # 状态机（IDLE/PRINTING/ERROR）
├── threads/
│   ├── ocr_thread.py              # OCR 识别线程
│   ├── print_worker.py            # 打印执行线程
│   ├── hardware_listener.py       # 硬件按钮监听线程
│   ├── mqtt_thread.py             # MQTT 通信线程
│   └── page_turner_thread.py      # 翻书机触发线程
├── modules/
│   ├── config_manager.py          # 配置管理单例
│   ├── logger_manager.py          # 日志管理单例
│   └── system_init.py             # 系统初始化（自动回零）
├── control/
│   └── control.py                 # 电机控制器
├── solenoid/
│   └── solenoid.py                # 电磁铁控制（Mock/真实双模式）
├── read_write/
│   └── read_write.py              # 位置文件读写（二进制 + 魔数校验）
├── translation/
│   ├── translation_language.py    # 中文→盲文转换（国标6点阵）
│   └── translation_motor.py       # 电机指令帧构建（UART协议）
├── ocr/
│   ├── book_ocr.py                # BookOCR（RKNN NPU 检测+识别）
│   └── ocr_adapter.py             # OCR 结果适配器
├── utils/
│   ├── logger.py                  # 日志工厂（RotatingFileHandler）
│   └── watchdog.py                # 看门狗线程
└── logs/                          # 日志输出目录
```

---

## 设计特点

- **消息驱动架构**：所有线程间通信通过四层队列总线，零直接耦合
- **优先级指令队列**：急停(0) > 回零(1) > 停止(2) > 暂停(3) > 恢复(4) > 开始(5)
- **指令过滤回填**：各线程只处理自身关心的指令，不认识的指令自动放回队列
- **翻页确认双通道**：同时使用 `status_q` 消息和 `threading.Event` 广播，避免单消费者竞争
- **自锁急停保护**：急停按钮采用自锁设计，按下后程序立即安全释放所有资源并退出
- **位置断电保护**：电机位置以二进制格式持久化到文件，带魔数校验保证完整性
- **Mock/真实双模式**：支持无硬件全流程调试，一键切换真实硬件模式

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 致谢

- [Rockchip RKNN](https://github.com/airockchip/rknn-toolkit2) - NPU 推理框架
- [pypinyin](https://github.com/mozillazg/python-pinyin) - 中文拼音转换
- [paho-mqtt](https://github.com/eclipse-paho/paho.mqtt.python) - MQTT 客户端

---

> 本项目旨在为视障群体提供便捷的盲文阅读材料制作工具，欢迎参与贡献和改进。
