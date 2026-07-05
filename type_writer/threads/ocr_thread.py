"""
OCR 线程（支持 CLI 模拟 + 真实 OCR 自动循环）。

职责：
1) CLI 模拟模式：从命令行读取 JSON 字符串（模拟 OCR 输出）
2) 真实 OCR 模式：响应 CMD_START_OCR，调用 BookOCR 识别，自动循环
3) 将识别结果转换为 TEXT_BATCH 消息投递到 QueueBus.text_q
"""

from __future__ import annotations

import time
import threading
from typing import Callable, Optional

import numpy as np

from core.messages import QueueBus, Msg, MsgType
from modules.logger_manager import logger_manager
from ocr.ocr_adapter import OCRAdapter, OCRAdapterError


class OCRThread(threading.Thread):

    def __init__(
        self,
        queue_bus: QueueBus,
        config_manager=None,
        adapter: Optional[OCRAdapter] = None,
        input_func: Callable[[str], str] = input,
        stop_commands: tuple[str, ...] = ("/quit", "/exit", "quit", "exit"),
    ) -> None:
        super().__init__(name="OCRThread", daemon=True)
        self._bus = queue_bus
        self._adapter = adapter or OCRAdapter(source_name="ocr-thread")

        # 延迟加载 config_manager
        if config_manager is None:
            from modules.config_manager import get_config_manager
            config_manager = get_config_manager()
        self._cfg = config_manager

        self._input = input_func
        self._stop_commands = {cmd.lower() for cmd in stop_commands}

        # 配置
        self._enable_cli = self._cfg.ocr_enable_cli
        self._enable_real = self._cfg.ocr_enable_real
        self._max_chars = self._cfg.ocr_max_chars_before_stop
        self._page_turn_delay = self._cfg.page_turner_delay_after_turn_ms / 1000.0

        # 状态
        self._running = True
        self._auto_loop = False
        self._book_ocr: Optional[BookOCR] = None
        self._total_chars = 0

        self._logger = logger_manager.get_logger(__name__)

    def stop(self) -> None:
        self._running = False
        self._auto_loop = False

    def run(self) -> None:
        self._logger.info("OCR线程启动: cli=%s, real=%s", self._enable_cli, self._enable_real)

        if self._enable_cli:
            self._logger.info("CLI 模拟模式已启用，请输入OCR JSON；输入 /quit 可退出")

        while self._running:
            self._handle_commands()

            if self._auto_loop and self._enable_real:
                self._do_ocr_cycle()
                continue

            if self._enable_cli:
                if self._enable_real:
                    time.sleep(0.1)
                else:
                    self._handle_cli_input()
            else:
                time.sleep(0.1)

        self._cleanup()
        self._logger.info("OCR线程已退出")

    def _handle_commands(self) -> None:
        cmd_msg = self._bus.recv_cmd(timeout=0.1)
        if cmd_msg is None:
            return

        if cmd_msg.type == MsgType.CMD_START_OCR:
            self._logger.info("收到 CMD_START_OCR，启动 OCR 自动循环")
            self._auto_loop = True

        elif cmd_msg.type == MsgType.CMD_STOP_OCR:
            self._logger.info("收到 CMD_STOP_OCR，停止 OCR 自动循环")
            self._auto_loop = False

    def _do_ocr_cycle(self) -> None:
        from ocr.book_ocr import BookOCR, BookOCRError

        if self._book_ocr is None:
            try:
                self._book_ocr = BookOCR(config_manager=self._cfg)
            except BookOCRError as exc:
                self._logger.error("BookOCR 初始化失败: %s", exc)
                self._auto_loop = False
                return

        try:
            img = self._capture_image()
            raw_list, formatted_text = self._book_ocr.recognize(img)
        except Exception as exc:
            self._logger.exception("OCR 识别失败: %s", exc)
            return

        try:
            messages = self._adapter.parse_book_ocr_result(
                raw_list, formatted_text, src=self.name,
            )
            for msg in messages:
                ok = self._bus.send_text(msg, block=True)
                if not ok:
                    self._logger.error("TEXT_BATCH 投递失败（队列已满）: %s", msg)
        except Exception as exc:
            self._logger.exception("OCR 结果解析失败: %s", exc)
            return

        self._total_chars += len(formatted_text.replace("\n", ""))
        self._logger.info(
            "OCR 识别完成: blocks=%s, total_chars=%s",
            len(raw_list), self._total_chars,
        )

        self._logger.debug("等待文字消费完毕...")
        page_complete = False
        while self._running and self._auto_loop:
            cmd_msg = self._bus.recv_cmd(timeout=0.1)
            if cmd_msg and cmd_msg.type in (MsgType.CMD_EMERGENCY_STOP, MsgType.CMD_STOP_OCR):
                self._logger.info("等待IDLE期间收到急停/停止指令，退出等待")
                self._auto_loop = False
                return
            status_msg = self._bus.recv_status(timeout=0.3)
            if status_msg is None:
                continue
            if status_msg.type == MsgType.STATUS_PAGE_COMPLETE:
                page_complete = True
                self._logger.info(
                    "检测到页满信号，剩余%s字待确认",
                    status_msg.payload.get("remaining_chars", 0),
                )
            if status_msg.type == MsgType.STATUS_STATE:
                new_state = status_msg.payload.get("new_state")
                if new_state == "IDLE":
                    self._logger.debug("文字消费完毕")
                    break

        if page_complete:
            self._logger.info("页满等待中：等待换页确认...")
            while self._running and self._auto_loop:
                cmd_msg = self._bus.recv_cmd(timeout=0.1)
                if cmd_msg is None:
                    continue
                if cmd_msg.type in (MsgType.CMD_EMERGENCY_STOP, MsgType.CMD_STOP_OCR):
                    self._logger.info("页满等待期间收到急停/停止指令，退出")
                    self._auto_loop = False
                    return
                if cmd_msg.type == MsgType.CMD_START_PRINT:
                    self._logger.info("收到换页确认，等待剩余文字消费...")
                    break
                if cmd_msg.type == MsgType.CMD_RESET:
                    self._logger.info("用户拒绝换页，跳过翻书")
                    return

            while self._running and self._auto_loop:
                cmd_msg = self._bus.recv_cmd(timeout=0.1)
                if cmd_msg and cmd_msg.type in (MsgType.CMD_EMERGENCY_STOP, MsgType.CMD_STOP_OCR):
                    self._logger.info("等待剩余文字期间收到急停/停止指令，退出")
                    self._auto_loop = False
                    return
                status_msg = self._bus.recv_status(timeout=0.3)
                if status_msg is None:
                    continue
                if status_msg.type == MsgType.STATUS_STATE:
                    if status_msg.payload.get("new_state") == "IDLE":
                        self._logger.debug("剩余文字消费完毕，触发翻书")
                        break

        self._bus.send_cmd(
            Msg(type=MsgType.CMD_TRIGGER_TURN_PAGE, payload={}, src=self.name),
            priority=5,
        )

        self._logger.debug("等待翻书延时: %.1fs", self._page_turn_delay)
        time.sleep(self._page_turn_delay)

        if self._total_chars >= self._max_chars:
            self._logger.info("已达到字数上限 %s，停止 OCR 自动循环", self._max_chars)
            self._auto_loop = False

    def _capture_image(self) -> np.ndarray:
        from ocr.book_ocr import capture_from_camera, enhance_text_image
        img = capture_from_camera(
            camera_id=self._cfg.ocr_camera_id,
            save_path=self._cfg.ocr_save_path,
        )
        img = enhance_text_image(img)
        return img

    def _handle_cli_input(self) -> None:
        if self._auto_loop:
            return
        try:
            raw = self._input("OCR JSON> ").strip()
        except EOFError:
            self._logger.info("检测到输入结束，OCR线程退出")
            self._running = False
            return
        except KeyboardInterrupt:
            self._logger.info("检测到中断信号，OCR线程退出")
            self._running = False
            return

        if not raw:
            return

        if raw.lower() in self._stop_commands:
            self._logger.info("收到退出命令，OCR线程停止")
            self._running = False
            return

        try:
            result = self._adapter.parse_mock_json(raw_json=raw, chinese_only=True)
            messages = [
                Msg(
                    type=MsgType.TEXT_BATCH,
                    payload={"text": "".join(result.chars), "count": len(result.chars)},
                    src=self.name,
                )
            ]
        except OCRAdapterError as exc:
            self._logger.warning("OCR输入解析失败: %s", exc)
            self._bus.send_error(code="OCR_PARSE_ERROR", msg=str(exc), src=self.name)
            return
        except Exception as exc:
            self._logger.exception("OCR线程出现未预期异常: %s", exc)
            self._bus.send_error(code="OCR_UNKNOWN_ERROR", msg=str(exc), src=self.name)
            return

        sent = 0
        for msg in messages:
            ok = self._bus.send_text(msg, block=True)
            if ok:
                sent += 1
            else:
                self._logger.error("TEXT_BATCH 投递失败（队列已满）: %s", msg)

        self._logger.info(
            "OCR消息投递完成: chars=%s sent=%s",
            messages[0].payload.get("count", 0), sent,
        )

    def _cleanup(self) -> None:
        if self._book_ocr is not None:
            self._book_ocr.release()
            self._book_ocr = None
            self._logger.debug("BookOCR 资源已释放")
