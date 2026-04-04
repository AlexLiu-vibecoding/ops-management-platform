"""
测试审计日志装饰器 - Audit Decorator Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import Request


class TestOperationType:
    """测试操作类型枚举"""
    
    def test_operation_type_values(self):
        """测试操作类型值"""
        from app.utils.audit_decorator import OperationType
        
        assert OperationType.INSTANCE_CREATE == "INSTANCE_CREATE"
        assert OperationType.LOGIN == "LOGIN"
        assert OperationType.OTHER == "OTHER"
    
    def test_operation_type_labels(self):
        """测试操作类型标签"""
        from app.utils.audit_decorator import OPERATION_TYPE_LABELS, OperationType
        
        assert OPERATION_TYPE_LABELS[OperationType.INSTANCE_CREATE] == "创建实例"
        assert OPERATION_TYPE_LABELS[OperationType.LOGIN] == "登录"
        assert OPERATION_TYPE_LABELS[OperationType.OTHER] == "其他操作"


class TestGetOperationLabel:
    """测试获取操作标签"""
    
    def test_get_existing_label(self):
        """测试获取存在的标签"""
        from app.utils.audit_decorator import get_operation_label
        
        label = get_operation_label("INSTANCE_CREATE")
        assert label == "创建实例"
    
    def test_get_nonexistent_label(self):
        """测试获取不存在的标签"""
        from app.utils.audit_decorator import get_operation_label
        
        label = get_operation_label("UNKNOWN_TYPE")
        assert label == "UNKNOWN_TYPE"


class TestAuditLogDecorator:
    """测试审计日志装饰器"""
    
    @pytest.fixture
    def mock_request(self):
        """创建模拟请求"""
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.query_params = "param=value"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.fixture
    def mock_user(self):
        """创建模拟用户"""
        user = MagicMock()
        user.id = 1
        user.username = "test_user"
        return user
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_async_success(self, mock_write_log, mock_request, mock_user):
        """测试异步审计日志装饰器成功"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func(request=None, current_user=None):
            return {"success": True}
        
        result = await test_func(request=mock_request, current_user=mock_user)
        
        assert result == {"success": True}
        mock_write_log.assert_called_once()
        
        # 验证审计数据
        audit_data = mock_write_log.call_args[0][0]
        assert audit_data["operation_type"] == "INSTANCE_CREATE"
        assert audit_data["user_id"] == 1
        assert audit_data["username"] == "test_user"
        assert audit_data["request_method"] == "POST"
        assert audit_data["response_code"] == 200
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_async_exception(self, mock_write_log, mock_request, mock_user):
        """测试异步审计日志装饰器异常"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func(request=None, current_user=None):
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await test_func(request=mock_request, current_user=mock_user)
        
        mock_write_log.assert_called_once()
        audit_data = mock_write_log.call_args[0][0]
        assert audit_data["response_code"] == 500
        assert "Test error" in audit_data["response_message"]
    
    @patch('app.utils.audit_decorator.write_audit_log_sync')
    def test_audit_log_sync_success(self, mock_write_log, mock_request, mock_user):
        """测试同步审计日志装饰器成功"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        def test_func(request=None, current_user=None):
            return {"success": True}
        
        result = test_func(request=mock_request, current_user=mock_user)
        
        assert result == {"success": True}
        mock_write_log.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_without_user(self, mock_write_log, mock_request):
        """测试没有用户的审计日志"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        @audit_log(operation_type=OperationType.LOGIN)
        async def test_func(request=None):
            return {"success": True}
        
        await test_func(request=mock_request)
        
        audit_data = mock_write_log.call_args[0][0]
        assert audit_data["user_id"] is None
        assert audit_data["username"] is None
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_without_request(self, mock_write_log, mock_user):
        """测试没有请求的审计日志"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func(current_user=None):
            return {"success": True}
        
        await test_func(current_user=mock_user)
        
        audit_data = mock_write_log.call_args[0][0]
        assert audit_data["request_method"] is None
        assert audit_data["request_path"] is None
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_with_custom_getters(self, mock_write_log, mock_request, mock_user):
        """测试带自定义获取函数的审计日志"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        def get_instance_id(*args, **kwargs):
            return 100
        
        def get_detail(*args, **kwargs):
            return "Custom detail"
        
        @audit_log(
            operation_type=OperationType.INSTANCE_CREATE,
            get_instance_id=get_instance_id,
            get_detail=get_detail
        )
        async def test_func(request=None, current_user=None):
            return {"success": True}
        
        await test_func(request=mock_request, current_user=mock_user)
        
        audit_data = mock_write_log.call_args[0][0]
        assert audit_data["instance_id"] == 100
        assert audit_data["operation_detail"] == "Custom detail"
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_custom_getter_exception(self, mock_write_log, mock_request, mock_user):
        """测试自定义获取函数异常处理"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        def get_instance_id(*args, **kwargs):
            raise ValueError("Getter error")
        
        @audit_log(
            operation_type=OperationType.INSTANCE_CREATE,
            get_instance_id=get_instance_id
        )
        async def test_func(request=None, current_user=None):
            return {"success": True}
        
        await test_func(request=mock_request, current_user=mock_user)
        
        # 即使 getter 失败，审计日志也应该被写入
        mock_write_log.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_get_params(self, mock_write_log, mock_user):
        """测试获取请求参数"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        # Mock body
        async def mock_body():
            return b'{"name": "test"}'
        request.body = mock_body
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func(request=None, current_user=None):
            return {"success": True}
        
        await test_func(request=request, current_user=mock_user)
        
        audit_data = mock_write_log.call_args[0][0]
        assert '{"name": "test"}' in audit_data["request_params"]
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_get_query_params(self, mock_write_log, mock_user):
        """测试获取 GET 请求查询参数"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        request.query_params = "page=1&size=10"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func(request=None, current_user=None):
            return {"success": True}
        
        await test_func(request=request, current_user=mock_user)
        
        audit_data = mock_write_log.call_args[0][0]
        assert "page=1" in audit_data["request_params"]


