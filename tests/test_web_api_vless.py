"""
Web API VLESS 链接解析测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from src.proxy_relay.models import UpstreamProxy


@pytest.fixture
def mock_vless_parser():
    """Mock VLESS 解析器"""
    with patch('src.proxy_relay.web_api.VLESSParser') as mock:
        yield mock


def test_parse_vless_url_success(client, mock_vless_parser):
    """测试成功解析 VLESS URL"""
    # 准备测试数据
    vless_url = "vless://550e8400-e29b-41d4-a716-446655440000@example.com:443?type=ws&security=tls"
    
    # Mock 解析结果
    mock_upstream = UpstreamProxy(
        server="example.com",
        port=443,
        protocol="vless",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        network="ws",
        tls=True,
        sni="example.com"
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": vless_url}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["server"] == "example.com"
    assert data["port"] == 443
    assert data["protocol"] == "vless"
    assert data["uuid"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["network"] == "ws"
    assert data["tls"] is True


def test_parse_vless_json_success(client, mock_vless_parser):
    """测试成功解析 VLESS JSON"""
    # 准备测试数据
    vless_json = '{"server": "example.com", "port": 443, "uuid": "550e8400-e29b-41d4-a716-446655440000"}'
    
    # Mock 解析结果
    mock_upstream = UpstreamProxy(
        server="example.com",
        port=443,
        protocol="vless",
        uuid="550e8400-e29b-41d4-a716-446655440000"
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": vless_json}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["server"] == "example.com"
    assert data["port"] == 443
    assert data["protocol"] == "vless"


def test_parse_vless_invalid_format(client, mock_vless_parser):
    """测试解析无效格式的 VLESS 链接"""
    from src.proxy_relay.vless_parser import VLESSParseError
    
    # Mock 解析失败
    mock_vless_parser.parse.side_effect = VLESSParseError("Invalid VLESS format")
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": "invalid-link"}
    )
    
    # 验证响应
    assert response.status_code == 400
    data = response.json()
    assert "Invalid VLESS link" in data["detail"]


def test_parse_vless_with_websocket(client, mock_vless_parser):
    """测试解析带 WebSocket 的 VLESS 链接"""
    # Mock 解析结果
    mock_upstream = UpstreamProxy(
        server="example.com",
        port=443,
        protocol="vless",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        network="ws",
        tls=True,
        sni="example.com",
        ws_path="/ws",
        ws_host="example.com"
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": "vless://..."}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["network"] == "ws"
    assert data["ws_path"] == "/ws"
    assert data["ws_host"] == "example.com"


def test_parse_vless_with_grpc(client, mock_vless_parser):
    """测试解析带 gRPC 的 VLESS 链接"""
    # Mock 解析结果
    mock_upstream = UpstreamProxy(
        server="example.com",
        port=443,
        protocol="vless",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        network="grpc",
        tls=True,
        grpc_service_name="myservice"
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": "vless://..."}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["network"] == "grpc"
    assert data["grpc_service_name"] == "myservice"


def test_parse_vless_with_flow(client, mock_vless_parser):
    """测试解析带 flow 的 VLESS 链接"""
    # Mock 解析结果
    mock_upstream = UpstreamProxy(
        server="example.com",
        port=443,
        protocol="vless",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        flow="xtls-rprx-vision",
        tls=True
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": "vless://..."}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["flow"] == "xtls-rprx-vision"


def test_parse_vless_socks5_fallback(client, mock_vless_parser):
    """测试解析 SOCKS5 链接（非 VLESS）"""
    # Mock 解析结果（SOCKS5 代理）
    mock_upstream = UpstreamProxy(
        server="proxy.example.com",
        port=1080,
        protocol="socks5",
        username="user",
        password="pass"
    )
    mock_vless_parser.parse.return_value = mock_upstream
    
    # 发送请求
    response = client.post(
        "/api/proxies/parse-vless",
        json={"link": "socks5://..."}
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["protocol"] == "socks5"
    assert data["username"] == "user"
    assert data["password"] == "pass"
    # VLESS 特定字段应该不存在或为 None
    assert data.get("uuid") is None


def test_create_proxy_with_vless_upstream(client, mock_config_manager, mock_proxy_manager):
    """测试使用 VLESS 上游创建代理"""
    # 准备测试数据
    proxy_data = {
        "local_port": 1080,
        "name": "VLESS Proxy",
        "upstream": {
            "server": "example.com",
            "port": 443,
            "protocol": "vless",
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "network": "ws",
            "tls": True,
            "sni": "example.com",
            "ws_path": "/ws"
        },
        "monitoring_enabled": False
    }
    
    # 发送请求
    response = client.post("/api/proxies", json=proxy_data)
    
    # 验证响应
    assert response.status_code == 201
    data = response.json()
    assert data["local_port"] == 1080
    assert data["name"] == "VLESS Proxy"
    assert data["upstream"]["protocol"] == "vless"
