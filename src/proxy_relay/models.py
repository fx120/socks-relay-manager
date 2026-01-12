"""
数据模型定义

包含系统中使用的所有数据类和验证逻辑。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class UpstreamProxy:
    """上游代理服务器配置"""
    server: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "socks5"
    # VLESS 特定配置
    uuid: Optional[str] = None  # VLESS UUID
    flow: Optional[str] = None  # VLESS flow (如 xtls-rprx-vision)
    encryption: str = "none"  # VLESS 加密方式，默认 none
    network: str = "tcp"  # 传输协议: tcp, ws, grpc, http
    # 传输层配置
    tls: bool = False  # 是否启用 TLS
    sni: Optional[str] = None  # TLS SNI
    alpn: Optional[List[str]] = None  # ALPN
    # Reality 配置 (VLESS Reality)
    reality: bool = False  # 是否启用 Reality
    reality_public_key: Optional[str] = None  # Reality 公钥
    reality_short_id: Optional[str] = None  # Reality 短 ID
    reality_server_name: Optional[str] = None  # Reality 握手服务器名称（通常与 SNI 相同）
    reality_fingerprint: Optional[str] = None  # uTLS 指纹 (chrome, firefox, safari, etc.)
    # WebSocket 配置
    ws_path: Optional[str] = None  # WebSocket 路径
    ws_host: Optional[str] = None  # WebSocket Host
    # gRPC 配置
    grpc_service_name: Optional[str] = None  # gRPC service name
    
    def __post_init__(self):
        """数据验证"""
        if not self.server:
            raise ValueError("server cannot be empty")
        if not isinstance(self.port, int):
            raise TypeError("port must be an integer")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        if self.protocol not in ["socks5", "http", "https", "vless"]:
            raise ValueError(f"protocol must be socks5, http, https, or vless, got {self.protocol}")
        
        # VLESS 协议特定验证
        if self.protocol == "vless":
            if not self.uuid:
                raise ValueError("uuid is required for vless protocol")
            if self.network not in ["tcp", "ws", "grpc", "http"]:
                raise ValueError(f"network must be tcp, ws, grpc, or http, got {self.network}")
            
            # Reality 验证
            if self.reality:
                if not self.reality_public_key:
                    raise ValueError("reality_public_key is required when reality is enabled")
                if not self.reality_short_id:
                    raise ValueError("reality_short_id is required when reality is enabled")


@dataclass
class ResponseFormat:
    """API响应格式配置"""
    type: str  # "91http", "custom"
    success_code: Optional[int] = None
    success_field: Optional[str] = None
    success_value: Optional[Any] = None
    data_path: Optional[str] = None
    ip_field: str = "ip"
    port_field: str = "port"
    username_field: Optional[str] = None
    password_field: Optional[str] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.type not in ["91http", "custom"]:
            raise ValueError(f"response format type must be '91http' or 'custom', got {self.type}")


@dataclass
class APIProviderConfig:
    """API提供商配置"""
    id: str
    name: str
    enabled: bool
    endpoint: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    timeout: int = 10
    retry_attempts: int = 3
    retry_backoff: int = 2
    response_format: Optional[ResponseFormat] = None
    
    def __post_init__(self):
        """数据验证"""
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.endpoint:
            raise ValueError("endpoint cannot be empty")
        if self.method not in ["GET", "POST"]:
            raise ValueError(f"method must be GET or POST, got {self.method}")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")
        if self.retry_attempts < 0:
            raise ValueError(f"retry_attempts must be non-negative, got {self.retry_attempts}")
        if self.retry_backoff <= 0:
            raise ValueError(f"retry_backoff must be positive, got {self.retry_backoff}")


@dataclass
class UpstreamProxyPool:
    """出口代理池配置"""
    id: str  # 唯一标识符
    name: str  # 显示名称
    proxy: UpstreamProxy  # 代理配置
    enabled: bool = True  # 是否启用
    description: Optional[str] = None  # 描述
    tags: Optional[List[str]] = None  # 标签（如：美国、日本、高速）
    
    def __post_init__(self):
        """数据验证"""
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not isinstance(self.proxy, UpstreamProxy):
            raise TypeError("proxy must be an UpstreamProxy instance")


@dataclass
class ProxyConfig:
    """代理配置"""
    local_port: int
    name: str
    upstream_id: Optional[str] = None  # 引用出口代理池中的 ID
    api_provider_id: Optional[str] = None  # 可选，仅在使用 API 获取上游代理时需要
    upstream: Optional[UpstreamProxy] = None  # 可选，如果为 None 则使用 direct 模式（向后兼容）
    monitoring_enabled: bool = False
    # SOCKS5 本地认证配置（可选）
    local_username: Optional[str] = None
    local_password: Optional[str] = None
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.local_port, int):
            raise TypeError("local_port must be an integer")
        if not (1024 <= self.local_port <= 65535):
            raise ValueError(f"local_port must be between 1024 and 65535, got {self.local_port}")
        if not self.name:
            raise ValueError("name cannot be empty")
        
        # 如果有上游代理，验证其类型
        if self.upstream is not None and not isinstance(self.upstream, UpstreamProxy):
            raise TypeError("upstream must be an UpstreamProxy instance or None")
        
        # 如果启用监控但没有上游代理和上游ID，报错
        if self.monitoring_enabled and self.upstream is None and not self.upstream_id:
            raise ValueError("monitoring cannot be enabled for direct mode proxies")


@dataclass
class WebAuthConfig:
    """Web认证配置"""
    enabled: bool = True
    username: str = "admin"
    password_hash: Optional[str] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.enabled and not self.password_hash:
            raise ValueError("password_hash is required when authentication is enabled")


@dataclass
class SystemConfig:
    """系统配置"""
    web_port: int = 8080
    web_auth: Optional[WebAuthConfig] = None
    log_level: str = "INFO"
    log_file: str = "/var/log/proxy-relay/app.log"
    database: str = "/var/lib/proxy-relay/data.db"
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.web_port, int):
            raise TypeError("web_port must be an integer")
        if not (1024 <= self.web_port <= 65535):
            raise ValueError(f"web_port must be between 1024 and 65535, got {self.web_port}")
        if self.log_level not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            raise ValueError(f"log_level must be DEBUG, INFO, WARN, or ERROR, got {self.log_level}")
        if not self.log_file:
            raise ValueError("log_file cannot be empty")
        if not self.database:
            raise ValueError("database cannot be empty")
        
        # 设置默认的 web_auth
        if self.web_auth is None:
            self.web_auth = WebAuthConfig()


@dataclass
class MonitoringConfig:
    """监控配置"""
    check_interval: int = 30
    failure_threshold: int = 3
    check_timeout: int = 10
    check_url: str = "http://www.google.com"
    
    def __post_init__(self):
        """数据验证"""
        if self.check_interval <= 0:
            raise ValueError(f"check_interval must be positive, got {self.check_interval}")
        if self.failure_threshold <= 0:
            raise ValueError(f"failure_threshold must be positive, got {self.failure_threshold}")
        if self.check_timeout <= 0:
            raise ValueError(f"check_timeout must be positive, got {self.check_timeout}")
        if not self.check_url:
            raise ValueError("check_url cannot be empty")


@dataclass
class Config:
    """完整的系统配置"""
    system: SystemConfig
    monitoring: MonitoringConfig
    api_providers: List[APIProviderConfig]
    upstream_proxies: List[UpstreamProxyPool]  # 出口代理池
    proxies: List[ProxyConfig]
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.system, SystemConfig):
            raise TypeError("system must be a SystemConfig instance")
        if not isinstance(self.monitoring, MonitoringConfig):
            raise TypeError("monitoring must be a MonitoringConfig instance")
        if not isinstance(self.api_providers, list):
            raise TypeError("api_providers must be a list")
        if not isinstance(self.upstream_proxies, list):
            raise TypeError("upstream_proxies must be a list")
        if not isinstance(self.proxies, list):
            raise TypeError("proxies must be a list")
        
        # 验证代理端口不重复
        ports = [p.local_port for p in self.proxies]
        if len(ports) != len(set(ports)):
            raise ValueError("duplicate local_port found in proxies")
        
        # 验证API提供商ID不重复
        provider_ids = [p.id for p in self.api_providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("duplicate id found in api_providers")
        
        # 验证出口代理池ID不重复
        upstream_ids = [u.id for u in self.upstream_proxies]
        if len(upstream_ids) != len(set(upstream_ids)):
            raise ValueError("duplicate id found in upstream_proxies")
        
        # 验证所有代理引用的API提供商存在（如果指定了 API 提供商）
        for proxy in self.proxies:
            if proxy.api_provider_id is not None and proxy.api_provider_id not in provider_ids:
                raise ValueError(f"proxy {proxy.name} references non-existent api_provider_id: {proxy.api_provider_id}")
            
            # 验证引用的出口代理存在
            if proxy.upstream_id is not None and proxy.upstream_id not in upstream_ids:
                raise ValueError(f"proxy {proxy.name} references non-existent upstream_id: {proxy.upstream_id}")
            
            # 如果有上游代理，验证其类型
            if proxy.upstream is not None and not isinstance(proxy.upstream, UpstreamProxy):
                raise TypeError(f"proxy {proxy.name} upstream must be an UpstreamProxy instance or None")


@dataclass
class MonitoringStatus:
    """监控状态"""
    local_port: int
    enabled: bool
    failure_count: int = 0
    last_check_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_upstream: Optional[UpstreamProxy] = None
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.local_port, int):
            raise TypeError("local_port must be an integer")
        if not (1024 <= self.local_port <= 65535):
            raise ValueError(f"local_port must be between 1024 and 65535, got {self.local_port}")
        if self.failure_count < 0:
            raise ValueError(f"failure_count must be non-negative, got {self.failure_count}")


@dataclass
class ProxyPortInfo:
    """代理端口信息"""
    local_port: int
    name: str
    upstream: UpstreamProxy
    monitoring_enabled: bool
    monitoring_status: Optional[MonitoringStatus] = None
    is_healthy: bool = True
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.local_port, int):
            raise TypeError("local_port must be an integer")
        if not (1024 <= self.local_port <= 65535):
            raise ValueError(f"local_port must be between 1024 and 65535, got {self.local_port}")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not isinstance(self.upstream, UpstreamProxy):
            raise TypeError("upstream must be an UpstreamProxy instance")


@dataclass
class SwitchHistoryEntry:
    """代理切换历史记录"""
    id: int
    local_port: int
    old_upstream: Optional[UpstreamProxy]
    new_upstream: UpstreamProxy
    reason: str
    timestamp: datetime
    success: bool
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.local_port, int):
            raise TypeError("local_port must be an integer")
        if not (1024 <= self.local_port <= 65535):
            raise ValueError(f"local_port must be between 1024 and 65535, got {self.local_port}")
        if not isinstance(self.new_upstream, UpstreamProxy):
            raise TypeError("new_upstream must be an UpstreamProxy instance")
        if self.old_upstream is not None and not isinstance(self.old_upstream, UpstreamProxy):
            raise TypeError("old_upstream must be an UpstreamProxy instance or None")
        if self.reason not in ["health_check_failed", "manual", "api_error"]:
            raise ValueError(f"reason must be 'health_check_failed', 'manual', or 'api_error', got {self.reason}")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime instance")