class TestWriteAuditLog:
    """测试写入审计日志"""
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.SessionLocal')
    async def test_write_audit_log_success(self, mock_session_class):
        """测试成功写入审计日志"""
        from app.utils.audit_decorator import write_audit_log
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        data = {
            "operation_type": "TEST",
            "user_id": 1,
            "username": "test",
            "response_code": 200
        }
        
        await write_audit_log(data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.SessionLocal')
    async def test_write_audit_log_exception(self, mock_session_class):
        """测试写入审计日志异常处理"""
        from app.utils.audit_decorator import write_audit_log
        
        mock_session_class.side_effect = Exception("Database error")
        
        data = {"operation_type": "TEST"}
        
        # 不应该抛出异常
        await write_audit_log(data)
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.SessionLocal')
    async def test_write_audit_log_db_exception(self, mock_session_class):
        """测试数据库操作异常"""
        from app.utils.audit_decorator import write_audit_log
        
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("Insert error")
        mock_session_class.return_value = mock_db
        
        data = {"operation_type": "TEST"}
        
        # 不应该抛出异常
        await write_audit_log(data)


class TestWriteAuditLogSync:
    """测试同步写入审计日志"""
    
    @patch('app.utils.audit_decorator.SessionLocal')
    def test_write_audit_log_sync_success(self, mock_session_class):
        """测试成功同步写入审计日志"""
        from app.utils.audit_decorator import write_audit_log_sync
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        data = {
            "operation_type": "TEST",
            "user_id": 1,
            "username": "test",
            "response_code": 200
        }
        
        write_audit_log_sync(data)
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('app.utils.audit_decorator.SessionLocal')
    def test_write_audit_log_sync_exception(self, mock_session_class):
        """测试同步写入异常处理"""
        from app.utils.audit_decorator import write_audit_log_sync
        
        mock_session_class.side_effect = Exception("Database error")
        
        data = {"operation_type": "TEST"}
        
        # 不应该抛出异常
        write_audit_log_sync(data)


class TestGetClientIP:
    """测试获取客户端 IP"""
    
    def test_get_ip_from_x_forwarded_for(self):
        """测试从 X-Forwarded-For 获取 IP"""
        from app.utils.audit_decorator import get_client_ip
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_get_ip_from_x_real_ip(self):
        """测试从 X-Real-IP 获取 IP"""
        from app.utils.audit_decorator import get_client_ip
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "192.168.1.2"}
        request.client = None
        
        ip = get_client_ip(request)
        assert ip == "192.168.1.2"
    
    def test_get_ip_from_client(self):
        """测试从 request.client 获取 IP"""
        from app.utils.audit_decorator import get_client_ip
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        ip = get_client_ip(request)
        assert ip == "127.0.0.1"
    
    def test_get_ip_unknown(self):
        """测试未知 IP"""
        from app.utils.audit_decorator import get_client_ip
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None
        
        ip = get_client_ip(request)
        assert ip == "unknown"


class TestAuditLogger:
    """测试审计日志记录器"""
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_logger_log(self, mock_write_log):
        """测试审计日志记录器"""
        from app.utils.audit_decorator import AuditLogger, OperationType
        
        user = MagicMock()
        user.id = 1
        user.username = "test_user"
        
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/test"
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        
        await AuditLogger.log(
            operation_type=OperationType.INSTANCE_CREATE,
            user=user,
            instance_id=100,
            instance_name="test_instance",
            detail="Test operation",
            request=request,
            response_code=201
        )
        
        mock_write_log.assert_called_once()
        data = mock_write_log.call_args[0][0]
        assert data["operation_type"] == "INSTANCE_CREATE"
        assert data["user_id"] == 1
        assert data["instance_id"] == 100
        assert data["response_code"] == 201
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_logger_log_minimal(self, mock_write_log):
        """测试最小化审计日志记录"""
        from app.utils.audit_decorator import AuditLogger, OperationType
        
        await AuditLogger.log(operation_type=OperationType.OTHER)
        
        mock_write_log.assert_called_once()
        data = mock_write_log.call_args[0][0]
        assert data["operation_type"] == "OTHER"
        assert data["user_id"] is None
        assert data["response_code"] == 200


class TestAuditDecoratorWithoutExtractUser:
    """测试不提取用户的审计装饰器"""
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_audit_log_no_extract_user(self, mock_write_log):
        """测试不提取用户的装饰器"""
        from app.utils.audit_decorator import audit_log, OperationType
        
        user = MagicMock()
        user.id = 1
        user.username = "test_user"
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE, extract_user=False)
        async def test_func(current_user=None):
            return {"success": True}
        
        await test_func(current_user=user)
        
        audit_data = mock_write_log.call_args[0][0]
        # extract_user=False，不应该提取用户信息
        assert audit_data.get("user_id") is None


class TestExecutionTime:
    """测试执行时间记录"""
    
    @pytest.mark.asyncio
    @patch('app.utils.audit_decorator.write_audit_log')
    async def test_execution_time_recorded(self, mock_write_log):
        """测试执行时间被记录"""
        from app.utils.audit_decorator import audit_log, OperationType
        import time
        
        @audit_log(operation_type=OperationType.INSTANCE_CREATE)
        async def test_func():
            time.sleep(0.01)  # 10ms
            return {"success": True}
        
        await test_func()
        
        audit_data = mock_write_log.call_args[0][0]
        assert "execution_time" in audit_data
        assert audit_data["execution_time"] >= 0  # 应该大于等于0
