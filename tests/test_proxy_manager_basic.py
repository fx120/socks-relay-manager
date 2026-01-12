"""
基本的ProxyManager测试

测试ProxyManager的核心功能。
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from src.proxy_relay.proxy_manager import ProxyManager
from src.proxy_relay.config_manager import ConfigManager
from src.proxy_relay.models import (
    Config,
    SystemConfig,
    MonitoringConfig,
    APIProviderConfig,
    ProxyConfig,
    UpstreamProxy,
    ResponseFormat,
    WebAuthConfig
)


@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = """
system:
  web_port: 8080
  web_auth:
    enabled: true
    username: admin
    password_hash: test_hash
  log_level: INFO
  log_file: /var/log/proxy-relay/app.log
  database: /var/lib/proxy-relay/data.db

monitoring:
  check_interval: 30
  failure_threshold: 3
  check_timeout: 10
  check_url: "http://www.google.com"

api_providers:
  - id: "provider1"
    name: "Test Provider"
    enabled: true
    endpoint: "https://api.example.com/proxy"
    method: "GET"
    timeout: 10
    retry_attempts: 3
    retry_backoff: 2
    response_format:
      type: "custom"
      success_field: "success"
      success_value: true
      data_path: "data"
      ip_field: "host"
      port_field: "port"

proxies:
  - local_port: 1080
    name: "代理1"
    api_provider_id: "provider1"
    upstream:
      server: "proxy1.example.com"
      port: 10000
      protocol: "socks5"
    monitoring_enabled: false
  - local_port: 1081
    name: "代理2"
    api_provider_id: "provider1"
    upstream:
      server: "proxy2.example.com"
      port: 10001
      username: "user"
      password: "pass"
      protocol: "socks5"
    monitoring_enabled: true
