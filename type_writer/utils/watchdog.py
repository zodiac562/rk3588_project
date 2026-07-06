"""
看门狗模块（Watchdog）。

职责：
1) 监控各线程心跳（通过监听 status_q 中的心跳消息）
2) 超时未收到某线程心跳则上报 STATUS_ERROR

配置来源: config.yaml → watchdog 配置段
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Set

from core.messages import Msg, MsgType, QueueBus
from modules.logger_manager import logger_manager


class Watchdog(threading.Thread):

    def __init__(
        self,
        queue_bus: QueueBus,
        config_manager=None,
        enable: bool = False,
        check_interval: float = 1.0,
        timeout: float = 3.0,
        monitored_threads: Set[str] = None,
    ) -> None:
        super().__init__(name="Watchdog", daemon=True)
        self._bus = queue_bus

        if config_manager is None:
            from modules.config_manager import get_config_manager
            config_manager = get_config_manager()
        self._cfg = config_manager

        self._enable = enable
        self._check_interval = check_interval
        self._timeout = timeout
        self._monitored = monitored_threads or {
            "OCRThread", "MotionPlannerThread", "PrintWorkerThread",
        }

        self._last_heartbeat: Dict[str, float] = {}
        self._running = True
        self._logger = logger_manager.get_logger(__name__)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        if not self._enable:
            self._logger.info("看门狗未启用，跳过")
            return

        self._logger.info(
            "看门狗启动: interval=%.1fs timeout=%.1fs monitored=%s",
            self._check_interval, self._timeout, self._monitored,
        )

        while self._running:
            self._check_all()
            time.sleep(self._check_interval)

        self._logger.info("看门狗已退出")

    def _check_all(self) -> None:
        for _ in range(3):
            status_msg = self._bus.recv_status(timeout=0.01)
            if status_msg is None:
                break

            src = status_msg.src or ""
            if src in self._monitored:
                self._last_heartbeat[src] = time.time()

        now = time.time()
        for name in self._monitored:
            last = self._last_heartbeat.get(name, 0)
            if last == 0:
                continue

            elapsed = now - last
            if elapsed > self._timeout:
                self._logger.warning(
                    "看门狗: 线程 %s 心跳超时 %.1fs > %.1fs",
                    name, elapsed, self._timeout,
                )
                self._bus.send_error(
                    code="WATCHDOG_TIMEOUT",
                    msg=f"线程 {name} 心跳超时 {elapsed:.1f}s",
                    src=self.name,
                )
