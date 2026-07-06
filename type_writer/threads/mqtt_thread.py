"""
MQTT 线程（MQTT Thread）。

职责：
1) 接收外部 MQTT 消息，解析映射为 CMD 指令投递到 cmd_q
2) 监听 status_q 中的状态类消息，转发至 MQTT broker

消息格式（可在 yaml 的 mqtt.message_format 段中配置）:
  - 默认格式: JSON { "type": "CMD_START_PRINT", "payload": {...} }
  - 收到后直接解析 type 字段，映射到 MsgType 枚举值投递到 cmd_q

MQTT 状态转发:
  - 从 status_q 取出 STATUS_POSITION / STATUS_PROGRESS / STATUS_STATE / STATUS_ERROR
  - 通过 MQTT publish 到对应主题
"""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Dict, Optional

from core.messages import Msg, MsgType, QueueBus
from modules.logger_manager import logger_manager

try:
    import paho.mqtt.client as mqtt
    HAS_PAHO = True
except ImportError:
    mqtt = None  # type: ignore
    HAS_PAHO = False


class MQTTThread(threading.Thread):

    DEFAULT_CMD_MAP: Dict[str, str] = {
        "CMD_START_PRINT": "CMD_START_PRINT",
        "CMD_STOP_PRINT": "CMD_STOP_PRINT",
        "CMD_PAUSE_PRINT": "CMD_PAUSE_PRINT",
        "CMD_RESUME_PRINT": "CMD_RESUME_PRINT",
        "CMD_EMERGENCY_STOP": "CMD_EMERGENCY_STOP",
        "CMD_START_OCR": "CMD_START_OCR",
        "CMD_STOP_OCR": "CMD_STOP_OCR",
        "CMD_TRIGGER_TURN_PAGE": "CMD_TRIGGER_TURN_PAGE",
        "CMD_HOME": "CMD_HOME",
        "CMD_RESET": "CMD_RESET",
    }

    def __init__(
        self,
        queue_bus: QueueBus,
        config_manager=None,
        enable: bool = False,
        cmd_map: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name="MQTTThread", daemon=True)
        self._bus = queue_bus

        if config_manager is None:
            from modules.config_manager import get_config_manager
            config_manager = get_config_manager()
        self._cfg = config_manager

        self._enable = enable
        self._cmd_map = cmd_map or self.DEFAULT_CMD_MAP

        # MQTT 配置
        self._broker = self._cfg.mqtt_broker
        self._port = self._cfg.mqtt_port
        self._client_id = self._cfg.mqtt_client_id
        self._keepalive = self._cfg.mqtt_keepalive
        self._topics = self._cfg.mqtt_topics
        self._reconnect_min = self._cfg._config.get("mqtt", {}).get("reconnect_delay_min", 1)
        self._reconnect_max = self._cfg._config.get("mqtt", {}).get("reconnect_delay_max", 30)

        self._subscribe_topics: Dict[str, int] = {}
        self._publish_topics: Dict[str, str] = {}

        self._running = True
        self._connected = False
        self._logger = logger_manager.get_logger(__name__)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        if not self._enable:
            self._logger.info("MQTT 线程未启用，跳过")
            return

        if not HAS_PAHO:
            self._logger.warning("paho-mqtt 未安装，MQTT 线程退出")
            return

        self._prepare_topics()
        self._logger.info(
            "MQTT 线程启动: broker=%s:%s client=%s",
            self._broker, self._port, self._client_id,
        )

        client = mqtt.Client(client_id=self._client_id)

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        while self._running:
            try:
                self._logger.debug("MQTT 连接中... %s:%s", self._broker, self._port)
                client.connect(self._broker, self._port, self._keepalive)
                client.loop_start()

                for _ in range(100):
                    if self._connected or not self._running:
                        break
                    time.sleep(0.1)

                if self._connected:
                    self._main_loop(client)
                    client.loop_stop()
                    client.disconnect()
                else:
                    self._logger.warning("MQTT 连接超时，将重试")
                    client.loop_stop()

            except Exception as exc:
                self._logger.error("MQTT 异常: %s，将重试", exc)
                try:
                    client.loop_stop()
                except Exception:
                    pass

            if self._running:
                delay = min(self._reconnect_max, self._reconnect_min)
                self._logger.info("MQTT %d秒后重连", delay)
                time.sleep(delay)

        self._logger.info("MQTT 线程已退出")

    def _prepare_topics(self) -> None:
        subscribe_raw = self._topics.get("subscribe", {})
        for key, topic in subscribe_raw.items():
            self._subscribe_topics[str(topic)] = 0  # QoS 0

        publish_raw = self._topics.get("publish", {})
        self._publish_topics = {
            key: str(topic) for key, topic in publish_raw.items()
        }

    def _main_loop(self, client) -> None:
        while self._running and self._connected:
            try:
                status_msg = self._bus.recv_status(timeout=0.5)
                if status_msg is not None:
                    self._forward_status(status_msg, client)
            except queue.Empty:
                continue
            except Exception as exc:
                self._logger.exception("状态消息转发异常: %s", exc)

    def _forward_status(self, msg: Msg, client) -> None:
        topic = self._get_publish_topic(msg.type)
        if topic is None:
            return

        try:
            payload = msg.to_json()
            client.publish(topic, payload, qos=0)
            self._logger.debug("MQTT 转发: topic=%s type=%s", topic, msg.type)
        except Exception as exc:
            self._logger.error("MQTT publish 失败: topic=%s err=%s", topic, exc)

    def _get_publish_topic(self, msg_type: str) -> Optional[str]:
        topic_map = {
            MsgType.STATUS_STATE: self._publish_topics.get("state"),
            MsgType.STATUS_POSITION: self._publish_topics.get("position"),
            MsgType.STATUS_ERROR: self._publish_topics.get("error"),
            MsgType.STATUS_PROGRESS: self._publish_topics.get("state"),  # 进度用 state 主题
        }
        return topic_map.get(msg_type)  # type: ignore

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            self._logger.info("MQTT 连接成功")

            for topic, qos in self._subscribe_topics.items():
                client.subscribe(topic, qos)
                self._logger.info("MQTT 订阅: topic=%s qos=%s", topic, qos)
        else:
            self._logger.error("MQTT 连接失败: rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        if rc != 0:
            self._logger.warning("MQTT 意外断开: rc=%s", rc)
        else:
            self._logger.info("MQTT 正常断开")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)

            cmd_type_raw = data.get("type", "")
            cmd_type = self._cmd_map.get(cmd_type_raw, cmd_type_raw)

            if cmd_type not in MsgType.__members__:
                self._logger.warning(
                    "MQTT 收到未知指令类型: %s (raw: %s)", cmd_type, cmd_type_raw,
                )
                return

            cmd_payload = data.get("payload", {})
            src = data.get("src", "mqtt")

            self._bus.send_cmd(
                Msg(type=cmd_type, payload=cmd_payload, src=src),
                priority=5,
            )
            self._logger.info("MQTT → cmd_q: type=%s src=%s", cmd_type, src)

        except json.JSONDecodeError as exc:
            self._logger.warning("MQTT 消息 JSON 解析失败: %s topic=%s", exc, msg.topic)
        except Exception as exc:
            self._logger.exception("MQTT 消息处理异常: %s", exc)
