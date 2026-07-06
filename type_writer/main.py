"""
盲文打印系统主线程入口。

当前版本编排已完成模块：
- SystemInit（自动回零）
- OCRThread（CLI 模拟 + 真实 OCR 自动循环）
- MotionPlannerThread（文字 -> 电机动作）
- PrintWorkerThread（电机动作执行 + 进度上报）
- HardwareListenerThread（3按钮：开始 / 拒绝 / 急停）
- MQTTThread（外部指令接收 + 状态转发）
- Watchdog（线程心跳监控）
- PageTurnerThread（翻书预留）

默认使用 mock 串口，便于在无硬件环境完成完整流程模拟。
"""

from __future__ import annotations

import argparse
import threading
import time
from typing import Dict

import serial

from core.messages import Msg, MsgType, QueueBus
from core.motion_planner_thread import MotionPlannerThread
from modules.config_manager import config_manager
from modules.logger_manager import logger_manager
from modules.system_init import SystemInit
from read_write.read_write import read_position, write_position
from threads.ocr_thread import OCRThread
from threads.print_worker import PrintWorkerThread
from threads.hardware_listener import HardwareListenerThread
from threads.mqtt_thread import MQTTThread
from threads.page_turner_thread import PageTurnerThread
from utils.watchdog import Watchdog


class MockSerialPort:
    """最小串口模拟实现，用于本地无硬件运行。"""

    def __init__(self, port: str):
        self.port = port
        self.is_open = True
        self._write_count = 0

    def write(self, data: bytes) -> int:
        self._write_count += 1
        return len(data)

    def flush(self) -> None:
        return None

    def read(self, size: int = 1) -> bytes:
        if size <= 0:
            return b""
        frame = bytes([0xC5, 0x01, 0x2A, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5C])
        return frame[:size].ljust(size, b"\x00")

    def reset_input_buffer(self) -> None:
        return None

    def reset_output_buffer(self) -> None:
        return None

    def close(self) -> None:
        self.is_open = False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="盲文打印系统主线程入口")
    parser.add_argument(
        "--real-serial",
        action="store_true",
        help="启用真实串口（默认关闭，默认使用 mock 串口）",
    )
    parser.add_argument(
        "--skip-init",
        action="store_true",
        help="跳过 SystemInit（仅调试用）",
    )
    return parser.parse_args()


def _ensure_position_files() -> None:
    """确保位置文件可用；若不存在/损坏则初始化为 0。"""
    logger = logger_manager.get_logger(__name__)
    for axis, file_path in config_manager.position_files.items():
        read_res = read_position(file_path)
        if read_res.success:
            continue
        write_res = write_position(file_path, 0)
        if not write_res.success:
            raise RuntimeError(f"位置文件初始化失败 axis={axis}: {write_res}")
        logger.warning("位置文件已重建为0: axis=%s file=%s", axis, file_path)


def _open_serial_ports(use_real_serial: bool) -> Dict[str, serial.Serial]:
    logger = logger_manager.get_logger(__name__)
    ports = config_manager.uart_ports

    if not use_real_serial:
        serials: Dict[str, serial.Serial] = {
            "y1": MockSerialPort("mock-y1"),
            "y2": MockSerialPort("mock-y2"),
            "x": MockSerialPort("mock-x"),
        }
        logger.info("已启用 mock 串口模式")
        return serials

    serials_real: Dict[str, serial.Serial] = {}
    for axis in ("y1", "y2", "x"):
        serials_real[axis] = serial.Serial(
            port=ports[axis],
            baudrate=config_manager.uart_baudrate,
            timeout=config_manager.uart_timeout,
        )
    logger.info("已启用真实串口模式: ports=%s", ports)
    return serials_real


def _close_serial_ports(serial_ports: Dict[str, serial.Serial]) -> None:
    logger = logger_manager.get_logger(__name__)
    for axis, ser in serial_ports.items():
        try:
            close_fn = getattr(ser, "close", None)
            if callable(close_fn):
                close_fn()
            logger.info("串口已关闭: axis=%s", axis)
        except Exception as exc:
            logger.warning("串口关闭失败: axis=%s err=%s", axis, exc)


