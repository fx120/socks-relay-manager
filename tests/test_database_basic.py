"""
数据库基本功能测试

测试数据库初始化、CRUD操作和事务管理。
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.proxy_relay.database import Database
from src.proxy_relay.models import UpstreamProxy


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


def test_database_initialization(temp_db):
    """测试数据库初始化"""
    # 验证数据库文件已创建
    assert os.path.exists(temp_db.db_path)
    
    # 验证表已创建
    with temp_db._get_connection() as conn:
        cursor = conn.cursor()
        
        # 检查 proxy_switch_history 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='proxy_switch_history'
        """)
        assert cursor.fetchone() is not None
        
        # 检查 health_check_log 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='health_check_log'
        """)
        assert cursor.fetchone() is not None
        
        # 检查 monitoring_state 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='monitoring_state'
        """)
        assert cursor.fetchone() is not None


def test_insert_switch_history(temp_db):
    """测试插入代理切换历史"""
    old_upstream = UpstreamProxy(
        server="old.proxy.com",
        port=10000,
        username="user1",
        password="pass1"
    )
    
    new_upstream = UpstreamProxy(
        server="new.proxy.com",
        port=10001,
        username="user2",
        password="pass2"
    )
    
    # 插入记录
    record_id = temp_db.insert_switch_history(
        local_port=1080,
        old_upstream=old_upstream,
        new_upstream=new_upstream,
        reason="health_check_failed",
        success=True
    )
    
    assert record_id > 0
    
    # 查询记录
    history = temp_db.get_switch_history(local_port=1080)
    assert len(history) == 1
    
    entry = history[0]
    assert entry.local_port == 1080
    assert entry.old_upstream.server == "old.proxy.com"
    assert entry.new_upstream.server == "new.proxy.com"
    assert entry.reason == "health_check_failed"
    assert entry.success is True


def test_insert_switch_history_without_old_upstream(temp_db):
    """测试插入切换历史（无旧代理）"""
    new_upstream = UpstreamProxy(
        server="new.proxy.com",
        port=10001
    )
    
    record_id = temp_db.insert_switch_history(
        local_port=1080,
        old_upstream=None,
        new_upstream=new_upstream,
        reason="manual",
        success=True
    )
    
    assert record_id > 0
    
    history = temp_db.get_switch_history(local_port=1080)
    assert len(history) == 1
    assert history[0].old_upstream is None


def test_insert_switch_history_invalid_reason(temp_db):
    """测试插入切换历史（无效原因）"""
    new_upstream = UpstreamProxy(server="proxy.com", port=10000)
    
    with pytest.raises(ValueError, match="Invalid reason"):
        temp_db.insert_switch_history(
            local_port=1080,
            old_upstream=None,
            new_upstream=new_upstream,
            reason="invalid_reason",
            success=True
        )


def test_get_switch_history_with_limit(temp_db):
    """测试查询切换历史（带限制）"""
    new_upstream = UpstreamProxy(server="proxy.com", port=10000)
    
    # 插入多条记录
    for i in range(5):
        temp_db.insert_switch_history(
            local_port=1080,
            old_upstream=None,
            new_upstream=new_upstream,
            reason="manual",
            success=True
        )
    
    # 查询前3条
    history = temp_db.get_switch_history(limit=3)
    assert len(history) == 3


def test_insert_health_check_log(temp_db):
    """测试插入健康检查日志"""
    record_id = temp_db.insert_health_check_log(
        local_port=1080,
        upstream_server="proxy.com",
        upstream_port=10000,
        check_result=True,
        response_time_ms=150
    )
    
    assert record_id > 0
    
    # 查询日志
    logs = temp_db.get_health_check_logs(local_port=1080)
    assert len(logs) == 1
    
    log = logs[0]
    assert log['local_port'] == 1080
    assert log['upstream_server'] == "proxy.com"
    assert log['check_result'] == 1  # SQLite stores boolean as integer
    assert log['response_time_ms'] == 150


def test_insert_health_check_log_with_error(temp_db):
    """测试插入健康检查日志（带错误信息）"""
    record_id = temp_db.insert_health_check_log(
        local_port=1080,
        upstream_server="proxy.com",
        upstream_port=10000,
        check_result=False,
        error_message="Connection timeout"
    )
    
    assert record_id > 0
    
    logs = temp_db.get_health_check_logs(local_port=1080)
    assert len(logs) == 1
    assert logs[0]['error_message'] == "Connection timeout"


