"""
电机动作计划线程。

职责：
1) 消费文字类消息（TEXT_CHAR）
2) 优先处理指令类消息（CMD_*）
3) 调用 MotionPlanner 生成动作序列
4) 在投递时完成动作细分，生产电机动作类消息（MOTOR_*）
"""

from __future__ import annotations

import threading
import time
from queue import Empty
from typing import Dict, List, Optional

from core.messages import Msg, MsgType, QueueBus
from core.motion_planner import Action, ActionType, MotionPlanner
from modules.config_manager import config_manager
from modules.logger_manager import logger_manager


class MotionPlannerThread(threading.Thread):
    """电机动作计划线程（文字 -> 动作 -> 电机消息）。"""

    def __init__(self, queue_bus: QueueBus, planner: Optional[MotionPlanner] = None) -> None:
        super().__init__(name="MotionPlannerThread", daemon=True)
        self._bus = queue_bus
        self._planner = planner or MotionPlanner()
        self._running = True
        self._paused = False
        self._logger = logger_manager.get_logger(__name__)
        self._position_files = config_manager.position_files
        self._pending_remainder: str = ""   # 换页暂存的剩余文字
        self._batch_overflow: bool = False   # 当前批次是否有超页分页

    def stop(self) -> None:
        """请求停止线程。"""
        self._running = False

    def run(self) -> None:
        self._logger.info("电机动作计划线程启动")

        while self._running:
            if self._handle_one_command():
                continue

            if self._paused:
                continue

            text_msg = self._bus.recv_text(timeout=0.1)
            if text_msg is None:
                continue

            try:
                if text_msg.type == MsgType.TEXT_BATCH:
                    text = str(text_msg.payload.get("text", ""))
                    if not text:
                        self._logger.warning("忽略空文本消息: payload=%s", text_msg.payload)
                        continue
                    self._process_text_batch(text, text_msg)
                elif text_msg.type == MsgType.TEXT_CHAR:
                    char = str(text_msg.payload.get("char", ""))
                    if not char:
                        self._logger.warning("忽略空字符消息: payload=%s", text_msg.payload)
                        continue
                    actions = self._planner.plan(char)
                    self._publish_motor_actions(actions=actions, source_msg=text_msg)
                else:
                    self._logger.warning("忽略非TEXT_CHAR/TEXT_BATCH消息: type=%s", text_msg.type)
                    continue
            except Exception as exc:
                self._logger.exception("动作规划失败: payload=%s err=%s", text_msg.payload, exc)
                self._bus.send_error(code="PLANNER_ERROR", msg=str(exc), src=self.name)

        self._logger.info("电机动作计划线程已退出")

    def _handle_one_command(self) -> bool:
        cmd_msg = self._bus.recv_cmd(timeout=0.001)
        if cmd_msg is None:
            return False

        cmd_type = cmd_msg.type

        if cmd_type in {
            MsgType.CMD_START_OCR,
            MsgType.CMD_STOP_OCR,
            MsgType.CMD_TRIGGER_TURN_PAGE,
        }:
            self._bus.send_cmd(cmd_msg, priority=self._default_priority(cmd_type))
            return True

        if cmd_type == MsgType.CMD_PAUSE_PRINT:
            self._paused = True
            self._logger.info("收到暂停指令，动作规划暂停")
            return True

        if cmd_type == MsgType.CMD_RESUME_PRINT:
            self._paused = False
            self._logger.info("收到恢复指令，动作规划继续")
            return True

        if cmd_type == MsgType.CMD_STOP_PRINT:
            self._paused = False
            self._pending_remainder = ""
            self._batch_overflow = False
            dropped = self._clear_text_queue()
            self._logger.info("收到停止指令，已清空文字队列和剩余文字: dropped=%s", dropped)
            return True

        if cmd_type == MsgType.CMD_EMERGENCY_STOP:
            self._paused = True
            self._pending_remainder = ""
            self._batch_overflow = False
            emergency_msg = Msg(
                type=MsgType.MOTOR_EMERGENCY_STOP,
                payload={"action_type": "emergency_stop", "reason": "from_cmd"},
                src=self.name,
            )
            ok = self._bus.send_motor(emergency_msg, block=True, timeout=3.0)
            if not ok:
                self._logger.error("急停 MOTOR_EMERGENCY_STOP 投递超时（motor_q 满）")
            self._logger.warning("收到急停指令，已投递 MOTOR_EMERGENCY_STOP")
            return True

        if cmd_type == MsgType.CMD_HOME:
            self._paused = True
            home_msg = Msg(
                type=MsgType.MOTOR_HOME_MOVE,
                payload={
                    "action_type": "home_move",
                    "position_file": self._position_files.get("x", ""),
                    "home_axis": "all",
                },
                src=self.name,
            )
            self._bus.send_motor(home_msg, block=True)
            self._logger.info("收到回零指令，已投递 MOTOR_HOME_MOVE")
            return True

        if cmd_type == MsgType.CMD_START_PRINT:
            if self._pending_remainder:
                remaining = self._pending_remainder
                self._pending_remainder = ""
                batch_msg = Msg(
                    type=MsgType.TEXT_BATCH,
                    payload={"text": remaining, "count": len(remaining)},
                    src=self.name,
                )
                self._bus.send_text(batch_msg, block=True)
                self._logger.info("换页确认，投递剩余文字: %s字", len(remaining))
            self._paused = False
            self._logger.info("收到开始打印指令")
            return True

        if cmd_type == MsgType.CMD_RESET:
            self._pending_remainder = ""
            self._batch_overflow = False
            dropped = self._clear_text_queue()
            self._paused = False
            self._logger.info("收到复位指令，清空文字队列和剩余文字: dropped=%s", dropped)
            return True

        self._bus.send_cmd(cmd_msg, priority=self._default_priority(cmd_type))
        return True

    def _publish_motor_actions(self, actions: List[Action], source_msg: Msg) -> None:
        char_index = int(source_msg.payload.get("index", -1))
        char_text = str(source_msg.payload.get("char") or source_msg.payload.get("text", ""))

        for seq, action in enumerate(actions):
            motor_msg = self._classify_action(action, seq=seq, char_index=char_index, char_text=char_text)
            ok = self._bus.send_motor(motor_msg, block=True)
            if not ok:
                self._logger.error("电机动作投递失败: %s", motor_msg)

    def _classify_action(self, action: Action, seq: int, char_index: int, char_text: str) -> Msg:
        payload: Dict[str, object] = {
            "action_type": "print_move",
            "source_action_type": action.type.value,
            "source_desc": action.desc,
            "char_index": char_index,
            "char_text": char_text,
            "sequence": seq,
            "position_file": self._position_files.get("x", ""),
        }

        if action.type == ActionType.PUNCH:
            msg_type = MsgType.MOTOR_PRINT_MOVE
            payload["punch_points"] = [action.value]
            return Msg(type=msg_type, payload=payload, src=self.name)

        if action.type == ActionType.MOVE_X:
            payload["x_delta"] = int(action.value)
            if "回退到行首" in action.desc:
                payload["action_type"] = "newline_move"
                msg_type = MsgType.MOTOR_NEWLINE_MOVE
            else:
                msg_type = MsgType.MOTOR_PRINT_MOVE
            return Msg(type=msg_type, payload=payload, src=self.name)

        if action.type == ActionType.MOVE_Y:
            payload["y_delta"] = int(action.value)
            if "换行" in action.desc:
                payload["action_type"] = "newline_move"
                msg_type = MsgType.MOTOR_NEWLINE_MOVE
            else:
                msg_type = MsgType.MOTOR_PRINT_MOVE
            return Msg(type=msg_type, payload=payload, src=self.name)

        payload["unknown_value"] = int(action.value)
        return Msg(type=MsgType.MOTOR_PRINT_MOVE, payload=payload, src=self.name)

    def _process_text_batch(self, text: str, source_msg: Msg) -> None:
        chinese_text = self._planner._braille_converter.keep_only_chinese(text)
        if not chinese_text:
            self._logger.warning("文本过滤后无中文字符，跳过并发送 IDLE")
            self._bus.send_status(Msg(
                type=MsgType.STATUS_STATE,
                payload={"new_state": "IDLE", "reason": "no_chinese"},
                src=self.name,
            ))
            return

        total_capacity = self._planner.chars_per_line * self._planner.max_lines
        actions, consumed = self._planner.plan_with_newline(chinese_text, max_total_chars=total_capacity)

        if not actions:
            return

        self._publish_motor_actions(actions=actions, source_msg=source_msg)

        if consumed < len(chinese_text):
            self._pending_remainder = chinese_text[consumed:]
            self._batch_overflow = True
            self._paused = True

            home_msg = Msg(
                type=MsgType.MOTOR_HOME_MOVE,
                payload={
                    "action_type": "home_move",
                    "position_file": self._position_files.get("x", ""),
                    "home_axis": "all",
                },
                src=self.name,
            )
            ok = self._bus.send_motor(home_msg, block=True, timeout=3.0)
            if not ok:
                self._logger.error("换页回零 MOTOR_HOME_MOVE 投递超时，取消本次换页")
                self._pending_remainder = ""
                self._batch_overflow = False
                self._paused = False
                return

            time.sleep(0.5)

            self._bus.send_status(Msg(
                type=MsgType.STATUS_PAGE_COMPLETE,
                payload={
                    "remaining_chars": len(self._pending_remainder),
                    "consumed_chars": consumed,
                },
                src=self.name,
            ))
            self._bus.signal_page_complete({
                "remaining_chars": len(self._pending_remainder),
                "consumed_chars": consumed,
            })
            self._logger.info(
                "文字超页(消费%s/%s字)，已触发回零+换页信号，剩余%s字",
                consumed, len(chinese_text), len(self._pending_remainder),
            )

    def _clear_text_queue(self) -> int:
        dropped = 0
        while True:
            try:
                self._bus.text_q.get_nowait()
                dropped += 1
            except Empty:
                break
        return dropped

    @staticmethod
    def _default_priority(msg_type: str) -> int:
        """根据消息类型返回默认优先级，用于重新放回队列。"""
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
