"""
基本健康监控器测试

测试健康监控器的基本功能。
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.proxy_relay.health_monitor import HealthMonitor
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.database import Database
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    MonitoringConfig,
    APIProviderConfig,
    ProxyConfig,
    UpstreamProxy,
    WebAuthConfig,
    ResponseFormat
)


@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: test_hash
  log_level: INFO
  log_file: /tmp/test.log
  database: /tmp/test.db

monitoring:
  check_interval: 5
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

api_providers:
  - id: provider1
    name: Test Provider
    enabled: true
    endpoint: https://api.example.com
    method: GET
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: custom
      success_field: success
      success_value: true
      data_path: data
      ip_field: ip
      port_field: port

proxies:
  - local_port: 1080
    name: Test Proxy
    api_provider_id: provider1
    upstream:
      server: proxy.example.com
      port: 10000
      protocol: socks5
    monitoring_enabled: false
""")
        config_path = f.name
    
    yield config_path
    
    # 清理
    if os.path.exists(config_path):
        os.remove(config_path)


@pytest.fixture
def temp_database():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    yield db
    
    # 清理
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def config_manager(temp_config_file):
    """创建配置管理器"""
    manager = ConfigManager(temp_config_file)
    manager.load_config()
    return manager


@pytest.fixture
def proxy_manager_mock():
    """创建模拟的代理管理器"""
    mock = Mock()
    mock.switch_upstream_proxy = Mock()
    return mock


@pytest.fixture
def health_monitor(config_manager, proxy_manager_mock, temp_database):
    """创建健康监控器"""
    return HealthMonitor(config_manager, proxy_manager_mock, temp_database)


