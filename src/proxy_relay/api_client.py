"""
API客户端

负责与代理供应商API交互，获取新的代理信息。
"""

import time
import logging
import requests
from typing import Optional, Dict, Any
from .models import APIProviderConfig, UpstreamProxy, ResponseFormat

logger = logging.getLogger(__name__)


class APIError(Exception):
    """API错误异常"""
    pass


class APIClient:
    """API客户端类"""
    
    def __init__(self, provider_config: APIProviderConfig):
        """
        初始化API客户端
        
        Args:
            provider_config: API提供商配置
        """
        if not isinstance(provider_config, APIProviderConfig):
            raise TypeError("provider_config must be an APIProviderConfig instance")
        
        self.provider_config = provider_config
        logger.info(f"Initialized API client for provider: {provider_config.name}")
    
    def get_new_proxy(self) -> UpstreamProxy:
        """
        从API获取新的代理
        
        Returns:
            UpstreamProxy: 新的上游代理配置
            
        Raises:
            APIError: API请求失败或响应解析失败
        """
        logger.info(f"Requesting new proxy from {self.provider_config.name}")
        
        try:
            # 发送API请求
            response_data = self._make_request()
            
            # 解析响应
            proxy = self.parse_api_response(response_data, self.provider_config.response_format)
            
            logger.info(f"Successfully obtained new proxy: {proxy.server}:{proxy.port}")
            return proxy
            
        except Exception as e:
            logger.error(f"Failed to get new proxy: {e}")
            raise APIError(f"Failed to get new proxy: {e}")
    
    def parse_api_response(self, response: Dict[str, Any], format_config: ResponseFormat) -> UpstreamProxy:
        """
        根据配置的格式解析API响应
        
        Args:
            response: API响应数据
            format_config: 响应格式配置
            
        Returns:
            UpstreamProxy: 解析后的上游代理配置
            
        Raises:
            APIError: 响应格式错误或解析失败
        """
        try:
            if format_config.type == "91http":
                return self._parse_91http_response(response, format_config)
            elif format_config.type == "custom":
                return self._parse_custom_response(response, format_config)
            else:
                raise APIError(f"Unsupported response format type: {format_config.type}")
        except Exception as e:
            logger.error(f"Failed to parse API response: {e}")
            raise APIError(f"Failed to parse API response: {e}")
    
    def test_connection(self) -> bool:
        """
        测试API连接是否正常
        
        Returns:
            bool: 连接成功返回 True，失败返回 False
        """
        logger.info(f"Testing connection to {self.provider_config.name}")
        
        try:
            self._make_request(retry=0)
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def _make_request(self, retry: int = None) -> Dict[str, Any]:
        """
        发送API请求（支持重试）
        
        Args:
            retry: 当前重试次数，None表示使用配置的重试次数
            
        Returns:
            Dict[str, Any]: API响应数据
            
        Raises:
            APIError: 请求失败或超时
        """
        max_retries = self.provider_config.retry_attempts if retry is None else retry
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 指数退避
                    backoff_time = self.provider_config.retry_backoff ** (attempt - 1)
                    logger.info(f"Retrying in {backoff_time} seconds (attempt {attempt}/{max_retries})")
                    time.sleep(backoff_time)
                
                logger.debug(f"Sending {self.provider_config.method} request to {self.provider_config.endpoint}")
                
                # 发送请求
                if self.provider_config.method == "GET":
                    response = requests.get(
                        self.provider_config.endpoint,
                        params=self.provider_config.params,
                        headers=self.provider_config.headers,
                        timeout=self.provider_config.timeout
                    )
                elif self.provider_config.method == "POST":
                    response = requests.post(
                        self.provider_config.endpoint,
                        json=self.provider_config.body,
                        headers=self.provider_config.headers,
                        timeout=self.provider_config.timeout
                    )
                else:
                    raise APIError(f"Unsupported HTTP method: {self.provider_config.method}")
                
                # 检查HTTP状态码
                response.raise_for_status()
                
                # 解析JSON响应
                data = response.json()
                logger.debug(f"Received response: {data}")
                
                return data
                
            except requests.exceptions.Timeout as e:
                last_error = f"Request timeout after {self.provider_config.timeout} seconds"
                logger.warning(f"{last_error} (attempt {attempt + 1}/{max_retries + 1})")
            except requests.exceptions.RequestException as e:
                last_error = f"Request failed: {str(e)}"
                logger.warning(f"{last_error} (attempt {attempt + 1}/{max_retries + 1})")
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.warning(f"{last_error} (attempt {attempt + 1}/{max_retries + 1})")
        
        # 所有重试都失败
        error_msg = f"API request failed after {max_retries + 1} attempts: {last_error}"
        logger.error(error_msg)
        raise APIError(error_msg)
    
    def _extract_value_by_path(self, data: Dict[str, Any], path: str) -> Any:
        """
        根据路径提取值，如 'data.proxy_list'
        
        Args:
            data: 数据字典
            path: 路径字符串，使用点号分隔
            
        Returns:
            Any: 提取的值
            
        Raises:
            KeyError: 路径不存在
        """
        if not path:
            return data
        
        keys = path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict):
                raise KeyError(f"Cannot access key '{key}' in non-dict value")
            if key not in current:
                raise KeyError(f"Key '{key}' not found in path '{path}'")
            current = current[key]
        
        return current
    
    def _parse_91http_response(self, response: Dict[str, Any], format_config: ResponseFormat) -> UpstreamProxy:
        """
        解析91HTTP格式的响应
        
        Args:
            response: API响应数据
            format_config: 响应格式配置
            
        Returns:
            UpstreamProxy: 解析后的上游代理配置
            
        Raises:
            APIError: 响应格式错误
        """
        # 检查成功码
        if format_config.success_code is not None:
            code = response.get('code')
            if code != format_config.success_code:
                msg = response.get('msg', 'Unknown error')
                raise APIError(f"API returned error code {code}: {msg}")
        
        # 提取代理列表
        if format_config.data_path:
            proxy_list = self._extract_value_by_path(response, format_config.data_path)
        else:
            raise APIError("data_path is required for 91http format")
        
        if not proxy_list or not isinstance(proxy_list, list) or len(proxy_list) == 0:
            raise APIError("No proxy found in response")
        
        # 获取第一个代理
        proxy_data = proxy_list[0]
        
        # 提取字段
        server = proxy_data.get(format_config.ip_field)
        port = proxy_data.get(format_config.port_field)
        
        if not server or not port:
            raise APIError(f"Missing required fields in proxy data: {proxy_data}")
        
        # 提取可选的认证信息
        # 91http 格式默认使用 http_user 和 http_pass 字段
        username = None
        password = None
        username_field = format_config.username_field or 'http_user'
        password_field = format_config.password_field or 'http_pass'
        username = proxy_data.get(username_field)
        password = proxy_data.get(password_field)
        
        # 检查是否有协议字段
        protocol = proxy_data.get("protocol", "socks5")
        
        # 如果是 VLESS 协议，提取额外字段
        if protocol == "vless":
            uuid = proxy_data.get("uuid")
            if not uuid:
                raise APIError("UUID is required for VLESS protocol")
            
            return UpstreamProxy(
                server=server,
                port=int(port),
                protocol="vless",
                uuid=uuid,
                flow=proxy_data.get("flow"),
                encryption=proxy_data.get("encryption", "none"),
                network=proxy_data.get("network", "tcp"),
                tls=proxy_data.get("tls", False),
                sni=proxy_data.get("sni"),
                alpn=proxy_data.get("alpn"),
                ws_path=proxy_data.get("ws_path"),
                ws_host=proxy_data.get("ws_host"),
                grpc_service_name=proxy_data.get("grpc_service_name")
            )
        else:
            return UpstreamProxy(
                server=server,
                port=int(port),
                username=username,
                password=password,
                protocol=protocol
            )
    
    def _parse_custom_response(self, response: Dict[str, Any], format_config: ResponseFormat) -> UpstreamProxy:
        """
        解析自定义格式的响应
        
        Args:
            response: API响应数据
            format_config: 响应格式配置
            
        Returns:
            UpstreamProxy: 解析后的上游代理配置
            
        Raises:
            APIError: 响应格式错误
        """
        # 检查成功标志
        if format_config.success_field:
            success = self._extract_value_by_path(response, format_config.success_field)
            if success != format_config.success_value:
                raise APIError(f"API returned failure: {response}")
        
        # 提取数据部分
        if format_config.data_path:
            data = self._extract_value_by_path(response, format_config.data_path)
        else:
            data = response
        
        # 提取字段
        server = data.get(format_config.ip_field)
        port = data.get(format_config.port_field)
        
        if not server or not port:
            raise APIError(f"Missing required fields in proxy data: {data}")
        
        # 提取可选的认证信息
        username = None
        password = None
        if format_config.username_field:
            username = data.get(format_config.username_field)
        if format_config.password_field:
            password = data.get(format_config.password_field)
        
        # 检查是否有协议字段
        protocol = data.get("protocol", "socks5")
        
        # 如果是 VLESS 协议，提取额外字段
        if protocol == "vless":
            uuid = data.get("uuid")
            if not uuid:
                raise APIError("UUID is required for VLESS protocol")
            
            return UpstreamProxy(
                server=server,
                port=int(port),
                protocol="vless",
                uuid=uuid,
                flow=data.get("flow"),
                encryption=data.get("encryption", "none"),
                network=data.get("network", "tcp"),
                tls=data.get("tls", False),
                sni=data.get("sni"),
                alpn=data.get("alpn"),
                ws_path=data.get("ws_path"),
                ws_host=data.get("ws_host"),
                grpc_service_name=data.get("grpc_service_name")
            )
        else:
            return UpstreamProxy(
                server=server,
                port=int(port),
                username=username,
                password=password,
                protocol=protocol
            )
