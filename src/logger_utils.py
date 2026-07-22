#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：Keen 
@File    ：logger_utils.py.py
@IDE     ：PyCharm 
@Author  ：张鹏
@Date    ：2026/7/22 23:45 
@Description： 
'''
# src/logger_utils.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path


class Logger:
    """统一日志管理器"""

    _instances = {}

    def __new__(cls, name='fall_detection', log_dir='logs', level=logging.INFO):
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name='fall_detection', log_dir='logs', level=logging.INFO):
        if self._initialized:
            return

        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加 handler
        if self.logger.handlers:
            return

        # 创建日志目录
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # 日志格式
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 简洁格式（控制台用）
        self.console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # 添加处理器
        self._add_handlers()

        self._initialized = True

    def _add_handlers(self):
        """添加日志处理器"""

        # 1. 控制台处理器（带颜色，更友好）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(self.console_formatter)
        self.logger.addHandler(console_handler)

        # 2. 文件处理器 - 按天切割（保留30天）
        log_file = os.path.join(self.log_dir, f'{self.name}.log')
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(self.formatter)
        file_handler.suffix = '%Y%m%d'
        self.logger.addHandler(file_handler)

        # 3. 错误日志单独文件（按大小切割）
        error_log_file = os.path.join(self.log_dir, f'{self.name}_error.log')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.formatter)
        self.logger.addHandler(error_handler)

    def get_logger(self):
        """获取 logger 实例"""
        return self.logger

    # 快捷方法
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


# ===== 全局日志实例（单例） =====
_logger = None


def get_logger(name='fall_detection'):
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        _logger = Logger(name=name)
    return _logger.get_logger()


# ===== 快速测试 =====
if __name__ == '__main__':
    log = get_logger('test')

    log.debug("这是调试信息")
    log.info("这是普通信息")
    log.warning("这是警告信息")
    log.error("这是错误信息")

    try:
        1 / 0
    except Exception as e:
        log.exception("捕获到异常")

    print("✅ 日志测试完成，请查看 logs/ 目录")
