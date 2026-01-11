"""
Command-line interface for Proxy Relay System.
"""

import sys
import os
import signal
import json
import click
import logging
from pathlib import Path
from typing import Optional

from . import __version__
from .config_manager import ConfigManager
from .proxy_manager import ProxyManager
from .logging_config import setup_logging, get_logger


# 默认配置路径
DEFAULT_CONFIG_PATH = os.environ.get('PROXY_RELAY_CONFIG', '/etc/proxy-relay/config.yaml')
DEFAULT_PID_FILE = '/var/run/sing-box.pid'


@click.group()
@click.version_option(version=__version__, prog_name='proxy-relay')
@click.option('--config', '-c', default=DEFAULT_CONFIG_PATH, 
              help='Configuration file path', show_default=True)
@click.pass_context
def cli(ctx, config):
    """Proxy Relay System - SOCKS5 proxy relay with automatic health monitoring."""
    # 将配置路径存储在上下文中，供子命令使用
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config


@cli.command()
@click.pass_context
def start(ctx):
    """Start the proxy relay service.
    
    This command loads the configuration, generates sing-box configuration,
    and starts the sing-box process.
    """
    config_path = ctx.obj['config_path']
    logger = None
    
    try:
        click.echo(f"Starting Proxy Relay System...")
        click.echo(f"Loading configuration from: {config_path}")
        
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 初始化日志系统
        logger = setup_logging(
            log_file=config.system.log_file,
            log_level=config.system.log_level
        )
        logger.info("Proxy Relay System starting...")
        logger.info(f"Configuration loaded from: {config_path}")
        
        click.echo(f"Loaded {len(config.proxies)} proxy configuration(s)")
        logger.info(f"Loaded {len(config.proxies)} proxy configurations")
        
        # 生成并应用sing-box配置
        proxy_manager = ProxyManager(config_manager)
        singbox_config = proxy_manager.generate_singbox_config()
        
        click.echo(f"Generated sing-box configuration with {len(singbox_config['inbounds'])} inbound(s)")
        logger.info(f"Generated sing-box configuration with {len(singbox_config['inbounds'])} inbounds")
        
        # 应用配置
        proxy_manager.apply_singbox_config(singbox_config)
        
        click.echo("✓ Configuration applied successfully")
        logger.info("sing-box configuration applied successfully")
        
        # 启动sing-box进程
        click.echo("Starting sing-box process...")
        logger.info("Starting sing-box process...")
        
        # 检查sing-box是否已安装
        singbox_path = _find_singbox_binary()
        if not singbox_path:
            click.echo("✗ Error: sing-box binary not found", err=True)
            logger.error("sing-box binary not found")
            click.echo("Please install sing-box first", err=True)
            sys.exit(1)
        
        logger.info(f"Found sing-box at: {singbox_path}")
        
        # 启动sing-box
        pid = _start_singbox(singbox_path, proxy_manager.singbox_config_path)
        
        if pid:
            click.echo(f"✓ sing-box started successfully (PID: {pid})")
            logger.info(f"sing-box started successfully (PID: {pid})")
            click.echo(f"\nProxy ports listening:")
            for proxy in config.proxies:
                click.echo(f"  - {proxy.name}: 0.0.0.0:{proxy.local_port}")
                logger.info(f"Proxy port listening: {proxy.name} on 0.0.0.0:{proxy.local_port}")
        else:
            click.echo("✗ Failed to start sing-box", err=True)
            logger.error("Failed to start sing-box")
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        if logger:
            logger.error(f"Configuration file not found: {e}")
        click.echo(f"Please create a configuration file at: {config_path}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ Configuration error: {e}", err=True)
        if logger:
            logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if logger:
            logger.exception(f"Unexpected error during startup: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop the proxy relay service.
    
    This command sends SIGTERM signal to the sing-box process
    and cleans up resources.
    """
    logger = get_logger(__name__)
    
    try:
        click.echo("Stopping Proxy Relay System...")
        logger.info("Stopping Proxy Relay System...")
        
        # 读取PID文件
        if not os.path.exists(DEFAULT_PID_FILE):
            click.echo("✗ sing-box is not running (PID file not found)", err=True)
            logger.warning("sing-box is not running (PID file not found)")
            sys.exit(1)
        
        with open(DEFAULT_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        click.echo(f"Sending SIGTERM to process {pid}...")
        logger.info(f"Sending SIGTERM to process {pid}")
        
        # 发送SIGTERM信号
        try:
            os.kill(pid, signal.SIGTERM)
            click.echo("✓ SIGTERM signal sent")
            logger.info("SIGTERM signal sent")
            
            # 等待进程结束
            import time
            max_wait = 10  # 最多等待10秒
            for i in range(max_wait):
                try:
                    # 检查进程是否还存在
                    os.kill(pid, 0)
                    time.sleep(1)
                except ProcessLookupError:
                    # 进程已结束
                    break
            
            # 再次检查进程是否结束
            try:
                os.kill(pid, 0)
                click.echo("⚠ Process did not terminate gracefully, sending SIGKILL...", err=True)
                logger.warning("Process did not terminate gracefully, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            
            # 清理PID文件
            if os.path.exists(DEFAULT_PID_FILE):
                os.remove(DEFAULT_PID_FILE)
            
            click.echo("✓ sing-box stopped successfully")
            logger.info("sing-box stopped successfully")
            
        except ProcessLookupError:
            click.echo("✗ Process not found (already stopped?)", err=True)
            logger.warning("Process not found (already stopped?)")
            # 清理PID文件
            if os.path.exists(DEFAULT_PID_FILE):
                os.remove(DEFAULT_PID_FILE)
            sys.exit(1)
        except PermissionError:
            click.echo("✗ Permission denied (try running with sudo)", err=True)
            logger.error("Permission denied when stopping sing-box")
            sys.exit(1)
            
    except ValueError as e:
        click.echo(f"✗ Invalid PID file: {e}", err=True)
        logger.error(f"Invalid PID file: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.exception(f"Error stopping service: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show the status of the proxy relay service.
    
    This command checks if sing-box is running and displays
    basic status information.
    """
    config_path = ctx.obj['config_path']
    
    try:
        click.echo("Proxy Relay System Status")
        click.echo("=" * 50)
        
        # 检查sing-box进程状态
        is_running = False
        pid = None
        
        if os.path.exists(DEFAULT_PID_FILE):
            try:
                with open(DEFAULT_PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                
                # 检查进程是否存在
                os.kill(pid, 0)
                is_running = True
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        
        if is_running:
            click.echo(f"Service Status: ✓ Running (PID: {pid})")
        else:
            click.echo("Service Status: ✗ Not running")
        
        # 显示配置信息
        click.echo(f"Configuration: {config_path}")
        
        if os.path.exists(config_path):
            try:
                config_manager = ConfigManager(config_path)
                config = config_manager.load_config()
                
                click.echo(f"Configured Proxies: {len(config.proxies)}")
                click.echo(f"Web Port: {config.system.web_port}")
                click.echo(f"Log Level: {config.system.log_level}")
            except Exception as e:
                click.echo(f"⚠ Failed to load configuration: {e}", err=True)
        else:
            click.echo("⚠ Configuration file not found", err=True)
        
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.pass_context
def list(ctx, verbose):
    """List all configured proxy ports and their status.
    
    This command reads the current configuration and displays
    all proxy ports with their upstream proxy information.
    """
    config_path = ctx.obj['config_path']
    
    try:
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        if not config.proxies:
            click.echo("No proxy configurations found.")
            return
        
        click.echo(f"Configured Proxy Ports ({len(config.proxies)} total)")
        click.echo("=" * 80)
        
        for proxy in config.proxies:
            click.echo(f"\n{proxy.name}")
            click.echo(f"  Local Port: {proxy.local_port}")
            click.echo(f"  Upstream: {proxy.upstream.protocol}://{proxy.upstream.server}:{proxy.upstream.port}")
            
            if proxy.upstream.username:
                click.echo(f"  Authentication: Yes (username: {proxy.upstream.username})")
            else:
                click.echo(f"  Authentication: No")
            
            click.echo(f"  Monitoring: {'Enabled' if proxy.monitoring_enabled else 'Disabled'}")
            click.echo(f"  API Provider: {proxy.api_provider_id}")
            
            if verbose:
                # 显示更详细的信息
                click.echo(f"  Protocol: {proxy.upstream.protocol}")
                if proxy.upstream.password:
                    click.echo(f"  Password: {'*' * len(proxy.upstream.password)}")
        
        click.echo()
        
    except FileNotFoundError as e:
        click.echo(f"✗ Error: Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


def _find_singbox_binary() -> Optional[str]:
    """
    查找sing-box二进制文件
    
    Returns:
        Optional[str]: sing-box路径，如果未找到返回None
    """
    # 常见的安装位置
    possible_paths = [
        '/usr/local/bin/sing-box',
        '/usr/bin/sing-box',
        '/opt/proxy-relay/sing-box',
        'sing-box'  # 在PATH中查找
    ]
    
    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # 尝试使用which命令查找
    import shutil
    which_result = shutil.which('sing-box')
    if which_result:
        return which_result
    
    return None


def _start_singbox(singbox_path: str, config_path: str) -> Optional[int]:
    """
    启动sing-box进程
    
    Args:
        singbox_path: sing-box二进制文件路径
        config_path: sing-box配置文件路径
        
    Returns:
        Optional[int]: 进程PID，如果启动失败返回None
    """
    import subprocess
    
    try:
        # 启动sing-box进程（后台运行）
        process = subprocess.Popen(
            [singbox_path, 'run', '-c', config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True  # 创建新的会话，使进程独立
        )
        
        # 等待一小段时间确保进程启动
        import time
        time.sleep(1)
        
        # 检查进程是否还在运行
        if process.poll() is not None:
            # 进程已退出，启动失败
            stderr = process.stderr.read().decode('utf-8')
            click.echo(f"sing-box failed to start: {stderr}", err=True)
            return None
        
        # 保存PID到文件
        pid = process.pid
        pid_dir = os.path.dirname(DEFAULT_PID_FILE)
        if pid_dir:
            os.makedirs(pid_dir, exist_ok=True)
        
        with open(DEFAULT_PID_FILE, 'w') as f:
            f.write(str(pid))
        
        return pid
        
    except Exception as e:
        click.echo(f"Failed to start sing-box: {e}", err=True)
        return None


@cli.group()
@click.pass_context
def monitor(ctx):
    """Monitor control commands.
    
    Commands to start, stop, and check monitoring status for proxy ports.
    """
    pass


@monitor.command('start')
@click.argument('port', type=int)
@click.pass_context
def monitor_start(ctx, port):
    """Start monitoring for a specific proxy port.
    
    Args:
        port: Local proxy port number to start monitoring
    """
    config_path = ctx.obj['config_path']
    logger = get_logger(__name__)
    
    try:
        click.echo(f"Starting monitoring for port {port}...")
        logger.info(f"Starting monitoring for port {port}")
        
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 初始化数据库
        from .database import Database
        database = Database(config.system.database)
        
        # 初始化代理管理器
        proxy_manager = ProxyManager(config_manager, database=database)
        
        # 初始化健康监控器
        from .health_monitor import HealthMonitor
        health_monitor = HealthMonitor(config_manager, proxy_manager, database)
        
        # 启动监控
        health_monitor.start_monitoring(port)
        
        click.echo(f"✓ Monitoring started for port {port}")
        logger.info(f"Monitoring started for port {port}")
        
        # 显示监控配置
        click.echo(f"\nMonitoring configuration:")
        click.echo(f"  Check interval: {config.monitoring.check_interval}s")
        click.echo(f"  Failure threshold: {config.monitoring.failure_threshold}")
        click.echo(f"  Check URL: {config.monitoring.check_url}")
        
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Error starting monitoring: {e}")
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Error starting monitoring: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        logger.exception(f"Unexpected error starting monitoring: {e}")
        sys.exit(1)


@monitor.command('stop')
@click.argument('port', type=int)
@click.pass_context
def monitor_stop(ctx, port):
    """Stop monitoring for a specific proxy port.
    
    Args:
        port: Local proxy port number to stop monitoring
    """
    config_path = ctx.obj['config_path']
    logger = get_logger(__name__)
    
    try:
        click.echo(f"Stopping monitoring for port {port}...")
        logger.info(f"Stopping monitoring for port {port}")
        
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 初始化数据库
        from .database import Database
        database = Database(config.system.database)
        
        # 初始化代理管理器
        proxy_manager = ProxyManager(config_manager, database=database)
        
        # 初始化健康监控器
        from .health_monitor import HealthMonitor
        health_monitor = HealthMonitor(config_manager, proxy_manager, database)
        
        # 停止监控
        health_monitor.stop_monitoring(port)
        
        click.echo(f"✓ Monitoring stopped for port {port}")
        logger.info(f"Monitoring stopped for port {port}")
        
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Error stopping monitoring: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        logger.exception(f"Unexpected error stopping monitoring: {e}")
        sys.exit(1)


@monitor.command('status')
@click.pass_context
def monitor_status(ctx):
    """Show monitoring status for all proxy ports.
    
    Displays which ports have monitoring enabled and their current status.
    """
    config_path = ctx.obj['config_path']
    
    try:
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 初始化数据库
        from .database import Database
        database = Database(config.system.database)
        
        # 查询所有监控状态
        monitoring_states = database.get_all_monitoring_states()
        
        if not monitoring_states:
            click.echo("No monitoring status found.")
            click.echo("\nConfigured proxy ports:")
            for proxy in config.proxies:
                status_text = "Enabled" if proxy.monitoring_enabled else "Disabled"
                click.echo(f"  Port {proxy.local_port} ({proxy.name}): {status_text} (not started)")
            return
        
        click.echo("Monitoring Status")
        click.echo("=" * 80)
        
        # 创建端口到配置的映射
        port_to_config = {proxy.local_port: proxy for proxy in config.proxies}
        
        for state in monitoring_states:
            port = state['local_port']
            proxy_config = port_to_config.get(port)
            
            if proxy_config:
                click.echo(f"\n{proxy_config.name} (Port {port})")
            else:
                click.echo(f"\nPort {port}")
            
            status_text = "✓ Running" if state['enabled'] else "✗ Stopped"
            click.echo(f"  Status: {status_text}")
            click.echo(f"  Failure count: {state['failure_count']}")
            
            if state['last_check_time']:
                click.echo(f"  Last check: {state['last_check_time']}")
            else:
                click.echo(f"  Last check: Never")
            
            if state['last_success_time']:
                click.echo(f"  Last success: {state['last_success_time']}")
            else:
                click.echo(f"  Last success: Never")
        
        # 显示未启动监控的端口
        monitored_ports = {state['local_port'] for state in monitoring_states}
        unmonitored_ports = [proxy for proxy in config.proxies if proxy.local_port not in monitored_ports]
        
        if unmonitored_ports:
            click.echo("\n" + "=" * 80)
            click.echo("Ports without monitoring:")
            for proxy in unmonitored_ports:
                status_text = "Enabled" if proxy.monitoring_enabled else "Disabled"
                click.echo(f"  Port {proxy.local_port} ({proxy.name}): {status_text} (not started)")
        
        click.echo()
        
    except FileNotFoundError as e:
        click.echo(f"✗ Error: Configuration file not found: {config_path}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('port', type=int)
@click.option('--api-provider', '-a', help='API provider ID to use for getting new proxy')
@click.pass_context
def switch(ctx, port, api_provider):
    """Manually trigger proxy replacement for a specific port.
    
    This command will get a new proxy from the configured API provider
    and switch the upstream proxy for the specified port.
    
    Args:
        port: Local proxy port number to switch
        api_provider: API provider ID (optional, uses port's configured provider if not specified)
    """
    config_path = ctx.obj['config_path']
    logger = get_logger(__name__)
    
    try:
        click.echo(f"Switching proxy for port {port}...")
        logger.info(f"Manual proxy switch requested for port {port}")
        
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 查找端口配置
        proxy_config = None
        for proxy in config.proxies:
            if proxy.local_port == port:
                proxy_config = proxy
                break
        
        if not proxy_config:
            click.echo(f"✗ Error: No proxy configuration found for port {port}", err=True)
            logger.error(f"No proxy configuration found for port {port}")
            sys.exit(1)
        
        # 确定使用哪个API提供商
        provider_id = api_provider if api_provider else proxy_config.api_provider_id
        
        if not provider_id:
            click.echo(f"✗ Error: No API provider specified", err=True)
            click.echo(f"Please specify --api-provider or configure api_provider_id for this port", err=True)
            logger.error(f"No API provider specified for port {port}")
            sys.exit(1)
        
        click.echo(f"Using API provider: {provider_id}")
        logger.info(f"Using API provider: {provider_id}")
        
        # 初始化数据库
        from .database import Database
        database = Database(config.system.database)
        
        # 初始化代理管理器
        proxy_manager = ProxyManager(config_manager, database=database)
        
        # 从API获取新代理
        click.echo(f"Getting new proxy from API...")
        logger.info(f"Getting new proxy from API provider: {provider_id}")
        
        try:
            new_upstream = proxy_manager.get_new_proxy_from_api(provider_id)
            click.echo(f"✓ New proxy obtained: {new_upstream.server}:{new_upstream.port}")
            logger.info(f"New proxy obtained: {new_upstream.server}:{new_upstream.port}")
        except Exception as e:
            click.echo(f"✗ Failed to get new proxy from API: {e}", err=True)
            logger.error(f"Failed to get new proxy from API: {e}")
            sys.exit(1)
        
        # 验证新代理（可选）
        click.echo(f"Validating new proxy...")
        is_valid = proxy_manager.validate_upstream_proxy(new_upstream)
        
        if not is_valid:
            click.echo(f"⚠ Warning: New proxy validation failed", err=True)
            click.echo(f"The proxy may not be working properly", err=True)
            logger.warning(f"New proxy validation failed: {new_upstream.server}:{new_upstream.port}")
            
            # 询问用户是否继续
            if not click.confirm("Do you want to continue with the switch?"):
                click.echo("Switch cancelled")
                logger.info("Manual switch cancelled by user")
                sys.exit(0)
        else:
            click.echo(f"✓ New proxy validated successfully")
            logger.info(f"New proxy validated successfully")
        
        # 执行切换
        click.echo(f"Switching upstream proxy...")
        logger.info(f"Switching upstream proxy for port {port}")
        
        try:
            proxy_manager.switch_upstream_proxy(port, new_upstream, reason="manual")
            click.echo(f"✓ Proxy switched successfully")
            logger.info(f"Proxy switched successfully for port {port}")
            
            # 显示新的代理信息
            click.echo(f"\nNew upstream proxy:")
            click.echo(f"  Server: {new_upstream.server}")
            click.echo(f"  Port: {new_upstream.port}")
            click.echo(f"  Protocol: {new_upstream.protocol}")
            if new_upstream.username:
                click.echo(f"  Username: {new_upstream.username}")
            
        except Exception as e:
            click.echo(f"✗ Failed to switch proxy: {e}", err=True)
            logger.error(f"Failed to switch proxy: {e}")
            sys.exit(1)
        
    except FileNotFoundError as e:
        click.echo(f"✗ Error: Configuration file not found: {config_path}", err=True)
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"✗ Error: {e}", err=True)
        logger.error(f"Error during manual switch: {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        logger.exception(f"Unexpected error during manual switch: {e}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
