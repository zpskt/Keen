"""
目标识别事件处理模块

作者: zhangpeng
时间: 2025-08-28
"""

from .event_handler import (
    objectDetectionEvent,
    EventHandler,
    event_handler,
    log_detection_event,
    tts_announcement_event,
    external_api_call_event,
    kafka_push_event
)

__all__ = [
    "objectDetectionEvent",
    "EventHandler",
    "event_handler",
    "log_detection_event",
    "tts_announcement_event",
    "external_api_call_event",
    "kafka_push_event"
]