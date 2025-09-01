"""
目标检测事件处理模块
当识别到目标时触发事件，支持日志记录、语音播报、外部接口调用和Kafka推送等功能

作者: zhangpeng
时间: 2025-08-31
"""

import logging
import json
import requests
from typing import List, Dict, Any, Callable
from datetime import datetime

# 尝试导入配置管理器
try:
    from src.config.config_manager import config_manager
    # 根据配置设置日志
    config_manager.setup_logging()
except ImportError:
    config_manager = None


class ObjectDetectionEvent:
    """目标检测事件类"""
    
    def __init__(self, objects: List[str], source: str = "unknown", timestamp: datetime = None):
        """
        初始化目标检测事件
        
        Args:
            objects: 检测到的目标列表
            source: 事件来源（如camera, image, video等）
            timestamp: 事件时间戳
        """
        self.objects = objects
        self.source = source
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """将事件转换为字典格式"""
        return {
            "objects": self.objects,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


class EventHandler:
    """事件处理器"""
    
    def __init__(self):
        """初始化事件处理器"""
        self.listeners = []
        self.logger = logging.getLogger(__name__)
        self._setup_logger()
        
        # 根据配置注册事件监听器
        self._register_configured_listeners()
    
    def _setup_logger(self):
        """设置日志记录器"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_config(self):
        """加载配置"""
        try:
            if config_manager:
                config = config_manager.get_config()
                
                # 根据配置添加监听器
                if config.get("event_handlers", {}).get("log", True):
                    self.add_listener(self._log_listener)
                
                if config.get("event_handlers", {}).get("tts", False):
                    self.add_listener(self._tts_listener)
                
                if config.get("event_handlers", {}).get("api", False):
                    self.add_listener(self._api_listener)
                
                if config.get("event_handlers", {}).get("kafka", False):
                    self.add_listener(self._kafka_listener)
            else:
                # 默认只启用日志监听器
                self.add_listener(self._log_listener)
                
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            # 默认只启用日志监听器
            self.add_listener(self._log_listener)
    
    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        添加事件监听器
        
        Args:
            listener: 监听器函数
        """
        self.listeners.append(listener)
        self.logger.debug(f"添加事件监听器: {listener.__name__}")
    
    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        移除事件监听器
        
        Args:
            listener: 监听器函数
        """
        if listener in self.listeners:
            self.listeners.remove(listener)
            self.logger.debug(f"移除事件监听器: {listener.__name__}")
    
    def handle_event(self, event: ObjectDetectionEvent):
        """
        处理事件
        
        Args:
            event: 目标检测事件
        """
        self.logger.debug(f"处理事件: {event.to_dict()}")
        
        # 通知所有监听器
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                self.logger.error(f"事件监听器 {listener.__name__} 处理失败: {e}")


# 预定义的事件监听器函数

    def _log_listener(self, event: ObjectDetectionEvent):
        """日志监听器"""
        self.logger.info(f"[目标检测事件] 检测到目标: {event.objects}, 来源: {event.source}")
    
    def _tts_listener(self, event: ObjectDetectionEvent):
        """语音播报监听器"""
        try:
            if config_manager:
                tts_config = config_manager.get_config().get("tts", {})
                if not tts_config.get("enabled", False):
                    return
                
                # 导入TTS模块
                import pyttsx3
                
                # 初始化TTS引擎
                engine = pyttsx3.init()
                
                # 设置语速
                rate = tts_config.get("rate", 200)
                engine.setProperty('rate', rate)
                
                # 播报检测到的目标
                message = f"检测到目标: {', '.join(event.objects)}"
                engine.say(message)
                engine.runAndWait()
                
                self.logger.debug("TTS播报完成")
            else:
                self.logger.warning("TTS监听器: 未找到配置管理器")
                
        except Exception as e:
            self.logger.error(f"TTS监听器处理失败: {e}")
    
    def _api_listener(self, event: ObjectDetectionEvent):
        """外部API调用监听器"""
        try:
            if config_manager:
                api_config = config_manager.get_config().get("api", {})
                if not api_config.get("enabled", False):
                    return
                
                endpoint = api_config.get("endpoint", "")
                if not endpoint:
                    self.logger.warning("API监听器: 未配置endpoint")
                    return
                
                # 发送POST请求
                payload = event.to_dict()
                response = requests.post(endpoint, json=payload, timeout=10)
                response.raise_for_status()
                
                self.logger.debug(f"API调用成功: {endpoint}")
            else:
                self.logger.warning("API监听器: 未找到配置管理器")
                
        except Exception as e:
            self.logger.error(f"API监听器处理失败: {e}")
    
    def _kafka_listener(self, event: ObjectDetectionEvent):
        """Kafka消息推送监听器"""
        try:
            if config_manager:
                kafka_config = config_manager.get_config().get("kafka", {})
                if not kafka_config.get("enabled", False):
                    return
                
                # 导入Kafka模块
                from kafka import KafkaProducer
                
                bootstrap_servers = kafka_config.get("bootstrap_servers", ["localhost:9092"])
                topic = kafka_config.get("topic", "object-detection-events")
                
                # 创建生产者
                producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                
                # 发送消息
                payload = event.to_dict()
                producer.send(topic, value=payload)
                producer.flush()
                
                self.logger.debug(f"Kafka消息发送成功: {topic}")
            else:
                self.logger.warning("Kafka监听器: 未找到配置管理器")
                
        except ImportError:
            self.logger.warning("Kafka监听器: 未安装kafka-python库")
        except Exception as e:
            self.logger.error(f"Kafka监听器处理失败: {e}")


# 全局事件处理器实例
event_handler = EventHandler()