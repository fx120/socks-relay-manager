"""
Web API SSE (Server-Sent Events) 测试

测试实时状态更新功能
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.proxy_relay.web_api import create_app
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager
from src.proxy_relay.health_monitor import HealthMonitor
from src.proxy_relay.database import Database
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    WebAuthConfig,
    MonitoringConfig,
    ProxyConfig,
    UpstreamProxy,
    APIProviderConfig,
    ResponseFormat,
    MonitoringStatus
)


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    return Config(
        system=SystemConfig(
            web_port=8080,
            web_auth=WebAuthConfig(
                enabled=False,  # 禁用认证以简化测试
                username="admin",
                password_hash="$2b$12$test"
            ),
            log_level="INFO",
            log_file="/var/log/proxy-relay/app.log",
            database="/var/lib/proxy-relay/data.db"
        ),
        monitoring=MonitoringConfig(
            check_interval=30,
            failure_threshold=3,
            check_timeout=10,
            check_url="http://www.google.com"
        ),
        api_providers=[
            APIProviderConfig(
                id="provider1",
                name="Test Provider",
                enabled=True,
                endpoint="https://api.example.com",
                method="GET",
                params={},
                timeout=10,
                retry_attempts=3,
                retry_backoff=2,
                response_format=ResponseFormat(
                    type="custom",
                    data_path="data",
                    ip_field="ip",
                    port_field="port"
                )
            )
        ],
        proxies=[
            ProxyConfig(
                local_port=1080,
                name="Test Proxy 1",
                api_provider_id="provider1",
                upstream=UpstreamProxy(
                    server="proxy1.example.com",
                    port=10000,
                    protocol="socks5"
                ),
                monitoring_enabled=True
            ),
            ProxyConfig(
                local_port=1081,
                name="Test Proxy 2",
                api_provider_id="provider1",
                upstream=UpstreamProxy(
                    server="proxy2.example.com",
                    port=10001,
                    protocol="socks5"
                ),
                monitoring_enabled=False
            )
        ]
    )


@pytest.fixture
def mock_config_manager(mock_config):
    """创建模拟配置管理器"""
    manager = Mock(spec=ConfigManager)
    manager._current_config = mock_config
    manager.load_config.return_value = mock_config
    return manager


@pytest.fixture
def mock_proxy_manager():
    """创建模拟代理管理器"""
    return Mock(spec=ProxyManager)


@pytest.fixture
def mock_health_monitor():
    """创建模拟健康监控器"""
    monitor = Mock(spec=HealthMonitor)
    
    # 模拟监控状态
    monitor.get_monitoring_status.return_value = {
        1080: MonitoringStatus(
            local_port=1080,
            enabled=True,
            failure_count=0,
            last_check_time=datetime.now(),
            last_success_time=datetime.now(),
            current_upstream=UpstreamProxy(
                server="proxy1.example.com",
                port=10000,
                protocol="socks5"
            )
        ),
        1081: MonitoringStatus(
            local_port=1081,
            enabled=False,
            failure_count=0,
            last_check_time=None,
            last_success_time=None,
            current_upstream=UpstreamProxy(
                server="proxy2.example.com",
                port=10001,
                protocol="socks5"
            )
        )
    }
    
    return monitor


@pytest.fixture
def mock_database():
    """创建模拟数据库"""
    return Mock(spec=Database)


@pytest.fixture
def test_app(mock_config_manager, mock_proxy_manager, mock_health_monitor, mock_database):
    """创建测试应用"""
    app = create_app(
        mock_config_manager,
        mock_proxy_manager,
        mock_health_monitor,
        mock_database
    )
    return app


@pytest.fixture
def client(test_app):
    """创建测试客户端"""
    return TestClient(test_app)


class TestSSEEndpoint:
    """SSE端点测试"""
    
    def test_sse_endpoint_exists(self, client):
        """测试SSE端点存在"""
        # 使用stream=True来处理SSE流
        with client.stream("GET", "/api/events/status", timeout=2.0) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
    
    def test_sse_initial_connection_message(self, client):
        """测试SSE初始连接消息"""
        with client.stream("GET", "/api/events/status", timeout=2.0) as response:
            # 读取第一条消息
            lines = []
            for line in response.iter_lines():
                lines.append(line)
                if len(lines) >= 2:  # data行 + 空行
                    break
            
            # 解析第一条消息
            assert len(lines) >= 1
            first_line = lines[0]
            assert first_line.startswith("data: ")
            
            # 解析JSON数据
            data = json.loads(first_line[6:])  # 去掉 "data: " 前缀
            assert data["type"] == "connected"
            assert "message" in data
            assert "timestamp" in data
    
    def test_sse_initial_status(self, client):
        """测试SSE初始状态消息"""
        with client.stream("GET", "/api/events/status", timeout=2.0) as response:
            # 读取前几条消息
            messages = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    messages.append(data)
                    if len(messages) >= 2:  # connected + initial_status
                        break
            
            # 检查初始状态消息
            assert len(messages) >= 2
            initial_status = messages[1]
            assert initial_status["type"] == "initial_status"
            assert "data" in initial_status
            assert "proxies" in initial_status["data"]
            assert len(initial_status["data"]["proxies"]) == 2
    
    def test_sse_status_format(self, client):
        """测试SSE状态数据格式"""
        with client.stream("GET", "/api/events/status", timeout=2.0) as response:
            # 读取初始状态消息
            messages = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    messages.append(data)
                    if data.get("type") == "initial_status":
                        break
            
            # 检查状态数据格式
            initial_status = next(m for m in messages if m["type"] == "initial_status")
            status_data = initial_status["data"]
            
            assert "proxies" in status_data
            assert "total_proxies" in status_data
            assert "active_monitoring" in status_data
            
            # 检查代理数据格式
            proxy = status_data["proxies"][0]
            assert "local_port" in proxy
            assert "name" in proxy
            assert "monitoring_enabled" in proxy
            assert "upstream" in proxy
            assert "monitoring_status" in proxy
            
            # 检查上游代理格式
            upstream = proxy["upstream"]
            assert "server" in upstream
            assert "port" in upstream
            assert "protocol" in upstream
            
            # 检查监控状态格式
            mon_status = proxy["monitoring_status"]
            assert "enabled" in mon_status
            assert "failure_count" in mon_status
            assert "is_healthy" in mon_status


class TestSSEStatusDetection:
    """SSE状态变化检测测试"""
    
    def test_detect_no_changes(self, test_app):
        """测试检测无变化"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        # 相同状态
        status = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(status, status)
        assert len(changes) == 0
    
    def test_detect_upstream_change(self, test_app):
        """测试检测上游代理变化"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        previous = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        current = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy2.com", "port": 10001, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(previous, current)
        assert len(changes) == 1
        assert changes[0]["type"] == "upstream_changed"
        assert changes[0]["port"] == 1080
    
    def test_detect_monitoring_toggle(self, test_app):
        """测试检测监控启停变化"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        previous = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": False, "is_healthy": True}
                }
            ]
        }
        
        current = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(previous, current)
        assert len(changes) == 1
        assert changes[0]["type"] == "monitoring_toggled"
        assert changes[0]["port"] == 1080
        assert changes[0]["enabled"] is True
    
    def test_detect_health_status_change(self, test_app):
        """测试检测健康状态变化"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        previous = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True, "failure_count": 0}
                }
            ]
        }
        
        current = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": False, "failure_count": 3}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(previous, current)
        assert len(changes) == 1
        assert changes[0]["type"] == "health_status_changed"
        assert changes[0]["port"] == 1080
        assert changes[0]["healthy"] is False
        assert changes[0]["failure_count"] == 3
    
    def test_detect_proxy_added(self, test_app):
        """测试检测新增代理"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        previous = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        current = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                },
                {
                    "local_port": 1081,
                    "upstream": {"server": "proxy2.com", "port": 10001, "protocol": "socks5"},
                    "monitoring_status": {"enabled": False, "is_healthy": True}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(previous, current)
        assert len(changes) == 1
        assert changes[0]["type"] == "proxy_added"
        assert changes[0]["port"] == 1081
    
    def test_detect_proxy_removed(self, test_app):
        """测试检测删除代理"""
        from src.proxy_relay.web_api import WebAPI
        
        # 获取WebAPI实例
        web_api = None
        for route in test_app.routes:
            if hasattr(route, 'endpoint') and hasattr(route.endpoint, '__self__'):
                if isinstance(route.endpoint.__self__, WebAPI):
                    web_api = route.endpoint.__self__
                    break
        
        assert web_api is not None
        
        previous = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                },
                {
                    "local_port": 1081,
                    "upstream": {"server": "proxy2.com", "port": 10001, "protocol": "socks5"},
                    "monitoring_status": {"enabled": False, "is_healthy": True}
                }
            ]
        }
        
        current = {
            "proxies": [
                {
                    "local_port": 1080,
                    "upstream": {"server": "proxy1.com", "port": 10000, "protocol": "socks5"},
                    "monitoring_status": {"enabled": True, "is_healthy": True}
                }
            ]
        }
        
        changes = web_api._detect_status_changes(previous, current)
        assert len(changes) == 1
        assert changes[0]["type"] == "proxy_removed"
        assert changes[0]["port"] == 1081
