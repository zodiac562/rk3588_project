"""
系统启动初始化模块。

职责：
1) 自动回零（Y1 / Y2 / X）
2) 控制台询问是否开始打印
3) 若确认开始打印，则按 YAML 配置移动到打印起始位置
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Iterable

import serial

from control.control import controller
from modules.config_manager import config_manager
from modules.logger_manager import logger_manager
from read_write.read_write import write_position
from translation.translation_motor import build_rel_pos_frame


class SystemInit:

    def __init__(self, serial_ports: Dict[str, serial.Serial]) -> None:
        self._serials = serial_ports
        self._controller = controller()
        self._logger = logger_manager.get_logger(__name__)
        self._motor_timing = config_manager.motor_timing
        execute_time = self._motor_timing.get("execute_time", {})
        self._home_move_time = float(execute_time.get("home_move", 0.0))
        self._print_move_time = float(execute_time.get("print_move", 0.0))

    def run(self) -> bool:
        self._validate_ports()

        self._logger.info("系统初始化开始：自动回零")
        self.auto_home_all()

        self._logger.info("系统初始化完成")
        return True

    def auto_home_all(self) -> None:
        self._logger.info("[MOTOR-HOME] 开始Y1/Y2同步回零，目标最小时长=%ss", self._home_move_time)
        self._home_axes_with_min_duration(("y1", "y2"), min_duration=self._home_move_time)
        self._logger.info("[MOTOR-HOME] 开始X轴回零，目标最小时长=%ss", self._home_move_time)
        self._home_axes_with_min_duration(("x",), min_duration=self._home_move_time)

    def _home_axes_with_min_duration(self, axes: Iterable[str], min_duration: float) -> None:
        axes = tuple(axes)
        started_at = time.perf_counter()
        asyncio.run(self._auto_zero_axes_async(axes))

        elapsed = time.perf_counter() - started_at
        remaining = max(0.0, min_duration - elapsed)
        if remaining > 0:
            self._logger.info(
                "[MOTOR-HOME] 回零实际执行%.3fs，小于配置%.3fs，补足等待%.3fs",
                elapsed,
                min_duration,
                remaining,
            )
            time.sleep(remaining)

        for axis in axes:
            write_res = write_position(config_manager.position_files[axis], 0)
            if not write_res.success:
                raise RuntimeError(f"回零后位置写入失败 axis={axis}: {write_res}")
            self._logger.info("[MOTOR-HOME] 回零完成: axis=%s total=%.3fs", axis.upper(), max(elapsed, min_duration))

    async def _auto_zero_axes_async(self, axes: Iterable[str]) -> None:
        tasks = []
        for axis in axes:
            if axis not in self._serials:
                raise ValueError(f"serial_ports 缺少轴: {axis}")
            tasks.append(self._controller.auto_zero_frame(self._serials[axis], config_manager.position_files[axis]))
        await asyncio.gather(*tasks)

    def _send_y_pair_rel_move(self, direction: str, pulses: int) -> None:
        if pulses <= 0:
            return

        frame_y1 = build_rel_pos_frame(
            addr=int(config_manager.motor_addresses["y1"]),
            direction=direction,
            accel=int(config_manager.motor_accel),
            speed_rpm=int(config_manager.motor_speed),
            position=pulses,
        )
        frame_y2 = build_rel_pos_frame(
            addr=int(config_manager.motor_addresses["y2"]),
            direction=direction,
            accel=int(config_manager.motor_accel),
            speed_rpm=int(config_manager.motor_speed),
            position=pulses,
        )

        self._serials["y1"].write(bytes.fromhex(frame_y1))
        self._serials["y2"].write(bytes.fromhex(frame_y2))
        self._serials["y1"].flush()
        self._serials["y2"].flush()
        self._logger.info("[MOTOR-MOVE] Y1/Y2同步移动: direction=%s pulses=%s", direction, pulses)

    def _send_rel_move(self, axis: str, direction: str, pulses: int) -> None:
        if pulses <= 0:
            return

        frame_hex = build_rel_pos_frame(
            addr=int(config_manager.motor_addresses[axis]),
            direction=direction,
            accel=int(config_manager.motor_accel),
            speed_rpm=int(config_manager.motor_speed),
            position=pulses,
        )
        motor_com = self._serials[axis]
        motor_com.write(bytes.fromhex(frame_hex))
        motor_com.flush()
        self._logger.info("[MOTOR-MOVE] %s轴移动: direction=%s pulses=%s", axis.upper(), direction, pulses)

    def _sync_position_files(self, y1: int, y2: int, x: int) -> None:
        position_files = config_manager.position_files

        for axis, value in (("y1", y1), ("y2", y2), ("x", x)):
            res = write_position(position_files[axis], value)
            if not res.success:
                raise RuntimeError(f"初始化位置写入失败 axis={axis}: {res}")

    def _validate_ports(self) -> None:
        for axis in ("y1", "y2", "x"):
            if axis not in self._serials:
                raise ValueError(f"serial_ports 缺少轴: {axis}")

    @staticmethod
    def _estimate_wait_time(pulses: int, speed_rpm: int, pulses_per_rev: int, min_duration: float = 0.0) -> float:
        if pulses <= 0 or speed_rpm <= 0 or pulses_per_rev <= 0:
            return max(0.05, min_duration)

        pulses_per_sec = speed_rpm * pulses_per_rev / 60.0
        motion_time = pulses / pulses_per_sec + 0.1
        return max(motion_time, min_duration)
