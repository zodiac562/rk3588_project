"""
OCR 识别适配模块（模拟版）。

当前阶段不接入真实 OCR 引擎：
- 输入来源：命令行传入的 JSON 字符串（模拟 OCR 结果）
- 输出结果：提取文本并拆分为单个汉字

后续可在不改调用方的情况下，将 `_extract_text_from_payload` 替换为真实 OCR 输出协议解析。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.messages import Msg, MsgType
from modules.logger_manager import logger_manager


class OCRAdapterError(ValueError):
    pass


@dataclass
class OCRMockResult:

    raw_json: str
    text: str
    chars: List[str]
    meta: Dict[str, Any]


class OCRAdapter:

    def __init__(self, source_name: str = "mock-ocr-cli") -> None:
        self.source_name = source_name
        self._logger = logger_manager.get_logger(__name__)

    def parse_mock_json(self, raw_json: str, chinese_only: bool = True) -> OCRMockResult:
        if not isinstance(raw_json, str) or not raw_json.strip():
            raise OCRAdapterError("OCR 输入不能为空 JSON 字符串")

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise OCRAdapterError(f"OCR JSON 解析失败: {exc}") from exc

        text = self._extract_text_from_payload(payload)
        if not text:
            raise OCRAdapterError("OCR JSON 中未找到可用文本字段")

        chars = self.split_to_chars(text=text, chinese_only=chinese_only)
        if not chars:
            raise OCRAdapterError("OCR 文本中没有可用字符")

        meta = {
            "source": self.source_name,
            "raw_length": len(raw_json),
            "text_length": len(text),
            "char_count": len(chars),
            "chinese_only": chinese_only,
        }
        self._logger.info("OCR 模拟解析完成: text_len=%s chars=%s", len(text), len(chars))
        return OCRMockResult(raw_json=raw_json, text=text, chars=chars, meta=meta)

    def build_text_msgs(self, chars: List[str], src: Optional[str] = None) -> List[Msg]:
        sender = src or self.source_name
        messages: List[Msg] = []
        for idx, ch in enumerate(chars):
            messages.append(
                Msg(
                    type=MsgType.TEXT_CHAR,
                    payload={"char": ch, "index": idx},
                    src=sender,
                )
            )
        return messages

    def parse_and_build_msgs(self, raw_json: str, chinese_only: bool = True, src: Optional[str] = None) -> List[Msg]:
        result = self.parse_mock_json(raw_json=raw_json, chinese_only=chinese_only)
        return self.build_text_msgs(chars=result.chars, src=src)

    def parse_book_ocr_result(
        self,
        raw_list: List[str],
        formatted_text: str,
        src: Optional[str] = None,
    ) -> List[Msg]:
        sender = src or self.source_name
        messages: List[Msg] = []

        chars = [ch for ch in formatted_text if not ch.isspace()]
        messages.append(
            Msg(
                type=MsgType.TEXT_BATCH,
                payload={
                    "text": formatted_text,
                    "count": len(raw_list),
                    "chars": chars,
                },
                src=sender,
            )
        )

        self._logger.info(
            "BookOCR 结果解析完成: blocks=%s, chars=%s",
            len(raw_list), len(chars),
        )
        return messages

    @staticmethod
    def split_to_chars(text: str, chinese_only: bool = True) -> List[str]:
        chars = [ch for ch in text if not ch.isspace()]
        if chinese_only:
            chars = [ch for ch in chars if OCRAdapter._is_chinese_char(ch)]
        return chars

    @staticmethod
    def _extract_text_from_payload(payload: Any) -> str:
        if isinstance(payload, dict):
            direct_text = payload.get("text")
            if isinstance(direct_text, str) and direct_text.strip():
                return direct_text.strip()

            result = payload.get("result")
            if isinstance(result, dict):
                nested_text = result.get("text")
                if isinstance(nested_text, str) and nested_text.strip():
                    return nested_text.strip()

            lines = payload.get("lines")
            if isinstance(lines, list):
                line_strs = [line.strip() for line in lines if isinstance(line, str) and line.strip()]
                if line_strs:
                    return "".join(line_strs)

            data = payload.get("data")
            if isinstance(data, list):
                parts: List[str] = []
                for item in data:
                    if isinstance(item, dict):
                        t = item.get("text")
                        if isinstance(t, str) and t.strip():
                            parts.append(t.strip())
                    elif isinstance(item, str) and item.strip():
                        parts.append(item.strip())
                if parts:
                    return "".join(parts)

            return ""

        if isinstance(payload, str):
            return payload.strip()

        return ""

    @staticmethod
    def _is_chinese_char(ch: str) -> bool:
        if len(ch) != 1:
            return False
        code = ord(ch)
        return 0x4E00 <= code <= 0x9FFF
