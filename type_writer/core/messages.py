"""
统一消息结构 + 线程间 Queue 封装。
所有线程间通信一律通过 Msg dataclass 流转，便于日志追踪与协议扩展。
"""

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue, PriorityQueue, Full, Empty
from typing import Any, Dict, Optional, Tuple


# ── 消息类型枚举（四层架构） ────────────────────────────────────────────

class MsgType(str, Enum):
    TEXT_CHAR = "TEXT_CHAR"
    TEXT_BATCH = "TEXT_BATCH"

    MOTOR_PRINT_MOVE = "MOTOR_PRINT_MOVE"
    MOTOR_NEWLINE_MOVE = "MOTOR_NEWLINE_MOVE"
    MOTOR_HOME_MOVE = "MOTOR_HOME_MOVE"
    MOTOR_EMERGENCY_STOP = "MOTOR_EMERGENCY_STOP"

    STATUS_POSITION = "STATUS_POSITION"
    STATUS_STATE = "STATUS_STATE"
    STATUS_PROGRESS = "STATUS_PROGRESS"
    STATUS_ERROR = "STATUS_ERROR"
    STATUS_PAGE_COMPLETE = "STATUS_PAGE_COMPLETE"

    CMD_START_PRINT = "CMD_START_PRINT"
    CMD_PAUSE_PRINT = "CMD_PAUSE_PRINT"
    CMD_RESUME_PRINT = "CMD_RESUME_PRINT"
    CMD_STOP_PRINT = "CMD_STOP_PRINT"
    CMD_EMERGENCY_STOP = "CMD_EMERGENCY_STOP"
    CMD_HOME = "CMD_HOME"
    CMD_RESET = "CMD_RESET"

    CMD_START_OCR = "CMD_START_OCR"
    CMD_STOP_OCR = "CMD_STOP_OCR"
    CMD_TRIGGER_TURN_PAGE = "CMD_TRIGGER_TURN_PAGE"


# ── 统一消息结构 ────────────────────────────────────────────

@dataclass
class Msg:
    type: str
    payload: Dict[str, Any]
    ts: float = field(default_factory=time.time)
    src: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Msg":
        d = json.loads(json_str)
        return cls(type=d["type"], payload=d["payload"], ts=d.get("ts", 0), src=d.get("src", ""))

    def __repr__(self) -> str:
        return f"Msg(type={self.type}, src={self.src}, payload_keys={list(self.payload.keys())})"


# ── Queue 总线（四层架构） ──────────────────────────────────────────────

class QueueBus:
    """
    四层消息总线：文字类、电机动作类、状态类、指令类
    所有线程共享同一个 QueueBus 实例。

    Queue 划分:
      text_q   : 文字类消息，大容量，禁止丢弃
      motor_q  : 电机动作类消息，大容量，禁止丢弃
      status_q : 状态类消息，中等容量，满时丢弃旧消息
      cmd_q    : 指令类消息，优先级队列，最高优先级，禁止丢弃
    """

    # 队列容量常量
    TEXT_Q_SIZE = 1000      # 文字类消息队列大小
    MOTOR_Q_SIZE = 2000     # 电机动作类消息队列大小
    STATUS_Q_SIZE = 256     # 状态类消息队列大小
    CMD_Q_SIZE = 50         # 指令类消息队列大小

    def __init__(self):
        self.text_q: Queue[Msg] = Queue(maxsize=self.TEXT_Q_SIZE)
        self.motor_q: Queue[Msg] = Queue(maxsize=self.MOTOR_Q_SIZE)
        self.status_q: Queue[Msg] = Queue(maxsize=self.STATUS_Q_SIZE)
        self.cmd_q: PriorityQueue[Tuple[int, int, Msg]] = PriorityQueue(maxsize=self.CMD_Q_SIZE)
        self._cmd_seq: int = 0

        self._page_complete_event = threading.Event()
        self._page_complete_info: Dict[str, Any] = {}
        self._page_info_lock = threading.Lock()

    def send_text(self, msg: Msg, block: bool = True, timeout: float = None) -> bool:
        try:
            self.text_q.put(msg, block=block, timeout=timeout)
            return True
        except Full:
            return False

    def send_motor(self, msg: Msg, block: bool = True, timeout: float = None) -> bool:
        try:
            self.motor_q.put(msg, block=block, timeout=timeout)
            return True
        except Full:
            return False

    def send_status(self, msg: Msg) -> bool:
        if self.status_q.full():
            try:
                self.status_q.get_nowait()
            except Empty:
                pass
        self.status_q.put_nowait(msg)
        return True

    def send_cmd(self, msg: Msg, priority: int = 5) -> bool:
        try:
            self._cmd_seq += 1
            self.cmd_q.put((priority, self._cmd_seq, msg), block=True, timeout=2.0)
            return True
        except Full:
            return False

    def send_error(self, code: str, msg: str, src: str = "") -> None:
        self.send_status(Msg(
            type=MsgType.STATUS_ERROR,
            payload={"code": code, "msg": msg},
            src=src,
        ))

    def signal_page_complete(self, info: Dict[str, Any]) -> None:
        with self._page_info_lock:
            self._page_complete_info = info.copy()
        self._page_complete_event.set()

    def is_page_complete(self) -> bool:
        return self._page_complete_event.is_set()

    def get_page_complete_info(self) -> Dict[str, Any]:
        with self._page_info_lock:
            return self._page_complete_info.copy()

    def clear_page_complete(self) -> None:
        self._page_complete_event.clear()
        with self._page_info_lock:
            self._page_complete_info.clear()

    def recv_text(self, timeout: Optional[float] = None) -> Optional[Msg]:
        try:
            return self.text_q.get(timeout=timeout)
        except Exception:
            return None

    def recv_motor(self, timeout: Optional[float] = None) -> Optional[Msg]:
        try:
            return self.motor_q.get(timeout=timeout)
        except Exception:
            return None

    def recv_status(self, timeout: Optional[float] = 0.1) -> Optional[Msg]:
        try:
            return self.status_q.get(timeout=timeout)
        except Exception:
            return None

    def recv_cmd(self, timeout: Optional[float] = None) -> Optional[Msg]:
        try:
            _, _, msg = self.cmd_q.get(timeout=timeout)
            return msg
        except Exception:
            return None

    def peek_cmd_priority(self) -> Optional[int]:
        if self.cmd_q.empty():
            return None
        return 0
