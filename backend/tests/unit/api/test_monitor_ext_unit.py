"""
监控扩展API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime as dt


class TestMonitorExtSchemas:
    """测试监控扩展Schema"""
    
    def test_replication_status_fields(self):
        """测试主从复制状态响应字段"""
        from app.api.monitor_ext import ReplicationStatusResponse
        
        fields = ReplicationStatusResponse.model_fields
        assert 'id' in fields
        assert 'instance_id' in fields
        assert 'slave_host' in fields
        assert 'slave_port' in fields
        assert 'slave_io_running' in fields
        assert 'slave_sql_running' in fields
        assert 'seconds_behind_master' in fields
    
    def test_lock_wait_fields(self):
        """测试锁等待响应字段"""
        from app.api.monitor_ext import LockWaitResponse
        
        fields = LockWaitResponse.model_fields
        assert 'id' in fields
        assert 'instance_id' in fields
        assert 'wait_type' in fields
        assert 'waiting_thread_id' in fields
        assert 'blocking_thread_id' in fields
        assert 'status' in fields
    
    def test_long_transaction_fields(self):
        """测试长事务响应字段"""
        from app.api.monitor_ext import LongTransactionResponse
        
        fields = LongTransactionResponse.model_fields
        assert 'id' in fields
        assert 'instance_id' in fields
        assert 'trx_thread_id' in fields
        assert 'trx_started' in fields
        assert 'trx_duration' in fields
        assert 'trx_query' in fields


class TestMonitorExtRouter:
    """测试路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.monitor_ext import router
        
        assert router.prefix == "/monitor-ext"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.monitor_ext import router
        
        assert "监控扩展" in router.tags


class TestReplicationStatusResponse:
    """测试主从复制状态响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.monitor_ext import ReplicationStatusResponse
        
        response = ReplicationStatusResponse(
            id=1,
            instance_id=1,
            instance_name="主库",
            slave_host="slave.example.com",
            slave_port=3306,
            slave_io_running="Yes",
            slave_sql_running="Yes",
            seconds_behind_master=0,
            last_io_error=None,
            last_sql_error=None,
            check_time=None
        )
        
        assert response.id == 1
        assert response.instance_name == "主库"
        assert response.slave_io_running == "Yes"
    
    def test_with_errors(self):
        """测试带错误的响应"""
        from app.api.monitor_ext import ReplicationStatusResponse
        
        response = ReplicationStatusResponse(
            id=2,
            instance_id=1,
            instance_name=None,
            slave_host=None,
            slave_port=None,
            slave_io_running="No",
            slave_sql_running=None,
            seconds_behind_master=None,
            last_io_error="Connection lost",
            last_sql_error=None,
            check_time=None
        )
        
        assert response.slave_io_running == "No"
        assert response.last_io_error == "Connection lost"


class TestLockWaitResponse:
    """测试锁等待响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.monitor_ext import LockWaitResponse
        
        now = dt.now()
        response = LockWaitResponse(
            id=1,
            instance_id=1,
            instance_name="MySQL主库",
            database_name="test_db",
            wait_type="TRANSACTION",
            waiting_thread_id=10,
            waiting_time=30,
            blocking_thread_id=20,
            blocking_sql=None,
            waiting_sql=None,
            status="active",
            created_at=now
        )
        
        assert response.id == 1
        assert response.wait_type == "TRANSACTION"
        assert response.waiting_time == 30
    
    def test_optional_fields(self):
        """测试可选字段"""
        from app.api.monitor_ext import LockWaitResponse
        
        response = LockWaitResponse(
            id=1,
            instance_id=1,
            instance_name=None,
            database_name=None,
            wait_type=None,
            waiting_thread_id=None,
            waiting_sql=None,
            waiting_time=None,
            blocking_thread_id=None,
            blocking_sql=None,
            status="resolved",
            created_at=dt.now()
        )
        
        assert response.database_name is None
        assert response.waiting_thread_id is None


class TestLongTransactionResponse:
    """测试长事务响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.monitor_ext import LongTransactionResponse
        
        now = dt.now()
        response = LongTransactionResponse(
            id=1,
            instance_id=1,
            instance_name="MySQL主库",
            database_name="production",
            trx_thread_id=15,
            trx_started=now,
            trx_duration=3600,
            trx_state="RUNNING",
            trx_query="UPDATE orders SET status='shipped' WHERE id=123",
            user="app_user",
            host="app-server-1",
            status="active",
            created_at=now
        )
        
        assert response.id == 1
        assert response.trx_duration == 3600
        assert response.user == "app_user"
    
    def test_critical_transaction(self):
        """测试严重长事务"""
        from app.api.monitor_ext import LongTransactionResponse
        
        response = LongTransactionResponse(
            id=2,
            instance_id=1,
            instance_name=None,
            database_name=None,
            trx_thread_id=25,
            trx_started=None,
            trx_duration=86400,  # 24小时
            trx_state=None,
            trx_query=None,
            user=None,
            host=None,
            status="critical",
            created_at=dt.now()
        )
        
        assert response.trx_duration == 86400


class TestMonitorExtModels:
    """测试监控扩展模型"""
    
    def test_replication_status_model(self):
        """测试复制状态模型"""
        from app.models import ReplicationStatus
        
        assert ReplicationStatus is not None
    
    def test_lock_wait_model(self):
        """测试锁等待模型"""
        from app.models import LockWait
        
        assert LockWait is not None
    
    def test_long_transaction_model(self):
        """测试长事务模型"""
        from app.models import LongTransaction
        
        assert LongTransaction is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
