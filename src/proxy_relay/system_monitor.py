"""
系统监控模块

提供系统资源监控功能，包括：
- 网络连接数统计
- 网卡流量统计
- 端口流量统计（通过 iptables）
"""

import os
import time
import logging
import subprocess
import threading
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class NetworkStats:
    """网络统计数据"""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PortTrafficStats:
    """端口流量统计"""
    port: int = 0
    bytes_sent: int = 0
    bytes_recv: int = 0
    last_bytes_sent: int = 0
    last_bytes_recv: int = 0


class SystemMonitor:
    """系统监控类"""
    
    def __init__(self):
        self._last_network_stats: Optional[NetworkStats] = None
        self._last_check_time: float = 0
        self._port_traffic: Dict[int, PortTrafficStats] = {}
        self._traffic_collector_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._database = None
        self._iptables_initialized = False
    
    def set_database(self, database):
        """设置数据库实例"""
        self._database = database
    
    def get_connection_count(self, port: Optional[int] = None) -> int:
        """
        获取当前连接数
        
        Args:
            port: 指定端口，None 表示所有端口
            
        Returns:
            int: 连接数
        """
        try:
            if port:
                # 统计指定端口的连接数
                cmd = f"ss -tn state established '( sport = :{port} or dport = :{port} )' 2>/dev/null | tail -n +2 | wc -l"
            else:
                # 统计所有 ESTABLISHED 连接
                cmd = "ss -tn state established 2>/dev/null | tail -n +2 | wc -l"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return int(result.stdout.strip() or 0)
            return 0
            
        except Exception as e:
            logger.warning(f"Failed to get connection count: {e}")
            return 0
    
    def get_network_stats(self) -> NetworkStats:
        """
        获取网络统计数据
        
        Returns:
            NetworkStats: 网络统计
        """
        try:
            # 读取 /proc/net/dev
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            total_recv = 0
            total_sent = 0
            total_packets_recv = 0
            total_packets_sent = 0
            
            for line in lines[2:]:  # 跳过头两行
                parts = line.split()
                if len(parts) < 10:
                    continue
                
                interface = parts[0].rstrip(':')
                # 跳过 lo 接口
                if interface == 'lo':
                    continue
                
                # bytes: recv=1, sent=9
                # packets: recv=2, sent=10
                total_recv += int(parts[1])
                total_packets_recv += int(parts[2])
                total_sent += int(parts[9])
                total_packets_sent += int(parts[10])
            
            return NetworkStats(
                bytes_sent=total_sent,
                bytes_recv=total_recv,
                packets_sent=total_packets_sent,
                packets_recv=total_packets_recv,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.warning(f"Failed to get network stats: {e}")
            return NetworkStats()
    
    def get_network_speed(self) -> Tuple[float, float]:
        """
        获取网络速度（字节/秒）
        
        Returns:
            Tuple[float, float]: (发送速度, 接收速度)
        """
        current_stats = self.get_network_stats()
        
        if self._last_network_stats is None:
            self._last_network_stats = current_stats
            return (0.0, 0.0)
        
        time_diff = current_stats.timestamp - self._last_network_stats.timestamp
        if time_diff <= 0:
            return (0.0, 0.0)
        
        send_speed = (current_stats.bytes_sent - self._last_network_stats.bytes_sent) / time_diff
        recv_speed = (current_stats.bytes_recv - self._last_network_stats.bytes_recv) / time_diff
        
        self._last_network_stats = current_stats
        
        return (max(0, send_speed), max(0, recv_speed))
    
    def get_port_connections(self, ports: list) -> Dict[int, int]:
        """
        获取多个端口的连接数
        
        Args:
            ports: 端口列表
            
        Returns:
            Dict[int, int]: {端口: 连接数}
        """
        result = {}
        for port in ports:
            result[port] = self.get_connection_count(port)
        return result
    
    # ==================== 端口流量统计 ====================
    
    def init_port_traffic_rules(self, ports: list) -> bool:
        """
        初始化端口流量统计的 iptables 规则
        
        Args:
            ports: 要监控的端口列表
            
        Returns:
            bool: 是否成功
        """
        try:
            for port in ports:
                # 添加入站规则
                subprocess.run(
                    ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"],
                    capture_output=True,
                    timeout=5
                )
                # 添加出站规则
                subprocess.run(
                    ["sudo", "iptables", "-A", "OUTPUT", "-p", "tcp", "--sport", str(port), "-j", "ACCEPT"],
                    capture_output=True,
                    timeout=5
                )
                
                self._port_traffic[port] = PortTrafficStats(port=port)
            
            self._iptables_initialized = True
            logger.info(f"Initialized iptables rules for ports: {ports}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to init iptables rules: {e}")
            return False
    
    def get_port_traffic_from_iptables(self, port: int) -> Tuple[int, int]:
        """
        从 iptables 获取端口流量
        
        Args:
            port: 端口号
            
        Returns:
            Tuple[int, int]: (发送字节数, 接收字节数)
        """
        bytes_sent = 0
        bytes_recv = 0
        
        try:
            # 获取入站流量（接收）
            result = subprocess.run(
                ["sudo", "iptables", "-L", "INPUT", "-v", "-n", "-x"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f"dpt:{port}" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                bytes_recv = int(parts[1])
                            except ValueError:
                                pass
                        break
            
            # 获取出站流量（发送）
            result = subprocess.run(
                ["sudo", "iptables", "-L", "OUTPUT", "-v", "-n", "-x"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f"spt:{port}" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                bytes_sent = int(parts[1])
                            except ValueError:
                                pass
                        break
                        
        except Exception as e:
            logger.warning(f"Failed to get port traffic from iptables: {e}")
        
        return (bytes_sent, bytes_recv)
    
    def collect_port_traffic(self, ports: list) -> Dict[int, Dict[str, int]]:
        """
        采集端口流量并计算增量
        
        Args:
            ports: 端口列表
            
        Returns:
            Dict[int, Dict[str, int]]: {端口: {bytes_sent, bytes_recv, delta_sent, delta_recv}}
        """
        result = {}
        
        for port in ports:
            current_sent, current_recv = self.get_port_traffic_from_iptables(port)
            
            # 获取上次的值
            if port not in self._port_traffic:
                self._port_traffic[port] = PortTrafficStats(port=port)
            
            stats = self._port_traffic[port]
            
            # 计算增量
            delta_sent = max(0, current_sent - stats.last_bytes_sent) if stats.last_bytes_sent > 0 else 0
            delta_recv = max(0, current_recv - stats.last_bytes_recv) if stats.last_bytes_recv > 0 else 0
            
            # 更新累计值
            stats.bytes_sent += delta_sent
            stats.bytes_recv += delta_recv
            stats.last_bytes_sent = current_sent
            stats.last_bytes_recv = current_recv
            
            result[port] = {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'delta_sent': delta_sent,
                'delta_recv': delta_recv
            }
        
        return result
    
    def start_traffic_collector(self, ports: list, interval: int = 60):
        """
        启动流量采集后台线程
        
        Args:
            ports: 要监控的端口列表
            interval: 采集间隔（秒）
        """
        if self._traffic_collector_thread and self._traffic_collector_thread.is_alive():
            logger.warning("Traffic collector already running")
            return
        
        self._stop_event.clear()
        self._traffic_collector_thread = threading.Thread(
            target=self._traffic_collector_loop,
            args=(ports, interval),
            daemon=True
        )
        self._traffic_collector_thread.start()
        logger.info(f"Started traffic collector for ports: {ports}, interval: {interval}s")
    
    def stop_traffic_collector(self):
        """停止流量采集"""
        self._stop_event.set()
        if self._traffic_collector_thread:
            self._traffic_collector_thread.join(timeout=5)
        logger.info("Stopped traffic collector")
    
    def _traffic_collector_loop(self, ports: list, interval: int):
        """流量采集循环"""
        while not self._stop_event.is_set():
            try:
                traffic_data = self.collect_port_traffic(ports)
                
                # 保存到数据库
                if self._database:
                    for port, data in traffic_data.items():
                        if data['delta_sent'] > 0 or data['delta_recv'] > 0:
                            self._database.update_port_traffic(
                                local_port=port,
                                bytes_sent=data['delta_sent'],
                                bytes_recv=data['delta_recv'],
                                connections=self.get_connection_count(port)
                            )
                
            except Exception as e:
                logger.error(f"Error in traffic collector: {e}")
            
            # 等待下一次采集
            self._stop_event.wait(timeout=interval)
    
    def get_system_metrics(self) -> dict:
        """
        获取系统指标汇总
        
        Returns:
            dict: 系统指标
        """
        network_stats = self.get_network_stats()
        send_speed, recv_speed = self.get_network_speed()
        total_connections = self.get_connection_count()
        
        return {
            "connections": {
                "total": total_connections
            },
            "network": {
                "bytes_sent": network_stats.bytes_sent,
                "bytes_recv": network_stats.bytes_recv,
                "send_speed": round(send_speed, 2),
                "recv_speed": round(recv_speed, 2),
                "send_speed_formatted": self._format_bytes(send_speed) + "/s",
                "recv_speed_formatted": self._format_bytes(recv_speed) + "/s",
                "total_sent_formatted": self._format_bytes(network_stats.bytes_sent),
                "total_recv_formatted": self._format_bytes(network_stats.bytes_recv)
            },
            "timestamp": time.time()
        }
    
    @staticmethod
    def _format_bytes(bytes_value: float) -> str:
        """格式化字节数"""
        if bytes_value < 1024:
            return f"{bytes_value:.0f} B"
        elif bytes_value < 1024 * 1024:
            return f"{bytes_value / 1024:.1f} KB"
        elif bytes_value < 1024 * 1024 * 1024:
            return f"{bytes_value / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"


# 全局实例
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """获取系统监控实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor
