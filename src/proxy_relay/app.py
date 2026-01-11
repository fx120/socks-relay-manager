"""
主应用模块

提供应用程序的启动、运行和优雅关闭功能。
"""

import signal
import sys
import asyncio
import logging
from typing import Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from .config_manager import ConfigManager
from .proxy_manager import ProxyManager
from .health_monitor import HealthMonitor
from .database import Database
from .web_api import WebAPI
from .logging_config import setup_logging, get_logger


logger = get_logger(__name__)


class ProxyRelayApp:
    """代理中转系统主应用类"""
    
    def __init__(self, config_path: str):
        """
        初始化应用
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config_manager: Optional[ConfigManager] = None
        self.proxy_manager: Optional[ProxyManager] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.database: Optional[Database] = None
        self.web_api: Optional[WebAPI] = None
        self.app: Optional[FastAPI] = None
        
        # 关闭标志
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False
        
        logger.info(f"Initializing Proxy Relay System with config: {config_path}")
    
    def initialize(self):
        """初始化所有组件"""
        try:
            # 加载配置
            logger.info("Loading configuration...")
            self.config_manager = ConfigManager(self.config_path)
            config = self.config_manager.load_config()
            
            # 设置日志系统
            logger.info("Setting up logging...")
            setup_logging(
                log_file=config.system.log_file,
                log_level=config.system.log_level
            )
            
            # 初始化数据库
            logger.info("Initializing database...")
            self.database = Database(config.system.database)
            
            # 初始化代理管理器
            logger.info("Initializing proxy manager...")
            self.proxy_manager = ProxyManager(
                self.config_manager,
                database=self.database
            )
            
            # 生成并应用sing-box配置
            logger.info("Generating sing-box configuration...")
            singbox_config = self.proxy_manager.generate_singbox_config()
            self.proxy_manager.apply_singbox_config(singbox_config)
            logger.info(f"Applied sing-box configuration with {len(singbox_config['inbounds'])} inbounds")
            
            # 初始化健康监控器
            logger.info("Initializing health monitor...")
            self.health_monitor = HealthMonitor(
                self.config_manager,
                self.proxy_manager,
                self.database
            )
            
            # 启动已配置的监控任务
            logger.info("Starting configured monitoring tasks...")
            for proxy in config.proxies:
                if proxy.monitoring_enabled:
                    try:
                        self.health_monitor.start_monitoring(proxy.local_port)
                        logger.info(f"Started monitoring for port {proxy.local_port}")
                    except Exception as e:
                        logger.error(f"Failed to start monitoring for port {proxy.local_port}: {e}")
            
            # 初始化Web API
            logger.info("Initializing Web API...")
            self.web_api = WebAPI(
                self.config_manager,
                self.proxy_manager,
                self.health_monitor,
                self.database
            )
            self.app = self.web_api.app
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            """信号处理函数"""
            signal_name = signal.Signals(signum).name
            logger.info(f"Received signal {signal_name} ({signum})")
            
            if not self._is_shutting_down:
                self._is_shutting_down = True
                logger.info("Initiating graceful shutdown...")
                
                # 在事件循环中触发关闭
                try:
                    loop = asyncio.get_event_loop()
                    loop.call_soon_threadsafe(self._shutdown_event.set)
                except RuntimeError:
                    # 如果没有事件循环，直接退出
                    logger.warning("No event loop available, forcing exit")
                    sys.exit(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Signal handlers registered for SIGTERM and SIGINT")
    
    async def shutdown(self):
        """优雅关闭应用"""
        logger.info("Starting graceful shutdown...")
        
        try:
            # 1. 停止所有监控任务
            if self.health_monitor:
                logger.info("Stopping all monitoring tasks...")
                monitoring_statuses = self.health_monitor.get_monitoring_status()
                for port, status in monitoring_statuses.items():
                    if status.enabled:
                        try:
                            self.health_monitor.stop_monitoring(port)
                            logger.info(f"Stopped monitoring for port {port}")
                        except Exception as e:
                            logger.error(f"Error stopping monitoring for port {port}: {e}")
            
            # 2. 保存当前状态
            if self.config_manager and self.config_manager._current_config:
                logger.info("Saving current configuration...")
                try:
                    self.config_manager.save_config(self.config_manager._current_config)
                    logger.info("Configuration saved successfully")
                except Exception as e:
                    logger.error(f"Error saving configuration: {e}")
            
            # 3. 关闭数据库连接
            if self.database:
                logger.info("Closing database connections...")
                try:
                    self.database.close()
                    logger.info("Database connections closed")
                except Exception as e:
                    logger.error(f"Error closing database: {e}")
            
            # 4. 停止sing-box进程（如果由我们管理）
            # 注意：如果sing-box作为独立服务运行，这里不需要停止它
            logger.info("sing-box process management is handled separately")
            
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
    
    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """
        运行应用
        
        Args:
            host: 监听地址
            port: 监听端口
        """
        try:
            # 初始化组件
            self.initialize()
            
            # 设置信号处理器
            self.setup_signal_handlers()
            
            # 获取配置的端口
            config = self.config_manager._current_config
            if config:
                port = config.system.web_port
            
            logger.info(f"Starting Web API server on {host}:{port}")
            logger.info(f"Configured proxy ports: {[p.local_port for p in config.proxies]}")
            
            # 运行uvicorn服务器
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            # 执行清理
            asyncio.run(self.shutdown())


def main():
    """主入口函数"""
    import os
    
    # 获取配置文件路径
    config_path = os.environ.get('PROXY_RELAY_CONFIG', '/etc/proxy-relay/config.yaml')
    
    # 创建并运行应用
    app = ProxyRelayApp(config_path)
    app.run()


if __name__ == "__main__":
    main()
