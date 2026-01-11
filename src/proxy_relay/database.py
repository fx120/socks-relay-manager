"""
数据库管理模块

负责SQLite数据库的初始化、连接管理和数据操作。
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import UpstreamProxy, SwitchHistoryEntry

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Database directory ensured: {db_dir}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        logger.info(f"Initializing database: {self.db_path}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建 proxy_switch_history 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proxy_switch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_port INTEGER NOT NULL,
                    old_upstream_server TEXT,
                    old_upstream_port INTEGER,
                    old_upstream_username TEXT,
                    old_upstream_password TEXT,
                    old_upstream_protocol TEXT,
                    new_upstream_server TEXT NOT NULL,
                    new_upstream_port INTEGER NOT NULL,
                    new_upstream_username TEXT,
                    new_upstream_password TEXT,
                    new_upstream_protocol TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL,
                    CHECK (reason IN ('health_check_failed', 'manual', 'api_error'))
                )
            """)
            
            # 创建 health_check_log 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_check_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_port INTEGER NOT NULL,
                    upstream_server TEXT NOT NULL,
                    upstream_port INTEGER NOT NULL,
                    check_result BOOLEAN NOT NULL,
                    response_time_ms INTEGER,
                    error_message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建 monitoring_state 表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_state (
                    local_port INTEGER PRIMARY KEY,
                    enabled BOOLEAN NOT NULL,
                    failure_count INTEGER DEFAULT 0,
                    last_check_time DATETIME,
                    last_success_time DATETIME
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_switch_history_port 
                ON proxy_switch_history(local_port)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_switch_history_timestamp 
                ON proxy_switch_history(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_check_port 
                ON health_check_log(local_port)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_check_timestamp 
                ON health_check_log(timestamp)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器
        
        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使用 Row 对象以便按列名访问
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            conn.close()
    
    # ==================== 代理切换历史操作 ====================
    
    def insert_switch_history(
        self,
        local_port: int,
        old_upstream: Optional[UpstreamProxy],
        new_upstream: UpstreamProxy,
        reason: str,
        success: bool,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        插入代理切换历史记录
        
        Args:
            local_port: 本地端口
            old_upstream: 旧的上游代理（可为None）
            new_upstream: 新的上游代理
            reason: 切换原因 ('health_check_failed', 'manual', 'api_error')
            success: 是否成功
            timestamp: 时间戳（可选，默认为当前时间）
            
        Returns:
            int: 插入记录的ID
        """
        if reason not in ['health_check_failed', 'manual', 'api_error']:
            raise ValueError(f"Invalid reason: {reason}")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if timestamp is None:
                timestamp = datetime.now()
            
            cursor.execute("""
                INSERT INTO proxy_switch_history (
                    local_port,
                    old_upstream_server, old_upstream_port, old_upstream_username,
                    old_upstream_password, old_upstream_protocol,
                    new_upstream_server, new_upstream_port, new_upstream_username,
                    new_upstream_password, new_upstream_protocol,
                    reason, timestamp, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_port,
                old_upstream.server if old_upstream else None,
                old_upstream.port if old_upstream else None,
                old_upstream.username if old_upstream else None,
                old_upstream.password if old_upstream else None,
                old_upstream.protocol if old_upstream else None,
                new_upstream.server,
                new_upstream.port,
                new_upstream.username,
                new_upstream.password,
                new_upstream.protocol,
                reason,
                timestamp.isoformat(),
                success
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"Switch history recorded: port={local_port}, reason={reason}, success={success}")
            return record_id
    
    def get_switch_history(
        self,
        local_port: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SwitchHistoryEntry]:
        """
        查询代理切换历史
        
        Args:
            local_port: 本地端口（可选，None表示查询所有端口）
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            List[SwitchHistoryEntry]: 切换历史记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if local_port is not None:
                cursor.execute("""
                    SELECT * FROM proxy_switch_history
                    WHERE local_port = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (local_port, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM proxy_switch_history
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            return [self._row_to_switch_history(row) for row in rows]
    
    def _row_to_switch_history(self, row: sqlite3.Row) -> SwitchHistoryEntry:
        """将数据库行转换为 SwitchHistoryEntry 对象"""
        old_upstream = None
        if row['old_upstream_server']:
            old_upstream = UpstreamProxy(
                server=row['old_upstream_server'],
                port=row['old_upstream_port'],
                username=row['old_upstream_username'],
                password=row['old_upstream_password'],
                protocol=row['old_upstream_protocol'] or 'socks5'
            )
        
        new_upstream = UpstreamProxy(
            server=row['new_upstream_server'],
            port=row['new_upstream_port'],
            username=row['new_upstream_username'],
            password=row['new_upstream_password'],
            protocol=row['new_upstream_protocol']
        )
        
        return SwitchHistoryEntry(
            id=row['id'],
            local_port=row['local_port'],
            old_upstream=old_upstream,
            new_upstream=new_upstream,
            reason=row['reason'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            success=bool(row['success'])
        )
    
    # ==================== 健康检查日志操作 ====================
    
    def insert_health_check_log(
        self,
        local_port: int,
        upstream_server: str,
        upstream_port: int,
        check_result: bool,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        插入健康检查日志
        
        Args:
            local_port: 本地端口
            upstream_server: 上游代理服务器
            upstream_port: 上游代理端口
            check_result: 检查结果（True=成功，False=失败）
            response_time_ms: 响应时间（毫秒）
            error_message: 错误信息
            timestamp: 时间戳（可选，默认为当前时间）
            
        Returns:
            int: 插入记录的ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if timestamp is None:
                timestamp = datetime.now()
            
            cursor.execute("""
                INSERT INTO health_check_log (
                    local_port, upstream_server, upstream_port,
                    check_result, response_time_ms, error_message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                local_port,
                upstream_server,
                upstream_port,
                check_result,
                response_time_ms,
                error_message,
                timestamp.isoformat()
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.debug(f"Health check logged: port={local_port}, result={check_result}")
            return record_id
    
    def get_health_check_logs(
        self,
        local_port: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询健康检查日志
        
        Args:
            local_port: 本地端口（可选，None表示查询所有端口）
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            List[Dict[str, Any]]: 健康检查日志列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if local_port is not None:
                cursor.execute("""
                    SELECT * FROM health_check_log
                    WHERE local_port = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (local_port, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM health_check_log
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ==================== 监控状态操作 ====================
    
    def upsert_monitoring_state(
        self,
        local_port: int,
        enabled: bool,
        failure_count: int = 0,
        last_check_time: Optional[datetime] = None,
        last_success_time: Optional[datetime] = None
    ) -> None:
        """
        插入或更新监控状态
        
        Args:
            local_port: 本地端口
            enabled: 是否启用监控
            failure_count: 失败计数
            last_check_time: 最后检查时间
            last_success_time: 最后成功时间
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO monitoring_state (
                    local_port, enabled, failure_count, last_check_time, last_success_time
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(local_port) DO UPDATE SET
                    enabled = excluded.enabled,
                    failure_count = excluded.failure_count,
                    last_check_time = excluded.last_check_time,
                    last_success_time = excluded.last_success_time
            """, (
                local_port,
                enabled,
                failure_count,
                last_check_time.isoformat() if last_check_time else None,
                last_success_time.isoformat() if last_success_time else None
            ))
            
            conn.commit()
            logger.debug(f"Monitoring state updated: port={local_port}, enabled={enabled}")
    
    def get_monitoring_state(self, local_port: int) -> Optional[Dict[str, Any]]:
        """
        获取指定端口的监控状态
        
        Args:
            local_port: 本地端口
            
        Returns:
            Optional[Dict[str, Any]]: 监控状态字典，不存在返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM monitoring_state
                WHERE local_port = ?
            """, (local_port,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_monitoring_states(self) -> List[Dict[str, Any]]:
        """
        获取所有端口的监控状态
        
        Returns:
            List[Dict[str, Any]]: 监控状态列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM monitoring_state")
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def delete_monitoring_state(self, local_port: int) -> bool:
        """
        删除指定端口的监控状态
        
        Args:
            local_port: 本地端口
            
        Returns:
            bool: 是否成功删除
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM monitoring_state
                WHERE local_port = ?
            """, (local_port,))
            
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Monitoring state deleted: port={local_port}")
            return deleted
    
    # ==================== 事务管理 ====================
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        使用示例:
            with db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
        """
        with self._get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
