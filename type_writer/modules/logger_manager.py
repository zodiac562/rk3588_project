"""
日志管理模块 —— 封装日志系统初始化与 logger 获取。
"""

import logging
from typing import Optional
from utils.logger import setup as setup_logging, get_logger as _get_logger, attach_mqtt_handler
from modules.config_manager import config_manager


class LoggerManager:

    _instance: Optional["LoggerManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "LoggerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, mqtt_publish_func=None) -> None:
        if self._initialized:
            return

        log_dir = config_manager.log_dir
        log_level = config_manager.log_level
        log_max_bytes = config_manager.log_max_bytes
        log_backup_count = config_manager.log_backup_count
        log_mqtt_level = config_manager.log_mqtt_level

        setup_logging(
            log_dir=log_dir,
            level=log_level,
            max_bytes=log_max_bytes,
            backup_count=log_backup_count,
            mqtt_level=log_mqtt_level,
        )

        if mqtt_publish_func is not None:
            attach_mqtt_handler(mqtt_publish_func)

        self._initialized = True
        self.get_logger(__name__).info("日志管理器初始化完成")

    def get_logger(self, name: str) -> logging.Logger:
        if not self._initialized:
            self.initialize()
        return _get_logger(name)

    def attach_mqtt(self, publish_func) -> None:
        attach_mqtt_handler(publish_func)
        self.get_logger(__name__).info("MQTT 日志 handler 已附加")


logger_manager = LoggerManager()