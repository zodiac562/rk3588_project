"""
打印线程（Print Worker）。

职责：
1) 从 motor_q 消费电机动作消息（MOTOR_*）
2) 按时间模型执行：解析耗时 -> 动作执行 -> 位置记录
3) 驱动电机控制与电磁铁（当前电磁铁为 Mock）
4) 回写位置文件，并上报 STATUS_POSITION / STATUS_ERROR
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, Optional

import serial

from control.control import controller
from core.messages import Msg, MsgType, QueueBus
from modules.config_manager import config_manager
from modules.logger_manager import logger_manager
from read_write.read_write import read_position, write_position
from solenoid.solenoid import Solenoid
from translation.translation_motor import build_rel_pos_frame


class PrintWorkerThread(threading.Thread):

    def __init__(self, queue_bus: QueueBus, serial_ports: Dict[str, serial.Serial]) -> None:
        super().__init__(name="PrintWorkerThread", daemon=True)
        self._bus = queue_bus
        self._serials = serial_ports
        self._controller = controller()
        self._logger = logger_manager.get_logger(__name__)
        # 根据配置选择 Mock 或真实 GPIO 模式
        use_real_gpio = config_manager.solenoid_use_real_gpio
        try:
            self._solenoid = Solenoid(use_real_gpio=use_real_gpio)
        except Exception as exc:
            self._logger.error("Solenoid 真实 GPIO 初始化失败，降级为 Mock 模式: %s", exc)
            self._solenoid = Solenoid(use_real_gpio=False)

        self._running = True
        self._paused = False

        self._position_files = config_manager.position_files
        self._motor_addresses = config_manager.motor_addresses
        self._motor_accel = int(config_manager.motor_accel)
        self._motor_speed = int(config_manager.motor_speed)
        self._pulses_per_rev = int(config_manager.motor_pulses_per_rev)

        timing = config_manager.motor_timing
        execute_time = timing.get("execute_time", {})
        self._parse_time = float(timing.get("parse_time", 0.01))
        self._position_read_time = float(timing.get("position_read_time", 0.01))
        self._execute_times = {
            "print_move": float(execute_time.get("print_move", 0.0)),
            "newline_move": float(execute_time.get("newline_move", 0.0)),
            "home_move": float(execute_time.get("home_move", 0.0)),
            "emergency_stop": float(execute_time.get("emergency_stop", 0.0)),
        }

        self._positions: Dict[str, int] = self._load_initial_positions()

        # 进度跟踪（用于 STATUS_PROGRESS 投递）
        self._chars_processed: int = 0
        self._total_chars: int = 0

        self._motor_busy: bool = False
        self._idle_count: int = 0
        self._IDLE_COUNT_THRESHOLD: int = 3

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self._validate_ports()
        self._logger.info("打印线程启动")

        while self._running:
            if self._paused:
                if self._handle_one_command(timeout=0.05):
                    continue
                continue

            self._handle_one_command(timeout=0.001)

            msg = self._bus.recv_motor(timeout=0.1)
            if msg is None:
                if self._motor_busy:
                    self._idle_count += 1
                    if self._idle_count >= self._IDLE_COUNT_THRESHOLD:
                        self._logger.debug("motor_q 连续空闲，发送 IDLE 信号")
                        self._bus.send_status(Msg(
                            type=MsgType.STATUS_STATE,
                            payload={"new_state": "IDLE", "reason": "motor_q_empty"},
                            src=self.name,
                        ))
                        self._motor_busy = False
                        self._idle_count = 0
                continue

            try:
                self._execute_message(msg)
                self._motor_busy = True
                self._idle_count = 0
            except Exception as exc:
                self._logger.exception("打印线程执行失败: msg=%s err=%s", msg, exc)
                self._bus.send_error(code="PRINT_WORKER_ERROR", msg=str(exc), src=self.name)

        self._solenoid.release()
        self._logger.info("打印线程已退出")

    def _execute_message(self, msg: Msg) -> None:
        action_type = self._resolve_action_type(msg)
        self._logger.info(
            "执行电机动作: msg_type=%s action_type=%s payload=%s",
            msg.type,
            action_type,
            msg.payload,
        )

        if self._parse_time > 0:
            time.sleep(self._parse_time)

        exec_started_at = time.perf_counter()

        total_chars = int(msg.payload.get("total_chars", 0) or 0)
        if total_chars > 0:
            self._total_chars = total_chars

        if action_type == "emergency_stop":
            self._execute_emergency_stop(msg.payload)
        elif action_type == "home_move":
            self._execute_home_move(msg.payload)
        elif action_type in ("print_move", "newline_move"):
            self._execute_move(msg.payload)
        else:
            self._logger.warning("未知动作类型，忽略: action_type=%s payload=%s", action_type, msg.payload)
            return

        execute_time = max(0.0, self._execute_times.get(action_type, 0.0))
        if action_type == "home_move":
            elapsed = time.perf_counter() - exec_started_at
            remaining = max(0.0, execute_time - elapsed)
            if remaining > 0:
                self._logger.info(
                    "[MOTOR-HOME] 回零实际执行%.3fs，小于配置%.3fs，补足等待%.3fs",
                    elapsed,
                    execute_time,
                    remaining,
                )
                time.sleep(remaining)
        elif execute_time > 0:
            time.sleep(execute_time)

        if self._position_read_time > 0:
            time.sleep(self._position_read_time)
        self._record_positions()


    def _execute_move(self, payload: Dict[str, Any]) -> None:
        x_delta = int(payload.get("x_delta", 0) or 0)
        y_delta = int(payload.get("y_delta", 0) or 0)
        punch_points = payload.get("punch_points", []) or []

        if x_delta != 0:
            self._send_axis_rel_move("x", x_delta)
            wait_time = self._estimate_wait(abs(x_delta))
            if wait_time > 0:
                time.sleep(wait_time)
            self._positions["x"] = self._clamp_position(self._positions.get("x", 0) + x_delta)

        if y_delta != 0:
            self._send_y_pair_rel_move(y_delta)
            wait_time = self._estimate_wait(abs(y_delta))
            if wait_time > 0:
                time.sleep(wait_time)
            self._positions["y1"] = self._clamp_position(self._positions.get("y1", 0) + y_delta)
            self._positions["y2"] = self._clamp_position(self._positions.get("y2", 0) + y_delta)

        for point in punch_points:
            self._logger.info("执行打点: point=%s", point)
            self._solenoid.punch(point=point)

        self._chars_processed += 1
        percentage = (
            self._chars_processed / self._total_chars * 100.0
        ) if self._total_chars > 0 else 0.0
        self._bus.send_status(Msg(
            type=MsgType.STATUS_PROGRESS,
            payload={
                "current": self._chars_processed,
                "total": self._total_chars,
                "percentage": round(percentage, 1),
            },
            src=self.name,
        ))


    def _execute_home_move(self, payload: Dict[str, Any]) -> None:
        axis_mode = str(payload.get("home_axis", "all")).lower()

        if axis_mode in ("all", "y", "y_pair"):
            self._home_y_pair_sync()
            if axis_mode != "all":
                return

        if axis_mode in ("all", "x"):
            asyncio.run(self._controller.auto_zero_frame(self._serials["x"], self._position_files["x"]))
            self._positions["x"] = 0
            self._logger.info("[MOTOR-HOME] X轴回零完成")
            return

        if axis_mode in ("y1", "y2"):
            asyncio.run(self._controller.auto_zero_frame(self._serials[axis_mode], self._position_files[axis_mode]))
            self._positions[axis_mode] = 0
            self._logger.info("[MOTOR-HOME] %s轴回零完成", axis_mode.upper())
            return

        self._logger.warning("回零忽略未知轴模式: %s", axis_mode)


    def _execute_emergency_stop(self, payload: Dict[str, Any]) -> None:
        _ = payload
        self._controller.hurry_stop(self._serials["y1"], self._serials["y2"], self._serials["x"])

    def _handle_one_command(self, timeout: float) -> bool:
        cmd = self._bus.recv_cmd(timeout=timeout)
        if cmd is None:
            return False

        cmd_type = cmd.type
        if cmd_type == MsgType.CMD_EMERGENCY_STOP:
            self._execute_emergency_stop({"reason": "cmd"})
            return True

        if cmd_type == MsgType.CMD_PAUSE_PRINT:
            self._paused = True
            self._logger.info("收到暂停指令，打印线程暂停消费 motor_q")
            return True

        if cmd_type == MsgType.CMD_RESUME_PRINT:
            self._paused = False
            self._logger.info("收到恢复指令，打印线程恢复")
            return True

        if cmd_type == MsgType.CMD_STOP_PRINT:
            self._paused = True
            self._drain_motor_queue()
            self._logger.info("收到停止指令，已清空 motor_q 并暂停")
            return True

        self._bus.send_cmd(cmd, priority=self._default_priority(cmd.type))
        return True

    def _drain_motor_queue(self) -> int:
        dropped = 0
        while True:
            msg = self._bus.recv_motor(timeout=0.0)
            if msg is None:
                break
            dropped += 1
        return dropped

    def _send_y_pair_rel_move(self, delta: int) -> None:
        direction = "forward" if delta >= 0 else "reverse"
        pulses = abs(int(delta))
        if pulses == 0:
            return

        frame_y1 = build_rel_pos_frame(
            addr=int(self._motor_addresses["y1"]),
            direction=direction,
            accel=self._motor_accel,
            speed_rpm=self._motor_speed,
            position=pulses,
        )
        frame_y2 = build_rel_pos_frame(
            addr=int(self._motor_addresses["y2"]),
            direction=direction,
            accel=self._motor_accel,
            speed_rpm=self._motor_speed,
            position=pulses,
        )

        self._serials["y1"].write(bytes.fromhex(frame_y1))
        self._serials["y2"].write(bytes.fromhex(frame_y2))
        self._serials["y1"].flush()
        self._serials["y2"].flush()

        self._logger.info(
            "[MOTOR-MOVE] Y1/Y2同步移动 direction=%s pulses=%s delta=%s",
            direction,
            pulses,
            delta,
        )

    def _send_axis_rel_move(self, axis: str, delta: int) -> None:
        direction = "forward" if delta >= 0 else "reverse"
        pulses = abs(int(delta))
        if pulses == 0:
            return

        frame_hex = build_rel_pos_frame(
            addr=int(self._motor_addresses[axis]),
            direction=direction,
            accel=self._motor_accel,
            speed_rpm=self._motor_speed,
            position=pulses,
        )
        motor_com = self._serials[axis]
        motor_com.write(bytes.fromhex(frame_hex))
        motor_com.flush()
        self._logger.info(
            "[MOTOR-MOVE] %s轴移动 direction=%s pulses=%s delta=%s",
            axis.upper(),
            direction,
            pulses,
            delta,
        )

    def _home_y_pair_sync(self) -> None:
        self._logger.info("[MOTOR-HOME] 开始Y1/Y2同步回零")
        asyncio.run(self._auto_zero_y_pair_async())
        self._positions["y1"] = 0
        self._positions["y2"] = 0
        self._logger.info("[MOTOR-HOME] Y1/Y2同步回零完成")

    async def _auto_zero_y_pair_async(self) -> None:
        await asyncio.gather(
            self._controller.auto_zero_frame(self._serials["y1"], self._position_files["y1"]),
            self._controller.auto_zero_frame(self._serials["y2"], self._position_files["y2"]),
        )



    def _record_positions(self) -> None:
        for axis in ("y1", "y2", "x"):
            value = int(self._positions.get(axis, 0))
            res = write_position(self._position_files[axis], value)
            if not res.success:
                self._logger.error("位置写入失败 axis=%s: %s", axis, res)
                return

        self._bus.send_status(
            Msg(
                type=MsgType.STATUS_POSITION,
                payload={
                    "y1": self._positions.get("y1", 0),
                    "y2": self._positions.get("y2", 0),
                    "x": self._positions.get("x", 0),
                },
                src=self.name,
            )
        )

    def _load_initial_positions(self) -> Dict[str, int]:
        result: Dict[str, int] = {"y1": 0, "y2": 0, "x": 0}
        for axis in ("y1", "y2", "x"):
            read_res = read_position(self._position_files[axis])
            if read_res.success and read_res.value is not None:
                result[axis] = int(read_res.value)
            else:
                self._logger.warning("初始化读取位置失败，默认0: axis=%s reason=%s", axis, read_res)
        return result

    def _validate_ports(self) -> None:
        for axis in ("y1", "y2", "x"):
            if axis not in self._serials:
                raise ValueError(f"serial_ports 缺少轴: {axis}")

    def _resolve_action_type(self, msg: Msg) -> str:
        action_type = str(msg.payload.get("action_type", "")).strip().lower()
        if action_type:
            return action_type

        if msg.type == MsgType.MOTOR_EMERGENCY_STOP:
            return "emergency_stop"
        if msg.type == MsgType.MOTOR_HOME_MOVE:
            return "home_move"
        if msg.type == MsgType.MOTOR_NEWLINE_MOVE:
            return "newline_move"
        return "print_move"

    def _estimate_wait(self, pulses: int) -> float:
        if pulses <= 0 or self._motor_speed <= 0 or self._pulses_per_rev <= 0:
            return 0.05
        pulses_per_sec = self._motor_speed * self._pulses_per_rev / 60.0
        return pulses / pulses_per_sec + 0.05

    @staticmethod
    def _default_priority(msg_type: str) -> int:
        if msg_type == MsgType.CMD_EMERGENCY_STOP:
            return 0
        if msg_type == MsgType.CMD_HOME:
            return 1
        if msg_type == MsgType.CMD_STOP_PRINT:
            return 2
        if msg_type == MsgType.CMD_PAUSE_PRINT:
            return 3
        if msg_type == MsgType.CMD_RESUME_PRINT:
            return 4
        if msg_type == MsgType.CMD_START_PRINT:
            return 5
        if msg_type == MsgType.CMD_RESET:
            return 6
        return 9

    @staticmethod
    def _clamp_position(value: int) -> int:
        return max(0, int(value))