"""
        f.write(config_data)
        temp_path = f.name
    
    yield temp_path
    
    # 清理
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def config_manager(temp_config_file):
    """创建配置管理器"""
    return ConfigManager(config_path=temp_config_file)


@pytest.fixture
def proxy_manager(config_manager):
    """创建代理管理器"""
    return ProxyManager(config_manager=config_manager)


def test_proxy_manager_initialization(proxy_manager):
    """测试ProxyManager初始化"""
    assert proxy_manager is not None
    assert proxy_manager.config_manager is not None
    assert proxy_manager.config is not None
    assert len(proxy_manager.config.proxies) == 2


def test_generate_singbox_config_basic(proxy_manager):
    """测试基本的sing-box配置生成"""
    config = proxy_manager.generate_singbox_config()
    
    # 验证配置结构
    assert "log" in config
    assert "inbounds" in config
    assert "outbounds" in config
    assert "route" in config
    
    # 验证inbounds数量
    assert len(config["inbounds"]) == 2
    
    # 验证outbounds数量
    assert len(config["outbounds"]) == 2
    
    # 验证路由规则数量
    assert len(config["route"]["rules"]) == 2


def test_generate_singbox_config_inbound_structure(proxy_manager):
    """测试inbound配置结构"""
    config = proxy_manager.generate_singbox_config()
    
    # 检查第一个inbound
    inbound1 = config["inbounds"][0]
    assert inbound1["type"] == "socks"
    assert inbound1["tag"] == "socks-1080"
    assert inbound1["listen"] == "0.0.0.0"
    assert inbound1["listen_port"] == 1080
    
    # 检查第二个inbound
    inbound2 = config["inbounds"][1]
    assert inbound2["type"] == "socks"
    assert inbound2["tag"] == "socks-1081"
    assert inbound2["listen"] == "0.0.0.0"
    assert inbound2["listen_port"] == 1081


def test_generate_singbox_config_outbound_structure(proxy_manager):
    """测试outbound配置结构"""
    config = proxy_manager.generate_singbox_config()
    
    # 检查第一个outbound（无认证）
    outbound1 = config["outbounds"][0]
    assert outbound1["type"] == "socks"  # sing-box 使用 "socks" 而不是 "socks5"
    assert outbound1["tag"] == "upstream-1080"
    assert outbound1["server"] == "proxy1.example.com"
    assert outbound1["server_port"] == 10000
    assert "username" not in outbound1
    assert "password" not in outbound1
    
    # 检查第二个outbound（有认证）
    outbound2 = config["outbounds"][1]
    assert outbound2["type"] == "socks"  # sing-box 使用 "socks" 而不是 "socks5"
    assert outbound2["tag"] == "upstream-1081"
    assert outbound2["server"] == "proxy2.example.com"
    assert outbound2["server_port"] == 10001
    assert outbound2["username"] == "user"
    assert outbound2["password"] == "pass"


def test_generate_singbox_config_routing_rules(proxy_manager):
    """测试路由规则配置"""
    config = proxy_manager.generate_singbox_config()
    
    rules = config["route"]["rules"]
    
    # 检查第一条规则
    rule1 = rules[0]
    assert rule1["inbound"] == ["socks-1080"]
    assert rule1["outbound"] == "upstream-1080"
    
    # 检查第二条规则
    rule2 = rules[1]
    assert rule2["inbound"] == ["socks-1081"]
    assert rule2["outbound"] == "upstream-1081"


def test_generate_singbox_config_without_loaded_config():
    """测试在没有加载配置时生成sing-box配置"""
    config_manager = ConfigManager(config_path="/nonexistent/path.yaml")
    proxy_manager = ProxyManager(config_manager=config_manager)
    
    with pytest.raises(RuntimeError, match="No configuration loaded"):
        proxy_manager.generate_singbox_config()


def test_apply_singbox_config_writes_file(proxy_manager):
    """测试apply_singbox_config写入文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 设置临时配置路径
        proxy_manager.singbox_config_path = os.path.join(tmpdir, "sing-box.json")
        proxy_manager.singbox_pid_file = os.path.join(tmpdir, "sing-box.pid")
        
        # 应用配置
        result = proxy_manager.apply_singbox_config()
        
        # 验证返回值
        assert result is True
        
        # 验证文件已创建
        assert os.path.exists(proxy_manager.singbox_config_path)
        
        # 验证文件内容
        with open(proxy_manager.singbox_config_path, 'r') as f:
            written_config = json.load(f)
        
        assert "inbounds" in written_config
        assert "outbounds" in written_config
        assert len(written_config["inbounds"]) == 2


def test_apply_singbox_config_with_custom_config(proxy_manager):
    """测试使用自定义配置应用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        proxy_manager.singbox_config_path = os.path.join(tmpdir, "sing-box.json")
        proxy_manager.singbox_pid_file = os.path.join(tmpdir, "sing-box.pid")
        
        # 自定义配置
        custom_config = {
            "log": {"level": "debug"},
            "inbounds": [],
            "outbounds": [],
            "route": {"rules": []}
        }
        
        # 应用自定义配置
        result = proxy_manager.apply_singbox_config(custom_config)
        
        assert result is True
        
        # 验证写入的是自定义配置
        with open(proxy_manager.singbox_config_path, 'r') as f:
            written_config = json.load(f)
        
        assert written_config["log"]["level"] == "debug"
        assert len(written_config["inbounds"]) == 0


def test_apply_singbox_config_creates_directory(proxy_manager):
    """测试apply_singbox_config创建目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 设置不存在的子目录路径
        config_path = os.path.join(tmpdir, "subdir", "sing-box.json")
        proxy_manager.singbox_config_path = config_path
        proxy_manager.singbox_pid_file = os.path.join(tmpdir, "sing-box.pid")
        
        # 应用配置
        result = proxy_manager.apply_singbox_config()
        
        assert result is True
        assert os.path.exists(config_path)
        assert os.path.exists(os.path.dirname(config_path))