def test_upsert_monitoring_state(temp_db):
    """测试插入/更新监控状态"""
    now = datetime.now()
    
    # 插入新状态
    temp_db.upsert_monitoring_state(
        local_port=1080,
        enabled=True,
        failure_count=0,
        last_check_time=now
    )
    
    # 查询状态
    state = temp_db.get_monitoring_state(1080)
    assert state is not None
    assert state['local_port'] == 1080
    assert state['enabled'] == 1  # SQLite stores boolean as integer
    assert state['failure_count'] == 0
    
    # 更新状态
    temp_db.upsert_monitoring_state(
        local_port=1080,
        enabled=True,
        failure_count=2,
        last_check_time=now
    )
    
    # 验证更新
    state = temp_db.get_monitoring_state(1080)
    assert state['failure_count'] == 2


def test_get_monitoring_state_not_found(temp_db):
    """测试获取不存在的监控状态"""
    state = temp_db.get_monitoring_state(9999)
    assert state is None


def test_get_all_monitoring_states(temp_db):
    """测试获取所有监控状态"""
    # 插入多个状态
    for port in [1080, 1081, 1082]:
        temp_db.upsert_monitoring_state(
            local_port=port,
            enabled=True,
            failure_count=0
        )
    
    # 查询所有状态
    states = temp_db.get_all_monitoring_states()
    assert len(states) == 3
    
    ports = [s['local_port'] for s in states]
    assert 1080 in ports
    assert 1081 in ports
    assert 1082 in ports


def test_delete_monitoring_state(temp_db):
    """测试删除监控状态"""
    # 插入状态
    temp_db.upsert_monitoring_state(
        local_port=1080,
        enabled=True,
        failure_count=0
    )
    
    # 验证存在
    assert temp_db.get_monitoring_state(1080) is not None
    
    # 删除状态
    result = temp_db.delete_monitoring_state(1080)
    assert result is True
    
    # 验证已删除
    assert temp_db.get_monitoring_state(1080) is None


def test_delete_monitoring_state_not_found(temp_db):
    """测试删除不存在的监控状态"""
    result = temp_db.delete_monitoring_state(9999)
    assert result is False


def test_transaction_commit(temp_db):
    """测试事务提交"""
    new_upstream = UpstreamProxy(server="proxy.com", port=10000)
    
    with temp_db.transaction() as conn:
        cursor = conn.cursor()
        
        # 在事务中插入多条记录
        for i in range(3):
            cursor.execute("""
                INSERT INTO proxy_switch_history (
                    local_port, new_upstream_server, new_upstream_port,
                    new_upstream_protocol, reason, success
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (1080 + i, "proxy.com", 10000, "socks5", "manual", True))
    
    # 验证所有记录都已提交
    history = temp_db.get_switch_history()
    assert len(history) == 3


def test_transaction_rollback(temp_db):
    """测试事务回滚"""
    new_upstream = UpstreamProxy(server="proxy.com", port=10000)
    
    try:
        with temp_db.transaction() as conn:
            cursor = conn.cursor()
            
            # 插入一条记录
            cursor.execute("""
                INSERT INTO proxy_switch_history (
                    local_port, new_upstream_server, new_upstream_port,
                    new_upstream_protocol, reason, success
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (1080, "proxy.com", 10000, "socks5", "manual", True))
            
            # 故意引发错误
            raise Exception("Test error")
    except Exception:
        pass
    
    # 验证记录未提交
    history = temp_db.get_switch_history()
    assert len(history) == 0


def test_query_switch_history_by_port(temp_db):
    """测试按端口查询切换历史"""
    new_upstream = UpstreamProxy(server="proxy.com", port=10000)
    
    # 为不同端口插入记录
    temp_db.insert_switch_history(1080, None, new_upstream, "manual", True)
    temp_db.insert_switch_history(1081, None, new_upstream, "manual", True)
    temp_db.insert_switch_history(1080, None, new_upstream, "manual", True)
    
    # 查询特定端口
    history_1080 = temp_db.get_switch_history(local_port=1080)
    assert len(history_1080) == 2
    
    history_1081 = temp_db.get_switch_history(local_port=1081)
    assert len(history_1081) == 1


def test_query_health_check_logs_by_port(temp_db):
    """测试按端口查询健康检查日志"""
    # 为不同端口插入日志
    temp_db.insert_health_check_log(1080, "proxy1.com", 10000, True, 100)
    temp_db.insert_health_check_log(1081, "proxy2.com", 10001, True, 150)
    temp_db.insert_health_check_log(1080, "proxy1.com", 10000, False, None, "Timeout")
    
    # 查询特定端口
    logs_1080 = temp_db.get_health_check_logs(local_port=1080)
    assert len(logs_1080) == 2
    
    logs_1081 = temp_db.get_health_check_logs(local_port=1081)
    assert len(logs_1081) == 1
