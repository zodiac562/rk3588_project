"""
电磁铁控制模块

支持两种模式：
- Mock模式：仅记录日志，不执行真实 GPIO 控制
- 真实模式：通过 gpiod 库控制 GPIO 输出高低电平

打点逻辑：
- 初始状态：低电平（电磁铁收缩）
- 打点过程：高电平（伸出）→ 延时 → 低电平（收缩）
- 高低电平循环一次即为一次完整打点
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from modules import config_manager, logger_manager


@dataclass
class PunchResult:
    success: bool
    duration_ms: int
    message: str = ""


class Solenoid:

    def __init__(self, punch_duration_ms: Optional[int] = None, use_real_gpio: bool = False):
        self._logger = logger_manager.get_logger("solenoid")
        self._gpio_chip_path = config_manager.solenoid_gpio_chip
        self._gpio_line_num = config_manager.solenoid_gpio_line
        self._punch_duration_ms = (
            int(punch_duration_ms)
            if punch_duration_ms is not None
            else int(config_manager.solenoid_punch_duration_ms)
        )
        self._use_real_gpio = use_real_gpio

        self._request = None

        if self._use_real_gpio:
            self._init_gpio()
        else:
            self._logger.info(
                "Solenoid Mock 初始化完成: gpio_chip=%s gpio_line=%s duration=%sms",
                self._gpio_chip_path,
                self._gpio_line_num,
                self._punch_duration_ms,
            )

    def _init_gpio(self) -> None:
        try:
            import gpiod
            from gpiod.line import Direction, Value

            self._request = gpiod.request_lines(
                self._gpio_chip_path,
                consumer="braille_solenoid",
                config={
                    self._gpio_line_num: gpiod.LineSettings(
                        direction=Direction.OUTPUT,
                        output_value=Value.INACTIVE,  # 初始低电平（收缩状态）
                    ),
                },
            )

            self._logger.info(
                "Solenoid GPIO 初始化完成: chip=%s line=%s duration=%sms",
                self._gpio_chip_path,
                self._gpio_line_num,
                self._punch_duration_ms,
            )
        except ImportError:
            self._logger.error("gpiod 库未安装，无法使用真实 GPIO 模式")
            raise RuntimeError("gpiod 库未安装，请执行: pip install gpiod")
        except Exception as e:
            self._logger.error("GPIO 初始化失败: %s", e)
            raise

    @property
    def punch_duration_ms(self) -> int:
        return self._punch_duration_ms

    def punch(self, point: Optional[int] = None) -> PunchResult:
        start = time.time()

        try:
            if self._use_real_gpio and self._request:
                self._punch_gpio()
            else:
                time.sleep(max(self._punch_duration_ms, 0) / 1000.0)

            elapsed_ms = int((time.time() - start) * 1000)

            if point is None:
                self._logger.info(
                    "[%s] 电磁铁打点: duration=%sms",
                    "GPIO" if self._use_real_gpio else "MOCK",
                    elapsed_ms,
                )
            else:
                self._logger.info(
                    "[%s] 电磁铁打点 point=%s duration=%sms",
                    "GPIO" if self._use_real_gpio else "MOCK",
                    point,
                    elapsed_ms,
                )

            return PunchResult(success=True, duration_ms=elapsed_ms, message="punch ok")

        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            self._logger.error("打点失败: %s", e)
            return PunchResult(success=False, duration_ms=elapsed_ms, message=str(e))

    def _punch_gpio(self) -> None:
        from gpiod.line import Value

        self._request.set_value(self._gpio_line_num, Value.ACTIVE)

        time.sleep(max(self._punch_duration_ms, 0) / 1000.0)

        self._request.set_value(self._gpio_line_num, Value.INACTIVE)

    def release(self) -> None:
        if self._use_real_gpio and self._request:
            try:
                from gpiod.line import Value

                self._request.set_value(self._gpio_line_num, Value.INACTIVE)
                self._request.release()
                self._logger.info("Solenoid GPIO 资源已释放")
            except Exception as e:
                self._logger.warning("释放 GPIO 资源时出错: %s", e)
        else:
            self._logger.info("Solenoid Mock 释放资源")
