"""
配置管理模块
用于管理目标检测项目的各种配置，包括事件监听器配置

作者: zhangpeng
时间: 2025-08-31
"""

import json
import os
import logging
from typing import Dict, List, Any


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为None，使用默认配置
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """
        获取默认配置文件路径
        
        Returns:
            str: 默认配置文件路径
        """
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        return os.path.join(project_root, 'config.json')
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        # 默认配置
        default_config = {
            "event_handlers": {
                "log": True,
                "tts": False,
                "api": False,
                "kafka": False
            },
            "tts": {
                "enabled": False,
                "rate": 200,
                "voice": "default"
            },
            "api": {
                "enabled": False,
                "endpoint": ""
            },
            "kafka": {
                "enabled": False,
                "bootstrap_servers": ["localhost:9092"],
                "topic": "object-detection-events"
            },
            "logging": {
                "enabled": True,
                "file": "logs/object_detection.log",
                "level": "INFO",
                "max_bytes": 10485760,
                "backup_count": 5
            }
        }
        
        # 尝试加载配置文件
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # 合并配置（文件配置覆盖默认配置）
                self._merge_config(default_config, file_config)
                logging.info(f"配置加载成功: {self.config_path}")
            except Exception as e:
                logging.error(f"配置文件加载失败，使用默认配置: {e}")
        else:
            logging.warning(f"配置文件不存在，使用默认配置: {self.config_path}")
        
        return default_config
    
    def _merge_config(self, default: Dict, override: Dict) -> Dict:
        """
        合并配置字典
        
        Args:
            default: 默认配置
            override: 覆盖配置
            
        Returns:
            Dict: 合并后的配置
        """
        for key in override:
            if key in default and isinstance(default[key], dict) and isinstance(override[key], dict):
                self._merge_config(default[key], override[key])
            else:
                default[key] = override[key]
        return default
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取配置
        
        Returns:
            Dict: 配置字典
        """
        return self.config
    
    def get(self, key_path: str, default=None) -> Any:
        """
        根据路径获取配置值
        
        Args:
            key_path: 配置键路径，如 "logging.level"
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def setup_logging(self):
        """设置日志"""
        log_config = self.config.get("logging", {})
        
        if not log_config.get("enabled", True):
            return
        
        # 创建日志目录
        log_file = log_config.get("file", "logs/object_detection.log")
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志级别
        log_level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 设置文件处理器
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=log_config.get("max_bytes", 10485760),  # 10MB
                backupCount=log_config.get("backup_count", 5),
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            logging.warning(f"文件日志处理器设置失败: {e}")
        
        # 设置控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
        
        logging.info("日志设置完成")


# 创建全局配置管理器实例
config_manager = ConfigManager()