def _console_confirm() -> bool:
    """控制台询问是否开始打印（阻塞，仅一次）。"""
    prompt = "系统初始化完成，是否开始打印？(y/n): "
    while True:
        try:
            answer = input(prompt).strip().lower()
            if answer in {"y", "yes", "是"}:
                return True
            if answer in {"n", "no", "否"}:
                return False
            print("输入无效，请输入 y 或 n")
        except EOFError:
            return False
        except KeyboardInterrupt:
            raise  # 重抛使主线程 finally 块可执行清理


def _wait_for_hardware_confirm(hw_listener: HardwareListenerThread) -> bool:
    """
    等待硬件按钮确认（阻塞）。

    Returns:
        True: 开始按钮按下
        False: 拒绝按钮按下或超时
    """
    logger = logger_manager.get_logger(__name__)
    logger.info("等待硬件按钮确认...（开始/拒绝/急停）")
    result = hw_listener.wait_for_confirm(timeout=120.0)
    if result == "start":
        logger.info("硬件按钮确认: 开始打印")
        return True
    elif result == "estop":
        logger.warning("硬件按钮: 急停")
        # 急停已由 listener 投递到 cmd_q，这里返回 False 不启动循环
        return False
    else:
        logger.info("硬件按钮确认: 拒绝或超时")
        return False


def main() -> int:
    args = _parse_args()
    logger = logger_manager.get_logger("main")

    logger.info("系统启动中...")
    _ensure_position_files()
    serial_ports = _open_serial_ports(use_real_serial=args.real_serial)

    try:
        if not args.skip_init:
            init_runner = SystemInit(serial_ports=serial_ports)
            init_runner.run()
            logger.info("系统初始化（回零）完成")
        else:
            logger.warning("跳过系统初始化（--skip-init）")

        bus = QueueBus()

        print_thread = PrintWorkerThread(bus, serial_ports)
        planner_thread = MotionPlannerThread(bus)
        ocr_thread = OCRThread(bus)

        print_thread.start()
        planner_thread.start()
        ocr_thread.start()
        logger.info("核心线程已启动：OCR / MotionPlanner / PrintWorker")
        hw_cfg = config_manager
        hw_enable = hw_cfg.hardware_listener_enable
        hw_listener = HardwareListenerThread(
            queue_bus=bus,
            gpio_chip_path=hw_cfg.hardware_listener_gpio_chip,
            button_start_line=hw_cfg.hardware_listener_button_start_line,
            button_reject_line=hw_cfg.hardware_listener_button_reject_line,
            button_estop_line=hw_cfg.hardware_listener_button_estop_line,
            enable=hw_enable,
            poll_interval=hw_cfg.hardware_listener_poll_interval_ms / 1000.0,
            debounce_count=max(
                3,
                hw_cfg.hardware_listener_debounce_ms
                // max(1, hw_cfg.hardware_listener_poll_interval_ms),
            ),
        )

        mqtt_thread = MQTTThread(bus, enable=config_manager._config.get("mqtt", {}).get("enable", False))
        watchdog = Watchdog(bus, enable=config_manager._config.get("watchdog", {}).get("enable", False))
        page_turner = PageTurnerThread(bus, enable=config_manager.page_turner_enable)

        if hw_enable:
            hw_listener.start()
            logger.info("硬件监听者线程已启动")
        if config_manager._config.get("mqtt", {}).get("enable", False):
            mqtt_thread.start()
            logger.info("MQTT 线程已启动")
        if config_manager._config.get("watchdog", {}).get("enable", False):
            watchdog.start()
            logger.info("看门狗线程已启动")
        if config_manager.page_turner_enable:
            page_turner.start()
            logger.info("翻书机线程已启动")

        logger.info("等待启动确认...")
        if hw_enable:
            confirmed = _wait_for_hardware_confirm(hw_listener)
        else:
            confirmed = _console_confirm()

        if not confirmed:
            logger.info("用户取消/急停，停止所有线程并退出")
            _stop_all_threads(
                bus=bus,
                ocr_thread=ocr_thread,
                planner_thread=planner_thread,
                print_thread=print_thread,
                hw_listener=hw_listener,
                mqtt_thread=mqtt_thread,
                watchdog=watchdog,
                page_turner=page_turner,
                logger=logger,
            )
            return 0

        logger.info("用户确认，启动 OCR 自动循环")
        bus.send_cmd(
            Msg(type=MsgType.CMD_START_OCR, payload={}, src="main"),
            priority=5,
        )

        logger.info("系统进入自动循环运行: OCR → 打印 → 翻书 → 延时 → OCR...")

        try:
            while ocr_thread.is_alive():
                if hw_enable and hw_listener.is_estop_pressed():
                    logger.warning("检测到急停信号，退出主循环")
                    break

                if bus.is_page_complete():
                    info = bus.get_page_complete_info()
                    remaining = info.get("remaining_chars", 0)
                    consumed = info.get("consumed_chars", 0)
                    logger.info(
                        "页面打印完成(已打%s字)，剩余%s字，等待换页确认...",
                        consumed, remaining,
                    )

                    if not ocr_thread.is_alive():
                        bus.clear_page_complete()
                        break

                    if hw_enable:
                        hw_listener.clear_events()
                        confirmed = _wait_for_hardware_confirm(hw_listener)
                    else:
                        confirmed = _console_confirm()

                    if confirmed:
                        bus.send_cmd(
                            Msg(type=MsgType.CMD_START_PRINT, payload={}, src="main"),
                            priority=5,
                        )
                        logger.info("换页确认，继续打印")
                    else:
                        if hw_enable and hw_listener.is_estop_pressed():
                            logger.warning("翻页确认期间检测到急停，退出主循环")
                            bus.clear_page_complete()
                            break
                        bus.send_cmd(
                            Msg(type=MsgType.CMD_RESET, payload={"reason": "user_reject"}, src="main"),
                            priority=4,
                        )
                        logger.info("用户拒绝换页，已清空剩余%s字", remaining)

                    bus.clear_page_complete()
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.warning("收到键盘中断，准备退出")
        finally:
            _stop_all_threads(
                bus=bus,
                ocr_thread=ocr_thread,
                planner_thread=planner_thread,
                print_thread=print_thread,
                hw_listener=hw_listener,
                mqtt_thread=mqtt_thread,
                watchdog=watchdog,
                page_turner=page_turner,
                logger=logger,
            )

        logger.info("主线程退出完成")
        return 0

    finally:
        _close_serial_ports(serial_ports)


