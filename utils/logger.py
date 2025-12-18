"""
日志工具模块
提供统一的日志管理功能
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class Logger:
    """日志管理器"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None, 
                   level: str = "INFO", max_bytes: int = 10485760, 
                   backup_count: int = 5) -> logging.Logger:
        """
        获取或创建日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径
            level: 日志级别
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的备份文件数量
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if logger.handlers:
            return logger
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    便捷函数:获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return Logger.get_logger(name)
