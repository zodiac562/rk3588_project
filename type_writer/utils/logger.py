"""
日志工厂 —— 统一管理所有模块的 logger 实例。
提供文件 RotatingFileHandler + 控制台输出 + 可选 MQTT Handler（ERROR 级别同步上报）。
格式: [时间][线程名][级别][模块名] 消息
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

_loggers: dict[str, logging.Logger] = {}

_log_dir: str = "logs"
_log_level: int = logging.INFO
_max_bytes: int = 5 * 1024 * 1024
_backup_count: int = 3
_mqtt_level: int = logging.ERROR
_mqtt_handler: Optional[logging.Handler] = None

_FORMAT = "[%(asctime)s][%(threadName)s][%(levelname)s][%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class MQTTLogHandler(logging.Handler):

    def __init__(self, publish_func=None):
        super().__init__(level=_mqtt_level)
        self._publish = publish_func

    def emit(self, record: logging.LogRecord) -> None:
        if self._publish is None:
            return
        try:
            self._publish(
                topic="printer/status/error",
                payload={
                    "code": f"LOG_{record.levelname}",
                    "msg": self.format(record),
                },
            )
        except Exception:
            pass


def setup(
    log_dir: str = "logs",
    level: str = "INFO",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    mqtt_level: str = "ERROR",
) -> None:
    global _log_dir, _log_level, _max_bytes, _backup_count, _mqtt_level

    _log_dir = log_dir
    _log_level = getattr(logging, level.upper(), logging.INFO)
    _max_bytes = max_bytes
    _backup_count = backup_count
    _mqtt_level = getattr(logging, mqtt_level.upper(), logging.ERROR)

    os.makedirs(_log_dir, exist_ok=True)


def attach_mqtt_handler(publish_func) -> None:
    global _mqtt_handler
    _mqtt_handler = MQTTLogHandler(publish_func)
    _mqtt_handler.setLevel(_mqtt_level)
    _mqtt_handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))

    for logger in _loggers.values():
        logger.addHandler(_mqtt_handler)


def get_logger(name: str) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(_log_level)

    logger.propagate = False

    formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(_log_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    os.makedirs(_log_dir, exist_ok=True)
    file_path = os.path.join(_log_dir, f"{name.replace('.', '_')}.log")
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=_max_bytes,
        backupCount=_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(_log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if _mqtt_handler is not None:
        logger.addHandler(_mqtt_handler)

    _loggers[name] = logger
    return logger
