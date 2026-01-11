"""
基本的ConfigManager测试

验证ConfigManager的核心功能是否正常工作。
"""

import os
import tempfile
import pytest
from src.proxy_relay.config_manager import ConfigManager
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


def test_config_manager_save_and_load():
    """测试配置的保存和加载"""
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = f.name
    
    try:
        # 创建配置对象
        config = Config(
            system=SystemConfig(
                web_port=8080,
                web_auth=WebAuthConfig(
                    enabled=True,
                    username="admin",
                    password_hash="test_hash"
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
                    response_format=ResponseFormat(type="custom")
                )
            ],
            proxies=[
                ProxyConfig(
                    local_port=1080,
                    name="Test Proxy",
                    api_provider_id="provider1",
                    upstream=UpstreamProxy(
                        server="proxy.example.com",
                        port=10000
                    ),
                    monitoring_enabled=False
                )
            ]
        )
        
        # 保存配置
        manager = ConfigManager(temp_path)
        manager.save_config(config)
        
        # 加载配置
        loaded_config = manager.load_config()
        
        # 验证配置
        assert loaded_config.system.web_port == 8080
        assert loaded_config.system.log_level == "INFO"
        assert loaded_config.monitoring.check_interval == 30
        assert len(loaded_config.api_providers) == 1
        assert loaded_config.api_providers[0].id == "provider1"
        assert len(loaded_config.proxies) == 1
        assert loaded_config.proxies[0].local_port == 1080
        assert loaded_config.proxies[0].upstream.server == "proxy.example.com"
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_config_validation():
    """测试配置验证"""
    manager = ConfigManager()
    
    # 创建有效配置
    valid_config = Config(
        system=SystemConfig(
            web_port=8080,
            web_auth=WebAuthConfig(enabled=False),
            log_level="INFO",
            log_file="/var/log/test.log",
            database="/var/lib/test.db"
        ),
        monitoring=MonitoringConfig(),
        api_providers=[
            APIProviderConfig(
                id="test",
                name="Test",
                enabled=True,
                endpoint="https://test.com",
                response_format=ResponseFormat(type="custom")
            )
        ],
        proxies=[
            ProxyConfig(
                local_port=1080,
                name="Test",
                api_provider_id="test",
                upstream=UpstreamProxy(server="test.com", port=10000)
            )
        ]
    )
    
    # 验证应该通过
    errors = manager.validate_config(valid_config)
    assert len(errors) == 0


def test_invalid_port_validation():
    """测试无效端口验证"""
    # 测试端口范围验证
    with pytest.raises(ValueError, match="local_port must be between 1024 and 65535"):
        ProxyConfig(
            local_port=80,  # 无效端口
            name="Test",
            api_provider_id="test",
            upstream=UpstreamProxy(server="test.com", port=10000)
        )


def test_get_proxy_config():
    """测试获取代理配置"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        temp_path = f.name
    
    try:
        config = Config(
            system=SystemConfig(
                web_port=8080,
                web_auth=WebAuthConfig(enabled=False),
                log_level="INFO",
                log_file="/var/log/test.log",
                database="/var/lib/test.db"
            ),
            monitoring=MonitoringConfig(),
            api_providers=[
                APIProviderConfig(
                    id="test",
                    name="Test",
                    enabled=True,
                    endpoint="https://test.com",
                    response_format=ResponseFormat(type="custom")
                )
            ],
            proxies=[
                ProxyConfig(
                    local_port=1080,
                    name="Proxy 1",
                    api_provider_id="test",
                    upstream=UpstreamProxy(server="proxy1.com", port=10000)
                ),
                ProxyConfig(
                    local_port=1081,
                    name="Proxy 2",
                    api_provider_id="test",
                    upstream=UpstreamProxy(server="proxy2.com", port=10001)
                )
            ]
        )
        
        manager = ConfigManager(temp_path)
        manager.save_config(config)
        manager.load_config()
        
        # 获取存在的代理配置
        proxy = manager.get_proxy_config(1080)
        assert proxy is not None
        assert proxy.name == "Proxy 1"
        assert proxy.upstream.server == "proxy1.com"
        
        # 获取不存在的代理配置
        proxy = manager.get_proxy_config(9999)
        assert proxy is None
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