def _stop_all_threads(
    bus: QueueBus,
    ocr_thread: OCRThread,
    planner_thread: MotionPlannerThread,
    print_thread: PrintWorkerThread,
    hw_listener: HardwareListenerThread,
    mqtt_thread: MQTTThread,
    watchdog: Watchdog,
    page_turner: PageTurnerThread,
    logger,
) -> None:
    """优雅停止所有线程。"""
    logger.info("正在停止所有线程...")

    bus.send_cmd(
        Msg(type=MsgType.CMD_STOP_OCR, payload={"reason": "main-exit"}, src="main"),
        priority=2,
    )
    bus.send_cmd(
        Msg(type=MsgType.CMD_STOP_PRINT, payload={"reason": "main-exit"}, src="main"),
        priority=2,
    )

    ocr_thread.stop()
    planner_thread.stop()
    print_thread.stop()
    hw_listener.stop()
    mqtt_thread.stop()
    watchdog.stop()
    page_turner.stop()

    for t, name in [
        (ocr_thread, "OCRThread"),
        (planner_thread, "MotionPlannerThread"),
        (print_thread, "PrintWorkerThread"),
        (hw_listener, "HardwareListenerThread"),
        (mqtt_thread, "MQTTThread"),
        (watchdog, "Watchdog"),
        (page_turner, "PageTurnerThread"),
    ]:
        if t.is_alive():
            t.join(timeout=3.0)
            if t.is_alive():
                logger.warning("线程 %s 超时未退出", name)
            else:
                logger.info("线程 %s 已退出", name)

    logger.info("所有线程已停止")


if __name__ == "__main__":
    raise SystemExit(main())
