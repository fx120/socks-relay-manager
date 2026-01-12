"""
VLESS 连接解析器

支持从 VLESS 链接导入代理配置。
"""

import re
import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, unquote
from .models import UpstreamProxy

logger = logging.getLogger(__name__)


class VLESSParseError(Exception):
    """VLESS 解析错误"""
    pass


class VLESSParser:
    """VLESS 连接解析器"""
    
    @staticmethod
    def parse_vless_url(vless_url: str) -> UpstreamProxy:
        """
        解析 VLESS URL 并返回 UpstreamProxy 配置
        
        VLESS URL 格式:
        vless://uuid@server:port?encryption=none&security=tls&sni=example.com&type=ws&path=/path#name
        
        Args:
            vless_url: VLESS 连接字符串
            
        Returns:
            UpstreamProxy: 解析后的代理配置
            
        Raises:
            VLESSParseError: 解析失败
        """
        logger.info("Parsing VLESS URL")
        
        try:
            # 验证 URL 格式
            if not vless_url.startswith("vless://"):
                raise VLESSParseError("URL must start with 'vless://'")
            
            # 解析 URL
            parsed = urlparse(vless_url)
            
            # 提取 UUID
            uuid = parsed.username
            if not uuid:
                raise VLESSParseError("UUID not found in URL")
            
            # 提取服务器和端口
            server = parsed.hostname
            port = parsed.port
            
            if not server:
                raise VLESSParseError("Server address not found in URL")
            if not port:
                raise VLESSParseError("Port not found in URL")
            
            # 解析查询参数
            params = parse_qs(parsed.query)
            
            # 提取参数（parse_qs 返回列表，取第一个值）
            def get_param(key: str, default: Optional[str] = None) -> Optional[str]:
                values = params.get(key, [])
                return values[0] if values else default
            
            encryption = get_param("encryption", "none")
            security = get_param("security", "none")  # none, tls, reality
            network = get_param("type", "tcp")  # tcp, ws, grpc, http
            flow = get_param("flow")
            
            # TLS 配置
            tls = security in ["tls", "reality"]
            sni = get_param("sni")
            alpn_str = get_param("alpn")
            alpn = alpn_str.split(",") if alpn_str else None
            
            # Reality 配置
            reality = security == "reality"
            reality_public_key = get_param("pbk") if reality else None  # pbk = public key
            reality_short_id = get_param("sid") if reality else None  # sid = short id
            reality_server_name = sni if reality else None  # Reality 使用 SNI 作为服务器名
            reality_fingerprint = get_param("fp") if reality else None  # fp = fingerprint
            
            # WebSocket 配置
            ws_path = None
            ws_host = None
            if network == "ws":
                ws_path = get_param("path", "/")
                ws_host = get_param("host")
            
            # gRPC 配置
            grpc_service_name = None
            if network == "grpc":
                grpc_service_name = get_param("serviceName")
            
            # 提取名称（fragment）
            name = unquote(parsed.fragment) if parsed.fragment else None
            
            logger.info(f"Successfully parsed VLESS URL: {server}:{port}, Reality: {reality}")
            
            return UpstreamProxy(
                server=server,
                port=port,
                protocol="vless",
                uuid=uuid,
                encryption=encryption,
                network=network,
                flow=flow,
                tls=tls,
                sni=sni,
                alpn=alpn,
                reality=reality,
                reality_public_key=reality_public_key,
                reality_short_id=reality_short_id,
                reality_server_name=reality_server_name,
                reality_fingerprint=reality_fingerprint,
                ws_path=ws_path,
                ws_host=ws_host,
                grpc_service_name=grpc_service_name
            )
            
        except VLESSParseError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse VLESS URL: {e}")
            raise VLESSParseError(f"Failed to parse VLESS URL: {e}")
    
    @staticmethod
    def parse_vless_json(vless_json: str) -> UpstreamProxy:
        """
        解析 VLESS JSON 配置并返回 UpstreamProxy 配置
        
        Args:
            vless_json: VLESS JSON 配置字符串
            
        Returns:
            UpstreamProxy: 解析后的代理配置
            
        Raises:
            VLESSParseError: 解析失败
        """
        logger.info("Parsing VLESS JSON configuration")
        
        try:
            config = json.loads(vless_json)
            
            # 提取必需字段
            server = config.get("server") or config.get("address")
            port = config.get("port")
            uuid = config.get("uuid") or config.get("id")
            
            if not server:
                raise VLESSParseError("Server address not found in JSON")
            if not port:
                raise VLESSParseError("Port not found in JSON")
            if not uuid:
                raise VLESSParseError("UUID not found in JSON")
            
            # 提取可选字段
            encryption = config.get("encryption", "none")
            network = config.get("network", "tcp")
            flow = config.get("flow")
            
            # TLS 配置
            tls_config = config.get("tls", {})
            tls = tls_config.get("enabled", False) if isinstance(tls_config, dict) else bool(tls_config)
            sni = tls_config.get("sni") if isinstance(tls_config, dict) else None
            alpn = tls_config.get("alpn") if isinstance(tls_config, dict) else None
            
            # Reality 配置
            reality = False
            reality_public_key = None
            reality_short_id = None
            reality_server_name = None
            reality_fingerprint = None
            
            if isinstance(tls_config, dict):
                reality_config = tls_config.get("reality", {})
                if isinstance(reality_config, dict):
                    reality = reality_config.get("enabled", False)
                    reality_public_key = reality_config.get("public_key") or reality_config.get("publicKey")
                    reality_short_id = reality_config.get("short_id") or reality_config.get("shortId")
                    reality_server_name = reality_config.get("server_name") or reality_config.get("serverName") or sni
                    
                # uTLS fingerprint
                utls_config = tls_config.get("utls", {})
                if isinstance(utls_config, dict):
                    reality_fingerprint = utls_config.get("fingerprint")
            
            # WebSocket 配置
            ws_config = config.get("ws", {})
            ws_path = ws_config.get("path") if isinstance(ws_config, dict) else None
            ws_host = ws_config.get("host") if isinstance(ws_config, dict) else None
            
            # gRPC 配置
            grpc_config = config.get("grpc", {})
            grpc_service_name = grpc_config.get("serviceName") if isinstance(grpc_config, dict) else None
            
            logger.info(f"Successfully parsed VLESS JSON: {server}:{port}, Reality: {reality}")
            
            return UpstreamProxy(
                server=server,
                port=int(port),
                protocol="vless",
                uuid=uuid,
                encryption=encryption,
                network=network,
                flow=flow,
                tls=tls,
                sni=sni,
                alpn=alpn,
                reality=reality,
                reality_public_key=reality_public_key,
                reality_short_id=reality_short_id,
                reality_server_name=reality_server_name,
                reality_fingerprint=reality_fingerprint,
                ws_path=ws_path,
                ws_host=ws_host,
                grpc_service_name=grpc_service_name
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise VLESSParseError(f"Invalid JSON format: {e}")
        except VLESSParseError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse VLESS JSON: {e}")
            raise VLESSParseError(f"Failed to parse VLESS JSON: {e}")
    
    @staticmethod
    def parse(input_str: str) -> UpstreamProxy:
        """
        自动检测并解析 VLESS 配置（URL 或 JSON）
        
        Args:
            input_str: VLESS 配置字符串（URL 或 JSON）
            
        Returns:
            UpstreamProxy: 解析后的代理配置
            
        Raises:
            VLESSParseError: 解析失败
        """
        input_str = input_str.strip()
        
        if input_str.startswith("vless://"):
            return VLESSParser.parse_vless_url(input_str)
        elif input_str.startswith("{"):
            return VLESSParser.parse_vless_json(input_str)
        else:
            raise VLESSParseError("Unsupported format. Expected VLESS URL or JSON configuration")
    
    @staticmethod
    def to_vless_url(proxy: UpstreamProxy) -> str:
        """
        将 UpstreamProxy 转换为 VLESS URL
        
        Args:
            proxy: 代理配置
            
        Returns:
            str: VLESS URL
            
        Raises:
            ValueError: 如果不是 VLESS 协议
        """
        if proxy.protocol != "vless":
            raise ValueError("Only VLESS protocol is supported")
        
        if not proxy.uuid:
            raise ValueError("UUID is required for VLESS")
        
        # 构建基础 URL
        url = f"vless://{proxy.uuid}@{proxy.server}:{proxy.port}"
        
        # 构建查询参数
        params = []
        
        if proxy.encryption and proxy.encryption != "none":
            params.append(f"encryption={proxy.encryption}")
        
        if proxy.tls:
            params.append("security=tls")
            if proxy.sni:
                params.append(f"sni={proxy.sni}")
            if proxy.alpn:
                params.append(f"alpn={','.join(proxy.alpn)}")
        
        if proxy.network and proxy.network != "tcp":
            params.append(f"type={proxy.network}")
        
        if proxy.flow:
            params.append(f"flow={proxy.flow}")
        
        # 传输层特定参数
        if proxy.network == "ws":
            if proxy.ws_path:
                params.append(f"path={proxy.ws_path}")
            if proxy.ws_host:
                params.append(f"host={proxy.ws_host}")
        elif proxy.network == "grpc":
            if proxy.grpc_service_name:
                params.append(f"serviceName={proxy.grpc_service_name}")
        
        # 添加查询参数
        if params:
            url += "?" + "&".join(params)
        
        return url
