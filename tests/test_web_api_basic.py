"""
Web API 基础测试

测试FastAPI应用的基本功能。
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
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    MonitoringConfig,
    APIProviderConfig,
    ProxyConfig,
    UpstreamProxy,
    WebAuthConfig,
    ResponseFormat,
)


@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
system:
  web_port: 8080
  web_auth:
    enabled: false
    username: admin
    password_hash: null
  log_level: INFO
  log_file: /tmp/test.log
  database: /tmp/test.db

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: http://www.google.com

api_providers:
  - id: test_provider
    name: Test Provider
    enabled: true
    endpoint: https://api.example.com/proxy
    method: GET
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: custom
      data_path: data
      ip_field: ip
      port_field: port

proxies:
  - local_port: 10800
    name: Test Proxy
    api_provider_id: test_provider
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
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    yield db
    
    # 清理
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def app_components(temp_config_file, temp_db):
    """创建应用组件"""
    config_manager = ConfigManager(temp_config_file)
    config_manager.load_config()
    
    proxy_manager = ProxyManager(config_manager, database=temp_db)
    health_monitor = HealthMonitor(config_manager, proxy_manager, temp_db)
    
    return config_manager, proxy_manager, health_monitor, temp_db


@pytest.fixture
def client(app_components):
    """创建测试客户端"""
    config_manager, proxy_manager, health_monitor, database = app_components
    app = create_app(config_manager, proxy_manager, health_monitor, database)
    return TestClient(app)


def test_app_creation(app_components):
    """测试应用创建"""
    config_manager, proxy_manager, health_monitor, database = app_components
    app = create_app(config_manager, proxy_manager, health_monitor, database)
    
    assert app is not None
    assert app.title == "Proxy Relay System API"


def test_get_proxies(client):
    """测试获取所有代理"""
    response = client.get("/api/proxies")
    assert response.status_code == 200
    
    data = response.json()
    assert "proxies" in data
    assert len(data["proxies"]) == 1
    assert data["proxies"][0]["local_port"] == 10800
    assert data["proxies"][0]["name"] == "Test Proxy"


def test_get_proxy(client):
    """测试获取指定代理"""
    response = client.get("/api/proxies/10800")
    assert response.status_code == 200
    
    data = response.json()
    assert data["local_port"] == 10800
    assert data["name"] == "Test Proxy"
    assert data["upstream"]["server"] == "proxy.example.com"


def test_get_proxy_not_found(client):
    """测试获取不存在的代理"""
    response = client.get("/api/proxies/99999")
    assert response.status_code == 404


def test_get_system_status(client):
    """测试获取系统状态"""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert data["status"] == "running"
    assert "total_proxies" in data
    assert data["total_proxies"] == 1


def test_get_config(client):
    """测试获取系统配置"""
    response = client.get("/api/config")
    assert response.status_code == 200
    
    data = response.json()
    assert "system" in data
    assert "monitoring" in data
    assert data["system"]["web_port"] == 8080
    assert data["monitoring"]["check_interval"] == 30


def test_get_api_providers(client):
    """测试获取API提供商"""
    response = client.get("/api/api-providers")
    assert response.status_code == 200
    
    data = response.json()
    assert "providers" in data
    assert len(data["providers"]) == 1
    assert data["providers"][0]["id"] == "test_provider"
    assert data["providers"][0]["name"] == "Test Provider"


def test_get_api_provider(client):
    """测试获取指定API提供商"""
    response = client.get("/api/api-providers/test_provider")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == "test_provider"
    assert data["name"] == "Test Provider"
    assert data["endpoint"] == "https://api.example.com/proxy"


def test_get_api_provider_not_found(client):
    """测试获取不存在的API提供商"""
    response = client.get("/api/api-providers/nonexistent")
    assert response.status_code == 404


def test_get_history(client):
    """测试获取切换历史"""
    response = client.get("/api/history")
    assert response.status_code == 200
    
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)


def test_get_logs(client):
    """测试获取日志"""
    response = client.get("/api/system/logs")
    assert response.status_code == 200
    
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)
