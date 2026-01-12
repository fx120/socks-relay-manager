"""
健康监控器

负责定期检查上游代理健康状态，触发自动切换。
"""

import time
import logging
import requests
import threading
from datetime import datetime
from typing import Optional, Dict
from urllib.parse import urlparse

from .config_manager import ConfigManager
from .database import Database
from .models import UpstreamProxy, MonitoringStatus

logger = logging.getLogger(__name__)


class HealthMonitor:
    """健康监控器类"""
    
    def __init__(self, config_manager: ConfigManager, proxy_manager, database: Database):
        """
        初始化健康监控器
        
        Args:
            config_manager: 配置管理器实例
            proxy_manager: 代理管理器实例
            database: 数据库实例
        """
        self.config_manager = config_manager
        self.proxy_manager = proxy_manager
        self.database = database
        
        # 监控线程字典: {local_port: thread}
        self._monitoring_threads: Dict[int, threading.Thread] = {}
        
        # 监控停止标志字典: {local_port: stop_event}
        self._stop_events: Dict[int, threading.Event] = {}
        
        # 监控状态字典: {local_port: MonitoringStatus}
        self._monitoring_statuses: Dict[int, MonitoringStatus] = {}
        
        # 线程锁
        self._lock = threading.Lock()
        
        logger.info("HealthMonitor initialized")
    
    def start_monitoring(self, port: int) -> None:
        """
        启动指定端口的监控
        
        Args:
            port: 本地端口号
            
        Raises:
            ValueError: 如果端口配置不存在
            RuntimeError: 如果监控已经在运行
        """
        with self._lock:
            # 检查端口配置是否存在
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise ValueError(f"Proxy configuration for port {port} not found")
            
            # 检查是否已经在监控
            if port in self._monitoring_threads and self._monitoring_threads[port].is_alive():
                raise RuntimeError(f"Monitoring for port {port} is already running")
            
            logger.info(f"Starting monitoring for port {port}")
            
            # 创建停止事件
            stop_event = threading.Event()
            self._stop_events[port] = stop_event
            
            # 初始化监控状态
            monitoring_status = MonitoringStatus(
                local_port=port,
                enabled=True,
                failure_count=0,
                last_check_time=None,
                last_success_time=None,
                current_upstream=proxy_config.upstream
            )
            self._monitoring_statuses[port] = monitoring_status
            
            # 持久化监控状态到数据库
            self.database.upsert_monitoring_state(
                local_port=port,
                enabled=True,
                failure_count=0,
                last_check_time=None,
                last_success_time=None
            )
            
            # 创建并启动监控线程
            thread = threading.Thread(
                target=self._monitoring_loop,
                args=(port,),
                name=f"HealthMonitor-{port}",
                daemon=True
            )
            self._monitoring_threads[port] = thread
            thread.start()
            
            logger.info(f"Monitoring started for port {port}")
    
    def stop_monitoring(self, port: int) -> None:
        """
        停止指定端口的监控
        
        Args:
            port: 本地端口号
            
        Raises:
            ValueError: 如果监控未运行
        """
        with self._lock:
            # 检查监控是否在运行
            if port not in self._monitoring_threads or not self._monitoring_threads[port].is_alive():
                raise ValueError(f"Monitoring for port {port} is not running")
            
            logger.info(f"Stopping monitoring for port {port}")
            
            # 设置停止标志
            if port in self._stop_events:
                self._stop_events[port].set()
            
            # 等待线程结束（最多等待5秒）
            thread = self._monitoring_threads[port]
            thread.join(timeout=5.0)
            
            if thread.is_alive():
                logger.warning(f"Monitoring thread for port {port} did not stop gracefully")
            
            # 清理资源
            if port in self._stop_events:
                del self._stop_events[port]
            if port in self._monitoring_threads:
                del self._monitoring_threads[port]
            
            # 更新监控状态
            if port in self._monitoring_statuses:
                self._monitoring_statuses[port].enabled = False
            
            # 持久化监控状态到数据库
            status = self._monitoring_statuses.get(port)
            if status:
                self.database.upsert_monitoring_state(
                    local_port=port,
                    enabled=False,
                    failure_count=status.failure_count,
                    last_check_time=status.last_check_time,
                    last_success_time=status.last_success_time
                )
            
            logger.info(f"Monitoring stopped for port {port}")
    
    def get_monitoring_status(self) -> Dict[int, MonitoringStatus]:
        """
        获取所有端口的监控状态
        
        Returns:
            Dict[int, MonitoringStatus]: 端口号到监控状态的映射
        """
        with self._lock:
            return self._monitoring_statuses.copy()
    
    def check_proxy_health(self, upstream: UpstreamProxy) -> tuple[bool, Optional[int], Optional[str]]:
        """
        检查单个代理的健康状态
        
        通过代理发送HTTP请求到检查URL，记录响应时间
        
        Args:
            upstream: 上游代理配置
            
        Returns:
            tuple[bool, Optional[int], Optional[str]]: 
                - 健康状态（True=健康，False=不健康）
                - 响应时间（毫秒，失败时为None）
                - 错误信息（成功时为None）
        """
        # VLESS 协议不支持直接 HTTP 测试
        if upstream.protocol == "vless":
            return True, None, "VLESS 协议不支持直接测试，请通过实际使用验证连接"
        
        config = self.config_manager._current_config
        if not config:
            return False, None, "Configuration not loaded"
        
        check_url = config.monitoring.check_url
        check_timeout = config.monitoring.check_timeout
        
        # 构建代理配置
        proxy_url = self._build_proxy_url(upstream)
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            logger.debug(f"Checking proxy health: {upstream.server}:{upstream.port} -> {check_url}")
            
            # 记录开始时间
            start_time = time.time()
            
            # 发送HTTP请求
            response = requests.get(
                check_url,
                proxies=proxies,
                timeout=check_timeout,
                allow_redirects=True
            )
            
            # 计算响应时间（毫秒）
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 检查响应状态码
            if response.status_code == 200:
                logger.debug(f"Health check passed: {upstream.server}:{upstream.port}, response_time={response_time_ms}ms")
                return True, response_time_ms, None
            else:
                error_msg = f"HTTP status code {response.status_code}"
                logger.debug(f"Health check failed: {upstream.server}:{upstream.port}, {error_msg}")
                return False, response_time_ms, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {check_timeout}s"
            logger.debug(f"Health check failed: {upstream.server}:{upstream.port}, {error_msg}")
            return False, None, error_msg
            
        except requests.exceptions.ProxyError as e:
            error_msg = f"Proxy error: {str(e)}"
            logger.debug(f"Health check failed: {upstream.server}:{upstream.port}, {error_msg}")
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            logger.debug(f"Health check failed: {upstream.server}:{upstream.port}, {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Health check failed: {upstream.server}:{upstream.port}, {error_msg}")
            return False, None, error_msg
    
    def _build_proxy_url(self, upstream: UpstreamProxy) -> str:
        """
        构建代理URL
        
        Args:
            upstream: 上游代理配置
            
        Returns:
            str: 代理URL（格式：protocol://[username:password@]server:port）
        """
        # 对于 SOCKS5 代理，使用 socks5h:// 让代理服务器解析 DNS
        # 这样可以避免本地 DNS 泄露，并且更可靠
        protocol = upstream.protocol
        if protocol == "socks5":
            protocol = "socks5h"
        
        if upstream.username and upstream.password:
            # 带认证的代理URL
            return f"{protocol}://{upstream.username}:{upstream.password}@{upstream.server}:{upstream.port}"
        else:
            # 不带认证的代理URL
            return f"{protocol}://{upstream.server}:{upstream.port}"
    
    def _trigger_proxy_switch(self, port: int) -> None:
        """
        触发代理切换
        
        Args:
            port: 本地端口号
        """
        try:
            logger.info(f"Triggering proxy switch for port {port}")
            
            # 调用 ProxyManager 的切换方法
            # 注意：这个方法将在任务 11 中实现
            if hasattr(self.proxy_manager, 'switch_upstream_proxy'):
                self.proxy_manager.switch_upstream_proxy(port)
            else:
                logger.warning(f"ProxyManager.switch_upstream_proxy not implemented yet")
                
        except Exception as e:
            logger.error(f"Failed to trigger proxy switch for port {port}: {e}", exc_info=True)
    
    def _monitoring_loop(self, port: int) -> None:
        """
        监控循环（内部方法，在独立线程中运行）
        
        按配置间隔执行健康检查，直到收到停止信号
        
        Args:
            port: 本地端口号
        """
        logger.info(f"Monitoring loop started for port {port}")
        
        stop_event = self._stop_events.get(port)
        if not stop_event:
            logger.error(f"Stop event not found for port {port}")
            return
        
        while not stop_event.is_set():
            try:
                # 获取当前配置
                config = self.config_manager._current_config
                if not config:
                    logger.error("Configuration not loaded, stopping monitoring loop")
                    break
                
                # 获取代理配置
                proxy_config = self.config_manager.get_proxy_config(port)
                if not proxy_config:
                    logger.error(f"Proxy configuration for port {port} not found, stopping monitoring loop")
                    break
                
                # 获取监控配置
                check_interval = config.monitoring.check_interval
                
                # 执行健康检查
                upstream = proxy_config.upstream
                is_healthy, response_time_ms, error_message = self.check_proxy_health(upstream)
                
                # 更新监控状态
                with self._lock:
                    if port in self._monitoring_statuses:
                        status = self._monitoring_statuses[port]
                        status.last_check_time = datetime.now()
                        status.current_upstream = upstream
                        
                        # 更新失败计数和状态标记
                        if is_healthy:
                            # 健康检查成功，重置失败计数
                            status.failure_count = 0
                            status.last_success_time = datetime.now()
                            logger.debug(f"Health check passed for port {port}, failure count reset to 0")
                        else:
                            # 健康检查失败，增加失败计数
                            status.failure_count += 1
                            logger.warning(f"Health check failed for port {port}: {error_message}, failure count: {status.failure_count}")
                            
                            # 检查是否达到失败阈值
                            failure_threshold = config.monitoring.failure_threshold
                            if status.failure_count >= failure_threshold:
                                logger.error(f"Failure threshold reached for port {port} ({status.failure_count}/{failure_threshold}), triggering proxy switch")
                                # 触发代理切换
                                self._trigger_proxy_switch(port)
                                # 重置失败计数（切换后重新开始计数）
                                status.failure_count = 0
                        
                        # 持久化监控状态到数据库
                        self.database.upsert_monitoring_state(
                            local_port=port,
                            enabled=True,
                            failure_count=status.failure_count,
                            last_check_time=status.last_check_time,
                            last_success_time=status.last_success_time
                        )
                
                # 记录健康检查日志到数据库
                self.database.insert_health_check_log(
                    local_port=port,
                    upstream_server=upstream.server,
                    upstream_port=upstream.port,
                    check_result=is_healthy,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    timestamp=datetime.now()
                )
                
                # 等待下一次检查（可被停止事件中断）
                stop_event.wait(timeout=check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for port {port}: {e}", exc_info=True)
                # 发生错误后等待一段时间再继续
                stop_event.wait(timeout=10)
        
        logger.info(f"Monitoring loop stopped for port {port}")
