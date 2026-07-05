"""
配置管理模块 —— 封装配置加载与访问，提供类型化配置项。
启动时一次性加载，不支持热重载。
"""

import logging
from typing import Any, Dict, Optional
from config.loader import get_config, reload_config


class ConfigManager:

    _instance: Optional["ConfigManager"] = None

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self._config = get_config()
        self._logger = logging.getLogger(__name__)
        self._ensure_motor_timing()
        self._logger.info("配置管理器初始化完成")
    
    def _ensure_motor_timing(self) -> None:
        if "motor_timing" not in self._config:
            self._config["motor_timing"] = {}

        mt = self._config["motor_timing"]
        mt.setdefault("parse_time", 0.01)
        mt.setdefault("position_read_time", 0.01)
        if "execute_time" not in mt:
            mt["execute_time"] = {}
        et = mt["execute_time"]
        et.setdefault("print_move", 0.0)
        et.setdefault("newline_move", 0.0)
        et.setdefault("home_move", 0.0)
        et.setdefault("emergency_stop", 0.0)

    @property
    def config(self) -> Dict[str, Any]:
        return self._config.copy()

    @property
    def uart_ports(self) -> Dict[str, str]:
        return self._config["uart"]["ports"]

    @property
    def uart_baudrate(self) -> int:
        return self._config["uart"]["baudrate"]

    @property
    def uart_timeout(self) -> float:
        return self._config["uart"]["timeout"]

    @property
    def motor_addresses(self) -> Dict[str, int]:
        return self._config["motor"]["addresses"]

    @property
    def motor_delay_time(self) -> float:
        return self._config["motor"]["delay_time"]

    @property
    def motor_accel(self) -> int:
        return self._config["motor"]["accel"]

    @property
    def motor_speed(self) -> int:
        return self._config["motor"]["speed"]

    @property
    def motor_pulses_per_rev(self) -> int:
        return self._config["motor"]["pulses_per_rev"]

    @property
    def motor_sync_threshold(self) -> int:
        return self._config["motor"]["sync_threshold"]

    @property
    def motor_timing(self) -> Dict[str, Any]:
        return self._config["motor_timing"]

    @property
    def solenoid_gpio_chip(self) -> str:
        return self._config["solenoid"]["gpio_chip"]

    @property
    def solenoid_gpio_line(self) -> int:
        return self._config["solenoid"]["gpio_line"]

    @property
    def solenoid_punch_duration_ms(self) -> int:
        return self._config["solenoid"]["punch_duration_ms"]

    @property
    def solenoid_use_real_gpio(self) -> bool:
        return self._config["solenoid"].get("use_real_gpio", False)

    @property
    def layout_dot_gap_pulse(self) -> int:
        return self._config["layout"]["dot_gap_pulse"]

    @property
    def layout_char_gap_pulse(self) -> int:
        return self._config["layout"]["char_gap_pulse"]

    @property
    def layout_line_gap_pulse(self) -> int:
        return self._config["layout"]["line_gap_pulse"]

    @property
    def layout_chars_per_line(self) -> int:
        return self._config["layout"]["chars_per_line"]

    @property
    def layout_max_lines(self) -> int:
        return self._config["layout"]["max_lines"]

    @property
    def position_files(self) -> Dict[str, str]:
        return self._config["position"]["files"]

    @property
    def position_print_start(self) -> Dict[str, int]:
        return self._config["position"]["print_start"]

    @property
    def mqtt_broker(self) -> str:
        return self._config["mqtt"]["broker"]

    @property
    def mqtt_port(self) -> int:
        return self._config["mqtt"]["port"]

    @property
    def mqtt_client_id(self) -> str:
        return self._config["mqtt"]["client_id"]

    @property
    def mqtt_keepalive(self) -> int:
        return self._config["mqtt"]["keepalive"]

    @property
    def mqtt_topics(self) -> Dict[str, Dict[str, str]]:
        return self._config["mqtt"]["topics"]

    @property
    def log_level(self) -> str:
        return self._config["log"]["level"]

    @property
    def log_dir(self) -> str:
        return self._config["log"]["dir"]

    @property
    def log_max_bytes(self) -> int:
        return self._config["log"]["max_bytes"]

    @property
    def log_backup_count(self) -> int:
        return self._config["log"]["backup_count"]

    @property
    def log_mqtt_level(self) -> str:
        return self._config["log"]["mqtt_level"]

    @property
    def watchdog_check_interval(self) -> float:
        return self._config["watchdog"]["check_interval"]

    @property
    def watchdog_timeout(self) -> float:
        return self._config["watchdog"]["timeout"]

    @property
    def translation_flip_dots(self) -> bool:
        return self._config.get("translation", {}).get("flip_dots", False)

    @property
    def ocr_det_model_path(self) -> str:
        return self._config["ocr"]["det_model_path"]

    @property
    def ocr_rec_model_path(self) -> str:
        return self._config["ocr"]["rec_model_path"]

    @property
    def ocr_dict_path(self) -> str:
        return self._config["ocr"]["dict_path"]

    @property
    def ocr_camera_id(self) -> int:
        return self._config["ocr"]["camera_id"]

    @property
    def ocr_save_path(self) -> str:
        return self._config["ocr"]["save_path"]

    @property
    def ocr_segmentation_threshold(self) -> float:
        return self._config["ocr"]["segmentation_threshold"]

    @property
    def ocr_min_box_size(self) -> int:
        return self._config["ocr"]["min_box_size"]

    @property
    def ocr_polygon_expand_ratio(self) -> float:
        return self._config["ocr"]["polygon_expand_ratio"]

    @property
    def ocr_enable_cli(self) -> bool:
        return self._config["ocr"].get("enable_cli", True)

    @property
    def ocr_enable_real(self) -> bool:
        return self._config["ocr"].get("enable_real", True)

    @property
    def ocr_max_chars_before_stop(self) -> int:
        return self._config["ocr"].get("max_chars_before_stop", 0)

    @property
    def page_turner_delay_after_turn_ms(self) -> int:
        return self._config.get("page_turner", {}).get("delay_after_turn_ms", 2000)

    @property
    def page_turner_enable(self) -> bool:
        return self._config.get("page_turner", {}).get("enable", False)

    @property
    def hardware_listener_enable(self) -> bool:
        return self._config.get("hardware_listener", {}).get("enable", False)

    @property
    def hardware_listener_gpio_chip(self) -> str:
        return self._config.get("hardware_listener", {}).get("gpio_chip", "/dev/gpiochip0")

    @property
    def hardware_listener_button_start_line(self) -> int:
        return self._config.get("hardware_listener", {}).get("button_start_line", 22)

    @property
    def hardware_listener_button_reject_line(self) -> int:
        return self._config.get("hardware_listener", {}).get("button_reject_line", 23)

    @property
    def hardware_listener_button_estop_line(self) -> int:
        return self._config.get("hardware_listener", {}).get("button_estop_line", 24)

    @property
    def hardware_listener_debounce_ms(self) -> int:
        return self._config.get("hardware_listener", {}).get("debounce_ms", 150)

    @property
    def hardware_listener_poll_interval_ms(self) -> int:
        return self._config.get("hardware_listener", {}).get("poll_interval_ms", 50)

    def reload(self) -> None:
        self._config = reload_config()
        self._ensure_motor_timing()
        self._logger.warning("配置已重新加载（仅调试）")


config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    return config_manager