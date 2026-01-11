"""
测试日志配置模块

验证日志系统的配置、格式、级别和轮转功能。
"""

import os
import logging
import tempfile
import pytest
from pathlib import Path

from src.proxy_relay.logging_config import (
    setup_logging,
    get_logger,
    set_log_level,
    shutdown_logging,
    DEFAULT_LOG_FORMAT,
    DEFAULT_MAX_BYTES,
    DEFAULT_BACKUP_COUNT
)


class TestLoggingConfig:
    """测试日志配置功能"""
    
    def test_setup_logging_creates_log_file(self, tmp_path):
        """测试日志系统创建日志文件"""
        log_file = tmp_path / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        assert logger is not None
        assert log_file.exists()
        
        # 清理
        shutdown_logging()
    
    def test_setup_logging_with_different_levels(self, tmp_path):
        """测试不同日志级别的配置"""
        log_file = tmp_path / "test.log"
        
        for level in ["DEBUG", "INFO", "WARN", "ERROR"]:
            logger = setup_logging(
                log_file=str(log_file),
                log_level=level
            )
            
            assert logger.level == getattr(logging, level if level != "WARN" else "WARNING")
            shutdown_logging()
    
    def test_setup_logging_invalid_level(self, tmp_path):
        """测试无效的日志级别"""
        log_file = tmp_path / "test.log"
        
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(
                log_file=str(log_file),
                log_level="INVALID"
            )
    
    def test_setup_logging_creates_directory(self, tmp_path):
        """测试日志系统自动创建目录"""
        log_dir = tmp_path / "logs" / "subdir"
        log_file = log_dir / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        assert log_dir.exists()
        assert log_file.exists()
        
        shutdown_logging()
    
    def test_logging_writes_to_file(self, tmp_path):
        """测试日志写入文件"""
        log_file = tmp_path / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        test_message = "Test log message"
        logger.info(test_message)
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证日志内容
        with open(log_file, 'r') as f:
            content = f.read()
            assert test_message in content
        
        shutdown_logging()
    
    def test_log_level_filtering(self, tmp_path):
        """测试日志级别过滤"""
        log_file = tmp_path / "test.log"
        
        # 设置为INFO级别
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        # 写入不同级别的日志
        logger.debug("Debug message")  # 不应该被记录
        logger.info("Info message")    # 应该被记录
        logger.warning("Warning message")  # 应该被记录
        logger.error("Error message")  # 应该被记录
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证日志内容
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Debug message" not in content  # DEBUG不应该出现
            assert "Info message" in content
            assert "Warning message" in content
            assert "Error message" in content
        
        shutdown_logging()
    
    def test_get_logger(self, tmp_path):
        """测试获取命名日志记录器"""
        log_file = tmp_path / "test.log"
        
        setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        # 获取命名日志记录器
        module_logger = get_logger("test_module")
        
        assert module_logger is not None
        assert module_logger.name == "test_module"
        
        # 测试日志记录
        test_message = "Module log message"
        module_logger.info(test_message)
        
        # 刷新日志
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        # 验证日志内容
        with open(log_file, 'r') as f:
            content = f.read()
            assert test_message in content
            assert "test_module" in content
        
        shutdown_logging()
    
    def test_set_log_level_dynamically(self, tmp_path):
        """测试动态设置日志级别"""
        log_file = tmp_path / "test.log"
        
        # 初始设置为INFO
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        # DEBUG消息不应该被记录
        logger.debug("Debug before change")
        
        # 动态改为DEBUG级别
        set_log_level("DEBUG")
        
        # 现在DEBUG消息应该被记录
        logger.debug("Debug after change")
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证日志内容
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Debug before change" not in content
            assert "Debug after change" in content
        
        shutdown_logging()
    
    def test_set_log_level_invalid(self, tmp_path):
        """测试设置无效的日志级别"""
        log_file = tmp_path / "test.log"
        
        setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        with pytest.raises(ValueError, match="Invalid log level"):
            set_log_level("INVALID")
        
        shutdown_logging()
    
    def test_log_format(self, tmp_path):
        """测试日志格式"""
        log_file = tmp_path / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        logger.info("Test message")
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证日志格式包含必要元素
        with open(log_file, 'r') as f:
            content = f.read()
            # 应该包含时间戳、日志级别、消息
            assert "INFO" in content
            assert "Test message" in content
            # 应该包含日期时间格式 (YYYY-MM-DD HH:MM:SS)
            import re
            assert re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', content)
        
        shutdown_logging()
    
    def test_custom_log_format(self, tmp_path):
        """测试自定义日志格式"""
        log_file = tmp_path / "test.log"
        custom_format = '%(levelname)s - %(message)s'
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO",
            log_format=custom_format
        )
        
        logger.info("Custom format test")
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证自定义格式
        with open(log_file, 'r') as f:
            content = f.read()
            assert "INFO - Custom format test" in content
        
        shutdown_logging()
    
    def test_rotating_file_handler_configuration(self, tmp_path):
        """测试日志轮转配置"""
        log_file = tmp_path / "test.log"
        max_bytes = 1024  # 1KB
        backup_count = 3
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO",
            max_bytes=max_bytes,
            backup_count=backup_count
        )
        
        # 验证处理器配置
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert file_handler.maxBytes == max_bytes
        assert file_handler.backupCount == backup_count
        
        shutdown_logging()
    
    def test_multiple_handlers(self, tmp_path):
        """测试日志系统同时输出到文件和控制台"""
        log_file = tmp_path / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        # 应该有两个处理器：文件和控制台
        assert len(logger.handlers) == 2
        
        # 验证处理器类型
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RotatingFileHandler" in handler_types
        assert "StreamHandler" in handler_types
        
        shutdown_logging()
    
    def test_logging_clears_existing_handlers(self, tmp_path):
        """测试重新配置日志时清除现有处理器"""
        log_file1 = tmp_path / "test1.log"
        log_file2 = tmp_path / "test2.log"
        
        # 第一次配置
        logger1 = setup_logging(
            log_file=str(log_file1),
            log_level="INFO"
        )
        handler_count_1 = len(logger1.handlers)
        
        # 第二次配置（应该清除之前的处理器）
        logger2 = setup_logging(
            log_file=str(log_file2),
            log_level="DEBUG"
        )
        handler_count_2 = len(logger2.handlers)
        
        # 处理器数量应该相同（旧的被清除了）
        assert handler_count_1 == handler_count_2
        
        shutdown_logging()
    
    def test_logging_with_unicode(self, tmp_path):
        """测试日志系统支持Unicode字符"""
        log_file = tmp_path / "test.log"
        
        logger = setup_logging(
            log_file=str(log_file),
            log_level="INFO"
        )
        
        # 写入包含中文的日志
        chinese_message = "测试中文日志消息"
        logger.info(chinese_message)
        
        # 刷新日志
        for handler in logger.handlers:
            handler.flush()
        
        # 验证Unicode内容
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert chinese_message in content
        
        shutdown_logging()
