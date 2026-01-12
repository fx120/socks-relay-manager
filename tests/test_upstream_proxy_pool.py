"""
测试出口代理池功能 (v1.2.0)

测试出口代理池的基本 CRUD 操作和引用解析。
"""

import pytest
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    MonitoringConfig,
    UpstreamProxy,
    UpstreamProxyPool,
    ProxyConfig,
    WebAuthConfig
)


class TestUpstreamProxyPool:
    """测试出口代理池功能"""
    
    def test_create_upstream_proxy_pool(self):
        """测试创建出口代理池"""
        proxy = UpstreamProxy(
            server="proxy.example.com",
            port=1080,
            protocol="socks5"
        )
        
        upstream_pool = UpstreamProxyPool(
            id="upstream-001",
            name="测试代理1",
            proxy=proxy,
            enabled=True,
            description="测试用代理",
            tags=["测试", "美国"]
        )
        
        assert upstream_pool.id == "upstream-001"
        assert upstream_pool.name == "测试代理1"
        assert upstream_pool.enabled is True
        assert upstream_pool.proxy.server == "proxy.example.com"
        assert upstream_pool.proxy.port == 1080
        assert upstream_pool.tags == ["测试", "美国"]
    
    def test_create_vless_upstream_proxy_pool(self):
        """测试创建 VLESS 出口代理池"""
        proxy = UpstreamProxy(
            server="vless.example.com",
            port=443,
            protocol="vless",
            uuid="550e8400-e29b-41d4-a716-446655440000",
            network="ws",
            tls=True,
            sni="vless.example.com",
            ws_path="/ws"
        )
        
        upstream_pool = UpstreamProxyPool(
            id="upstream-vless-001",
            name="VLESS代理1",
            proxy=proxy,
            enabled=True
        )
        
        assert upstream_pool.proxy.protocol == "vless"
        assert upstream_pool.proxy.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert upstream_pool.proxy.network == "ws"
        assert upstream_pool.proxy.tls is True
    
    def test_config_with_upstream_proxies(self):
        """测试包含出口代理池的配置"""
        # 创建出口代理池
        proxy1 = UpstreamProxy(
            server="proxy1.example.com",
            port=1080,
            protocol="socks5"
        )
        upstream1 = UpstreamProxyPool(
            id="upstream-001",
            name="代理1",
            proxy=proxy1
        )
        
        proxy2 = UpstreamProxy(
            server="proxy2.example.com",
            port=1081,
            protocol="socks5"
        )
        upstream2 = UpstreamProxyPool(
            id="upstream-002",
            name="代理2",
            proxy=proxy2
        )
        
        # 创建本地代理，引用出口代理池
        local_proxy1 = ProxyConfig(
            local_port=10080,
            name="本地代理1",
            upstream_id="upstream-001",  # 引用出口代理池
            monitoring_enabled=False
        )
        
        local_proxy2 = ProxyConfig(
            local_port=10081,
            name="本地代理2",
            upstream_id="upstream-002",
            monitoring_enabled=False
        )
        
        # 创建完整配置
        config = Config(
            system=SystemConfig(
                web_port=8080,
                web_auth=WebAuthConfig(
                    enabled=False,
                    username="admin",
                    password_hash=None
                )
            ),
            monitoring=MonitoringConfig(),
            api_providers=[],
            upstream_proxies=[upstream1, upstream2],
            proxies=[local_proxy1, local_proxy2]
        )
        
        assert len(config.upstream_proxies) == 2
        assert len(config.proxies) == 2
        assert config.proxies[0].upstream_id == "upstream-001"
        assert config.proxies[1].upstream_id == "upstream-002"
    
    def test_config_validation_invalid_upstream_id(self):
        """测试配置验证：引用不存在的出口代理 ID"""
        upstream1 = UpstreamProxyPool(
            id="upstream-001",
            name="代理1",
            proxy=UpstreamProxy(
                server="proxy1.example.com",
                port=1080,
                protocol="socks5"
            )
        )
        
        # 引用不存在的出口代理 ID
        local_proxy = ProxyConfig(
            local_port=10080,
            name="本地代理1",
            upstream_id="upstream-999",  # 不存在的 ID
            monitoring_enabled=False
        )
        
        # 应该抛出验证错误
        with pytest.raises(ValueError, match="references non-existent upstream_id"):
            Config(
                system=SystemConfig(
                    web_port=8080,
                    web_auth=WebAuthConfig(
                        enabled=False,
                        username="admin",
                        password_hash=None
                    )
                ),
                monitoring=MonitoringConfig(),
                api_providers=[],
                upstream_proxies=[upstream1],
                proxies=[local_proxy]
            )
    
    def test_config_with_mixed_upstream_modes(self):
        """测试混合使用 upstream_id 和直接配置 upstream 的情况"""
        # 出口代理池
        upstream_pool = UpstreamProxyPool(
            id="upstream-001",
            name="代理1",
            proxy=UpstreamProxy(
                server="proxy1.example.com",
                port=1080,
                protocol="socks5"
            )
        )
        
        # 使用 upstream_id 的本地代理
        local_proxy1 = ProxyConfig(
            local_port=10080,
            name="本地代理1",
            upstream_id="upstream-001",
            monitoring_enabled=False
        )
        
        # 直接配置 upstream 的本地代理（向后兼容）
        local_proxy2 = ProxyConfig(
            local_port=10081,
            name="本地代理2",
            upstream=UpstreamProxy(
                server="direct.example.com",
                port=1082,
                protocol="socks5"
            ),
            monitoring_enabled=False
        )
        
        # 直连模式的本地代理
        local_proxy3 = ProxyConfig(
            local_port=10082,
            name="直连代理",
            monitoring_enabled=False
        )
        
        config = Config(
            system=SystemConfig(
                web_port=8080,
                web_auth=WebAuthConfig(
                    enabled=False,
                    username="admin",
                    password_hash=None
                )
            ),
            monitoring=MonitoringConfig(),
            api_providers=[],
            upstream_proxies=[upstream_pool],
            proxies=[local_proxy1, local_proxy2, local_proxy3]
        )
        
        assert config.proxies[0].upstream_id == "upstream-001"
        assert config.proxies[0].upstream is None
        assert config.proxies[1].upstream_id is None
        assert config.proxies[1].upstream is not None
        assert config.proxies[2].upstream_id is None
        assert config.proxies[2].upstream is None
    
    def test_upstream_proxy_pool_validation(self):
        """测试出口代理池数据验证"""
        # 测试空 ID
        with pytest.raises(ValueError, match="id cannot be empty"):
            UpstreamProxyPool(
                id="",
                name="测试",
                proxy=UpstreamProxy(
                    server="proxy.example.com",
                    port=1080,
                    protocol="socks5"
                )
            )
        
        # 测试空名称
        with pytest.raises(ValueError, match="name cannot be empty"):
            UpstreamProxyPool(
                id="upstream-001",
                name="",
                proxy=UpstreamProxy(
                    server="proxy.example.com",
                    port=1080,
                    protocol="socks5"
                )
            )
        
        # 测试无效的 proxy 类型
        with pytest.raises(TypeError, match="proxy must be an UpstreamProxy instance"):
            UpstreamProxyPool(
                id="upstream-001",
                name="测试",
                proxy="not a proxy object"  # 错误的类型
            )
    
    def test_duplicate_upstream_proxy_ids(self):
        """测试重复的出口代理 ID"""
        upstream1 = UpstreamProxyPool(
            id="upstream-001",
            name="代理1",
            proxy=UpstreamProxy(
                server="proxy1.example.com",
                port=1080,
                protocol="socks5"
            )
        )
        
        upstream2 = UpstreamProxyPool(
            id="upstream-001",  # 重复的 ID
            name="代理2",
            proxy=UpstreamProxy(
                server="proxy2.example.com",
                port=1081,
                protocol="socks5"
            )
        )
        
        # 应该抛出验证错误
        with pytest.raises(ValueError, match="duplicate id found in upstream_proxies"):
            Config(
                system=SystemConfig(
                    web_port=8080,
                    web_auth=WebAuthConfig(
                        enabled=False,
                        username="admin",
                        password_hash=None
                    )
                ),
                monitoring=MonitoringConfig(),
                api_providers=[],
                upstream_proxies=[upstream1, upstream2],
                proxies=[]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
