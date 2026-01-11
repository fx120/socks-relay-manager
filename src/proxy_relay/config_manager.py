"""
配置管理器

负责加载、保存和验证系统配置文件。
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from .models import (
    Config,
    SystemConfig,
    MonitoringConfig,
    APIProviderConfig,
    ProxyConfig,
    UpstreamProxy,
    WebAuthConfig,
    ResponseFormat,
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器类"""
    
    DEFAULT_CONFIG_PATH = "/etc/proxy-relay/config.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 /etc/proxy-relay/config.yaml
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._current_config: Optional[Config] = None
    
    def load_config(self) -> Config:
        """
        加载配置文件
        
        Returns:
            Config: 配置对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        logger.info(f"Loading configuration from: {self.config_path}")
        
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.error("Configuration file is empty")
                raise ValueError("Configuration file is empty")
            
            config = self._parse_config(data)
            self._current_config = config
            
            logger.info(f"Configuration loaded successfully: {len(config.proxies)} proxies, {len(config.api_providers)} API providers")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML format: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: Config) -> None:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置对象
            
        Raises:
            ValueError: 配置验证失败
            IOError: 文件写入失败
        """
        logger.info(f"Saving configuration to: {self.config_path}")
        
        # 验证配置
        errors = self.validate_config(config)
        if errors:
            logger.error(f"Configuration validation failed: {', '.join(errors)}")
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        # 转换为字典
        data = self._config_to_dict(config)
        
        # 确保目录存在
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        
        # 写入文件
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            self._current_config = config
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise IOError(f"Failed to save configuration: {e}")
    
    def reload_config(self) -> Config:
        """
        重新加载配置文件
        
        Returns:
            Config: 新的配置对象
        """
        return self.load_config()
    
    def validate_config(self, config: Config) -> List[str]:
        """
        验证配置对象
        
        Args:
            config: 要验证的配置对象
            
        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        errors = []
        
        try:
            # 基本类型检查
            if not isinstance(config, Config):
                errors.append("config must be a Config instance")
                return errors
            
            # 验证系统配置
            if not isinstance(config.system, SystemConfig):
                errors.append("system must be a SystemConfig instance")
            else:
                # 验证端口范围
                if not (1024 <= config.system.web_port <= 65535):
                    errors.append(f"system.web_port must be between 1024 and 65535, got {config.system.web_port}")
                
                # 验证日志级别
                if config.system.log_level not in ["DEBUG", "INFO", "WARN", "ERROR"]:
                    errors.append(f"system.log_level must be DEBUG, INFO, WARN, or ERROR, got {config.system.log_level}")
            
            # 验证监控配置
            if not isinstance(config.monitoring, MonitoringConfig):
                errors.append("monitoring must be a MonitoringConfig instance")
            else:
                if config.monitoring.check_interval <= 0:
                    errors.append(f"monitoring.check_interval must be positive, got {config.monitoring.check_interval}")
                if config.monitoring.failure_threshold <= 0:
                    errors.append(f"monitoring.failure_threshold must be positive, got {config.monitoring.failure_threshold}")
                if config.monitoring.check_timeout <= 0:
                    errors.append(f"monitoring.check_timeout must be positive, got {config.monitoring.check_timeout}")
            
            # 验证API提供商配置
            if not isinstance(config.api_providers, list):
                errors.append("api_providers must be a list")
            else:
                provider_ids = set()
                for i, provider in enumerate(config.api_providers):
                    if not isinstance(provider, APIProviderConfig):
                        errors.append(f"api_providers[{i}] must be an APIProviderConfig instance")
                        continue
                    
                    if provider.id in provider_ids:
                        errors.append(f"duplicate api_provider id: {provider.id}")
                    provider_ids.add(provider.id)
                    
                    if provider.timeout <= 0:
                        errors.append(f"api_providers[{i}].timeout must be positive")
                    if provider.retry_attempts < 0:
                        errors.append(f"api_providers[{i}].retry_attempts must be non-negative")
            
            # 验证代理配置
            if not isinstance(config.proxies, list):
                errors.append("proxies must be a list")
            else:
                ports = set()
                for i, proxy in enumerate(config.proxies):
                    if not isinstance(proxy, ProxyConfig):
                        errors.append(f"proxies[{i}] must be a ProxyConfig instance")
                        continue
                    
                    # 验证端口范围
                    if not (1024 <= proxy.local_port <= 65535):
                        errors.append(f"proxies[{i}].local_port must be between 1024 and 65535, got {proxy.local_port}")
                    
                    # 检查端口重复
                    if proxy.local_port in ports:
                        errors.append(f"duplicate local_port: {proxy.local_port}")
                    ports.add(proxy.local_port)
                    
                    # 验证上游代理
                    if not isinstance(proxy.upstream, UpstreamProxy):
                        errors.append(f"proxies[{i}].upstream must be an UpstreamProxy instance")
                    else:
                        if not (1 <= proxy.upstream.port <= 65535):
                            errors.append(f"proxies[{i}].upstream.port must be between 1 and 65535")
                    
                    # 验证API提供商引用
                    if hasattr(config, 'api_providers'):
                        provider_ids_list = [p.id for p in config.api_providers]
                        if proxy.api_provider_id not in provider_ids_list:
                            errors.append(f"proxies[{i}].api_provider_id '{proxy.api_provider_id}' not found in api_providers")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def get_proxy_config(self, port: int) -> Optional[ProxyConfig]:
        """
        获取指定端口的代理配置
        
        Args:
            port: 本地端口号
            
        Returns:
            ProxyConfig: 代理配置，如果不存在返回 None
        """
        if not self._current_config:
            raise RuntimeError("No configuration loaded. Call load_config() first.")
        
        for proxy in self._current_config.proxies:
            if proxy.local_port == port:
                return proxy
        
        return None
    
    def update_proxy_config(self, port: int, new_config: ProxyConfig) -> None:
        """
        更新指定端口的代理配置
        
        Args:
            port: 本地端口号
            new_config: 新的代理配置
            
        Raises:
            ValueError: 端口不存在或配置无效
        """
        if not self._current_config:
            raise RuntimeError("No configuration loaded. Call load_config() first.")
        
        # 查找并更新配置
        found = False
        for i, proxy in enumerate(self._current_config.proxies):
            if proxy.local_port == port:
                self._current_config.proxies[i] = new_config
                found = True
                break
        
        if not found:
            raise ValueError(f"Proxy with port {port} not found")
        
        # 保存更新后的配置
        self.save_config(self._current_config)
    
    def _parse_config(self, data: Dict[str, Any]) -> Config:
        """
        解析配置字典为配置对象
        
        Args:
            data: 配置字典
            
        Returns:
            Config: 配置对象
        """
        # 解析系统配置
        system_data = data.get('system', {})
        web_auth_data = system_data.get('web_auth', {})
        web_auth = WebAuthConfig(
            enabled=web_auth_data.get('enabled', True),
            username=web_auth_data.get('username', 'admin'),
            password_hash=web_auth_data.get('password_hash')
        )
        
        system = SystemConfig(
            web_port=system_data.get('web_port', 8080),
            web_auth=web_auth,
            log_level=system_data.get('log_level', 'INFO'),
            log_file=system_data.get('log_file', '/var/log/proxy-relay/app.log'),
            database=system_data.get('database', '/var/lib/proxy-relay/data.db')
        )
        
        # 解析监控配置
        monitoring_data = data.get('monitoring', {})
        monitoring = MonitoringConfig(
            check_interval=monitoring_data.get('check_interval', 30),
            failure_threshold=monitoring_data.get('failure_threshold', 3),
            check_timeout=monitoring_data.get('check_timeout', 10),
            check_url=monitoring_data.get('check_url', 'http://www.google.com')
        )
        
        # 解析API提供商配置
        api_providers = []
        for provider_data in data.get('api_providers', []):
            response_format_data = provider_data.get('response_format', {})
            response_format = ResponseFormat(
                type=response_format_data.get('type', 'custom'),
                success_code=response_format_data.get('success_code'),
                success_field=response_format_data.get('success_field'),
                success_value=response_format_data.get('success_value'),
                data_path=response_format_data.get('data_path'),
                ip_field=response_format_data.get('ip_field', 'ip'),
                port_field=response_format_data.get('port_field', 'port'),
                username_field=response_format_data.get('username_field'),
                password_field=response_format_data.get('password_field')
            )
            
            provider = APIProviderConfig(
                id=provider_data['id'],
                name=provider_data['name'],
                enabled=provider_data.get('enabled', True),
                endpoint=provider_data['endpoint'],
                method=provider_data.get('method', 'GET'),
                params=provider_data.get('params'),
                headers=provider_data.get('headers'),
                body=provider_data.get('body'),
                timeout=provider_data.get('timeout', 10),
                retry_attempts=provider_data.get('retry_attempts', 3),
                retry_backoff=provider_data.get('retry_backoff', 2),
                response_format=response_format
            )
            api_providers.append(provider)
        
        # 解析代理配置
        proxies = []
        for proxy_data in data.get('proxies', []):
            upstream_data = proxy_data['upstream']
            upstream = UpstreamProxy(
                server=upstream_data['server'],
                port=upstream_data['port'],
                username=upstream_data.get('username'),
                password=upstream_data.get('password'),
                protocol=upstream_data.get('protocol', 'socks5')
            )
            
            proxy = ProxyConfig(
                local_port=proxy_data['local_port'],
                name=proxy_data['name'],
                api_provider_id=proxy_data['api_provider_id'],
                upstream=upstream,
                monitoring_enabled=proxy_data.get('monitoring_enabled', False)
            )
            proxies.append(proxy)
        
        return Config(
            system=system,
            monitoring=monitoring,
            api_providers=api_providers,
            proxies=proxies
        )
    
    def _config_to_dict(self, config: Config) -> Dict[str, Any]:
        """
        将配置对象转换为字典
        
        Args:
            config: 配置对象
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            'system': {
                'web_port': config.system.web_port,
                'web_auth': {
                    'enabled': config.system.web_auth.enabled,
                    'username': config.system.web_auth.username,
                    'password_hash': config.system.web_auth.password_hash
                },
                'log_level': config.system.log_level,
                'log_file': config.system.log_file,
                'database': config.system.database
            },
            'monitoring': {
                'check_interval': config.monitoring.check_interval,
                'failure_threshold': config.monitoring.failure_threshold,
                'check_timeout': config.monitoring.check_timeout,
                'check_url': config.monitoring.check_url
            },
            'api_providers': [
                {
                    'id': provider.id,
                    'name': provider.name,
                    'enabled': provider.enabled,
                    'endpoint': provider.endpoint,
                    'method': provider.method,
                    'params': provider.params,
                    'headers': provider.headers,
                    'body': provider.body,
                    'timeout': provider.timeout,
                    'retry_attempts': provider.retry_attempts,
                    'retry_backoff': provider.retry_backoff,
                    'response_format': {
                        'type': provider.response_format.type,
                        'success_code': provider.response_format.success_code,
                        'success_field': provider.response_format.success_field,
                        'success_value': provider.response_format.success_value,
                        'data_path': provider.response_format.data_path,
                        'ip_field': provider.response_format.ip_field,
                        'port_field': provider.response_format.port_field,
                        'username_field': provider.response_format.username_field,
                        'password_field': provider.response_format.password_field
                    }
                }
                for provider in config.api_providers
            ],
            'proxies': [
                {
                    'local_port': proxy.local_port,
                    'name': proxy.name,
                    'api_provider_id': proxy.api_provider_id,
                    'upstream': {
                        'server': proxy.upstream.server,
                        'port': proxy.upstream.port,
                        'username': proxy.upstream.username,
                        'password': proxy.upstream.password,
                        'protocol': proxy.upstream.protocol
                    },
                    'monitoring_enabled': proxy.monitoring_enabled
                }
                for proxy in config.proxies
            ]
        }
