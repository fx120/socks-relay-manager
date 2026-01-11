"""
测试密码修改功能
"""

import pytest
from fastapi.testclient import TestClient
from src.proxy_relay.web_api import create_app
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.proxy_manager import ProxyManager
from src.proxy_relay.health_monitor import HealthMonitor
from src.proxy_relay.database import Database
from src.proxy_relay.auth import hash_password, verify_password
import tempfile
import os


@pytest.fixture
def test_config_file():
    """创建测试配置文件"""
    config_content = """
system:
  web_port: 8080
  log_level: INFO
  log_file: /tmp/test.log
  database: /tmp/test.db
  web_auth:
    enabled: true
    username: admin
    password_hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIq.Ejm2W2

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: http://www.google.com

api_providers: []
proxies: []
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    yield config_path
    
    # 清理
    if os.path.exists(config_path):
        os.unlink(config_path)


@pytest.fixture
def test_client(test_config_file):
    """创建测试客户端"""
    config_manager = ConfigManager(test_config_file)
    database = Database(":memory:")
    proxy_manager = ProxyManager(config_manager, database)
    health_monitor = HealthMonitor(config_manager, proxy_manager, database)
    
    app = create_app(config_manager, proxy_manager, health_monitor, database)
    client = TestClient(app)
    
    return client, config_manager


def test_password_hash_and_verify():
    """测试密码哈希和验证"""
    password = "test123"
    hashed = hash_password(password)
    
    # 验证正确密码
    assert verify_password(password, hashed)
    
    # 验证错误密码
    assert not verify_password("wrong", hashed)


def test_change_password_success(test_client):
    """测试成功修改密码"""
    client, config_manager = test_client
    
    # 使用默认密码登录并修改密码
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "admin123",
            "new_password": "newpass123"
        },
        auth=("admin", "admin123")
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "成功" in data["message"]
    
    # 验证新密码已保存
    config = config_manager.load_config()
    assert verify_password("newpass123", config.system.web_auth.password_hash)


def test_change_password_wrong_old_password(test_client):
    """测试使用错误的旧密码"""
    client, _ = test_client
    
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "wrongpass",
            "new_password": "newpass123"
        },
        auth=("admin", "admin123")
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "不正确" in data["detail"]


def test_change_password_short_new_password(test_client):
    """测试新密码太短"""
    client, _ = test_client
    
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "admin123",
            "new_password": "123"  # 少于6个字符
        },
        auth=("admin", "admin123")
    )
    
    # Pydantic 验证应该失败
    assert response.status_code == 422


def test_change_password_unauthorized(test_client):
    """测试未认证的密码修改请求"""
    client, _ = test_client
    
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "admin123",
            "new_password": "newpass123"
        }
    )
    
    assert response.status_code == 401


def test_change_password_wrong_credentials(test_client):
    """测试使用错误的认证凭据"""
    client, _ = test_client
    
    response = client.post(
        "/api/auth/change-password",
        json={
            "old_password": "admin123",
            "new_password": "newpass123"
        },
        auth=("admin", "wrongpass")
    )
    
    assert response.status_code == 401
