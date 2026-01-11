"""
Web API 认证集成测试
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager
from src.proxy_relay.health_monitor import HealthMonitor
from src.proxy_relay.database import Database
from src.proxy_relay.web_api import create_app
from src.proxy_relay.auth import hash_password
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    WebAuthConfig,
    MonitoringConfig,
    ProxyConfig,
    UpstreamProxy,
    APIProviderConfig,
    ResponseFormat,
)


@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_path = f.name
    yield config_path
    if os.path.exists(config_path):
        os.unlink(config_path)


@pytest.fixture
def temp_db_file():
    """创建临时数据库文件"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def config_with_auth_enabled(temp_config_file, temp_db_file):
    """创建启用认证的配置"""
    config = Config(
        system=SystemConfig(
            web_port=8080,
            log_level="INFO",
            log_file="/tmp/test.log",
            database=temp_db_file,
            web_auth=WebAuthConfig(
                enabled=True,
                username="admin",
                password_hash=hash_password("test_password_123")
            )
        ),
        monitoring=MonitoringConfig(
            check_interval=30,
            failure_threshold=3,
            check_timeout=10,
            check_url="http://www.google.com"
        ),
        api_providers=[
            APIProviderConfig(
                id="test_provider",
                name="Test Provider",
                enabled=True,
                endpoint="http://api.example.com",
                method="GET",
                params={},
                timeout=10,
                retry_attempts=3,
                retry_backoff=2,
                response_format=ResponseFormat(
                    type="custom",
                    ip_field="ip",
                    port_field="port"
                )
            )
        ],
        proxies=[]
    )
    
    config_manager = ConfigManager(temp_config_file)
    config_manager.save_config(config)
    
    return config_manager


@pytest.fixture
def config_with_auth_disabled(temp_config_file, temp_db_file):
    """创建禁用认证的配置"""
    config = Config(
        system=SystemConfig(
            web_port=8080,
            log_level="INFO",
            log_file="/tmp/test.log",
            database=temp_db_file,
            web_auth=WebAuthConfig(
                enabled=False,
                username="admin",
                password_hash=hash_password("test_password_123")
            )
        ),
        monitoring=MonitoringConfig(
            check_interval=30,
            failure_threshold=3,
            check_timeout=10,
            check_url="http://www.google.com"
        ),
        api_providers=[],
        proxies=[]
    )
    
    config_manager = ConfigManager(temp_config_file)
    config_manager.save_config(config)
    
    return config_manager


@pytest.fixture
def app_with_auth_enabled(config_with_auth_enabled, temp_db_file):
    """创建启用认证的FastAPI应用"""
    config_manager = config_with_auth_enabled
    database = Database(temp_db_file)
    proxy_manager = ProxyManager(config_manager, database)
    health_monitor = HealthMonitor(config_manager, proxy_manager, database)
    
    app = create_app(config_manager, proxy_manager, health_monitor, database)
    return app


@pytest.fixture
def app_with_auth_disabled(config_with_auth_disabled, temp_db_file):
    """创建禁用认证的FastAPI应用"""
    config_manager = config_with_auth_disabled
    database = Database(temp_db_file)
    proxy_manager = ProxyManager(config_manager, database)
    health_monitor = HealthMonitor(config_manager, proxy_manager, database)
    
    app = create_app(config_manager, proxy_manager, health_monitor, database)
    return app


class TestWebAPIAuthEnabled:
    """Web API 启用认证测试"""
    
    def test_get_proxies_without_auth(self, app_with_auth_enabled):
        """测试未认证访问代理列表"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get("/api/proxies")
        
        # 应该返回401未授权
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
    
    def test_get_proxies_with_wrong_credentials(self, app_with_auth_enabled):
        """测试错误凭据访问代理列表"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get(
            "/api/proxies",
            auth=("admin", "wrong_password")
        )
        
        # 应该返回401未授权
        assert response.status_code == 401
    
    def test_get_proxies_with_correct_credentials(self, app_with_auth_enabled):
        """测试正确凭据访问代理列表"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get(
            "/api/proxies",
            auth=("admin", "test_password_123")
        )
        
        # 应该返回200成功
        assert response.status_code == 200
        data = response.json()
        assert "proxies" in data
        assert isinstance(data["proxies"], list)
    
    def test_get_system_status_without_auth(self, app_with_auth_enabled):
        """测试未认证访问系统状态"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get("/api/system/status")
        
        # 应该返回401未授权
        assert response.status_code == 401
    
    def test_get_system_status_with_correct_credentials(self, app_with_auth_enabled):
        """测试正确凭据访问系统状态"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get(
            "/api/system/status",
            auth=("admin", "test_password_123")
        )
        
        # 应该返回200成功
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"
    
    def test_get_config_without_auth(self, app_with_auth_enabled):
        """测试未认证访问配置"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get("/api/config")
        
        # 应该返回401未授权
        assert response.status_code == 401
    
    def test_get_config_with_correct_credentials(self, app_with_auth_enabled):
        """测试正确凭据访问配置"""
        client = TestClient(app_with_auth_enabled)
        
        response = client.get(
            "/api/config",
            auth=("admin", "test_password_123")
        )
        
        # 应该返回200成功
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "monitoring" in data


class TestWebAPIAuthDisabled:
    """Web API 禁用认证测试"""
    
    def test_get_proxies_without_auth(self, app_with_auth_disabled):
        """测试禁用认证时未认证访问代理列表"""
        client = TestClient(app_with_auth_disabled)
        
        response = client.get("/api/proxies")
        
        # 应该返回200成功（认证已禁用）
        assert response.status_code == 200
        data = response.json()
        assert "proxies" in data
    
    def test_get_system_status_without_auth(self, app_with_auth_disabled):
        """测试禁用认证时未认证访问系统状态"""
        client = TestClient(app_with_auth_disabled)
        
        response = client.get("/api/system/status")
        
        # 应该返回200成功（认证已禁用）
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_get_config_without_auth(self, app_with_auth_disabled):
        """测试禁用认证时未认证访问配置"""
        client = TestClient(app_with_auth_disabled)
        
        response = client.get("/api/config")
        
        # 应该返回200成功（认证已禁用）
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
