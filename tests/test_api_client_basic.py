"""
API客户端基础测试

测试API客户端的核心功能。
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from src.proxy_relay.api_client import APIClient, APIError
from src.proxy_relay.models import APIProviderConfig, ResponseFormat, UpstreamProxy


@pytest.fixture
def api_provider_91http():
    """创建91HTTP API提供商配置"""
    return APIProviderConfig(
        id="provider1",
        name="91HTTP",
        enabled=True,
        endpoint="https://api.91http.com/v1/get-ip",
        method="GET",
        params={
            "trade_no": "A461584673943",
            "secret": "jg3p8xBYPpM7J6sy",
            "num": "1",
            "format": "json",
            "protocol": "socks5"
        },
        timeout=10,
        retry_attempts=3,
        retry_backoff=2,
        response_format=ResponseFormat(
            type="91http",
            success_code=0,
            data_path="data.proxy_list",
            ip_field="ip",
            port_field="port"
        )
    )


@pytest.fixture
def api_provider_custom():
    """创建自定义格式API提供商配置"""
    return APIProviderConfig(
        id="provider2",
        name="Custom Provider",
        enabled=True,
        endpoint="https://api.example.com/proxy",
        method="POST",
        headers={"Authorization": "Bearer token123"},
        body={"type": "socks5", "count": 1},
        timeout=10,
        retry_attempts=3,
        retry_backoff=2,
        response_format=ResponseFormat(
            type="custom",
            success_field="success",
            success_value=True,
            data_path="data",
            ip_field="host",
            port_field="port",
            username_field="username",
            password_field="password"
        )
    )


class TestAPIClientInitialization:
    """测试API客户端初始化"""
    
    def test_init_with_valid_config(self, api_provider_91http):
        """测试使用有效配置初始化"""
        client = APIClient(api_provider_91http)
        assert client.provider_config == api_provider_91http
    
    def test_init_with_invalid_config(self):
        """测试使用无效配置初始化"""
        with pytest.raises(TypeError):
            APIClient("not a config")


class TestAPIRequest:
    """测试API请求功能"""
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_make_request_get_success(self, mock_get, api_provider_91http):
        """测试GET请求成功"""
        # 模拟响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "msg": "OK",
            "data": {
                "proxy_list": [
                    {"ip": "8.8.8.8", "port": 12234}
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = APIClient(api_provider_91http)
        result = client._make_request()
        
        assert result["code"] == 0
        assert "data" in result
        mock_get.assert_called_once()
    
    @patch('src.proxy_relay.api_client.requests.post')
    def test_make_request_post_success(self, mock_post, api_provider_custom):
        """测试POST请求成功"""
        # 模拟响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "host": "proxy.example.com",
                "port": 10000,
                "username": "user123",
                "password": "pass123"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = APIClient(api_provider_custom)
        result = client._make_request()
        
        assert result["success"] is True
        assert "data" in result
        mock_post.assert_called_once()
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_make_request_timeout(self, mock_get, api_provider_91http):
        """测试请求超时"""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        client = APIClient(api_provider_91http)
        
        with pytest.raises(APIError) as exc_info:
            client._make_request()
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('src.proxy_relay.api_client.requests.get')
    @patch('src.proxy_relay.api_client.time.sleep')
    def test_make_request_retry(self, mock_sleep, mock_get, api_provider_91http):
        """测试请求重试机制"""
        # 前两次失败，第三次成功
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0, "data": {"proxy_list": [{"ip": "8.8.8.8", "port": 12234}]}}
        mock_response.raise_for_status = Mock()
        
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            mock_response
        ]
        
        client = APIClient(api_provider_91http)
        result = client._make_request()
        
        assert result["code"] == 0
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # 两次重试前的等待


class TestAPIResponseParsing:
    """测试API响应解析"""
    
    def test_parse_91http_response_success(self, api_provider_91http):
        """测试解析91HTTP格式响应成功"""
        response = {
            "code": 0,
            "msg": "OK",
            "data": {
                "proxy_list": [
                    {"ip": "8.8.8.8", "port": 12234}
                ]
            }
        }
        
        client = APIClient(api_provider_91http)
        proxy = client.parse_api_response(response, api_provider_91http.response_format)
        
        assert isinstance(proxy, UpstreamProxy)
        assert proxy.server == "8.8.8.8"
        assert proxy.port == 12234
        assert proxy.protocol == "socks5"
    
    def test_parse_91http_response_error_code(self, api_provider_91http):
        """测试解析91HTTP错误响应"""
        response = {
            "code": 1,
            "msg": "Invalid parameters",
            "data": None
        }
        
        client = APIClient(api_provider_91http)
        
        with pytest.raises(APIError) as exc_info:
            client.parse_api_response(response, api_provider_91http.response_format)
        
        assert "error code" in str(exc_info.value).lower()
    
    def test_parse_91http_response_empty_list(self, api_provider_91http):
        """测试解析空代理列表"""
        response = {
            "code": 0,
            "msg": "OK",
            "data": {
                "proxy_list": []
            }
        }
        
        client = APIClient(api_provider_91http)
        
        with pytest.raises(APIError) as exc_info:
            client.parse_api_response(response, api_provider_91http.response_format)
        
        assert "no proxy" in str(exc_info.value).lower()
    
    def test_parse_custom_response_success(self, api_provider_custom):
        """测试解析自定义格式响应成功"""
        response = {
            "success": True,
            "data": {
                "host": "proxy.example.com",
                "port": 10000,
                "username": "user123",
                "password": "pass123"
            }
        }
        
        client = APIClient(api_provider_custom)
        proxy = client.parse_api_response(response, api_provider_custom.response_format)
        
        assert isinstance(proxy, UpstreamProxy)
        assert proxy.server == "proxy.example.com"
        assert proxy.port == 10000
        assert proxy.username == "user123"
        assert proxy.password == "pass123"
    
    def test_parse_custom_response_failure(self, api_provider_custom):
        """测试解析自定义格式失败响应"""
        response = {
            "success": False,
            "error": "No proxies available"
        }
        
        client = APIClient(api_provider_custom)
        
        with pytest.raises(APIError) as exc_info:
            client.parse_api_response(response, api_provider_custom.response_format)
        
        assert "failure" in str(exc_info.value).lower()


class TestExtractValueByPath:
    """测试路径提取功能"""
    
    def test_extract_simple_path(self, api_provider_91http):
        """测试提取简单路径"""
        data = {"key": "value"}
        client = APIClient(api_provider_91http)
        
        result = client._extract_value_by_path(data, "key")
        assert result == "value"
    
    def test_extract_nested_path(self, api_provider_91http):
        """测试提取嵌套路径"""
        data = {
            "data": {
                "proxy_list": [
                    {"ip": "8.8.8.8"}
                ]
            }
        }
        client = APIClient(api_provider_91http)
        
        result = client._extract_value_by_path(data, "data.proxy_list")
        assert result == [{"ip": "8.8.8.8"}]
    
    def test_extract_missing_key(self, api_provider_91http):
        """测试提取不存在的键"""
        data = {"key": "value"}
        client = APIClient(api_provider_91http)
        
        with pytest.raises(KeyError):
            client._extract_value_by_path(data, "missing")
    
    def test_extract_empty_path(self, api_provider_91http):
        """测试空路径"""
        data = {"key": "value"}
        client = APIClient(api_provider_91http)
        
        result = client._extract_value_by_path(data, "")
        assert result == data


class TestGetNewProxy:
    """测试获取新代理功能"""
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_get_new_proxy_success(self, mock_get, api_provider_91http):
        """测试成功获取新代理"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "msg": "OK",
            "data": {
                "proxy_list": [
                    {"ip": "8.8.8.8", "port": 12234}
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = APIClient(api_provider_91http)
        proxy = client.get_new_proxy()
        
        assert isinstance(proxy, UpstreamProxy)
        assert proxy.server == "8.8.8.8"
        assert proxy.port == 12234
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_get_new_proxy_failure(self, mock_get, api_provider_91http):
        """测试获取新代理失败"""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        client = APIClient(api_provider_91http)
        
        with pytest.raises(APIError):
            client.get_new_proxy()


class TestConnectionTest:
    """测试连接测试功能"""
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_connection_success(self, mock_get, api_provider_91http):
        """测试连接成功"""
        mock_response = Mock()
        mock_response.json.return_value = {"code": 0}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = APIClient(api_provider_91http)
        result = client.test_connection()
        
        assert result is True
    
    @patch('src.proxy_relay.api_client.requests.get')
    def test_connection_failure(self, mock_get, api_provider_91http):
        """测试连接失败"""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        client = APIClient(api_provider_91http)
        result = client.test_connection()
        
        assert result is False
