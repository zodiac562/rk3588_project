"""
硬件监听者线程（Hardware Listener Thread）。

职责：
1) 监听 3 个 GPIO 按钮：开始(确认/y)、拒绝(n)、急停
2) 软件消抖（连续 N 次读取一致才确认）
3) 开始/拒绝按钮事件通过 threading.Event 通知 main.py 的确认逻辑
4) 急停按钮直接投递 CMD_EMERGENCY_STOP 到 cmd_q
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from core.messages import Msg, MsgType, QueueBus
from modules.logger_manager import logger_manager

try:
    import gpiod
    HAS_GPIOD = True
except ImportError:
    gpiod = None  # type: ignore
    HAS_GPIOD = False


class HardwareListenerThread(threading.Thread):

    def __init__(
        self,
        queue_bus: QueueBus,
        gpio_chip_path: str = "/dev/gpiochip0",
        button_start_line: int = 22,
        button_reject_line: int = 23,
        button_estop_line: int = 24,
        enable: bool = False,
        poll_interval: float = 0.05,
        debounce_count: int = 3,
    ) -> None:
        super().__init__(name="HardwareListenerThread", daemon=True)
        self._bus = queue_bus
        self._gpio_chip_path = gpio_chip_path
        self._button_start_line = button_start_line
        self._button_reject_line = button_reject_line
        self._button_estop_line = button_estop_line
        self._enable = enable
        self._poll_interval = poll_interval
        self._debounce_count = debounce_count

        # 确认事件（供 main.py 等待）
        self._event_start = threading.Event()
        self._event_reject = threading.Event()
        self._event_estop = threading.Event()

        self._running = True
        self._logger = logger_manager.get_logger(__name__)

    def stop(self) -> None:
        self._running = False

    def is_start_pressed(self) -> bool:
        return self._event_start.is_set()

    def is_reject_pressed(self) -> bool:
        return self._event_reject.is_set()

    def is_estop_pressed(self) -> bool:
        return self._event_estop.is_set()

    def clear_events(self) -> None:
        self._event_start.clear()
        self._event_reject.clear()
        self._event_estop.clear()

    def wait_for_confirm(self, timeout: Optional[float] = None) -> Optional[str]:
        deadline = time.time() + timeout if timeout else None
        while self._running:
            remaining = deadline - time.time() if deadline else 0.05
            if remaining <= 0:
                return None

            if self._event_start.wait(timeout=min(remaining, 0.1)):
                return "start"
            if self._event_reject.is_set():
                return "reject"
            if self._event_estop.is_set():
                return "estop"

            if not self._running:
                return None
        return None

    def run(self) -> None:
        if not self._enable:
            self._logger.info("硬件监听者线程未启用，跳过")
            return

        if not HAS_GPIOD:
            self._logger.warning(
                "gpiod 未安装，硬件监听者线程降级为 Mock 模式"
            )
            self._run_mock()
            return

        self._logger.info(
            "硬件监听者线程启动: chip=%s, start=%s, reject=%s, estop=%s",
            self._gpio_chip_path,
            self._button_start_line,
            self._button_reject_line,
            self._button_estop_line,
        )

        try:
            self._run_gpio()
        except Exception as exc:
            self._logger.error("GPIO 初始化失败，降级为 Mock 模式: %s", exc)
            self._run_mock()

        self._logger.info("硬件监听者线程已退出")

    def _run_gpio(self) -> None:
        from gpiod.line import Bias, Direction, Value

        config = {
            self._button_start_line: gpiod.LineSettings(
                direction=Direction.INPUT, bias=Bias.PULL_UP
            ),
            self._button_reject_line: gpiod.LineSettings(
                direction=Direction.INPUT, bias=Bias.PULL_UP
            ),
            self._button_estop_line: gpiod.LineSettings(
                direction=Direction.INPUT, bias=Bias.PULL_UP
            ),
        }
        request = gpiod.request_lines(
            self._gpio_chip_path,
            consumer="braille-hw-listener",
            config=config,
        )

        button_offsets = {
            "start": self._button_start_line,
            "reject": self._button_reject_line,
            "estop": self._button_estop_line,
        }

        debounce = {"start": 0, "reject": 0, "estop": 0}

        try:
            while self._running:
                for btn_name, offset in button_offsets.items():
                    value = request.get_value(offset)
                    if value == Value.INACTIVE:  # 低电平 = 按钮按下
                        debounce[btn_name] += 1
                        if debounce[btn_name] >= self._debounce_count:
                            self._fire_event(btn_name)
                            debounce[btn_name] = 0  # 防止重复触发
                    else:
                        debounce[btn_name] = 0

                time.sleep(self._poll_interval)
        finally:
            request.release()

    def _fire_event(self, btn_name: str) -> None:
        if btn_name == "start":
            if not self._event_start.is_set():
                self._event_start.set()
                self._logger.info("[硬件按钮] 开始打印按钮按下")
        elif btn_name == "reject":
            if not self._event_reject.is_set():
                self._event_reject.set()
                self._logger.info("[硬件按钮] 拒绝打印按钮按下")
        elif btn_name == "estop":
            if not self._event_estop.is_set():
                self._event_estop.set()
                self._logger.warning("[硬件按钮] 急停按钮按下")
                self._bus.send_cmd(
                    Msg(
                        type=MsgType.CMD_EMERGENCY_STOP,
                        payload={"reason": "hardware_button_estop"},
                        src=self.name,
                    ),
                    priority=0,
                )

    def _run_mock(self) -> None:
        self._logger.info("硬件监听者进入 Mock 等待模式")
        while self._running:
            time.sleep(0.5)
