"""
翻书机触发模块（Page Turner Thread）—— GPIO 硬件控制。

职责：
1) 监听 cmd_q 中的 CMD_TRIGGER_TURN_PAGE 指令
2) 通过 GPIO 发出 100ms 高电平脉冲触发 STM32 翻书
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import gpiod
from gpiod.line import Direction, Value

from core.messages import Msg, MsgType, QueueBus
from modules.logger_manager import logger_manager


class PageTurnerThread(threading.Thread):

    def __init__(
        self,
        queue_bus: QueueBus,
        config_manager=None,
        enable: bool = False,
    ) -> None:
        super().__init__(name="PageTurnerThread", daemon=True)
        self._bus = queue_bus

        if config_manager is None:
            from modules.config_manager import get_config_manager
            config_manager = get_config_manager()
        self._cfg = config_manager

        self._enable = enable
        self._running = True
        self._logger = logger_manager.get_logger(__name__)

        # GPIO 配置
        self._gpio_chip = "/dev/gpiochip4"
        self._gpio_line = 144
        self._request = None

    def stop(self) -> None:
        self._running = False

    def _init_gpio(self) -> bool:
        try:
            self._gpio_chip = self._cfg.get("page_turner.gpio_chip", "/dev/gpiochip4")
            self._gpio_line = self._cfg.get("page_turner.gpio_line", 144)

            self._request = gpiod.request_lines(
                self._gpio_chip,
                consumer="page_turner",
                config={
                    self._gpio_line: gpiod.LineSettings(
                        direction=Direction.OUTPUT,
                        output_value=Value.INACTIVE,
                    ),
                },
            )
            self._logger.info(
                "翻书机 GPIO 初始化成功: %s:%d", self._gpio_chip, self._gpio_line
            )
            return True
        except Exception as e:
            self._logger.error("翻书机 GPIO 初始化失败: %s", e)
            return False

    def _trigger_gpio(self) -> None:
        if self._request is None:
            self._logger.warning("[翻书机] GPIO 未初始化，无法触发")
            return

        try:
            self._request.set_value(self._gpio_line, Value.ACTIVE)
            time.sleep(0.1)
            self._request.set_value(self._gpio_line, Value.INACTIVE)
            self._logger.info("[翻书机] GPIO 脉冲已发送")
        except Exception as e:
            self._logger.error("[翻书机] GPIO 触发失败: %s", e)

    def _release_gpio(self) -> None:
        if self._request is not None:
            try:
                self._request.set_value(self._gpio_line, Value.INACTIVE)
                self._request.release()
                self._logger.info("翻书机 GPIO 已释放")
            except Exception as e:
                self._logger.warning("翻书机 GPIO 释放异常: %s", e)
            self._request = None

    def run(self) -> None:
        if not self._enable:
            self._logger.info("翻书机线程未启用，跳过")
            return

        if not self._init_gpio():
            self._logger.error("翻书机 GPIO 初始化失败，线程退出")
            return

        self._logger.info("翻书机线程启动（GPIO 硬件模式）")

        while self._running:
            cmd_msg = self._bus.recv_cmd(timeout=0.5)
            if cmd_msg is None:
                continue

            if cmd_msg.type == MsgType.CMD_TRIGGER_TURN_PAGE:
                self._logger.info("[翻书机] 收到翻书指令，触发 GPIO")
                self._trigger_gpio()
            else:
                self._bus.send_cmd(cmd_msg, priority=9)

        self._release_gpio()
        self._logger.info("翻书机线程已退出")
