"""
Web API 模块

提供基于FastAPI的RESTful API接口，用于管理代理配置和监控状态。
"""

import logging
import asyncio
import json
import subprocess
from typing import Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config_manager import ConfigManager
from .proxy_manager import ProxyManager
from .health_monitor import HealthMonitor
from .database import Database
from .auth import create_auth_dependency
from .system_monitor import get_system_monitor
from .models import (
    UpstreamProxy,
    ProxyConfig,
    APIProviderConfig,
    ResponseFormat,
    Config,
)

logger = logging.getLogger(__name__)


# ==================== Pydantic 模型 ====================

class UpstreamProxyModel(BaseModel):
    """上游代理模型"""
    server: str
    port: int = Field(ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "socks5"
    # VLESS 特定字段
    uuid: Optional[str] = None
    flow: Optional[str] = None
    encryption: Optional[str] = "none"
    network: Optional[str] = "tcp"
    tls: Optional[bool] = False
    sni: Optional[str] = None
    alpn: Optional[List[str]] = None
    # Reality 配置
    reality: Optional[bool] = False
    reality_public_key: Optional[str] = None
    reality_short_id: Optional[str] = None
    reality_server_name: Optional[str] = None
    reality_fingerprint: Optional[str] = None
    # WebSocket/gRPC 配置
    ws_path: Optional[str] = None
    ws_host: Optional[str] = None
    grpc_service_name: Optional[str] = None


class ProxyConfigModel(BaseModel):
    """代理配置模型"""
    local_port: int = Field(ge=1024, le=65535)
    name: str
    upstream_id: Optional[str] = None  # 引用出口代理池 ID（v1.2.0 新增）
    api_provider_id: Optional[str] = None  # 可选，仅在使用 API 获取上游代理时需要
    upstream: Optional[UpstreamProxyModel] = None  # 可选，如果为 None 则使用 direct 模式（向后兼容）
    monitoring_enabled: bool = False
    # SOCKS5 本地认证配置（可选）
    local_username: Optional[str] = None
    local_password: Optional[str] = None


class ResponseFormatModel(BaseModel):
    """API响应格式模型"""
    type: str
    success_code: Optional[int] = None
    success_field: Optional[str] = None
    success_value: Optional[str] = None
    data_path: Optional[str] = None
    ip_field: str = "ip"
    port_field: str = "port"
    username_field: Optional[str] = None
    password_field: Optional[str] = None


class APIProviderConfigModel(BaseModel):
    """API提供商配置模型"""
    id: str
    name: str
    enabled: bool = True
    endpoint: str
    method: str = "GET"
    params: Optional[dict] = None
    headers: Optional[dict] = None
    body: Optional[dict] = None
    timeout: int = 10
    retry_attempts: int = 3
    retry_backoff: int = 2
    response_format: ResponseFormatModel


class VLESSLinkModel(BaseModel):
    """VLESS 链接模型"""
    link: str = Field(..., description="VLESS URL 或 JSON 配置")


class ProxyUpdateModel(BaseModel):
    """代理更新模型"""
    name: Optional[str] = None
    upstream_id: Optional[str] = None  # 引用出口代理池 ID（v1.2.0 新增）
    api_provider_id: Optional[str] = None
    upstream: Optional[UpstreamProxyModel] = None
    monitoring_enabled: Optional[bool] = None
    local_username: Optional[str] = None
    local_password: Optional[str] = None
    fetch_from_api: Optional[bool] = False  # 是否从 API 获取上游代理


class APIProviderUpdateModel(BaseModel):
    """API提供商更新模型"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    params: Optional[dict] = None
    headers: Optional[dict] = None
    body: Optional[dict] = None
    timeout: Optional[int] = None
    retry_attempts: Optional[int] = None
    retry_backoff: Optional[int] = None
    response_format: Optional[ResponseFormatModel] = None


class PasswordChangeModel(BaseModel):
    """密码修改模型"""
    old_password: str
    new_password: str = Field(min_length=6)


class UpstreamProxyPoolModel(BaseModel):
    """出口代理池模型"""
    id: str
    name: str
    proxy: UpstreamProxyModel
    enabled: bool = True
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class UpstreamProxyPoolCreateModel(BaseModel):
    """创建出口代理池模型"""
    id: str
    name: str
    proxy: UpstreamProxyModel
    enabled: bool = True
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class UpstreamProxyPoolUpdateModel(BaseModel):
    """更新出口代理池模型"""
    name: Optional[str] = None
    proxy: Optional[UpstreamProxyModel] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ==================== FastAPI 应用 ====================

class WebAPI:
    """Web API 类"""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        proxy_manager: ProxyManager,
        health_monitor: HealthMonitor,
        database: Database
    ):
        """
        初始化Web API
        
        Args:
            config_manager: 配置管理器实例
            proxy_manager: 代理管理器实例
            health_monitor: 健康监控器实例
            database: 数据库实例
        """
        self.config_manager = config_manager
        self.proxy_manager = proxy_manager
        self.health_monitor = health_monitor
        self.database = database
        
        # SSE客户端连接管理
        self._sse_clients: List[asyncio.Queue] = []
        self._sse_lock = asyncio.Lock()
        
        # 启动后台任务监控状态变化
        self._monitoring_task = None
        
        # 创建认证依赖
        config = config_manager._current_config or config_manager.load_config()
        self.auth_dependency = create_auth_dependency(config.system.web_auth)
        
        # 初始化系统监控并启动流量采集
        system_monitor = get_system_monitor()
        system_monitor.set_database(database)
        
        # 获取所有代理端口并启动流量采集
        proxy_ports = [p.local_port for p in config.proxies]
        if proxy_ports:
            system_monitor.start_traffic_collector(proxy_ports, interval=60)
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="Proxy Relay System API",
            description="代理中转系统 RESTful API",
            version="1.0.0"
        )
        
        # 设置模板目录
        web_dir = Path(__file__).parent / "web"
        templates_dir = web_dir / "templates"
        static_dir = web_dir / "static"
        
        # 创建目录（如果不存在）
        templates_dir.mkdir(parents=True, exist_ok=True)
        static_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置模板引擎
        self.templates = Jinja2Templates(directory=str(templates_dir))
        
        # 挂载静态文件目录
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # 配置CORS
        self._setup_cors()
        
        # 设置路由
        self._setup_routes()
        
        logger.info("Web API initialized")
    
    def _setup_cors(self):
        """配置CORS中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 在生产环境中应该限制具体的域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.debug("CORS middleware configured")
    
    def _setup_routes(self):
        """设置API路由"""
        # HTML页面路由
        self.app.get("/", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_dashboard)
        self.app.get("/proxies", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_proxies)
        self.app.get("/monitoring", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_monitoring)
        self.app.get("/history", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_history)
        self.app.get("/api-providers", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_api_providers)
        self.app.get("/settings", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_settings)
        
        # 代理管理路由
        self.app.get("/api/proxies", dependencies=[Depends(self.auth_dependency)])(self.get_proxies)
        self.app.post("/api/proxies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(self.auth_dependency)])(self.create_proxy)
        self.app.get("/api/proxies/{port}", dependencies=[Depends(self.auth_dependency)])(self.get_proxy)
        self.app.put("/api/proxies/{port}", dependencies=[Depends(self.auth_dependency)])(self.update_proxy)
        self.app.delete("/api/proxies/{port}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(self.auth_dependency)])(self.delete_proxy)
        self.app.post("/api/proxies/parse-vless", dependencies=[Depends(self.auth_dependency)])(self.parse_vless_link)
        
        # 监控控制路由
        self.app.post("/api/proxies/{port}/monitoring/start", dependencies=[Depends(self.auth_dependency)])(self.start_monitoring)
        self.app.post("/api/proxies/{port}/monitoring/stop", dependencies=[Depends(self.auth_dependency)])(self.stop_monitoring)
        self.app.get("/api/proxies/{port}/monitoring/status", dependencies=[Depends(self.auth_dependency)])(self.get_monitoring_status)
        
        # 手动操作路由
        self.app.post("/api/proxies/{port}/switch", dependencies=[Depends(self.auth_dependency)])(self.switch_proxy)
        self.app.post("/api/proxies/{port}/test", dependencies=[Depends(self.auth_dependency)])(self.test_proxy)
        
        # 系统信息路由
        self.app.get("/api/system/status", dependencies=[Depends(self.auth_dependency)])(self.get_system_status)
        self.app.get("/api/system/metrics", dependencies=[Depends(self.auth_dependency)])(self.get_system_metrics)
        self.app.get("/api/system/logs", dependencies=[Depends(self.auth_dependency)])(self.get_logs)
        self.app.get("/api/history", dependencies=[Depends(self.auth_dependency)])(self.get_history)
        
        # sing-box 服务管理路由
        self.app.post("/api/system/singbox/start", dependencies=[Depends(self.auth_dependency)])(self.start_singbox)
        self.app.post("/api/system/singbox/stop", dependencies=[Depends(self.auth_dependency)])(self.stop_singbox)
        self.app.post("/api/system/singbox/restart", dependencies=[Depends(self.auth_dependency)])(self.restart_singbox)
        
        # 配置管理路由
        self.app.get("/api/config", dependencies=[Depends(self.auth_dependency)])(self.get_config)
        self.app.put("/api/config", dependencies=[Depends(self.auth_dependency)])(self.update_config)
        
        # API提供商管理路由
        self.app.get("/api/api-providers", dependencies=[Depends(self.auth_dependency)])(self.get_api_providers)
        self.app.post("/api/api-providers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(self.auth_dependency)])(self.create_api_provider)
        self.app.get("/api/api-providers/{provider_id}", dependencies=[Depends(self.auth_dependency)])(self.get_api_provider)
        self.app.put("/api/api-providers/{provider_id}", dependencies=[Depends(self.auth_dependency)])(self.update_api_provider)
        self.app.delete("/api/api-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(self.auth_dependency)])(self.delete_api_provider)
        self.app.post("/api/api-providers/{provider_id}/test", dependencies=[Depends(self.auth_dependency)])(self.test_api_provider)
        
        # 出口代理池管理路由 (v1.2.0)
        self.app.get("/upstream-proxies", response_class=HTMLResponse, dependencies=[Depends(self.auth_dependency)])(self.page_upstream_proxies)
        self.app.get("/api/upstream-proxies", dependencies=[Depends(self.auth_dependency)])(self.get_upstream_proxies)
        self.app.post("/api/upstream-proxies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(self.auth_dependency)])(self.create_upstream_proxy)
        self.app.get("/api/upstream-proxies/{upstream_id}", dependencies=[Depends(self.auth_dependency)])(self.get_upstream_proxy)
        self.app.put("/api/upstream-proxies/{upstream_id}", dependencies=[Depends(self.auth_dependency)])(self.update_upstream_proxy)
        self.app.delete("/api/upstream-proxies/{upstream_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(self.auth_dependency)])(self.delete_upstream_proxy)
        self.app.post("/api/upstream-proxies/{upstream_id}/test", dependencies=[Depends(self.auth_dependency)])(self.test_upstream_proxy)
        
        # 实时状态更新路由 (SSE)
        self.app.get("/api/events/status", dependencies=[Depends(self.auth_dependency)])(self.stream_status_updates)
        
        # 密码修改路由
        self.app.post("/api/auth/change-password", dependencies=[Depends(self.auth_dependency)])(self.change_password)
        
        logger.debug("API routes configured with authentication")
    
    # ==================== HTML页面端点 ====================
    
    async def page_dashboard(self, request: Request):
        """仪表板页面"""
        return self.templates.TemplateResponse("dashboard.html", {"request": request})
    
    async def page_proxies(self, request: Request):
        """代理管理页面"""
        return self.templates.TemplateResponse("proxies.html", {"request": request})
    
    async def page_monitoring(self, request: Request):
        """监控控制页面"""
        return self.templates.TemplateResponse("monitoring.html", {"request": request})
    
    async def page_history(self, request: Request):
        """历史记录页面"""
        return self.templates.TemplateResponse("history.html", {"request": request})
    
    async def page_api_providers(self, request: Request):
        """API提供商管理页面"""
        return self.templates.TemplateResponse("api_providers.html", {"request": request})
    
    async def page_settings(self, request: Request):
        """系统设置页面"""
        return self.templates.TemplateResponse("settings.html", {"request": request})
    
    # ==================== 代理管理端点 ====================
    
    async def get_proxies(self):
        """
        获取所有代理配置
        
        Returns:
            List[dict]: 代理配置列表
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 获取监控状态
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            
            # 获取流量统计
            traffic_stats = self.database.get_port_traffic_summary()
            
            # 获取连接数
            system_monitor = get_system_monitor()
            proxy_ports = [p.local_port for p in config.proxies]
            port_connections = system_monitor.get_port_connections(proxy_ports)
            
            # 构建响应
            proxies = []
            for proxy in config.proxies:
                monitoring_status = monitoring_statuses.get(proxy.local_port)
                traffic = traffic_stats.get(proxy.local_port, {})
                
                proxy_dict = {
                    "local_port": proxy.local_port,
                    "name": proxy.name,
                    "upstream_id": proxy.upstream_id,  # v1.2.0 新增
                    "api_provider_id": proxy.api_provider_id,
                    "upstream": {
                        "server": proxy.upstream.server,
                        "port": proxy.upstream.port,
                        "username": proxy.upstream.username,
                        "password": proxy.upstream.password,
                        "protocol": proxy.upstream.protocol
                    } if proxy.upstream else None,
                    "monitoring_enabled": proxy.monitoring_enabled,
                    "monitoring_status": None,
                    "local_username": proxy.local_username,
                    "local_password": proxy.local_password,
                    "connections": port_connections.get(proxy.local_port, 0),
                    "traffic": {
                        "total_sent": traffic.get('total_bytes_sent', 0),
                        "total_recv": traffic.get('total_bytes_recv', 0),
                        "total_sent_formatted": self._format_bytes(traffic.get('total_bytes_sent', 0)),
                        "total_recv_formatted": self._format_bytes(traffic.get('total_bytes_recv', 0))
                    }
                }
                
                if monitoring_status:
                    proxy_dict["monitoring_status"] = {
                        "enabled": monitoring_status.enabled,
                        "failure_count": monitoring_status.failure_count,
                        "last_check_time": monitoring_status.last_check_time.isoformat() if monitoring_status.last_check_time else None,
                        "last_success_time": monitoring_status.last_success_time.isoformat() if monitoring_status.last_success_time else None
                    }
                
                proxies.append(proxy_dict)
            
            logger.info(f"Retrieved {len(proxies)} proxy configurations")
            return {"proxies": proxies}
            
        except Exception as e:
            logger.error(f"Failed to get proxies: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get proxies: {str(e)}"
            )
    
    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """格式化字节数"""
        if bytes_value < 1024:
            return f"{bytes_value} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
    
    async def create_proxy(self, proxy: ProxyConfigModel):
        """
        添加新代理
        
        Args:
            proxy: 代理配置
            
        Returns:
            dict: 创建的代理配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 检查端口是否已存在
            for existing_proxy in config.proxies:
                if existing_proxy.local_port == proxy.local_port:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Proxy with port {proxy.local_port} already exists"
                    )
            
            # 如果指定了 API 提供商，检查其是否存在
            if proxy.api_provider_id:
                provider_exists = any(p.id == proxy.api_provider_id for p in config.api_providers)
                if not provider_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"API provider '{proxy.api_provider_id}' not found"
                    )
            
            # 如果指定了 upstream_id，检查其是否存在
            if proxy.upstream_id:
                upstream_exists = any(u.id == proxy.upstream_id for u in config.upstream_proxies)
                if not upstream_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Upstream proxy '{proxy.upstream_id}' not found in upstream proxy pool"
                    )
            
            # 创建上游代理配置
            upstream = None
            if proxy.upstream_id:
                # 使用出口代理池中的代理（v1.2.0 新方式）
                # upstream 字段留空，由 proxy_manager 根据 upstream_id 解析
                pass
            elif proxy.upstream:
                # 手动输入的上游代理
                upstream = UpstreamProxy(
                    server=proxy.upstream.server,
                    port=proxy.upstream.port,
                    username=proxy.upstream.username,
                    password=proxy.upstream.password,
                    protocol=proxy.upstream.protocol,
                    # VLESS 特定字段
                    uuid=proxy.upstream.uuid,
                    flow=proxy.upstream.flow,
                    encryption=proxy.upstream.encryption or "none",
                    network=proxy.upstream.network or "tcp",
                    tls=proxy.upstream.tls or False,
                    sni=proxy.upstream.sni,
                    alpn=proxy.upstream.alpn,
                    ws_path=proxy.upstream.ws_path,
                    ws_host=proxy.upstream.ws_host,
                    grpc_service_name=proxy.upstream.grpc_service_name
                )
            elif proxy.api_provider_id:
                # 通过 API 获取上游代理
                try:
                    logger.info(f"Fetching upstream proxy from API provider: {proxy.api_provider_id}")
                    upstream = self.proxy_manager.get_new_proxy_from_api(proxy.api_provider_id)
                    logger.info(f"Got upstream proxy from API: {upstream.server}:{upstream.port}")
                except Exception as api_error:
                    logger.error(f"Failed to get proxy from API: {api_error}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to get proxy from API provider: {str(api_error)}"
                    )
            
            # 验证：如果开启监控但没有上游代理和上游ID，报错
            if proxy.monitoring_enabled and not upstream and not proxy.upstream_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot enable monitoring for direct mode proxy (no upstream configured). Please configure an upstream proxy or disable monitoring."
                )
            
            # 创建新的代理配置
            new_proxy = ProxyConfig(
                local_port=proxy.local_port,
                name=proxy.name,
                upstream_id=proxy.upstream_id,  # v1.2.0 新增
                api_provider_id=proxy.api_provider_id,
                upstream=upstream,
                monitoring_enabled=proxy.monitoring_enabled,
                local_username=proxy.local_username,
                local_password=proxy.local_password
            )
            
            # 添加到配置
            config.proxies.append(new_proxy)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            # 应用sing-box配置
            try:
                self.proxy_manager.apply_singbox_config()
                logger.info(f"sing-box configuration applied successfully for proxy {proxy.name}")
            except Exception as apply_error:
                # 配置应用失败，回滚
                logger.error(f"Failed to apply sing-box config: {apply_error}")
                config.proxies.remove(new_proxy)
                self.config_manager.save_config(config)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to apply sing-box configuration: {str(apply_error)}"
                )
            
            logger.info(f"Created proxy: {proxy.name} (port {proxy.local_port})")
            
            # 构建返回数据
            result = {
                "local_port": new_proxy.local_port,
                "name": new_proxy.name,
                "upstream_id": new_proxy.upstream_id,  # v1.2.0 新增
                "api_provider_id": new_proxy.api_provider_id,
                "upstream": None,
                "monitoring_enabled": new_proxy.monitoring_enabled,
                "local_username": new_proxy.local_username,
                "local_password": "***" if new_proxy.local_password else None
            }
            
            if new_proxy.upstream:
                result["upstream"] = {
                    "server": new_proxy.upstream.server,
                    "port": new_proxy.upstream.port,
                    "username": new_proxy.upstream.username,
                    "password": "***" if new_proxy.upstream.password else None,
                    "protocol": new_proxy.upstream.protocol
                }
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create proxy: {str(e)}"
            )
    
    async def get_proxy(self, port: int):
        """
        获取指定代理
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 代理配置
        """
        try:
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 获取监控状态
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            monitoring_status = monitoring_statuses.get(port)
            
            proxy_dict = {
                "local_port": proxy_config.local_port,
                "name": proxy_config.name,
                "upstream_id": proxy_config.upstream_id,  # v1.2.0 新增
                "api_provider_id": proxy_config.api_provider_id,
                "upstream": {
                    "server": proxy_config.upstream.server,
                    "port": proxy_config.upstream.port,
                    "username": proxy_config.upstream.username,
                    "password": proxy_config.upstream.password,
                    "protocol": proxy_config.upstream.protocol
                } if proxy_config.upstream else None,
                "monitoring_enabled": proxy_config.monitoring_enabled,
                "monitoring_status": None,
                "local_username": proxy_config.local_username,
                "local_password": proxy_config.local_password
            }
            
            if monitoring_status:
                proxy_dict["monitoring_status"] = {
                    "enabled": monitoring_status.enabled,
                    "failure_count": monitoring_status.failure_count,
                    "last_check_time": monitoring_status.last_check_time.isoformat() if monitoring_status.last_check_time else None,
                    "last_success_time": monitoring_status.last_success_time.isoformat() if monitoring_status.last_success_time else None
                }
            
            logger.info(f"Retrieved proxy configuration for port {port}")
            return proxy_dict
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get proxy: {str(e)}"
            )
    
    async def update_proxy(self, port: int, proxy_update: ProxyUpdateModel):
        """
        更新代理配置
        
        Args:
            port: 本地端口号
            proxy_update: 更新的配置
            
        Returns:
            dict: 更新后的代理配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找代理配置
            proxy_config = None
            for proxy in config.proxies:
                if proxy.local_port == port:
                    proxy_config = proxy
                    break
            
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 更新字段
            if proxy_update.name is not None:
                proxy_config.name = proxy_update.name
            
            if proxy_update.upstream_id is not None:
                # 检查出口代理是否存在
                upstream_exists = any(u.id == proxy_update.upstream_id for u in config.upstream_proxies)
                if not upstream_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Upstream proxy '{proxy_update.upstream_id}' not found in upstream proxy pool"
                    )
                proxy_config.upstream_id = proxy_update.upstream_id
                # 清空直接配置的 upstream，使用 upstream_id
                proxy_config.upstream = None
            
            if proxy_update.api_provider_id is not None:
                # 检查API提供商是否存在
                provider_exists = any(p.id == proxy_update.api_provider_id for p in config.api_providers)
                if not provider_exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"API provider '{proxy_update.api_provider_id}' not found"
                    )
                proxy_config.api_provider_id = proxy_update.api_provider_id
            
            # 处理上游代理配置
            if proxy_update.upstream is not None:
                # 手动输入的上游代理（向后兼容）
                proxy_config.upstream = UpstreamProxy(
                    server=proxy_update.upstream.server,
                    port=proxy_update.upstream.port,
                    username=proxy_update.upstream.username,
                    password=proxy_update.upstream.password,
                    protocol=proxy_update.upstream.protocol,
                    # VLESS 特定字段
                    uuid=proxy_update.upstream.uuid,
                    flow=proxy_update.upstream.flow,
                    encryption=proxy_update.upstream.encryption or "none",
                    network=proxy_update.upstream.network or "tcp",
                    tls=proxy_update.upstream.tls or False,
                    sni=proxy_update.upstream.sni,
                    alpn=proxy_update.upstream.alpn,
                    ws_path=proxy_update.upstream.ws_path,
                    ws_host=proxy_update.upstream.ws_host,
                    grpc_service_name=proxy_update.upstream.grpc_service_name
                )
                # 清空 upstream_id
                proxy_config.upstream_id = None
            elif proxy_update.fetch_from_api and proxy_config.api_provider_id:
                # 从 API 获取上游代理
                try:
                    logger.info(f"Fetching upstream proxy from API provider: {proxy_config.api_provider_id}")
                    proxy_config.upstream = self.proxy_manager.get_new_proxy_from_api(proxy_config.api_provider_id)
                    logger.info(f"Got upstream proxy from API: {proxy_config.upstream.server}:{proxy_config.upstream.port}")
                except Exception as api_error:
                    logger.error(f"Failed to get proxy from API: {api_error}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to get proxy from API provider: {str(api_error)}"
                    )
            
            if proxy_update.monitoring_enabled is not None:
                proxy_config.monitoring_enabled = proxy_update.monitoring_enabled
            
            # 验证：如果开启监控但没有上游代理和上游ID，报错
            if proxy_config.monitoring_enabled and not proxy_config.upstream and not proxy_config.upstream_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot enable monitoring for direct mode proxy (no upstream configured). Please configure an upstream proxy or disable monitoring."
                )
            
            # 保存配置
            self.config_manager.save_config(config)
            
            # 应用sing-box配置
            self.proxy_manager.apply_singbox_config()
            
            logger.info(f"Updated proxy configuration for port {port}")
            
            return {
                "local_port": proxy_config.local_port,
                "name": proxy_config.name,
                "upstream_id": proxy_config.upstream_id,  # v1.2.0 新增
                "api_provider_id": proxy_config.api_provider_id,
                "upstream": {
                    "server": proxy_config.upstream.server,
                    "port": proxy_config.upstream.port,
                    "username": proxy_config.upstream.username,
                    "password": proxy_config.upstream.password,
                    "protocol": proxy_config.upstream.protocol
                } if proxy_config.upstream else None,
                "monitoring_enabled": proxy_config.monitoring_enabled,
                "local_username": proxy_config.local_username,
                "local_password": proxy_config.local_password
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update proxy: {str(e)}"
            )
    
    async def delete_proxy(self, port: int):
        """
        删除代理
        
        Args:
            port: 本地端口号
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找并删除代理配置
            proxy_index = None
            for i, proxy in enumerate(config.proxies):
                if proxy.local_port == port:
                    proxy_index = i
                    break
            
            if proxy_index is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 如果监控正在运行，先停止监控
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            if port in monitoring_statuses and monitoring_statuses[port].enabled:
                try:
                    self.health_monitor.stop_monitoring(port)
                except Exception as e:
                    logger.warning(f"Failed to stop monitoring for port {port}: {e}")
            
            # 删除代理配置
            deleted_proxy = config.proxies.pop(proxy_index)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            # 应用sing-box配置
            self.proxy_manager.apply_singbox_config()
            
            # 删除监控状态
            self.database.delete_monitoring_state(port)
            
            logger.info(f"Deleted proxy: {deleted_proxy.name} (port {port})")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete proxy: {str(e)}"
            )
    
    async def parse_vless_link(self, data: VLESSLinkModel):
        """
        解析 VLESS 链接
        
        Args:
            data: VLESS 链接数据
            
        Returns:
            dict: 解析后的代理配置
        """
        try:
            from .vless_parser import VLESSParser, VLESSParseError
            
            logger.info("Parsing VLESS link")
            
            # 解析 VLESS 链接
            try:
                upstream = VLESSParser.parse(data.link)
                logger.info(f"Successfully parsed VLESS link: {upstream.server}:{upstream.port}")
            except VLESSParseError as e:
                logger.error(f"Failed to parse VLESS link: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid VLESS link: {str(e)}"
                )
            
            # 构建返回数据
            result = {
                "server": upstream.server,
                "port": upstream.port,
                "protocol": upstream.protocol,
                "username": upstream.username,
                "password": upstream.password
            }
            
            # 添加 VLESS 特定字段
            if upstream.protocol == "vless":
                result.update({
                    "uuid": upstream.uuid,
                    "flow": upstream.flow,
                    "encryption": upstream.encryption,
                    "network": upstream.network,
                    "tls": upstream.tls,
                    "sni": upstream.sni,
                    "alpn": upstream.alpn,
                    "reality": upstream.reality,
                    "reality_public_key": upstream.reality_public_key,
                    "reality_short_id": upstream.reality_short_id,
                    "reality_server_name": upstream.reality_server_name,
                    "reality_fingerprint": upstream.reality_fingerprint,
                    "ws_path": upstream.ws_path,
                    "ws_host": upstream.ws_host,
                    "grpc_service_name": upstream.grpc_service_name
                })
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to parse VLESS link: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse VLESS link: {str(e)}"
            )
    
    # ==================== 监控控制端点 ====================
    
    async def start_monitoring(self, port: int):
        """
        启动监控
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 操作结果
        """
        try:
            # 检查代理配置是否存在
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 验证：如果没有上游代理，不能启动监控
            if not proxy_config.upstream:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot start monitoring for direct mode proxy (no upstream configured). Please configure an upstream proxy first."
                )
            
            # 启动监控
            self.health_monitor.start_monitoring(port)
            
            logger.info(f"Started monitoring for port {port}")
            return {
                "message": f"Monitoring started for port {port}",
                "port": port,
                "status": "started"
            }
            
        except ValueError as e:
            # 监控已经在运行
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start monitoring: {str(e)}"
            )
    
    async def stop_monitoring(self, port: int):
        """
        停止监控
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 操作结果
        """
        try:
            # 停止监控
            self.health_monitor.stop_monitoring(port)
            
            logger.info(f"Stopped monitoring for port {port}")
            return {
                "message": f"Monitoring stopped for port {port}",
                "port": port,
                "status": "stopped"
            }
            
        except ValueError as e:
            # 监控未运行
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop monitoring: {str(e)}"
            )
    
    async def get_monitoring_status(self, port: int):
        """
        获取监控状态
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 监控状态
        """
        try:
            # 检查代理配置是否存在
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 获取监控状态
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            monitoring_status = monitoring_statuses.get(port)
            
            if not monitoring_status:
                # 监控未启动
                return {
                    "port": port,
                    "enabled": False,
                    "failure_count": 0,
                    "last_check_time": None,
                    "last_success_time": None
                }
            
            return {
                "port": port,
                "enabled": monitoring_status.enabled,
                "failure_count": monitoring_status.failure_count,
                "last_check_time": monitoring_status.last_check_time.isoformat() if monitoring_status.last_check_time else None,
                "last_success_time": monitoring_status.last_success_time.isoformat() if monitoring_status.last_success_time else None,
                "current_upstream": {
                    "server": monitoring_status.current_upstream.server,
                    "port": monitoring_status.current_upstream.port,
                    "protocol": monitoring_status.current_upstream.protocol
                } if monitoring_status.current_upstream else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get monitoring status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get monitoring status: {str(e)}"
            )
    
    # ==================== 手动操作端点 ====================
    
    async def switch_proxy(self, port: int):
        """
        手动切换代理
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 操作结果
        """
        try:
            # 检查代理配置是否存在
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 从API获取新代理
            new_upstream = self.proxy_manager.get_new_proxy_from_api(proxy_config.api_provider_id)
            
            # 切换代理
            success = self.proxy_manager.switch_upstream_proxy(
                local_port=port,
                new_upstream=new_upstream,
                reason="manual"
            )
            
            if success:
                logger.info(f"Manually switched proxy for port {port}")
                return {
                    "message": f"Proxy switched successfully for port {port}",
                    "port": port,
                    "new_upstream": {
                        "server": new_upstream.server,
                        "port": new_upstream.port,
                        "protocol": new_upstream.protocol
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to switch proxy"
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to switch proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to switch proxy: {str(e)}"
            )
    
    async def test_proxy(self, port: int):
        """
        测试代理连接
        
        Args:
            port: 本地端口号
            
        Returns:
            dict: 测试结果
        """
        try:
            # 检查代理配置是否存在
            proxy_config = self.config_manager.get_proxy_config(port)
            if not proxy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Proxy with port {port} not found"
                )
            
            # 检查是否有上游代理配置
            if not proxy_config.upstream:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Proxy port {port} has no upstream configured. Please configure an upstream proxy first."
                )
            
            # 测试代理健康状态
            is_healthy, response_time_ms, error_message = self.health_monitor.check_proxy_health(
                proxy_config.upstream
            )
            
            logger.info(f"Tested proxy for port {port}: healthy={is_healthy}")
            
            return {
                "port": port,
                "healthy": is_healthy,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "upstream": {
                    "server": proxy_config.upstream.server,
                    "port": proxy_config.upstream.port,
                    "protocol": proxy_config.upstream.protocol
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to test proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to test proxy: {str(e)}"
            )
    
    # ==================== 系统信息端点 ====================
    
    async def get_system_status(self):
        """
        获取系统状态
        
        Returns:
            dict: 系统状态信息
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 获取监控状态
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            
            # 统计信息
            total_proxies = len(config.proxies)
            active_monitoring = sum(1 for status in monitoring_statuses.values() if status.enabled)
            healthy_proxies = 0
            unhealthy_proxies = 0
            
            for proxy in config.proxies:
                status = monitoring_statuses.get(proxy.local_port)
                if status and status.enabled:
                    if status.failure_count == 0:
                        healthy_proxies += 1
                    else:
                        unhealthy_proxies += 1
            
            # 获取最近的切换历史
            recent_switches = self.database.get_switch_history(limit=5)
            
            # 检查 sing-box 服务状态
            singbox_status = self._check_singbox_status()
            
            # 获取系统监控数据
            system_monitor = get_system_monitor()
            system_metrics = system_monitor.get_system_metrics()
            
            # 获取各端口连接数
            proxy_ports = [p.local_port for p in config.proxies]
            port_connections = system_monitor.get_port_connections(proxy_ports)
            
            return {
                "status": "running",
                "total_proxies": total_proxies,
                "active_monitoring": active_monitoring,
                "healthy_proxies": healthy_proxies,
                "unhealthy_proxies": unhealthy_proxies,
                "recent_switches": len(recent_switches),
                "singbox": singbox_status,
                "config": {
                    "web_port": config.system.web_port,
                    "log_level": config.system.log_level,
                    "check_interval": config.monitoring.check_interval,
                    "failure_threshold": config.monitoring.failure_threshold
                },
                "metrics": system_metrics,
                "port_connections": port_connections
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get system status: {str(e)}"
            )
    
    async def get_system_metrics(self):
        """
        获取系统实时监控指标
        
        Returns:
            dict: 系统监控指标
        """
        try:
            system_monitor = get_system_monitor()
            metrics = system_monitor.get_system_metrics()
            
            # 获取各端口连接数
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            proxy_ports = [p.local_port for p in config.proxies]
            port_connections = system_monitor.get_port_connections(proxy_ports)
            
            metrics["port_connections"] = port_connections
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get system metrics: {str(e)}"
            )
    
    async def get_logs(self, limit: int = 100, offset: int = 0):
        """
        获取日志
        
        Args:
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            dict: 日志列表
        """
        try:
            # 获取健康检查日志
            health_logs = self.database.get_health_check_logs(limit=limit, offset=offset)
            
            logger.info(f"Retrieved {len(health_logs)} health check logs")
            
            return {
                "logs": health_logs,
                "limit": limit,
                "offset": offset,
                "total": len(health_logs)
            }
            
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get logs: {str(e)}"
            )
    
    async def get_history(self, port: Optional[int] = None, limit: int = 100, offset: int = 0):
        """
        获取切换历史
        
        Args:
            port: 本地端口（可选，None表示查询所有端口）
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            dict: 切换历史列表
        """
        try:
            # 获取切换历史
            history_entries = self.database.get_switch_history(
                local_port=port,
                limit=limit,
                offset=offset
            )
            
            # 转换为字典列表
            history = []
            for entry in history_entries:
                history_dict = {
                    "id": entry.id,
                    "local_port": entry.local_port,
                    "old_upstream": None,
                    "new_upstream": {
                        "server": entry.new_upstream.server,
                        "port": entry.new_upstream.port,
                        "protocol": entry.new_upstream.protocol
                    },
                    "reason": entry.reason,
                    "timestamp": entry.timestamp.isoformat(),
                    "success": entry.success
                }
                
                if entry.old_upstream:
                    history_dict["old_upstream"] = {
                        "server": entry.old_upstream.server,
                        "port": entry.old_upstream.port,
                        "protocol": entry.old_upstream.protocol
                    }
                
                history.append(history_dict)
            
            logger.info(f"Retrieved {len(history)} switch history entries")
            
            return {
                "history": history,
                "port": port,
                "limit": limit,
                "offset": offset,
                "total": len(history)
            }
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get history: {str(e)}"
            )
    
    # ==================== sing-box 服务管理端点 ====================
    
    def _check_singbox_status(self):
        """
        检查 sing-box 服务状态
        
        Returns:
            dict: sing-box 服务状态信息
        """
        try:
            # 检查 systemd 服务状态 - 使用 returncode 判断更可靠
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "sing-box"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # returncode 0 表示 active，非 0 表示 inactive
            is_active = result.returncode == 0
            status_text = result.stdout.strip()
            
            logger.info(f"sing-box status check: returncode={result.returncode}, is_active={is_active}, output='{status_text}'")
            
            # 如果有 stderr 输出，可能是权限问题
            if result.stderr.strip():
                logger.warning(f"sing-box status check stderr: {result.stderr.strip()}")
            
            # 获取版本信息
            version_result = subprocess.run(
                ["sing-box", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = version_result.stdout.strip().split('\n')[0] if version_result.returncode == 0 else "unknown"
            
            status_dict = {
                "running": is_active,
                "status": status_text if status_text else ("active" if is_active else "inactive"),
                "version": version,
                "enabled": self._is_singbox_enabled()
            }
            
            logger.info(f"sing-box status result: {status_dict}")
            return status_dict
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout checking sing-box status")
            return {
                "running": False,
                "status": "unknown",
                "version": "unknown",
                "enabled": False,
                "error": "Timeout"
            }
        except PermissionError as e:
            logger.error(f"Permission denied checking sing-box status: {e}")
            return {
                "running": False,
                "status": "error",
                "version": "unknown",
                "enabled": False,
                "error": "Permission denied - sudo configuration may be missing"
            }
        except Exception as e:
            logger.error(f"Failed to check sing-box status: {e}")
            return {
                "running": False,
                "status": "error",
                "version": "unknown",
                "enabled": False,
                "error": str(e)
            }
    
    def _is_singbox_enabled(self):
        """检查 sing-box 服务是否设置为开机自启"""
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "is-enabled", "sing-box"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # returncode 0 表示 enabled
            return result.returncode == 0
        except Exception:
            return False
    
    async def start_singbox(self):
        """
        启动 sing-box 服务
        
        Returns:
            dict: 操作结果
        """
        try:
            logger.info("Starting sing-box service...")
            result = subprocess.run(
                ["sudo", "systemctl", "start", "sing-box"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 等待一下让服务启动
                await asyncio.sleep(2)
                
                # 检查服务状态
                status = self._check_singbox_status()
                
                if status["running"]:
                    logger.info("sing-box service started successfully")
                    return {
                        "message": "sing-box 服务启动成功",
                        "success": True,
                        "status": status
                    }
                else:
                    logger.error("sing-box service failed to start")
                    return {
                        "message": "sing-box 服务启动失败",
                        "success": False,
                        "status": status,
                        "error": "Service did not become active"
                    }
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Failed to start sing-box: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"启动失败: {error_msg}"
                )
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout starting sing-box service")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="启动超时"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to start sing-box: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"启动失败: {str(e)}"
            )
    
    async def stop_singbox(self):
        """
        停止 sing-box 服务
        
        Returns:
            dict: 操作结果
        """
        try:
            logger.info("Stopping sing-box service...")
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "sing-box"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("sing-box service stopped successfully")
                return {
                    "message": "sing-box 服务已停止",
                    "success": True
                }
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Failed to stop sing-box: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"停止失败: {error_msg}"
                )
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout stopping sing-box service")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="停止超时"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to stop sing-box: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"停止失败: {str(e)}"
            )
    
    async def restart_singbox(self):
        """
        重启 sing-box 服务
        
        Returns:
            dict: 操作结果
        """
        try:
            logger.info("Restarting sing-box service...")
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "sing-box"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 等待一下让服务重启
                await asyncio.sleep(2)
                
                # 检查服务状态
                status = self._check_singbox_status()
                
                if status["running"]:
                    logger.info("sing-box service restarted successfully")
                    return {
                        "message": "sing-box 服务重启成功",
                        "success": True,
                        "status": status
                    }
                else:
                    logger.error("sing-box service failed to restart")
                    return {
                        "message": "sing-box 服务重启失败",
                        "success": False,
                        "status": status,
                        "error": "Service did not become active"
                    }
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Failed to restart sing-box: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"重启失败: {error_msg}"
                )
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout restarting sing-box service")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重启超时"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to restart sing-box: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"重启失败: {str(e)}"
            )
    
    # ==================== 配置管理端点 ====================
    
    async def change_password(self, password_change: PasswordChangeModel):
        """
        修改管理员密码
        
        Args:
            password_change: 密码修改请求
            
        Returns:
            dict: 操作结果
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 验证旧密码
            from .auth import verify_password, hash_password
            if not verify_password(password_change.old_password, config.system.web_auth.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="旧密码不正确"
                )
            
            # 生成新密码哈希
            new_password_hash = hash_password(password_change.new_password)
            
            # 更新配置
            config.system.web_auth.password_hash = new_password_hash
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info("管理员密码已修改")
            
            return {
                "message": "密码修改成功",
                "success": True
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to change password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"密码修改失败: {str(e)}"
            )
    
    async def get_config(self):
        """
        获取系统配置
        
        Returns:
            dict: 系统配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 转换为字典（不包含敏感信息如密码）
            config_dict = {
                "system": {
                    "web_port": config.system.web_port,
                    "log_level": config.system.log_level,
                    "log_file": config.system.log_file,
                    "database": config.system.database,
                    "web_auth": {
                        "enabled": config.system.web_auth.enabled,
                        "username": config.system.web_auth.username
                        # 不返回 password_hash
                    }
                },
                "monitoring": {
                    "check_interval": config.monitoring.check_interval,
                    "failure_threshold": config.monitoring.failure_threshold,
                    "check_timeout": config.monitoring.check_timeout,
                    "check_url": config.monitoring.check_url
                }
            }
            
            logger.info("Retrieved system configuration")
            return config_dict
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get config: {str(e)}"
            )
    
    async def update_config(self, config_update: dict):
        """
        更新系统配置
        
        Args:
            config_update: 更新的配置
            
        Returns:
            dict: 更新后的配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 更新系统配置
            if "system" in config_update:
                system_update = config_update["system"]
                if "web_port" in system_update:
                    config.system.web_port = int(system_update["web_port"])
                if "log_level" in system_update:
                    config.system.log_level = str(system_update["log_level"])
                if "log_file" in system_update:
                    config.system.log_file = str(system_update["log_file"])
                if "database" in system_update:
                    config.system.database = str(system_update["database"])
            
            # 更新监控配置
            if "monitoring" in config_update:
                monitoring_update = config_update["monitoring"]
                if "check_interval" in monitoring_update:
                    config.monitoring.check_interval = int(monitoring_update["check_interval"])
                if "failure_threshold" in monitoring_update:
                    config.monitoring.failure_threshold = int(monitoring_update["failure_threshold"])
                if "check_timeout" in monitoring_update:
                    config.monitoring.check_timeout = int(monitoring_update["check_timeout"])
                if "check_url" in monitoring_update:
                    config.monitoring.check_url = str(monitoring_update["check_url"])
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info("Updated system configuration")
            
            # 返回更新后的配置
            return {
                "message": "Configuration updated successfully",
                "system": {
                    "web_port": config.system.web_port,
                    "log_level": config.system.log_level,
                    "log_file": config.system.log_file,
                    "database": config.system.database
                },
                "monitoring": {
                    "check_interval": config.monitoring.check_interval,
                    "failure_threshold": config.monitoring.failure_threshold,
                    "check_timeout": config.monitoring.check_timeout,
                    "check_url": config.monitoring.check_url
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update config: {str(e)}"
            )
    
    # ==================== API提供商管理端点 ====================
    
    async def get_api_providers(self):
        """
        获取所有API提供商
        
        Returns:
            dict: API提供商列表
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 转换为字典列表
            providers = []
            for provider in config.api_providers:
                provider_dict = {
                    "id": provider.id,
                    "name": provider.name,
                    "enabled": provider.enabled,
                    "endpoint": provider.endpoint,
                    "method": provider.method,
                    "timeout": provider.timeout,
                    "retry_attempts": provider.retry_attempts,
                    "retry_backoff": provider.retry_backoff,
                    "response_format": {
                        "type": provider.response_format.type,
                        "success_code": provider.response_format.success_code,
                        "success_field": provider.response_format.success_field,
                        "success_value": provider.response_format.success_value,
                        "data_path": provider.response_format.data_path,
                        "ip_field": provider.response_format.ip_field,
                        "port_field": provider.response_format.port_field,
                        "username_field": provider.response_format.username_field,
                        "password_field": provider.response_format.password_field
                    }
                }
                providers.append(provider_dict)
            
            logger.info(f"Retrieved {len(providers)} API providers")
            return {"providers": providers}
            
        except Exception as e:
            logger.error(f"Failed to get API providers: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get API providers: {str(e)}"
            )
    
    async def create_api_provider(self, provider: APIProviderConfigModel):
        """
        添加API提供商
        
        Args:
            provider: API提供商配置
            
        Returns:
            dict: 创建的API提供商配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 检查ID是否已存在
            for existing_provider in config.api_providers:
                if existing_provider.id == provider.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"API provider with id '{provider.id}' already exists"
                    )
            
            # 创建新的API提供商配置
            response_format = ResponseFormat(
                type=provider.response_format.type,
                success_code=provider.response_format.success_code,
                success_field=provider.response_format.success_field,
                success_value=provider.response_format.success_value,
                data_path=provider.response_format.data_path,
                ip_field=provider.response_format.ip_field,
                port_field=provider.response_format.port_field,
                username_field=provider.response_format.username_field,
                password_field=provider.response_format.password_field
            )
            
            new_provider = APIProviderConfig(
                id=provider.id,
                name=provider.name,
                enabled=provider.enabled,
                endpoint=provider.endpoint,
                method=provider.method,
                params=provider.params,
                headers=provider.headers,
                body=provider.body,
                timeout=provider.timeout,
                retry_attempts=provider.retry_attempts,
                retry_backoff=provider.retry_backoff,
                response_format=response_format
            )
            
            # 添加到配置
            config.api_providers.append(new_provider)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info(f"Created API provider: {provider.name} (id: {provider.id})")
            
            return {
                "id": new_provider.id,
                "name": new_provider.name,
                "enabled": new_provider.enabled,
                "endpoint": new_provider.endpoint,
                "method": new_provider.method,
                "timeout": new_provider.timeout,
                "retry_attempts": new_provider.retry_attempts,
                "retry_backoff": new_provider.retry_backoff
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create API provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create API provider: {str(e)}"
            )
    
    async def get_api_provider(self, provider_id: str):
        """
        获取指定API提供商
        
        Args:
            provider_id: API提供商ID
            
        Returns:
            dict: API提供商配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找API提供商
            provider_config = None
            for provider in config.api_providers:
                if provider.id == provider_id:
                    provider_config = provider
                    break
            
            if not provider_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API provider with id '{provider_id}' not found"
                )
            
            return {
                "id": provider_config.id,
                "name": provider_config.name,
                "enabled": provider_config.enabled,
                "endpoint": provider_config.endpoint,
                "method": provider_config.method,
                "params": provider_config.params,
                "headers": provider_config.headers,
                "body": provider_config.body,
                "timeout": provider_config.timeout,
                "retry_attempts": provider_config.retry_attempts,
                "retry_backoff": provider_config.retry_backoff,
                "response_format": {
                    "type": provider_config.response_format.type,
                    "success_code": provider_config.response_format.success_code,
                    "success_field": provider_config.response_format.success_field,
                    "success_value": provider_config.response_format.success_value,
                    "data_path": provider_config.response_format.data_path,
                    "ip_field": provider_config.response_format.ip_field,
                    "port_field": provider_config.response_format.port_field,
                    "username_field": provider_config.response_format.username_field,
                    "password_field": provider_config.response_format.password_field
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get API provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get API provider: {str(e)}"
            )
    
    async def update_api_provider(self, provider_id: str, provider_update: APIProviderUpdateModel):
        """
        更新API提供商
        
        Args:
            provider_id: API提供商ID
            provider_update: 更新的配置
            
        Returns:
            dict: 更新后的API提供商配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找API提供商
            provider_config = None
            for provider in config.api_providers:
                if provider.id == provider_id:
                    provider_config = provider
                    break
            
            if not provider_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API provider with id '{provider_id}' not found"
                )
            
            # 更新字段
            if provider_update.name is not None:
                provider_config.name = provider_update.name
            if provider_update.enabled is not None:
                provider_config.enabled = provider_update.enabled
            if provider_update.endpoint is not None:
                provider_config.endpoint = provider_update.endpoint
            if provider_update.method is not None:
                provider_config.method = provider_update.method
            if provider_update.params is not None:
                provider_config.params = provider_update.params
            if provider_update.headers is not None:
                provider_config.headers = provider_update.headers
            if provider_update.body is not None:
                provider_config.body = provider_update.body
            if provider_update.timeout is not None:
                provider_config.timeout = provider_update.timeout
            if provider_update.retry_attempts is not None:
                provider_config.retry_attempts = provider_update.retry_attempts
            if provider_update.retry_backoff is not None:
                provider_config.retry_backoff = provider_update.retry_backoff
            if provider_update.response_format is not None:
                provider_config.response_format = ResponseFormat(
                    type=provider_update.response_format.type,
                    success_code=provider_update.response_format.success_code,
                    success_field=provider_update.response_format.success_field,
                    success_value=provider_update.response_format.success_value,
                    data_path=provider_update.response_format.data_path,
                    ip_field=provider_update.response_format.ip_field,
                    port_field=provider_update.response_format.port_field,
                    username_field=provider_update.response_format.username_field,
                    password_field=provider_update.response_format.password_field
                )
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info(f"Updated API provider: {provider_id}")
            
            return {
                "id": provider_config.id,
                "name": provider_config.name,
                "enabled": provider_config.enabled,
                "endpoint": provider_config.endpoint,
                "method": provider_config.method,
                "timeout": provider_config.timeout,
                "retry_attempts": provider_config.retry_attempts,
                "retry_backoff": provider_config.retry_backoff
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update API provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update API provider: {str(e)}"
            )
    
    async def delete_api_provider(self, provider_id: str):
        """
        删除API提供商
        
        Args:
            provider_id: API提供商ID
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 检查是否有代理正在使用此API提供商
            for proxy in config.proxies:
                if proxy.api_provider_id == provider_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot delete API provider '{provider_id}': it is being used by proxy on port {proxy.local_port}"
                    )
            
            # 查找并删除API提供商
            provider_index = None
            for i, provider in enumerate(config.api_providers):
                if provider.id == provider_id:
                    provider_index = i
                    break
            
            if provider_index is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API provider with id '{provider_id}' not found"
                )
            
            # 删除API提供商
            deleted_provider = config.api_providers.pop(provider_index)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info(f"Deleted API provider: {deleted_provider.name} (id: {provider_id})")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete API provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete API provider: {str(e)}"
            )
    
    async def test_api_provider(self, provider_id: str):
        """
        测试API提供商连接
        
        Args:
            provider_id: API提供商ID
            
        Returns:
            dict: 测试结果
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找API提供商
            provider_config = None
            for provider in config.api_providers:
                if provider.id == provider_id:
                    provider_config = provider
                    break
            
            if not provider_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API provider with id '{provider_id}' not found"
                )
            
            # 创建API客户端并测试连接
            from .api_client import APIClient
            api_client = APIClient(provider_config)
            
            try:
                # 尝试获取新代理来测试连接
                new_proxy = api_client.get_new_proxy()
                
                logger.info(f"API provider test successful: {provider_id}")
                
                return {
                    "provider_id": provider_id,
                    "success": True,
                    "message": "API provider connection successful",
                    "test_proxy": {
                        "server": new_proxy.server,
                        "port": new_proxy.port,
                        "protocol": new_proxy.protocol
                    }
                }
                
            except Exception as api_error:
                logger.warning(f"API provider test failed: {provider_id}, error: {api_error}")
                
                return {
                    "provider_id": provider_id,
                    "success": False,
                    "message": f"API provider connection failed: {str(api_error)}"
                }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to test API provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to test API provider: {str(e)}"
            )
    
    # ==================== 实时状态更新端点 (SSE) ====================
    
    async def stream_status_updates(self, request: Request):
        """
        实时状态更新流 (Server-Sent Events)
        
        推送代理状态变化和监控状态更新
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            StreamingResponse: SSE流响应
        """
        async def event_generator():
            """生成SSE事件"""
            # 创建客户端队列
            client_queue = asyncio.Queue()
            
            async with self._sse_lock:
                self._sse_clients.append(client_queue)
            
            try:
                # 发送初始连接消息
                yield self._format_sse_message({
                    "type": "connected",
                    "message": "Connected to status updates stream",
                    "timestamp": self._get_timestamp()
                })
                
                # 发送初始状态
                initial_status = await self._get_current_status()
                yield self._format_sse_message({
                    "type": "initial_status",
                    "data": initial_status,
                    "timestamp": self._get_timestamp()
                })
                
                # 持续监听状态变化
                while True:
                    # 检查客户端是否断开连接
                    if await request.is_disconnected():
                        logger.info("SSE client disconnected")
                        break
                    
                    try:
                        # 等待状态更新（带超时）
                        update = await asyncio.wait_for(
                            client_queue.get(),
                            timeout=30.0  # 30秒心跳
                        )
                        yield self._format_sse_message(update)
                        
                    except asyncio.TimeoutError:
                        # 发送心跳保持连接
                        yield self._format_sse_message({
                            "type": "heartbeat",
                            "timestamp": self._get_timestamp()
                        })
                        
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}", exc_info=True)
                yield self._format_sse_message({
                    "type": "error",
                    "message": str(e),
                    "timestamp": self._get_timestamp()
                })
                
            finally:
                # 移除客户端队列
                async with self._sse_lock:
                    if client_queue in self._sse_clients:
                        self._sse_clients.remove(client_queue)
                logger.info("SSE client removed from list")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用nginx缓冲
            }
        )
    
    async def _get_current_status(self) -> dict:
        """
        获取当前完整状态
        
        Returns:
            dict: 当前状态数据
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 获取监控状态
            monitoring_statuses = self.health_monitor.get_monitoring_status()
            
            # 构建代理状态列表
            proxies = []
            for proxy in config.proxies:
                monitoring_status = monitoring_statuses.get(proxy.local_port)
                
                proxy_dict = {
                    "local_port": proxy.local_port,
                    "name": proxy.name,
                    "monitoring_enabled": proxy.monitoring_enabled,
                    "upstream": {
                        "server": proxy.upstream.server,
                        "port": proxy.upstream.port,
                        "protocol": proxy.upstream.protocol
                    }
                }
                
                if monitoring_status:
                    proxy_dict["monitoring_status"] = {
                        "enabled": monitoring_status.enabled,
                        "failure_count": monitoring_status.failure_count,
                        "last_check_time": monitoring_status.last_check_time.isoformat() if monitoring_status.last_check_time else None,
                        "last_success_time": monitoring_status.last_success_time.isoformat() if monitoring_status.last_success_time else None,
                        "is_healthy": monitoring_status.failure_count == 0
                    }
                
                proxies.append(proxy_dict)
            
            return {
                "proxies": proxies,
                "total_proxies": len(proxies),
                "active_monitoring": sum(1 for p in proxies if p.get("monitoring_status", {}).get("enabled", False))
            }
            
        except Exception as e:
            logger.error(f"Failed to get current status: {e}")
            return {"error": str(e)}
    
    def _format_sse_message(self, data: dict) -> str:
        """
        格式化SSE消息
        
        Args:
            data: 消息数据
            
        Returns:
            str: 格式化的SSE消息
        """
        return f"data: {json.dumps(data)}\n\n"
    
    def _get_timestamp(self) -> str:
        """
        获取当前时间戳
        
        Returns:
            str: ISO格式时间戳
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def broadcast_status_update(self, update: dict):
        """
        广播状态更新到所有SSE客户端
        
        Args:
            update: 状态更新数据
        """
        async with self._sse_lock:
            for client_queue in self._sse_clients:
                try:
                    await client_queue.put(update)
                except Exception as e:
                    logger.error(f"Failed to send update to SSE client: {e}")
    
    def start_status_monitoring(self):
        """启动后台状态监控任务"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_status_changes())
            logger.info("Started background status monitoring task")
    
    async def _monitor_status_changes(self):
        """
        后台任务：监控状态变化并广播更新
        """
        logger.info("Status monitoring task started")
        previous_status = {}
        
        try:
            while True:
                await asyncio.sleep(5)  # 每5秒检查一次状态变化
                
                # 获取当前状态
                current_status = await self._get_current_status()
                
                # 检测变化
                changes = self._detect_status_changes(previous_status, current_status)
                
                if changes:
                    # 广播变化
                    await self.broadcast_status_update({
                        "type": "status_update",
                        "changes": changes,
                        "timestamp": self._get_timestamp()
                    })
                    logger.debug(f"Broadcasted status changes: {len(changes)} changes")
                
                # 更新上一次状态
                previous_status = current_status
                
        except asyncio.CancelledError:
            logger.info("Status monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in status monitoring task: {e}", exc_info=True)
    
    def _detect_status_changes(self, previous: dict, current: dict) -> List[dict]:
        """
        检测状态变化
        
        Args:
            previous: 上一次状态
            current: 当前状态
            
        Returns:
            List[dict]: 变化列表
        """
        changes = []
        
        # 如果没有上一次状态，不报告变化
        if not previous or "proxies" not in previous:
            return changes
        
        # 创建端口到代理的映射
        prev_proxies = {p["local_port"]: p for p in previous.get("proxies", [])}
        curr_proxies = {p["local_port"]: p for p in current.get("proxies", [])}
        
        # 检查每个代理的变化
        for port, curr_proxy in curr_proxies.items():
            prev_proxy = prev_proxies.get(port)
            
            if not prev_proxy:
                # 新增代理
                changes.append({
                    "type": "proxy_added",
                    "port": port,
                    "proxy": curr_proxy
                })
                continue
            
            # 检查上游代理变化
            if prev_proxy.get("upstream") != curr_proxy.get("upstream"):
                changes.append({
                    "type": "upstream_changed",
                    "port": port,
                    "old_upstream": prev_proxy.get("upstream"),
                    "new_upstream": curr_proxy.get("upstream")
                })
            
            # 检查监控状态变化
            prev_mon = prev_proxy.get("monitoring_status", {})
            curr_mon = curr_proxy.get("monitoring_status", {})
            
            if prev_mon.get("enabled") != curr_mon.get("enabled"):
                changes.append({
                    "type": "monitoring_toggled",
                    "port": port,
                    "enabled": curr_mon.get("enabled", False)
                })
            
            # 检查健康状态变化
            prev_healthy = prev_mon.get("is_healthy", True)
            curr_healthy = curr_mon.get("is_healthy", True)
            
            if prev_healthy != curr_healthy:
                changes.append({
                    "type": "health_status_changed",
                    "port": port,
                    "healthy": curr_healthy,
                    "failure_count": curr_mon.get("failure_count", 0)
                })
        
        # 检查删除的代理
        for port in prev_proxies:
            if port not in curr_proxies:
                changes.append({
                    "type": "proxy_removed",
                    "port": port
                })
        
        return changes

    async def page_upstream_proxies(self, request: Request):
        """出口代理池管理页面"""
        return self.templates.TemplateResponse("upstream_proxies.html", {"request": request})
    
    async def get_upstream_proxies(self):
        """
        获取所有出口代理池配置
        
        Returns:
            dict: 出口代理池列表
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 构建响应
            upstream_proxies = []
            for upstream in config.upstream_proxies:
                # 统计使用此出口代理的本地代理数量
                usage_count = sum(1 for p in config.proxies if p.upstream_id == upstream.id)
                
                upstream_dict = {
                    "id": upstream.id,
                    "name": upstream.name,
                    "enabled": upstream.enabled,
                    "description": upstream.description,
                    "tags": upstream.tags,
                    "proxy": {
                        "server": upstream.proxy.server,
                        "port": upstream.proxy.port,
                        "protocol": upstream.proxy.protocol,
                        "username": upstream.proxy.username,
                        "password": "***" if upstream.proxy.password else None
                    },
                    "usage_count": usage_count
                }
                
                # 添加 VLESS 特定字段
                if upstream.proxy.protocol == "vless":
                    upstream_dict["proxy"].update({
                        "uuid": upstream.proxy.uuid,
                        "flow": upstream.proxy.flow,
                        "encryption": upstream.proxy.encryption,
                        "network": upstream.proxy.network,
                        "tls": upstream.proxy.tls,
                        "sni": upstream.proxy.sni,
                        "alpn": upstream.proxy.alpn,
                        "reality": upstream.proxy.reality,
                        "reality_public_key": upstream.proxy.reality_public_key,
                        "reality_short_id": upstream.proxy.reality_short_id,
                        "reality_server_name": upstream.proxy.reality_server_name,
                        "reality_fingerprint": upstream.proxy.reality_fingerprint,
                        "ws_path": upstream.proxy.ws_path,
                        "ws_host": upstream.proxy.ws_host,
                        "grpc_service_name": upstream.proxy.grpc_service_name
                    })
                
                upstream_proxies.append(upstream_dict)
            
            logger.info(f"Retrieved {len(upstream_proxies)} upstream proxy configurations")
            return {"upstream_proxies": upstream_proxies}
            
        except Exception as e:
            logger.error(f"Failed to get upstream proxies: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get upstream proxies: {str(e)}"
            )
    
    async def create_upstream_proxy(self, upstream: UpstreamProxyPoolCreateModel):
        """
        添加新的出口代理
        
        Args:
            upstream: 出口代理配置
            
        Returns:
            dict: 创建的出口代理配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 检查 ID 是否已存在
            for existing in config.upstream_proxies:
                if existing.id == upstream.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Upstream proxy with id '{upstream.id}' already exists"
                    )
            
            # 创建上游代理配置
            from .models import UpstreamProxyPool
            proxy = UpstreamProxy(
                server=upstream.proxy.server,
                port=upstream.proxy.port,
                username=upstream.proxy.username,
                password=upstream.proxy.password,
                protocol=upstream.proxy.protocol,
                # VLESS 特定字段
                uuid=upstream.proxy.uuid,
                flow=upstream.proxy.flow,
                encryption=upstream.proxy.encryption or "none",
                network=upstream.proxy.network or "tcp",
                tls=upstream.proxy.tls or False,
                sni=upstream.proxy.sni,
                alpn=upstream.proxy.alpn,
                # Reality 配置
                reality=upstream.proxy.reality or False,
                reality_public_key=upstream.proxy.reality_public_key,
                reality_short_id=upstream.proxy.reality_short_id,
                reality_server_name=upstream.proxy.reality_server_name,
                reality_fingerprint=upstream.proxy.reality_fingerprint,
                # WebSocket/gRPC 配置
                ws_path=upstream.proxy.ws_path,
                ws_host=upstream.proxy.ws_host,
                grpc_service_name=upstream.proxy.grpc_service_name
            )
            
            new_upstream = UpstreamProxyPool(
                id=upstream.id,
                name=upstream.name,
                proxy=proxy,
                enabled=upstream.enabled,
                description=upstream.description,
                tags=upstream.tags
            )
            
            # 添加到配置
            config.upstream_proxies.append(new_upstream)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info(f"Created upstream proxy: {upstream.name} (id: {upstream.id})")
            
            return {
                "id": new_upstream.id,
                "name": new_upstream.name,
                "enabled": new_upstream.enabled,
                "description": new_upstream.description,
                "tags": new_upstream.tags,
                "proxy": {
                    "server": new_upstream.proxy.server,
                    "port": new_upstream.proxy.port,
                    "protocol": new_upstream.proxy.protocol
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create upstream proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create upstream proxy: {str(e)}"
            )
    
    async def get_upstream_proxy(self, upstream_id: str):
        """
        获取指定出口代理
        
        Args:
            upstream_id: 出口代理 ID
            
        Returns:
            dict: 出口代理配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找出口代理
            upstream = None
            for u in config.upstream_proxies:
                if u.id == upstream_id:
                    upstream = u
                    break
            
            if not upstream:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upstream proxy with id '{upstream_id}' not found"
                )
            
            # 统计使用此出口代理的本地代理
            usage_count = sum(1 for p in config.proxies if p.upstream_id == upstream_id)
            used_by_ports = [p.local_port for p in config.proxies if p.upstream_id == upstream_id]
            
            result = {
                "id": upstream.id,
                "name": upstream.name,
                "enabled": upstream.enabled,
                "description": upstream.description,
                "tags": upstream.tags,
                "proxy": {
                    "server": upstream.proxy.server,
                    "port": upstream.proxy.port,
                    "protocol": upstream.proxy.protocol,
                    "username": upstream.proxy.username,
                    "password": upstream.proxy.password
                },
                "usage_count": usage_count,
                "used_by_ports": used_by_ports
            }
            
            # 添加 VLESS 特定字段
            if upstream.proxy.protocol == "vless":
                result["proxy"].update({
                    "uuid": upstream.proxy.uuid,
                    "flow": upstream.proxy.flow,
                    "encryption": upstream.proxy.encryption,
                    "network": upstream.proxy.network,
                    "tls": upstream.proxy.tls,
                    "sni": upstream.proxy.sni,
                    "alpn": upstream.proxy.alpn,
                    "reality": upstream.proxy.reality,
                    "reality_public_key": upstream.proxy.reality_public_key,
                    "reality_short_id": upstream.proxy.reality_short_id,
                    "reality_server_name": upstream.proxy.reality_server_name,
                    "reality_fingerprint": upstream.proxy.reality_fingerprint,
                    "ws_path": upstream.proxy.ws_path,
                    "ws_host": upstream.proxy.ws_host,
                    "grpc_service_name": upstream.proxy.grpc_service_name
                })
            
            logger.info(f"Retrieved upstream proxy: {upstream_id}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get upstream proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get upstream proxy: {str(e)}"
            )
    
    async def update_upstream_proxy(self, upstream_id: str, upstream_update: UpstreamProxyPoolUpdateModel):
        """
        更新出口代理配置
        
        Args:
            upstream_id: 出口代理 ID
            upstream_update: 更新的配置
            
        Returns:
            dict: 更新后的出口代理配置
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找出口代理
            upstream = None
            for u in config.upstream_proxies:
                if u.id == upstream_id:
                    upstream = u
                    break
            
            if not upstream:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upstream proxy with id '{upstream_id}' not found"
                )
            
            # 更新字段
            if upstream_update.name is not None:
                upstream.name = upstream_update.name
            
            if upstream_update.enabled is not None:
                upstream.enabled = upstream_update.enabled
            
            if upstream_update.description is not None:
                upstream.description = upstream_update.description
            
            if upstream_update.tags is not None:
                upstream.tags = upstream_update.tags
            
            if upstream_update.proxy is not None:
                # 更新代理配置
                upstream.proxy = UpstreamProxy(
                    server=upstream_update.proxy.server,
                    port=upstream_update.proxy.port,
                    username=upstream_update.proxy.username,
                    password=upstream_update.proxy.password,
                    protocol=upstream_update.proxy.protocol,
                    # VLESS 特定字段
                    uuid=upstream_update.proxy.uuid,
                    flow=upstream_update.proxy.flow,
                    encryption=upstream_update.proxy.encryption or "none",
                    network=upstream_update.proxy.network or "tcp",
                    tls=upstream_update.proxy.tls or False,
                    sni=upstream_update.proxy.sni,
                    alpn=upstream_update.proxy.alpn,
                    # Reality 配置
                    reality=upstream_update.proxy.reality or False,
                    reality_public_key=upstream_update.proxy.reality_public_key,
                    reality_short_id=upstream_update.proxy.reality_short_id,
                    reality_server_name=upstream_update.proxy.reality_server_name,
                    reality_fingerprint=upstream_update.proxy.reality_fingerprint,
                    # WebSocket/gRPC 配置
                    ws_path=upstream_update.proxy.ws_path,
                    ws_host=upstream_update.proxy.ws_host,
                    grpc_service_name=upstream_update.proxy.grpc_service_name
                )
            
            # 保存配置
            self.config_manager.save_config(config)
            
            # 如果有本地代理使用此出口代理，需要重新生成 sing-box 配置
            usage_count = sum(1 for p in config.proxies if p.upstream_id == upstream_id)
            if usage_count > 0:
                try:
                    self.proxy_manager.apply_singbox_config()
                    logger.info(f"Applied sing-box configuration after updating upstream proxy {upstream_id}")
                except Exception as apply_error:
                    logger.error(f"Failed to apply sing-box config: {apply_error}")
                    # 不抛出异常，因为配置已经保存
            
            logger.info(f"Updated upstream proxy: {upstream_id}")
            
            return {
                "id": upstream.id,
                "name": upstream.name,
                "enabled": upstream.enabled,
                "description": upstream.description,
                "tags": upstream.tags,
                "proxy": {
                    "server": upstream.proxy.server,
                    "port": upstream.proxy.port,
                    "protocol": upstream.proxy.protocol
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update upstream proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update upstream proxy: {str(e)}"
            )
    
    async def delete_upstream_proxy(self, upstream_id: str):
        """
        删除出口代理
        
        Args:
            upstream_id: 出口代理 ID
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 检查是否有本地代理正在使用此出口代理
            usage_count = sum(1 for p in config.proxies if p.upstream_id == upstream_id)
            if usage_count > 0:
                used_by = [f"{p.name} (port {p.local_port})" for p in config.proxies if p.upstream_id == upstream_id]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot delete upstream proxy '{upstream_id}' because it is being used by {usage_count} local proxy(ies): {', '.join(used_by)}"
                )
            
            # 查找并删除出口代理
            upstream_index = None
            for i, u in enumerate(config.upstream_proxies):
                if u.id == upstream_id:
                    upstream_index = i
                    break
            
            if upstream_index is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upstream proxy with id '{upstream_id}' not found"
                )
            
            # 删除出口代理
            deleted_upstream = config.upstream_proxies.pop(upstream_index)
            
            # 保存配置
            self.config_manager.save_config(config)
            
            logger.info(f"Deleted upstream proxy: {deleted_upstream.name} (id: {upstream_id})")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete upstream proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete upstream proxy: {str(e)}"
            )
    
    async def test_upstream_proxy(self, upstream_id: str):
        """
        测试出口代理连接
        
        Args:
            upstream_id: 出口代理 ID
            
        Returns:
            dict: 测试结果
        """
        try:
            config = self.config_manager._current_config
            if not config:
                config = self.config_manager.load_config()
            
            # 查找出口代理
            upstream = None
            for u in config.upstream_proxies:
                if u.id == upstream_id:
                    upstream = u
                    break
            
            if not upstream:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Upstream proxy with id '{upstream_id}' not found"
                )
            
            # 测试代理健康状态
            is_healthy, response_time_ms, error_message = self.health_monitor.check_proxy_health(
                upstream.proxy
            )
            
            logger.info(f"Tested upstream proxy {upstream_id}: healthy={is_healthy}")
            
            return {
                "id": upstream_id,
                "name": upstream.name,
                "healthy": is_healthy,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "proxy": {
                    "server": upstream.proxy.server,
                    "port": upstream.proxy.port,
                    "protocol": upstream.proxy.protocol
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to test upstream proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to test upstream proxy: {str(e)}"
            )



def create_app(
    config_manager: ConfigManager,
    proxy_manager: ProxyManager,
    health_monitor: HealthMonitor,
    database: Database
) -> FastAPI:
    """
    创建FastAPI应用实例
    
    Args:
        config_manager: 配置管理器实例
        proxy_manager: 代理管理器实例
        health_monitor: 健康监控器实例
        database: 数据库实例
        
    Returns:
        FastAPI: FastAPI应用实例
    """
    web_api = WebAPI(config_manager, proxy_manager, health_monitor, database)
    return web_api.app


# ==================== 默认应用实例 ====================
# 用于 uvicorn 直接启动

# 创建默认实例（用于开发和简单部署）
try:
    from pathlib import Path
    import os
    
    # 默认配置文件路径
    config_path = os.environ.get(
        "PROXY_RELAY_CONFIG",
        "/etc/proxy-relay/config.yaml"
    )
    
    # 如果配置文件不存在，尝试其他位置
    if not Path(config_path).exists():
        # 尝试开发环境路径
        dev_config = Path(__file__).parent.parent.parent / "config.yaml.example"
        if dev_config.exists():
            config_path = str(dev_config)
    
    # 创建组件实例
    _config_manager = ConfigManager(config_path)
    _database = Database(_config_manager._current_config.system.database if _config_manager._current_config else "/var/lib/proxy-relay/data.db")
    _proxy_manager = ProxyManager(_config_manager, _database)
    _health_monitor = HealthMonitor(_config_manager, _proxy_manager, _database)
    
    # 创建应用实例
    app = create_app(_config_manager, _proxy_manager, _health_monitor, _database)
    
    logger.info(f"默认应用实例已创建，配置文件: {config_path}")
    
except Exception as e:
    error_message = str(e)
    logger.error(f"创建默认应用实例失败: {error_message}")
    # 创建一个最小的应用实例，避免导入错误
    app = FastAPI(title="Proxy Relay System (Error)", description="应用初始化失败")
    
    @app.get("/")
    async def root():
        return {
            "error": "应用初始化失败",
            "message": error_message,
            "hint": "请检查配置文件是否存在: /etc/proxy-relay/config.yaml"
        }