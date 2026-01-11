"""
测试直连模式（无上游代理）的代理配置
"""

import pytest
from src.proxy_relay.models import ProxyConfig, Config, SystemConfig, MonitoringConfig, WebAuthConfig


def test_proxy_config_direct_mode():
    """测试创建直连模式的代理配置"""
    proxy = ProxyConfig(
        local_port=10810,
        name="Direct Proxy",
        api_provider_id=None,
        upstream=None,
        monitoring_enabled=False,
        local_username="testuser",
        local_password="testpass"
    )
    
    assert proxy.local_port == 10810
    assert proxy.name == "Direct Proxy"
    assert proxy.api_provider_id is None
    assert proxy.upstream is None
    assert proxy.monitoring_enabled is False
    assert proxy.local_username == "testuser"
    assert proxy.local_password == "testpass"


def test_proxy_config_direct_mode_with_monitoring_fails():
    """测试直连模式不能启用监控"""
    with pytest.raises(ValueError, match="monitoring cannot be enabled for direct mode proxies"):
        ProxyConfig(
            local_port=10810,
            name="Direct Proxy",
            api_provider_id=None,
            upstream=None,
            monitoring_enabled=True
        )


def test_config_with_direct_mode_proxy():
    """测试包含直连模式代理的完整配置"""
    web_auth = WebAuthConfig(
        enabled=True,
        username="admin",
        password_hash="$2b$12$test"
    )
    
    system = SystemConfig(
        web_port=8080,
        web_auth=web_auth,
        log_level="INFO",
        log_file="/var/log/proxy-relay/app.log",
        database="/var/lib/proxy-relay/data.db"
    )
    
    monitoring = MonitoringConfig(
        check_interval=30,
        failure_threshold=3,
        check_timeout=10,
        check_url="http://www.google.com"
    )
    
    proxy = ProxyConfig(
        local_port=10810,
        name="Direct Proxy",
        api_provider_id=None,
        upstream=None,
        monitoring_enabled=False,
        local_username="qidian",
        local_password="password"
    )
    
    config = Config(
        system=system,
        monitoring=monitoring,
        api_providers=[],
        proxies=[proxy]
    )
    
    assert len(config.proxies) == 1
    assert config.proxies[0].upstream is None
    assert config.proxies[0].api_provider_id is None
