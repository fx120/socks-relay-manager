"""
日志配置模块

负责配置Python logging系统，包括日志格式、级别、文件处理器和日志轮转。
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


# 默认日志格式
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 默认日志文件大小限制（100MB）
DEFAULT_MAX_BYTES = 100 * 1024 * 1024  # 100MB
DEFAULT_BACKUP_COUNT = 5  # 保留5个备份文件


def setup_logging(
    log_file: str,
    log_level: str = "INFO",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None
) -> logging.Logger:
    """
    配置应用程序的日志系统
    
    Args:
        log_file: 日志文件路径
        log_level: 日志级别 (DEBUG, INFO, WARN, ERROR)
        max_bytes: 日志文件最大大小（字节），超过后轮转
        backup_count: 保留的备份日志文件数量
        log_format: 自定义日志格式
        date_format: 自定义日期格式
        
    Returns:
        logging.Logger: 配置好的根日志记录器
        
    Raises:
        ValueError: 日志级别无效
        IOError: 无法创建日志目录或文件
    """
    # 验证日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    if log_level.upper() not in level_map:
        raise ValueError(f"Invalid log level: {log_level}. Must be one of {list(level_map.keys())}")
    
    level = level_map[log_level.upper()]
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            raise IOError(f"Failed to create log directory {log_dir}: {e}")
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器（避免重复配置）
    root_logger.handlers.clear()
    
    # 创建日志格式器
    formatter = logging.Formatter(
        fmt=log_format or DEFAULT_LOG_FORMAT,
        datefmt=date_format or DEFAULT_DATE_FORMAT
    )
    
    # 创建文件处理器（带轮转）
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        raise IOError(f"Failed to create log file handler for {log_file}: {e}")
    
    # 创建控制台处理器（用于开发和调试）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 记录日志系统初始化信息
    root_logger.info(f"Logging system initialized: level={log_level}, file={log_file}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称（通常使用模块名 __name__）
        
    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    动态设置日志级别
    
    Args:
        level: 新的日志级别 (DEBUG, INFO, WARN, ERROR)
        
    Raises:
        ValueError: 日志级别无效
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    if level.upper() not in level_map:
        raise ValueError(f"Invalid log level: {level}. Must be one of {list(level_map.keys())}")
    
    new_level = level_map[level.upper()]
    
    # 更新根日志记录器和所有处理器的级别
    root_logger = logging.getLogger()
    root_logger.setLevel(new_level)
    
    for handler in root_logger.handlers:
        handler.setLevel(new_level)
    
    root_logger.info(f"Log level changed to {level}")


def shutdown_logging() -> None:
    """
    关闭日志系统，刷新并关闭所有处理器
    """
    logging.shutdown()