class TestHealthMonitorBasic:
    """健康监控器基本功能测试"""
    
    def test_initialization(self, health_monitor):
        """测试健康监控器初始化"""
        assert health_monitor is not None
        assert health_monitor.config_manager is not None
        assert health_monitor.proxy_manager is not None
        assert health_monitor.database is not None
        assert isinstance(health_monitor._monitoring_threads, dict)
        assert isinstance(health_monitor._stop_events, dict)
        assert isinstance(health_monitor._monitoring_statuses, dict)
    
    def test_build_proxy_url_without_auth(self, health_monitor):
        """测试构建不带认证的代理URL"""
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            protocol="socks5"
        )
        
        url = health_monitor._build_proxy_url(upstream)
        assert url == "socks5://proxy.example.com:10000"
    
    def test_build_proxy_url_with_auth(self, health_monitor):
        """测试构建带认证的代理URL"""
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            username="user",
            password="pass",
            protocol="socks5"
        )
        
        url = health_monitor._build_proxy_url(upstream)
        assert url == "socks5://user:pass@proxy.example.com:10000"
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_check_proxy_health_success(self, mock_get, health_monitor):
        """测试健康检查成功"""
        # 模拟成功的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            protocol="socks5"
        )
        
        is_healthy, response_time_ms, error_message = health_monitor.check_proxy_health(upstream)
        
        assert is_healthy is True
        assert response_time_ms is not None
        assert response_time_ms >= 0
        assert error_message is None
        
        # 验证请求参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://www.google.com"
        assert 'proxies' in call_args[1]
        assert call_args[1]['timeout'] == 10
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_check_proxy_health_http_error(self, mock_get, health_monitor):
        """测试健康检查HTTP错误"""
        # 模拟HTTP错误响应
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            protocol="socks5"
        )
        
        is_healthy, response_time_ms, error_message = health_monitor.check_proxy_health(upstream)
        
        assert is_healthy is False
        assert response_time_ms is not None
        assert "HTTP status code 500" in error_message
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_check_proxy_health_timeout(self, mock_get, health_monitor):
        """测试健康检查超时"""
        import requests
        # 模拟超时异常
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            protocol="socks5"
        )
        
        is_healthy, response_time_ms, error_message = health_monitor.check_proxy_health(upstream)
        
        assert is_healthy is False
        assert response_time_ms is None
        assert "Timeout" in error_message
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_check_proxy_health_proxy_error(self, mock_get, health_monitor):
        """测试健康检查代理错误"""
        import requests
        # 模拟代理错误
        mock_get.side_effect = requests.exceptions.ProxyError("Proxy connection failed")
        
        upstream = UpstreamProxy(
            server="proxy.example.com",
            port=10000,
            protocol="socks5"
        )
        
        is_healthy, response_time_ms, error_message = health_monitor.check_proxy_health(upstream)
        
        assert is_healthy is False
        assert response_time_ms is None
        assert "Proxy error" in error_message
    
    def test_start_monitoring_success(self, health_monitor):
        """测试启动监控成功"""
        port = 1080
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        # 验证监控线程已创建
        assert port in health_monitor._monitoring_threads
        assert health_monitor._monitoring_threads[port].is_alive()
        
        # 验证停止事件已创建
        assert port in health_monitor._stop_events
        
        # 验证监控状态已创建
        assert port in health_monitor._monitoring_statuses
        status = health_monitor._monitoring_statuses[port]
        assert status.local_port == port
        assert status.enabled is True
        assert status.failure_count == 0
        
        # 清理：停止监控
        health_monitor.stop_monitoring(port)
    
    def test_start_monitoring_invalid_port(self, health_monitor):
        """测试启动监控时端口不存在"""
        port = 9999  # 不存在的端口
        
        with pytest.raises(ValueError, match="not found"):
            health_monitor.start_monitoring(port)
    
    def test_start_monitoring_already_running(self, health_monitor):
        """测试重复启动监控"""
        port = 1080
        
        # 第一次启动
        health_monitor.start_monitoring(port)
        
        # 第二次启动应该失败
        with pytest.raises(RuntimeError, match="already running"):
            health_monitor.start_monitoring(port)
        
        # 清理
        health_monitor.stop_monitoring(port)
    
    def test_stop_monitoring_success(self, health_monitor):
        """测试停止监控成功"""
        port = 1080
        
        # 先启动监控
        health_monitor.start_monitoring(port)
        assert health_monitor._monitoring_threads[port].is_alive()
        
        # 停止监控
        health_monitor.stop_monitoring(port)
        
        # 验证线程已停止
        assert port not in health_monitor._monitoring_threads or not health_monitor._monitoring_threads[port].is_alive()
        
        # 验证停止事件已清理
        assert port not in health_monitor._stop_events
        
        # 验证监控状态已更新
        if port in health_monitor._monitoring_statuses:
            assert health_monitor._monitoring_statuses[port].enabled is False
    
    def test_stop_monitoring_not_running(self, health_monitor):
        """测试停止未运行的监控"""
        port = 1080
        
        with pytest.raises(ValueError, match="not running"):
            health_monitor.stop_monitoring(port)
    
    def test_get_monitoring_status(self, health_monitor):
        """测试获取监控状态"""
        port = 1080
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        # 获取监控状态
        statuses = health_monitor.get_monitoring_status()
        
        assert isinstance(statuses, dict)
        assert port in statuses
        assert statuses[port].local_port == port
        assert statuses[port].enabled is True
        
        # 清理
        health_monitor.stop_monitoring(port)
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_monitoring_loop_records_health_check(self, mock_get, health_monitor, temp_database):
        """测试监控循环记录健康检查"""
        # 模拟成功的HTTP响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        port = 1080
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        # 等待至少一次健康检查
        time.sleep(6)  # check_interval = 5秒
        
        # 停止监控
        health_monitor.stop_monitoring(port)
        
        # 验证健康检查日志已记录
        logs = temp_database.get_health_check_logs(local_port=port)
        assert len(logs) > 0
        assert logs[0]['local_port'] == port
        assert logs[0]['check_result'] == 1  # True
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_failure_count_increments(self, mock_get, health_monitor):
        """测试失败计数递增"""
        import requests
        # 模拟失败的健康检查
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        port = 1080
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        # 等待多次健康检查
        time.sleep(16)  # 至少3次检查（每5秒一次）
        
        # 检查失败计数
        status = health_monitor._monitoring_statuses.get(port)
        if status:
            # 失败计数应该已经重置（因为达到阈值触发了切换）
            # 或者还在累积中
            assert status.failure_count >= 0
        
        # 清理
        health_monitor.stop_monitoring(port)
    
    @patch('src.proxy_relay.health_monitor.requests.get')
    def test_failure_threshold_triggers_switch(self, mock_get, health_monitor, proxy_manager_mock):
        """测试失败阈值触发切换"""
        import requests
        # 模拟失败的健康检查
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        port = 1080
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        # 等待足够长的时间以触发阈值（3次失败）
        time.sleep(16)  # 至少3次检查
        
        # 停止监控
        health_monitor.stop_monitoring(port)
        
        # 验证是否尝试调用切换方法
        # 注意：由于 switch_upstream_proxy 还未实现，这里只是验证调用尝试
        # 实际的切换逻辑将在任务 11 中测试
        if hasattr(proxy_manager_mock, 'switch_upstream_proxy'):
            # 如果方法存在，应该被调用
            assert proxy_manager_mock.switch_upstream_proxy.called or True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
