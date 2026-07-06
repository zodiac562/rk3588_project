"""
运动规划模块 —— 将盲文点位转换为电机动作序列。

输入: ChineseToBraille.convert_text() 的结果列表
输出: 动作序列，每项为 {type: "move_x"|"move_y"|"punch", ...}

布局说明:
    盲文每个字符占2列3行,共6个点
    - 第1列: 点1(左上), 点2(左中), 点3(左下)
    - 第2列: 点4(右上), 点5(右中), 点6(右下)
    
    每个汉字包含3个盲文格(声母/韵母/声调)
"""

import sys
from pathlib import Path

# 处理直接运行时的路径问题
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from translation.translation_language import ChineseToBraille
from config.loader import get_config


class ActionType(Enum):
    MOVE_X = "move_x"
    MOVE_Y = "move_y"
    PUNCH = "punch"


@dataclass
class Action:
    type: ActionType
    value: int
    desc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "desc": self.desc
        }


class MotionPlanner:

    DOT_POSITIONS: Dict[int, Tuple[int, int]] = {
        1: (0, 2),
        2: (0, 1),
        3: (0, 0),
        4: (1, 2),
        5: (1, 1),
        6: (1, 0),
    }

    DOT_ORDER = [3, 2, 1, 4, 5, 6]

    def __init__(self):
        cfg = get_config()
        layout = cfg["layout"]

        self.dot_gap = layout["dot_gap_pulse"]
        self.grid_gap = layout.get("grid_gap_pulse", 0)
        self.char_gap = layout["char_gap_pulse"]
        self.line_gap = layout["line_gap_pulse"]
        self.chars_per_line = layout["chars_per_line"]
        self.max_lines = layout["max_lines"]

        self._braille_converter = ChineseToBraille()

        self._current_x = 0
        self._current_y = 0

    def _reset_cursor(self, x: int = 0, y: int = 0) -> None:
        self._current_x = x
        self._current_y = y

    @staticmethod
    def _extract_dots_list(char_result: Dict[str, Any]) -> List[List[int]]:
        dots_list: List[List[int]] = []
        for key in ["braille_initial", "braille_final", "braille_tone"]:
            dots = char_result.get(key, [])
            if dots and any(d == 1 for d in dots):
                dots_list.append(dots)
        return dots_list

    def _plan_braille_results(self, braille_results: List[Dict[str, Any]], line_base_y: int = 0) -> List[Action]:
        actions: List[Action] = []

        for idx, char_result in enumerate(braille_results):
            dots_list = self._extract_dots_list(char_result)
            char_start_x = self._current_x

            for grid_idx, dots in enumerate(dots_list):
                grid_actions = self._plan_single_grid(dots, grid_idx, char_start_x, line_base_y)
                actions.extend(grid_actions)

            if idx < len(braille_results) - 1:
                move_distance = self.char_gap
                actions.append(Action(
                    type=ActionType.MOVE_X,
                    value=move_distance,
                    desc=f"字符间距: {move_distance}脉冲"
                ))
                self._current_x += self.char_gap

        return actions

    def plan(self, text: str) -> List[Action]:
        chinese_text = self._braille_converter.keep_only_chinese(text)
        if not chinese_text:
            return []

        braille_results = self._braille_converter.convert_text(chinese_text)
        self._reset_cursor()

        return self._plan_braille_results(braille_results, line_base_y=0)

    
    def _plan_single_grid(self, dots: List[int], grid_idx: int, char_start_x: int, line_base_y: int = 0) -> List[Action]:

        actions: List[Action] = []

        grid_dot3_x = char_start_x + grid_idx * (2 * self.dot_gap + self.grid_gap)

        for dot_num in self.DOT_ORDER:
            if dots[dot_num - 1] != 1:
                continue

            col, row = self.DOT_POSITIONS[dot_num]
            target_x = grid_dot3_x + col * self.dot_gap
            target_y = line_base_y + row * self.dot_gap

            if target_x != self._current_x:
                delta_x = target_x - self._current_x
                actions.append(Action(
                    type=ActionType.MOVE_X,
                    value=delta_x,
                    desc=f"移动到点{dot_num} X位置"
                ))
                self._current_x = target_x

            if target_y != self._current_y:
                delta_y = target_y - self._current_y
                actions.append(Action(
                    type=ActionType.MOVE_Y,
                    value=delta_y,
                    desc=f"移动到点{dot_num} Y位置"
                ))
                self._current_y = target_y

            actions.append(Action(
                type=ActionType.PUNCH,
                value=dot_num,
                desc=f"打点位置{dot_num}"
            ))

        end_x = grid_dot3_x + 1 * self.dot_gap
        end_y = line_base_y

        if end_x != self._current_x:
            delta_x = end_x - self._current_x
            actions.append(Action(
                type=ActionType.MOVE_X,
                value=delta_x,
                desc="格结束:移动到点位6"
            ))
            self._current_x = end_x

        if end_y != self._current_y:
            delta_y = end_y - self._current_y
            actions.append(Action(
                type=ActionType.MOVE_Y,
                value=delta_y,
                desc="格结束:移动到点位6"
            ))
            self._current_y = end_y

        return actions
    
    def plan_with_newline(
        self, text: str, max_chars_per_line: int = None,
        max_total_chars: int = None,
    ):
        if max_chars_per_line is None:
            max_chars_per_line = self.chars_per_line

        if not isinstance(max_chars_per_line, int) or max_chars_per_line <= 0:
            raise ValueError("max_chars_per_line 必须是正整数")
            
        chinese_text = self._braille_converter.keep_only_chinese(text)
        if not chinese_text:
            return ([], 0)

        total_capacity = max_chars_per_line * self.max_lines
        if len(chinese_text) > total_capacity:
            if max_total_chars is not None:
                chinese_text = chinese_text[:max_total_chars]
            else:
                raise ValueError(
                    f"文本长度 {len(chinese_text)} 超出最大版面容量 {total_capacity} "
                    f"(每行 {max_chars_per_line} 字，最多 {self.max_lines} 行)"
                )

        braille_results = self._braille_converter.convert_text(chinese_text)
        total_lines = (len(braille_results) + max_chars_per_line - 1) // max_chars_per_line
        all_actions: List[Action] = []

        self._reset_cursor()
        line_base_y = 0
        
        for line_index, start in enumerate(range(0, len(braille_results), max_chars_per_line)):
            line_results = braille_results[start:start + max_chars_per_line]
            all_actions.extend(self._plan_braille_results(line_results, line_base_y))
            
            if line_index < total_lines - 1:
                if self._current_x != 0:
                    delta_x = -self._current_x
                    all_actions.append(Action(
                        type=ActionType.MOVE_X,
                        value=delta_x,
                        desc=f"回退到行首: {delta_x}脉冲"
                    ))
                    self._current_x = 0
                
                newline_y_move = self.line_gap + 3 * self.dot_gap
                all_actions.append(Action(
                    type=ActionType.MOVE_Y,
                    value=newline_y_move,
                    desc=f"换行: {newline_y_move}脉冲 (行间距+3点距)"
                ))
                line_base_y += newline_y_move
                self._current_y = line_base_y
        
        return (all_actions, len(chinese_text))

    
    def estimate_time(self, actions: List[Action],
                     x_speed: float = 200,
                     y_speed: float = 200,
                     punch_time_ms: float = 50) -> float:
        total_time = 0.0

        for action in actions:
            if action.type == ActionType.MOVE_X:
                total_time += abs(action.value) / x_speed
            elif action.type == ActionType.MOVE_Y:
                total_time += abs(action.value) / y_speed
            elif action.type == ActionType.PUNCH:
                total_time += punch_time_ms / 1000.0

        return total_time

    def to_dict_list(self, actions: List[Action]) -> List[Dict[str, Any]]:
        return [action.to_dict() for action in actions]


def plan_text(text: str) -> List[Action]:
    planner = MotionPlanner()
    return planner.plan(text)


def plan_text_with_newline(text: str, max_chars_per_line: int = None) -> List[Action]:
    planner = MotionPlanner()
    actions, _ = planner.plan_with_newline(text, max_chars_per_line)
    return actions

