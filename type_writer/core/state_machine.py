"""
状态机模块 —— 管理盲文打印系统的3状态生命周期。

状态定义:
    IDLE     - 空闲状态，可接受打印任务
    PRINTING - 打印中，正在执行动作序列
    ERROR    - 错误状态，需要手动复位

合法状态转移:
    IDLE → PRINTING (开始打印)
    PRINTING → IDLE (打印完成/停止)
    PRINTING → ERROR (打印错误)
    ERROR → IDLE (复位)
"""

from enum import Enum, auto
from typing import Callable, Optional, Dict, Set, Tuple
from dataclasses import dataclass


class State(Enum):
    IDLE = "IDLE"
    PRINTING = "PRINTING"
    ERROR = "ERROR"


class StateTransitionError(Exception):
    pass


@dataclass
class StateChangeEvent:
    old_state: State
    new_state: State
    reason: str
    ts: float


class StateMachine:

    _VALID_TRANSITIONS: Set[Tuple[State, State]] = {
        (State.IDLE, State.PRINTING),
        (State.PRINTING, State.IDLE),
        (State.PRINTING, State.ERROR),
        (State.ERROR, State.IDLE),
    }

    def __init__(self, on_change: Optional[Callable[[StateChangeEvent], None]] = None):
        self._state = State.IDLE
        self._on_change = on_change
        self._history: list[StateChangeEvent] = []

    @property
    def state(self) -> State:
        return self._state

    @property
    def is_idle(self) -> bool:
        return self._state == State.IDLE

    @property
    def is_printing(self) -> bool:
        return self._state == State.PRINTING

    @property
    def is_error(self) -> bool:
        return self._state == State.ERROR

    def can_transition_to(self, new_state: State) -> bool:
        return (self._state, new_state) in self._VALID_TRANSITIONS

    def transition(self, new_state: State, reason: str = "") -> StateChangeEvent:
        if not self.can_transition_to(new_state):
            raise StateTransitionError(
                f"非法状态转移: {self._state.value} -> {new_state.value}"
            )

        old_state = self._state
        self._state = new_state

        import time
        event = StateChangeEvent(
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            ts=time.time()
        )
        self._history.append(event)

        if self._on_change:
            try:
                self._on_change(event)
            except Exception:
                pass

        return event

    def start_printing(self, reason: str = "开始打印") -> StateChangeEvent:
        return self.transition(State.PRINTING, reason)

    def finish_printing(self, reason: str = "打印完成") -> StateChangeEvent:
        return self.transition(State.IDLE, reason)

    def set_error(self, reason: str = "发生错误") -> StateChangeEvent:
        return self.transition(State.ERROR, reason)

    def reset(self, reason: str = "系统复位") -> StateChangeEvent:
        return self.transition(State.IDLE, reason)

    def get_history(self, limit: int = 10) -> list[StateChangeEvent]:
        return self._history[-limit:][::-1]

    def __repr__(self) -> str:
        return f"StateMachine(state={self._state.value})"
