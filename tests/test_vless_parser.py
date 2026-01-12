"""
VLESS 解析器测试
"""

import pytest
from src.proxy_relay.vless_parser import VLESSParser, VLESSParseError
from src.proxy_relay.models import UpstreamProxy


class TestVLESSParser:
    """VLESS 解析器测试类"""
    
    def test_parse_basic_vless_url(self):
        """测试解析基本的 VLESS URL"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443"
        proxy = VLESSParser.parse_vless_url(url)
        
        assert proxy.server == "example.com"
        assert proxy.port == 443
        assert proxy.protocol == "vless"
        assert proxy.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert proxy.encryption == "none"
        assert proxy.network == "tcp"
    
    def test_parse_vless_url_with_tls(self):
        """测试解析带 TLS 的 VLESS URL"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?security=tls&sni=example.com&alpn=h2,http/1.1"
        proxy = VLESSParser.parse_vless_url(url)
        
        assert proxy.tls is True
        assert proxy.sni == "example.com"
        assert proxy.alpn == ["h2", "http/1.1"]
    
    def test_parse_vless_url_with_websocket(self):
        """测试解析带 WebSocket 的 VLESS URL"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&path=/ws&host=example.com"
        proxy = VLESSParser.parse_vless_url(url)
        
        assert proxy.network == "ws"
        assert proxy.ws_path == "/ws"
        assert proxy.ws_host == "example.com"
    
    def test_parse_vless_url_with_grpc(self):
        """测试解析带 gRPC 的 VLESS URL"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=grpc&serviceName=myservice"
        proxy = VLESSParser.parse_vless_url(url)
        
        assert proxy.network == "grpc"
        assert proxy.grpc_service_name == "myservice"
    
    def test_parse_vless_url_with_flow(self):
        """测试解析带 flow 的 VLESS URL"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?flow=xtls-rprx-vision"
        proxy = VLESSParser.parse_vless_url(url)
        
        assert proxy.flow == "xtls-rprx-vision"
    
    def test_parse_vless_url_invalid_format(self):
        """测试解析无效格式的 URL"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse_vless_url("http://example.com")
    
    def test_parse_vless_url_missing_uuid(self):
        """测试解析缺少 UUID 的 URL"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse_vless_url("vless://example.com:443")
    
    def test_parse_vless_url_missing_port(self):
        """测试解析缺少端口的 URL"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse_vless_url("vless://550e8400-e29b-41d4-a716-446655440000@example.com")
    
    def test_parse_vless_json(self):
        """测试解析 VLESS JSON 配置"""
        json_config = '''
        {
            "server": "example.com",
            "port": 443,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "network": "ws",
            "tls": {
                "enabled": true,
                "sni": "example.com"
            },
            "ws": {
                "path": "/ws",
                "host": "example.com"
            }
        }
        '''
        proxy = VLESSParser.parse_vless_json(json_config)
        
        assert proxy.server == "example.com"
        assert proxy.port == 443
        assert proxy.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert proxy.network == "ws"
        assert proxy.tls is True
        assert proxy.sni == "example.com"
        assert proxy.ws_path == "/ws"
        assert proxy.ws_host == "example.com"
    
    def test_parse_vless_json_invalid(self):
        """测试解析无效的 JSON"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse_vless_json("not a json")
    
    def test_parse_vless_json_missing_required_fields(self):
        """测试解析缺少必需字段的 JSON"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse_vless_json('{"server": "example.com"}')
    
    def test_parse_auto_detect_url(self):
        """测试自动检测 URL 格式"""
        url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443"
        proxy = VLESSParser.parse(url)
        
        assert proxy.server == "example.com"
        assert proxy.protocol == "vless"
    
    def test_parse_auto_detect_json(self):
        """测试自动检测 JSON 格式"""
        json_config = '{"server": "example.com", "port": 443, "uuid": "550e8400-e29b-41d4-a716-446655440000"}'
        proxy = VLESSParser.parse(json_config)
        
        assert proxy.server == "example.com"
        assert proxy.protocol == "vless"
    
    def test_parse_unsupported_format(self):
        """测试不支持的格式"""
        with pytest.raises(VLESSParseError):
            VLESSParser.parse("some random text")
    
    def test_to_vless_url_basic(self):
        """测试将 UpstreamProxy 转换为 VLESS URL"""
        proxy = UpstreamProxy(
            server="example.com",
            port=443,
            protocol="vless",
            uuid="550e8400-e29b-41d4-a716-446655440000"
        )
        
        url = VLESSParser.to_vless_url(proxy)
        assert url.startswith("vless://550e8400-e29b-41d4-a716-446655440000@example.com:443")
    
    def test_to_vless_url_with_tls(self):
        """测试将带 TLS 的 UpstreamProxy 转换为 URL"""
        proxy = UpstreamProxy(
            server="example.com",
            port=443,
            protocol="vless",
            uuid="550e8400-e29b-41d4-a716-446655440000",
            tls=True,
            sni="example.com",
            alpn=["h2", "http/1.1"]
        )
        
        url = VLESSParser.to_vless_url(proxy)
        assert "security=tls" in url
        assert "sni=example.com" in url
        assert "alpn=h2,http/1.1" in url
    
    def test_to_vless_url_with_websocket(self):
        """测试将带 WebSocket 的 UpstreamProxy 转换为 URL"""
        proxy = UpstreamProxy(
            server="example.com",
            port=443,
            protocol="vless",
            uuid="550e8400-e29b-41d4-a716-446655440000",
            network="ws",
            ws_path="/ws",
            ws_host="example.com"
        )
        
        url = VLESSParser.to_vless_url(proxy)
        assert "type=ws" in url
        assert "path=/ws" in url
        assert "host=example.com" in url
    
    def test_to_vless_url_non_vless_protocol(self):
        """测试转换非 VLESS 协议的代理"""
        proxy = UpstreamProxy(
            server="example.com",
            port=1080,
            protocol="socks5"
        )
        
        with pytest.raises(ValueError):
            VLESSParser.to_vless_url(proxy)
    
    def test_to_vless_url_missing_uuid(self):
        """测试转换缺少 UUID 的代理"""
        # VLESS 协议必须有 UUID，所以创建时就会失败
        with pytest.raises(ValueError, match="uuid is required for vless protocol"):
            proxy = UpstreamProxy(
                server="example.com",
                port=443,
                protocol="vless"
            )
    
    def test_roundtrip_conversion(self):
        """测试往返转换（URL -> Proxy -> URL）"""
        original_url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?security=tls&sni=example.com&type=ws&path=/ws"
        
        # 解析 URL
        proxy = VLESSParser.parse_vless_url(original_url)
        
        # 转换回 URL
        new_url = VLESSParser.to_vless_url(proxy)
        
        # 再次解析
        proxy2 = VLESSParser.parse_vless_url(new_url)
        
        # 验证关键字段相同
        assert proxy.server == proxy2.server
        assert proxy.port == proxy2.port
        assert proxy.uuid == proxy2.uuid
        assert proxy.tls == proxy2.tls
        assert proxy.sni == proxy2.sni
        assert proxy.network == proxy2.network
        assert proxy.ws_path == proxy2.ws_path
