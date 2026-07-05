"""
配置加载器 —— 从 config.yaml 一次性读入全局配置，提供 get_config() 单例访问。
启动时做基本字段校验，缺字段抛清晰错误。
"""

import os
import yaml
from typing import Any, Dict

_CONFIG: Dict[str, Any] | None = None

# 项目根目录（config/loader.py 的上上级）
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)


def _validate(cfg: Dict[str, Any]) -> None:
    required_top_keys = ["uart", "motor", "solenoid", "layout", "position", "mqtt", "log", "watchdog"]
    for key in required_top_keys:
        if key not in cfg:
            raise ValueError(f"配置文件缺少顶级字段: {key}")

    if "ports" not in cfg["uart"]:
        raise ValueError("uart.ports 缺失，需指定 x1/x2/y 串口")
    for motor_name in ("y1", "y2", "x"):
        if motor_name not in cfg["uart"]["ports"]:
            raise ValueError(f"uart.ports.{motor_name} 缺失")

    if "addresses" not in cfg["motor"]:
        raise ValueError("motor.addresses 缺失")
    for motor_name in ("y1", "y2", "x"):
        if motor_name not in cfg["motor"]["addresses"]:
            raise ValueError(f"motor.addresses.{motor_name} 缺失")

    layout = cfg["layout"]
    required_layout_keys = ["dot_gap_pulse", "char_gap_pulse", "line_gap_pulse", "chars_per_line", "max_lines"]
    for key in required_layout_keys:
        if key not in layout:
            raise ValueError(f"layout.{key} 缺失")

    positive_layout_keys = ["dot_gap_pulse", "line_gap_pulse", "chars_per_line", "max_lines"]
    for key in positive_layout_keys:
        value = layout[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"layout.{key} 必须是正整数")

    char_gap = layout["char_gap_pulse"]
    if not isinstance(char_gap, int) or isinstance(char_gap, bool) or char_gap < 0:
        raise ValueError("layout.char_gap_pulse 必须是非负整数")

    position = cfg["position"]
    if "print_start" not in position:
        raise ValueError("position.print_start 缺失")

    print_start = position["print_start"]
    for axis in ("y1", "y2", "x"):
        if axis not in print_start:
            raise ValueError(f"position.print_start.{axis} 缺失")
        value = print_start[axis]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"position.print_start.{axis} 必须是非负整数")

    if print_start["y1"] != print_start["y2"]:
        raise ValueError("position.print_start.y1 与 position.print_start.y2 必须相等")

    for sub in ("subscribe", "publish"):
        if sub not in cfg["mqtt"].get("topics", {}):
            raise ValueError(f"mqtt.topics.{sub} 缺失")


def load_config(path: str | None = None) -> Dict[str, Any]:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    if path is None:
        path = os.path.join(_PROJECT_ROOT, "config", "config.yaml")

    if not os.path.isfile(path):
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if cfg is None:
        raise ValueError("配置文件为空")

    _validate(cfg)

    for motor_name, rel_path in cfg["position"]["files"].items():
        cfg["position"]["files"][motor_name] = _resolve_path(
            os.path.join(cfg["position"]["dir"], rel_path)
        )

    cfg["log"]["dir"] = _resolve_path(cfg["log"]["dir"])

    _CONFIG = cfg
    return _CONFIG


def get_config() -> Dict[str, Any]:
    return load_config()


def reload_config(path: str | None = None) -> Dict[str, Any]:
    global _CONFIG
    _CONFIG = None
    return load_config(path)
