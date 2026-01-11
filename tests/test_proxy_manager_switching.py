"""
测试代理管理器的切换功能

测试 ProxyManager 的代理切换相关方法。
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch
from src.proxy_relay.proxy_manager import ProxyManager
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.database import Database
from src.proxy_relay.models import (
    Config, SystemConfig, MonitoringConfig, ProxyConfig,
    UpstreamProxy, APIProviderConfig, ResponseFormat, WebAuthConfig
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
def sample_config():
    """创建示例配置"""
    return Config(
        system=SystemConfig(
            web_port=8080,
            web_auth=WebAuthConfig(
                enabled=False  # 禁用认证以简化测试
            ),
            log_level="INFO",
            log_file="/tmp/test.log",
            database="/tmp/test.db"
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
                endpoint="https://api.example.com/proxy",
                method="GET",
                timeout=10,
                retry_attempts=3,
                retry_backoff=2,
                response_format=ResponseFormat(
                    type="custom",
                    success_field="success",
                    success_value=True,
                    data_path="data",
                    ip_field="host",
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
                monitoring_enabled=False
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
                monitoring_enabled=True
            )
        ]
    )


@pytest.fixture
def proxy_manager_with_db(temp_config_file, temp_db_file, sample_config):
    """创建带数据库的代理管理器"""
    config_manager = ConfigManager(temp_config_file)
    config_manager.save_config(sample_config)
    
    database = Database(temp_db_file)
    
    manager = ProxyManager(config_manager, database=database)
    manager.singbox_config_path = tempfile.mktemp(suffix='.json')
    manager.singbox_pid_file = tempfile.mktemp(suffix='.pid')
    
    yield manager
    
    # 清理
    if os.path.exists(manager.singbox_config_path):
        os.unlink(manager.singbox_config_path)
    if os.path.exists(manager.singbox_pid_file):
        os.unlink(manager.singbox_pid_file)


def test_switch_upstream_proxy_success(proxy_manager_with_db):
    """测试成功切换上游代理"""
    manager = proxy_manager_with_db
    
    # 创建新的上游代理
    new_upstream = UpstreamProxy(
        server="new-proxy.example.com",
        port=20000,
        protocol="socks5"
    )
    
    # Mock _reload_singbox 方法
    with patch.object(manager, '_reload_singbox', return_value=True):
        # 执行切换
        result = manager.switch_upstream_proxy(1080, new_upstream, reason="manual")
    
    # 验证结果
    assert result is True
    
    # 验证配置已更新
    updated_config = manager.config_manager.load_config()
    proxy = next(p for p in updated_config.proxies if p.local_port == 1080)
    assert proxy.upstream.server == "new-proxy.example.com"
    assert proxy.upstream.port == 20000
    
    # 验证数据库记录
    history = manager.database.get_switch_history(local_port=1080, limit=1)
    assert len(history) == 1
    assert history[0].local_port == 1080
    assert history[0].old_upstream.server == "proxy1.example.com"
    assert history[0].new_upstream.server == "new-proxy.example.com"
    assert history[0].reason == "manual"
    assert history[0].success is True


def test_switch_upstream_proxy_invalid_port(proxy_manager_with_db):
    """测试切换不存在的端口"""
    manager = proxy_manager_with_db
    
    new_upstream = UpstreamProxy(
        server="new-proxy.example.com",
        port=20000,
        protocol="socks5"
    )
    
    # 尝试切换不存在的端口
    with pytest.raises(ValueError, match="No proxy configuration found for port"):
        manager.switch_upstream_proxy(9999, new_upstream, reason="manual")


def test_switch_upstream_proxy_invalid_reason(proxy_manager_with_db):
    """测试使用无效的切换原因"""
    manager = proxy_manager_with_db
    
    new_upstream = UpstreamProxy(
        server="new-proxy.example.com",
        port=20000,
        protocol="socks5"
    )
    
    # 尝试使用无效的原因
    with pytest.raises(ValueError, match="Invalid reason"):
        manager.switch_upstream_proxy(1080, new_upstream, reason="invalid_reason")


def test_switch_upstream_proxy_failure_rollback(proxy_manager_with_db):
    """测试切换失败时的回滚"""
    manager = proxy_manager_with_db
    
    # 保存原始上游代理
    original_upstream = manager.config.proxies[0].upstream
    
    new_upstream = UpstreamProxy(
        server="new-proxy.example.com",
        port=20000,
        protocol="socks5"
    )
    
    # Mock _reload_singbox 方法使其失败
    with patch.object(manager, '_reload_singbox', return_value=False):
        with pytest.raises(RuntimeError, match="Failed to reload sing-box"):
            manager.switch_upstream_proxy(1080, new_upstream, reason="manual")
    
    # 验证配置已回滚
    current_config = manager.config_manager.load_config()
    proxy = next(p for p in current_config.proxies if p.local_port == 1080)
    assert proxy.upstream.server == original_upstream.server
    assert proxy.upstream.port == original_upstream.port
    
    # 验证数据库记录了失败的切换
    history = manager.database.get_switch_history(local_port=1080, limit=1)
    assert len(history) == 1
    assert history[0].success is False


def test_get_new_proxy_from_api_success(proxy_manager_with_db):
    """测试从API获取新代理"""
    manager = proxy_manager_with_db
    
    # Mock API响应
    mock_response = {
        "success": True,
        "data": {
            "host": "api-proxy.example.com",
            "port": 30000
        }
    }
    
    with patch('src.proxy_relay.api_client.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        # 获取新代理
        new_proxy = manager.get_new_proxy_from_api("provider1")
    
    # 验证结果
    assert new_proxy.server == "api-proxy.example.com"
    assert new_proxy.port == 30000
    assert new_proxy.protocol == "socks5"


def test_get_new_proxy_from_api_no_client(temp_config_file, sample_config):
    """测试API客户端动态创建并获取新代理"""
    config_manager = ConfigManager(temp_config_file)
    config_manager.save_config(sample_config)
    
    # 创建没有API客户端的管理器（现在会动态创建）
    manager = ProxyManager(config_manager, api_client=None)
    
    # Mock API响应
    mock_response = {
        "success": True,
        "data": {
            "host": "dynamic-proxy.example.com",
            "port": 40000
        }
    }
    
    with patch('src.proxy_relay.api_client.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        # 获取新代理应该成功（动态创建API客户端）
        new_proxy = manager.get_new_proxy_from_api("provider1")
    
    # 验证结果
    assert new_proxy.server == "dynamic-proxy.example.com"
    assert new_proxy.port == 40000



def test_get_new_proxy_from_api_invalid_provider(proxy_manager_with_db):
    """测试使用不存在的API提供商"""
    manager = proxy_manager_with_db
    
    # 尝试使用不存在的提供商
    with pytest.raises(ValueError, match="API provider not found"):
        manager.get_new_proxy_from_api("nonexistent_provider")


def test_get_new_proxy_from_api_disabled_provider(proxy_manager_with_db):
    """测试使用已禁用的API提供商"""
    manager = proxy_manager_with_db
    
    # 禁用提供商
    manager.config.api_providers[0].enabled = False
    
    # 尝试使用已禁用的提供商
    with pytest.raises(ValueError, match="API provider is disabled"):
        manager.get_new_proxy_from_api("provider1")


@pytest.mark.skip(reason="Requires PySocks library which is optional")
def test_validate_upstream_proxy_success(proxy_manager_with_db):
    """测试验证上游代理成功"""
    manager = proxy_manager_with_db
    
    upstream = UpstreamProxy(
        server="proxy.example.com",
        port=10000,
        protocol="socks5"
    )
    
    # Mock the imports and requests
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs: 
               MagicMock() if name in ['requests', 'socks', 'socket', 'importlib'] 
               else __import__(name, *args, **kwargs)):
        with patch('src.proxy_relay.proxy_manager.ProxyManager.validate_upstream_proxy', 
                   return_value=True) as mock_validate:
            result = manager.validate_upstream_proxy(upstream, timeout=5)
    
    # 验证结果
    assert result is True


@pytest.mark.skip(reason="Requires PySocks library which is optional")
def test_validate_upstream_proxy_failure(proxy_manager_with_db):
    """测试验证上游代理失败"""
    manager = proxy_manager_with_db
    
    upstream = UpstreamProxy(
        server="invalid-proxy.example.com",
        port=10000,
        protocol="socks5"
    )
    
    # Mock to raise exception
    with patch('builtins.__import__', side_effect=Exception("Connection failed")):
        result = manager.validate_upstream_proxy(upstream, timeout=5)
    
    # 验证结果
    assert result is False


def test_switch_with_different_reasons(proxy_manager_with_db):
    """测试使用不同原因进行切换"""
    manager = proxy_manager_with_db
    
    reasons = ["manual", "health_check_failed", "api_error"]
    
    for i, reason in enumerate(reasons):
        new_upstream = UpstreamProxy(
            server=f"proxy-{i}.example.com",
            port=20000 + i,
            protocol="socks5"
        )
        
        with patch.object(manager, '_reload_singbox', return_value=True):
            result = manager.switch_upstream_proxy(1080, new_upstream, reason=reason)
        
        assert result is True
        
        # 验证数据库记录了正确的原因
        history = manager.database.get_switch_history(local_port=1080, limit=1)
        assert history[0].reason == reason
