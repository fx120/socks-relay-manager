"""
代理管理器

负责管理sing-box配置，处理代理切换逻辑。
"""

import os
import json
import signal
import subprocess
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from .config_manager import ConfigManager
from .models import Config, ProxyConfig, UpstreamProxy, ProxyPortInfo

logger = logging.getLogger(__name__)


class ProxyManager:
    """代理管理器类"""
    
    DEFAULT_SINGBOX_CONFIG_PATH = "/etc/sing-box/config.json"
    DEFAULT_SINGBOX_PID_FILE = "/var/run/sing-box.pid"
    
    def __init__(self, config_manager: ConfigManager, api_client=None, database=None):
        """
        初始化代理管理器
        
        Args:
            config_manager: 配置管理器实例
            api_client: API客户端实例（可选，用于获取新代理）
            database: 数据库实例（可选，用于记录切换历史）
        """
        self.config_manager = config_manager
        self.api_client = api_client
        self.database = database
        self.singbox_config_path = self.DEFAULT_SINGBOX_CONFIG_PATH
        self.singbox_pid_file = self.DEFAULT_SINGBOX_PID_FILE
        
        # 加载当前配置
        try:
            self.config = self.config_manager.load_config()
        except FileNotFoundError:
            # 如果配置文件不存在，使用空配置
            self.config = None
    
    def generate_singbox_config(self) -> Dict[str, Any]:
        """
        根据当前配置生成sing-box配置
        
        Returns:
            Dict[str, Any]: sing-box配置字典
            
        Raises:
            RuntimeError: 如果没有加载配置
        """
        if not self.config:
            logger.error("No configuration loaded")
            raise RuntimeError("No configuration loaded. Call config_manager.load_config() first.")
        
        logger.info(f"Generating sing-box configuration for {len(self.config.proxies)} proxies")
        
        inbounds = []
        outbounds = []
        rules = []
        
        # 为每个代理端口生成配置
        for proxy in self.config.proxies:
            logger.debug(f"Generating configuration for proxy: {proxy.name} (port {proxy.local_port})")
            
            # 生成inbound配置（本地SOCKS5代理）
            inbound_tag = f"socks-{proxy.local_port}"
            inbound = {
                "type": "socks",
                "tag": inbound_tag,
                "listen": "0.0.0.0",
                "listen_port": proxy.local_port
            }
            
            # 如果配置了本地认证，添加认证信息
            if proxy.local_username and proxy.local_password:
                inbound["users"] = [{
                    "username": proxy.local_username,
                    "password": proxy.local_password
                }]
                logger.debug(f"Added local authentication for proxy {proxy.name}")
            
            inbounds.append(inbound)
            
            # 生成outbound配置
            outbound_tag = f"upstream-{proxy.local_port}"
            
            if proxy.upstream is None:
                # Direct 模式：直接连接，不使用上游代理
                outbound = {
                    "type": "direct",
                    "tag": outbound_tag
                }
                logger.debug(f"Using direct mode for proxy {proxy.name}")
            else:
                # 上游代理模式
                # sing-box 使用 "socks" 而不是 "socks5"
                outbound_type = "socks" if proxy.upstream.protocol == "socks5" else proxy.upstream.protocol
                outbound = {
                    "type": outbound_type,
                    "tag": outbound_tag,
                    "server": proxy.upstream.server,
                    "server_port": proxy.upstream.port
                }
                
                # 如果需要认证，添加认证信息
                if proxy.upstream.username and proxy.upstream.password:
                    outbound["username"] = proxy.upstream.username
                    outbound["password"] = proxy.upstream.password
                    logger.debug(f"Added upstream authentication for proxy {proxy.name}")
            
            outbounds.append(outbound)
            
            # 生成路由规则（将inbound流量路由到对应的outbound）
            rule = {
                "inbound": [inbound_tag],
                "outbound": outbound_tag
            }
            rules.append(rule)
        
        logger.info(f"Generated sing-box configuration: {len(inbounds)} inbounds, {len(outbounds)} outbounds, {len(rules)} rules")
        
        # 构建完整的sing-box配置
        singbox_config = {
            "log": {
                "level": "info",
                "timestamp": True
            },
            "inbounds": inbounds,
            "outbounds": outbounds,
            "route": {
                "rules": rules
            }
        }
        
        return singbox_config
    
    def apply_singbox_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        应用sing-box配置并重载
        
        Args:
            config: sing-box配置字典，如果为None则生成新配置
            
        Returns:
            bool: 成功返回True，失败返回False
            
        Raises:
            RuntimeError: 如果配置应用失败
        """
        logger.info("Applying sing-box configuration")
        
        # 如果没有提供配置，生成新配置
        if config is None:
            config = self.generate_singbox_config()
        
        # 备份当前配置（用于回滚）
        backup_path = None
        if os.path.exists(self.singbox_config_path):
            backup_path = f"{self.singbox_config_path}.backup"
            try:
                with open(self.singbox_config_path, 'r') as f:
                    backup_content = f.read()
                with open(backup_path, 'w') as f:
                    f.write(backup_content)
                logger.debug(f"Created configuration backup at: {backup_path}")
            except Exception as e:
                # 备份失败不应该阻止配置更新
                logger.warning(f"Failed to create configuration backup: {e}")
                backup_path = None
        
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self.singbox_config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            # 写入新配置
            with open(self.singbox_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration written to: {self.singbox_config_path}")
            
            # 重载sing-box
            success = self._reload_singbox()
            
            if not success:
                # 重载失败，尝试回滚
                logger.error("Failed to reload sing-box")
                if backup_path and os.path.exists(backup_path):
                    self._rollback_config(backup_path)
                raise RuntimeError("Failed to reload sing-box, configuration rolled back")
            
            logger.info("sing-box configuration applied and reloaded successfully")
            
            # 清理备份文件
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                logger.debug("Removed configuration backup")
            
            return True
            
        except Exception as e:
            # 发生错误，尝试回滚
            logger.error(f"Error applying configuration: {e}")
            if backup_path and os.path.exists(backup_path):
                self._rollback_config(backup_path)
            raise RuntimeError(f"Failed to apply sing-box configuration: {e}")
    
    def _reload_singbox(self) -> bool:
        """
        重载sing-box进程
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 检查 sing-box 服务是否运行
            result = subprocess.run(
                ["sudo", "systemctl", "is-active", "sing-box"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # 服务正在运行，重启以应用新配置
                logger.info("Restarting sing-box service to apply new configuration")
                result = subprocess.run(
                    ["sudo", "systemctl", "restart", "sing-box"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info("sing-box service restarted successfully")
                    # 等待服务启动
                    import time
                    time.sleep(1)
                    return True
                else:
                    logger.error(f"Failed to restart sing-box: stderr={result.stderr}, stdout={result.stdout}")
                    return False
            else:
                # 服务未运行，尝试启动
                logger.info("sing-box service not running, attempting to start")
                result = subprocess.run(
                    ["sudo", "systemctl", "start", "sing-box"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info("sing-box service started successfully")
                    # 等待服务启动
                    import time
                    time.sleep(1)
                    return True
                else:
                    logger.error(f"Failed to start sing-box: stderr={result.stderr}, stdout={result.stdout}")
                    # 检查是否是配置文件问题
                    if not os.path.exists(self.singbox_config_path):
                        logger.error(f"sing-box config file not found: {self.singbox_config_path}")
                    return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout while reloading sing-box")
            return False
        except Exception as e:
            logger.error(f"Unexpected error reloading sing-box: {e}")
            return False
    
    def _rollback_config(self, backup_path: str) -> None:
        """
        回滚配置到备份
        
        Args:
            backup_path: 备份文件路径
        """
        try:
            with open(backup_path, 'r') as f:
                backup_content = f.read()
            with open(self.singbox_config_path, 'w') as f:
                f.write(backup_content)
            
            # 尝试重载回滚后的配置
            self._reload_singbox()
            
        except Exception:
            # 回滚失败，但不抛出异常，因为已经在错误处理流程中
            pass
    
    def switch_upstream_proxy(self, local_port: int, new_upstream: UpstreamProxy, reason: str = "manual") -> bool:
        """
        切换指定端口的上游代理
        
        Args:
            local_port: 本地端口
            new_upstream: 新的上游代理配置
            reason: 切换原因 ('health_check_failed', 'manual', 'api_error')
            
        Returns:
            bool: 成功返回True，失败返回False
            
        Raises:
            ValueError: 如果端口不存在或原因无效
            RuntimeError: 如果切换失败
        """
        if reason not in ['health_check_failed', 'manual', 'api_error']:
            raise ValueError(f"Invalid reason: {reason}. Must be 'health_check_failed', 'manual', or 'api_error'")
        
        logger.info(f"Switching upstream proxy for port {local_port}, reason: {reason}")
        
        if not self.config:
            raise RuntimeError("No configuration loaded")
        
        # 查找指定端口的代理配置
        proxy_config = None
        for proxy in self.config.proxies:
            if proxy.local_port == local_port:
                proxy_config = proxy
                break
        
        if not proxy_config:
            raise ValueError(f"No proxy configuration found for port {local_port}")
        
        # 保存旧的上游代理（用于日志记录）
        old_upstream = proxy_config.upstream
        logger.info(f"Old upstream: {old_upstream.server}:{old_upstream.port}")
        logger.info(f"New upstream: {new_upstream.server}:{new_upstream.port}")
        
        # 更新配置中的上游代理
        proxy_config.upstream = new_upstream
        
        success = False
        try:
            # 保存更新后的配置到文件
            self.config_manager.save_config(self.config)
            logger.debug("Configuration saved to file")
            
            # 生成并应用新的sing-box配置
            self.apply_singbox_config()
            
            success = True
            logger.info(f"Successfully switched upstream proxy for port {local_port}")
            
        except Exception as e:
            # 切换失败，回滚配置
            logger.error(f"Failed to switch upstream proxy: {e}")
            proxy_config.upstream = old_upstream
            try:
                self.config_manager.save_config(self.config)
                self.apply_singbox_config()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback configuration: {rollback_error}")
            
            # 记录失败的切换事件到数据库
            if self.database:
                try:
                    self.database.insert_switch_history(
                        local_port=local_port,
                        old_upstream=old_upstream,
                        new_upstream=new_upstream,
                        reason=reason,
                        success=False
                    )
                    logger.debug("Failed switch event recorded to database")
                except Exception as db_error:
                    logger.error(f"Failed to record switch event to database: {db_error}")
            
            raise RuntimeError(f"Failed to switch upstream proxy: {e}")
        
        # 记录成功的切换事件到数据库
        if self.database:
            try:
                self.database.insert_switch_history(
                    local_port=local_port,
                    old_upstream=old_upstream,
                    new_upstream=new_upstream,
                    reason=reason,
                    success=True
                )
                logger.debug("Switch event recorded to database")
            except Exception as db_error:
                logger.error(f"Failed to record switch event to database: {db_error}")
                # 数据库记录失败不应该影响切换操作
        
        return success
    
    def get_new_proxy_from_api(self, api_provider_id: str) -> UpstreamProxy:
        """
        从API获取新的代理
        
        Args:
            api_provider_id: API提供商ID
            
        Returns:
            UpstreamProxy: 新的上游代理配置
            
        Raises:
            RuntimeError: 如果API客户端未配置或获取失败
            ValueError: 如果API提供商不存在或未启用
        """
        logger.info(f"Getting new proxy from API provider: {api_provider_id}")
        
        if not self.config:
            raise RuntimeError("No configuration loaded")
        
        # 查找指定的API提供商配置
        provider_config = None
        for provider in self.config.api_providers:
            if provider.id == api_provider_id:
                provider_config = provider
                break
        
        if not provider_config:
            raise ValueError(f"API provider not found: {api_provider_id}")
        
        if not provider_config.enabled:
            raise ValueError(f"API provider is disabled: {api_provider_id}")
        
        # 创建API客户端实例
        from .api_client import APIClient
        api_client = APIClient(provider_config)
        
        try:
            # 从API获取新代理
            new_proxy = api_client.get_new_proxy()
            logger.info(f"Successfully obtained new proxy: {new_proxy.server}:{new_proxy.port}")
            return new_proxy
            
        except Exception as e:
            logger.error(f"Failed to get new proxy from API: {e}")
            raise RuntimeError(f"Failed to get new proxy from API: {e}")
    
    def validate_upstream_proxy(self, upstream: UpstreamProxy, timeout: int = 10) -> bool:
        """
        验证上游代理是否可用
        
        Args:
            upstream: 上游代理配置
            timeout: 超时时间（秒）
            
        Returns:
            bool: 可用返回True，不可用返回False
        """
        logger.info(f"Validating upstream proxy: {upstream.server}:{upstream.port}")
        
        try:
            # Import here to avoid requiring PySocks at module level
            import requests
            import socks
            import socket
            import importlib
            
            # 配置SOCKS代理
            socks.set_default_proxy(
                socks.SOCKS5,
                upstream.server,
                upstream.port,
                username=upstream.username,
                password=upstream.password
            )
            socket.socket = socks.socksocket
            
            # 尝试通过代理发送HTTP请求
            test_url = "http://www.google.com"
            if self.config and self.config.monitoring:
                test_url = self.config.monitoring.check_url
            
            response = requests.get(test_url, timeout=timeout)
            
            # 恢复默认socket
            importlib.reload(socket)
            
            if response.status_code == 200:
                logger.info(f"Upstream proxy validation successful")
                return True
            else:
                logger.warning(f"Upstream proxy returned status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Upstream proxy validation failed: {e}")
            # 恢复默认socket
            try:
                import importlib
                import socket
                importlib.reload(socket)
            except:
                pass
            return False
