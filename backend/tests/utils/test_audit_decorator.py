"""
测试 audit_decorator.py 模块

功能点：
1. OperationType 枚举和标签映射
2. audit_log 装饰器（异步和同步）
3. write_audit_log 和 write_audit_log_sync
4. get_client_ip
5. AuditLogger 类

测试策略：
- 使用 pytest 和 pytest-asyncio
- 使用 fixtures 提供 mock 对象
- 测试正常路径和异常场景
- 验证数据库写入逻辑
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.utils.audit_decorator import (
    OperationType,
    get_operation_label,
    audit_log,
    write_audit_log,
    write_audit_log_sync,
    get_client_ip,
    AuditLogger,
)
from app.models import AuditLog, User
from fastapi import Request


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Mock 数据库 Session"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_user():
    """Mock 用户对象"""
    user = Mock(spec=User)
    user.id = 1
    user.username = "testuser"
    return user


@pytest.fixture
def mock_request():
    """Mock FastAPI Request 对象"""
    request = Mock(spec=Request)
    request.method = "POST"
    request.url.path = "/api/v1/instances"
    request.query_params = {}
    request.headers = {}
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.body = AsyncMock(return_value=b'{"name":"test"}')
    return request


@pytest.fixture
def mock_request_with_proxy():
    """Mock 带代理头的 Request 对象"""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/api/v1/instances/1"
    request.query_params = {"id": "1"}
    request.headers = {
        "X-Forwarded-For": "10.0.0.1, 10.0.0.2",
        "X-Real-IP": "10.0.0.1",
    }
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.body = AsyncMock(return_value=b"")
    return request


@pytest.fixture
def mock_request_no_client():
    """Mock 没有 client 的 Request 对象"""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/api/v1/instances"
    request.query_params = {"id": "1"}
    request.headers = {}
    request.client = None
    request.body = AsyncMock(return_value=b"")
    return request


# =============================================================================
# 1. OperationType 枚举和标签映射测试
# =============================================================================

class TestOperationType:
    """测试 OperationType 枚举"""

    def test_operation_type_values(self):
        """测试操作类型枚举值"""
        # 实例管理
        assert OperationType.INSTANCE_CREATE == "INSTANCE_CREATE"
        assert OperationType.INSTANCE_UPDATE == "INSTANCE_UPDATE"
        assert OperationType.INSTANCE_DELETE == "INSTANCE_DELETE"
        assert OperationType.INSTANCE_TEST_CONNECTION == "INSTANCE_TEST_CONNECTION"

        # 变更管理
        assert OperationType.DB_CHANGE_CREATE == "DB_CHANGE_CREATE"
        assert OperationType.DB_CHANGE_SUBMIT == "DB_CHANGE_SUBMIT"

        # 审批管理
        assert OperationType.APPROVAL_APPROVE == "APPROVAL_APPROVE"
        assert OperationType.APPROVAL_EXECUTE == "APPROVAL_EXECUTE"

        # 监控管理
        assert OperationType.MONITOR_SWITCH_ENABLE == "MONITOR_SWITCH_ENABLE"
        assert OperationType.ALERT_ACKNOWLEDGE == "ALERT_ACKNOWLEDGE"

        # 脚本管理
        assert OperationType.SCRIPT_CREATE == "SCRIPT_CREATE"
        assert OperationType.SCRIPT_EXECUTE == "SCRIPT_EXECUTE"

        # 定时任务
        assert OperationType.SCHEDULE_CREATE == "SCHEDULE_CREATE"
        assert OperationType.SCHEDULE_ENABLE == "SCHEDULE_ENABLE"

        # 用户管理
        assert OperationType.USER_CREATE == "USER_CREATE"
        assert OperationType.USER_PASSWORD_RESET == "USER_PASSWORD_RESET"

        # 角色管理
        assert OperationType.ROLE_CREATE == "ROLE_CREATE"
        assert OperationType.ROLE_ASSIGN == "ROLE_ASSIGN"

        # 系统配置
        assert OperationType.SYSTEM_CONFIG_UPDATE == "SYSTEM_CONFIG_UPDATE"

        # 数据操作
        assert OperationType.DATA_EXPORT == "DATA_EXPORT"
        assert OperationType.DATA_BACKUP == "DATA_BACKUP"

        # 登录
        assert OperationType.LOGIN == "LOGIN"
        assert OperationType.LOGIN_FAILED == "LOGIN_FAILED"

        # 其他
        assert OperationType.OTHER == "OTHER"

    def test_get_operation_label_valid(self):
        """测试获取有效的操作类型标签"""
        assert get_operation_label("INSTANCE_CREATE") == "创建实例"
        assert get_operation_label("INSTANCE_UPDATE") == "更新实例"
        assert get_operation_label("INSTANCE_DELETE") == "删除实例"
        assert get_operation_label("DB_CHANGE_CREATE") == "创建变更申请"
        assert get_operation_label("APPROVAL_APPROVE") == "审批通过"
        assert get_operation_label("MONITOR_SWITCH_ENABLE") == "启用监控"
        assert get_operation_label("ALERT_ACKNOWLEDGE") == "确认告警"
        assert get_operation_label("SCRIPT_CREATE") == "创建脚本"
        assert get_operation_label("SCHEDULE_CREATE") == "创建定时任务"
        assert get_operation_label("USER_CREATE") == "创建用户"
        assert get_operation_label("LOGIN") == "登录"

    def test_get_operation_label_invalid(self):
        """测试获取无效的操作类型标签（应该抛出异常）"""
        # 无效的操作类型会抛出 ValueError
        with pytest.raises(ValueError, match="is not a valid OperationType"):
            get_operation_label("INVALID_TYPE")

        with pytest.raises(ValueError, match="is not a valid OperationType"):
            get_operation_label("UNKNOWN")


# =============================================================================
# 2. audit_log 装饰器 - 异步函数测试
# =============================================================================

class TestAuditLogDecoratorAsync:
    """测试 audit_log 装饰器 - 异步函数"""

    @pytest.mark.asyncio
    async def test_audit_log_basic_async(self, mock_request, mock_user, mock_db):
        """测试基本的异步审计日志装饰器"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.INSTANCE_CREATE)
            async def create_instance(request: Request, current_user: User):
                return {"id": 1, "name": "test"}

            result = await create_instance(request=mock_request, current_user=mock_user)
            assert result == {"id": 1, "name": "test"}

            # 验证数据库写入
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

            # 验证写入的数据
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "INSTANCE_CREATE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.username == "testuser"
            assert audit_log_obj.request_method == "POST"
            assert audit_log_obj.request_path == "/api/v1/instances"
            assert audit_log_obj.request_ip == "192.168.1.100"
            assert audit_log_obj.response_code == 200
            assert audit_log_obj.response_message == "操作成功"

    @pytest.mark.asyncio
    async def test_audit_log_with_custom_fields(self, mock_request, mock_user, mock_db):
        """测试带自定义字段的审计日志"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(
                operation_type=OperationType.INSTANCE_UPDATE,
                get_instance_id=lambda *args, **kwargs: 42,
                get_instance_name=lambda *args, **kwargs: "test-instance",
                get_environment_id=lambda *args, **kwargs: 1,
                get_environment_name=lambda *args, **kwargs: "production",
                get_detail=lambda *args, **kwargs: "更新实例配置",
            )
            async def update_instance(request: Request, current_user: User):
                return {"id": 42, "name": "test-instance"}

            result = await update_instance(request=mock_request, current_user=mock_user)
            assert result == {"id": 42, "name": "test-instance"}

            # 验证自定义字段
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.instance_id == 42
            assert audit_log_obj.instance_name == "test-instance"
            assert audit_log_obj.environment_id == 1
            assert audit_log_obj.environment_name == "production"
            assert audit_log_obj.operation_detail == "更新实例配置"

    @pytest.mark.asyncio
    async def test_audit_log_with_exception(self, mock_request, mock_user, mock_db):
        """测试异常情况下的审计日志"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.INSTANCE_DELETE)
            async def delete_instance(request: Request, current_user: User):
                raise ValueError("实例不存在")

            with pytest.raises(ValueError, match="实例不存在"):
                await delete_instance(request=mock_request, current_user=mock_user)

            # 验证异常信息被记录
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.response_code == 500
            assert "实例不存在" in audit_log_obj.response_message
            assert audit_log_obj.response_message == "实例不存在"

    @pytest.mark.asyncio
    async def test_audit_log_no_extract_user(self, mock_request, mock_db):
        """测试不提取用户信息"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(
                operation_type=OperationType.LOGIN,
                extract_user=False
            )
            async def public_login(request: Request):
                return {"success": True}

            result = await public_login(request=mock_request)
            assert result == {"success": True}

            # 验证用户信息未提取
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.user_id is None
            assert audit_log_obj.username is None

    @pytest.mark.asyncio
    async def test_audit_log_no_user_provided(self, mock_request, mock_db):
        """测试未提供用户对象"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.LOGIN_FAILED)
            async def failed_login(request: Request):
                return {"success": False}

            result = await failed_login(request=mock_request)
            assert result == {"success": False}

            # 验证用户信息为 None
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.user_id is None
            assert audit_log_obj.username is None

    @pytest.mark.asyncio
    async def test_audit_log_no_request(self, mock_user, mock_db):
        """测试未提供 Request 对象"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.SCRIPT_EXECUTE)
            async def execute_script(current_user: User):
                return {"script_id": 1}

            result = await execute_script(current_user=mock_user)
            assert result == {"script_id": 1}

            # 验证请求信息为 None
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.request_method is None
            assert audit_log_obj.request_path is None
            assert audit_log_obj.request_ip is None
            # 但用户信息应该被提取
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.username == "testuser"

    @pytest.mark.asyncio
    async def test_audit_log_custom_field_exception(self, mock_request, mock_user, mock_db):
        """测试自定义字段提取异常"""
        def failing_extractor(*args, **kwargs):
            raise Exception("提取失败")

        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(
                operation_type=OperationType.INSTANCE_UPDATE,
                get_instance_id=failing_extractor,
            )
            async def update_instance(request: Request, current_user: User):
                return {"id": 1}

            result = await update_instance(request=mock_request, current_user=mock_user)
            assert result == {"id": 1}

            # 验证函数仍然执行成功，自定义字段为 None
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.instance_id is None

    @pytest.mark.asyncio
    async def test_audit_log_execution_time(self, mock_request, mock_user, mock_db):
        """测试执行时间记录"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.SCRIPT_EXECUTE)
            async def long_operation(request: Request, current_user: User):
                import asyncio
                await asyncio.sleep(0.01)
                return {"done": True}

            result = await long_operation(request=mock_request, current_user=mock_user)
            assert result == {"done": True}

            # 验证执行时间被记录（应该 > 0）
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.execution_time > 0
            # 应该在合理范围内（> 10ms）
            assert audit_log_obj.execution_time >= 10

    @pytest.mark.asyncio
    async def test_audit_log_request_params_post(self, mock_request, mock_db):
        """测试 POST 请求参数提取"""
        mock_request.body = AsyncMock(return_value=b'{"name":"test","value":123}')

        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.DB_CHANGE_CREATE)
            async def create_change(request: Request):
                return {"id": 1}

            result = await create_change(request=mock_request)
            assert result == {"id": 1}

            # 验证请求参数被提取
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.request_params == '{"name":"test","value":123}'

    @pytest.mark.asyncio
    async def test_audit_log_request_params_get(self, mock_request_with_proxy, mock_db):
        """测试 GET 请求参数提取"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.INSTANCE_TEST_CONNECTION)
            async def test_connection(request: Request):
                return {"connected": True}

            result = await test_connection(request=mock_request_with_proxy)
            assert result == {"connected": True}

            # 验证请求参数被提取（QueryParams 的 str 表示是字典格式）
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.request_params == "{'id': '1'}"

    @pytest.mark.asyncio
    async def test_audit_log_request_params_limit(self, mock_request, mock_db):
        """测试请求参数长度限制"""
        # 超过 2000 字符的请求体
        long_body = b'{"data":"' + (b"x" * 3000) + b'"}'
        mock_request.body = AsyncMock(return_value=long_body)

        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.DATA_IMPORT)
            async def import_data(request: Request):
                return {"imported": True}

            result = await import_data(request=mock_request)
            assert result == {"imported": True}

            # 验证请求参数被截断到 2000 字符
            audit_log_obj = mock_db.add.call_args[0][0]
            assert len(audit_log_obj.request_params) <= 2000


# =============================================================================
# 3. audit_log 装饰器 - 同步函数测试
# =============================================================================

class TestAuditLogDecoratorSync:
    """测试 audit_log 装饰器 - 同步函数"""

    def test_audit_log_basic_sync(self, mock_request, mock_user, mock_db):
        """测试基本的同步审计日志装饰器"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.INSTANCE_CREATE)
            def create_instance(request: Request, current_user: User):
                return {"id": 1, "name": "test"}

            result = create_instance(request=mock_request, current_user=mock_user)
            assert result == {"id": 1, "name": "test"}

            # 验证数据库写入
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

            # 验证写入的数据
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "INSTANCE_CREATE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.username == "testuser"
            assert audit_log_obj.response_code == 200

    def test_audit_log_sync_with_exception(self, mock_request, mock_user, mock_db):
        """测试同步函数异常情况"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.INSTANCE_DELETE)
            def delete_instance(request: Request, current_user: User):
                raise RuntimeError("删除失败")

            with pytest.raises(RuntimeError, match="删除失败"):
                delete_instance(request=mock_request, current_user=mock_user)

            # 验证异常信息被记录
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.response_code == 500
            assert audit_log_obj.response_message == "删除失败"

    def test_audit_log_sync_custom_fields_not_supported(self, mock_request, mock_user, mock_db):
        """测试同步装饰器不支持自定义字段提取（已知限制）"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(
                operation_type=OperationType.MONITOR_SWITCH_ENABLE,
                get_instance_id=lambda *args, **kwargs: 99,
                get_instance_name=lambda *args, **kwargs: "monitor-server",
                get_detail=lambda *args, **kwargs: "启用监控开关",
            )
            def enable_monitor(request: Request, current_user: User):
                return {"enabled": True}

            result = enable_monitor(request=mock_request, current_user=mock_user)
            assert result == {"enabled": True}

            # 验证自定义字段未被提取（同步装饰器的已知限制）
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.instance_id is None  # 同步装饰器不支持
            assert audit_log_obj.instance_name is None  # 同步装饰器不支持
            assert audit_log_obj.operation_detail is None  # 同步装饰器不支持

    def test_audit_log_sync_no_user(self, mock_request, mock_db):
        """测试同步函数未提供用户"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.LOGOUT)
            def logout(request: Request):
                return {"logged_out": True}

            result = logout(request=mock_request)
            assert result == {"logged_out": True}

            # 验证用户信息为 None
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.user_id is None
            assert audit_log_obj.username is None

    def test_audit_log_sync_execution_time(self, mock_request, mock_user, mock_db):
        """测试同步函数执行时间记录"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            @audit_log(operation_type=OperationType.SCRIPT_EXECUTE)
            def slow_operation(request: Request, current_user: User):
                import time
                time.sleep(0.01)
                return {"done": True}

            result = slow_operation(request=mock_request, current_user=mock_user)
            assert result == {"done": True}

            # 验证执行时间被记录
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.execution_time > 0
            assert audit_log_obj.execution_time >= 10


# =============================================================================
# 4. write_audit_log 和 write_audit_log_sync 测试
# =============================================================================

class TestWriteAuditLog:
    """测试审计日志写入函数"""

    @pytest.mark.asyncio
    async def test_write_audit_log_success(self, mock_db):
        """测试成功写入异步审计日志"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            data = {
                "operation_type": "INSTANCE_CREATE",
                "user_id": 1,
                "username": "testuser",
                "instance_id": 42,
                "instance_name": "test-instance",
                "environment_id": 1,
                "environment_name": "production",
                "operation_detail": "创建新实例",
                "request_ip": "192.168.1.100",
                "request_method": "POST",
                "request_path": "/api/v1/instances",
                "request_params": '{"name":"test"}',
                "response_code": 200,
                "response_message": "操作成功",
                "execution_time": 123.45,
            }

            await write_audit_log(data)

            # 验证数据库操作
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

            # 验证写入的对象
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "INSTANCE_CREATE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.instance_id == 42
            assert audit_log_obj.response_code == 200

    @pytest.mark.asyncio
    async def test_write_audit_log_minimal_data(self, mock_db):
        """测试最小数据写入"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            data = {
                "operation_type": "LOGIN",
                "response_code": 200,
                "response_message": "登录成功",
            }

            await write_audit_log(data)

            # 验证数据库操作
            mock_db.add.assert_called_once()

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "LOGIN"
            assert audit_log_obj.user_id is None
            assert audit_log_obj.response_code == 200

    @pytest.mark.asyncio
    async def test_write_audit_log_db_exception(self, mock_db):
        """测试数据库异常处理"""
        mock_db.commit.side_effect = Exception("数据库错误")

        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            data = {
                "operation_type": "INSTANCE_CREATE",
                "response_code": 200,
                "response_message": "操作成功",
            }

            # 应该不抛出异常，只记录错误
            await write_audit_log(data)

            # 验证 close 仍然被调用
            mock_db.close.assert_called_once()

    def test_write_audit_log_sync_success(self, mock_db):
        """测试成功写入同步审计日志"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            data = {
                "operation_type": "USER_CREATE",
                "user_id": 2,
                "username": "admin",
                "operation_detail": "创建管理员账户",
                "response_code": 201,
                "response_message": "创建成功",
                "execution_time": 45.67,
            }

            write_audit_log_sync(data)

            # 验证数据库操作
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "USER_CREATE"
            assert audit_log_obj.user_id == 2
            assert audit_log_obj.response_code == 201

    def test_write_audit_log_sync_exception(self, mock_db):
        """测试同步写入异常处理"""
        mock_db.add.side_effect = RuntimeError("添加失败")

        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            data = {
                "operation_type": "OTHER",
                "response_code": 200,
                "response_message": "操作成功",
            }

            # 应该不抛出异常
            write_audit_log_sync(data)

            # 验证 close 仍然被调用
            mock_db.close.assert_called_once()


# =============================================================================
# 5. get_client_ip 测试
# =============================================================================

class TestGetClientIP:
    """测试获取客户端 IP 功能"""

    def test_get_client_ip_with_x_forwarded_for(self, mock_request_with_proxy):
        """测试从 X-Forwarded-For 获取 IP"""
        ip = get_client_ip(mock_request_with_proxy)
        # 应该取第一个 IP
        assert ip == "10.0.0.1"

    def test_get_client_ip_with_x_forwarded_for_multiple(self):
        """测试 X-Forwarded-For 多个 IP"""
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": " 10.0.0.1 , 10.0.0.2 , 10.0.0.3  ",
        }
        request.client = Mock(host="192.168.1.1")

        ip = get_client_ip(request)
        # 应该取第一个 IP，并去除空格
        assert ip == "10.0.0.1"

    def test_get_client_ip_with_x_real_ip(self):
        """测试从 X-Real-IP 获取 IP"""
        request = Mock(spec=Request)
        request.headers = {
            "X-Real-IP": "10.0.0.5",
        }
        request.client = Mock(host="192.168.1.1")

        ip = get_client_ip(request)
        assert ip == "10.0.0.5"

    def test_get_client_ip_from_client_host(self, mock_request):
        """测试从 client.host 获取 IP"""
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_unknown(self, mock_request_no_client):
        """测试无法获取 IP 的情况"""
        ip = get_client_ip(mock_request_no_client)
        assert ip == "unknown"

    def test_get_client_ip_x_forwarded_for_priority(self):
        """测试 X-Forwarded-For 优先级高于 X-Real-IP"""
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "10.0.0.1",
            "X-Real-IP": "10.0.0.5",
        }
        request.client = Mock(host="192.168.1.1")

        ip = get_client_ip(request)
        # 应该使用 X-Forwarded-For
        assert ip == "10.0.0.1"

    def test_get_client_ip_empty_x_forwarded_for(self):
        """测试空的 X-Forwarded-For"""
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "",
            "X-Real-IP": "10.0.0.5",
        }
        request.client = Mock(host="192.168.1.1")

        ip = get_client_ip(request)
        # 应该使用 X-Real-IP
        assert ip == "10.0.0.5"


# =============================================================================
# 6. AuditLogger 类测试
# =============================================================================

class TestAuditLogger:
    """测试 AuditLogger 类"""

    @pytest.mark.asyncio
    async def test_audit_logger_log_basic(self, mock_user, mock_request, mock_db):
        """测试 AuditLogger.log 基本功能"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            await AuditLogger.log(
                operation_type=OperationType.SCRIPT_EXECUTE,
                user=mock_user,
                request=mock_request,
                detail="执行备份脚本",
                response_code=200,
                response_message="执行成功",
            )

            # 验证数据库写入
            mock_db.add.assert_called_once()

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "SCRIPT_EXECUTE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.username == "testuser"
            assert audit_log_obj.operation_detail == "执行备份脚本"
            assert audit_log_obj.response_code == 200

    @pytest.mark.asyncio
    async def test_audit_logger_log_full_params(self, mock_user, mock_request, mock_db):
        """测试 AuditLogger.log 完整参数"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            await AuditLogger.log(
                operation_type=OperationType.DB_CHANGE_CREATE,
                user=mock_user,
                instance_id=100,
                instance_name="prod-db",
                environment_id=2,
                environment_name="staging",
                detail="创建数据库变更",
                request=mock_request,
                response_code=201,
                response_message="创建成功",
            )

            # 验证所有字段
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.username == "testuser"
            assert audit_log_obj.instance_id == 100
            assert audit_log_obj.instance_name == "prod-db"
            assert audit_log_obj.environment_id == 2
            assert audit_log_obj.environment_name == "staging"
            assert audit_log_obj.operation_detail == "创建数据库变更"
            assert audit_log_obj.request_method == "POST"
            assert audit_log_obj.request_path == "/api/v1/instances"
            assert audit_log_obj.request_ip == "192.168.1.100"
            assert audit_log_obj.response_code == 201

    @pytest.mark.asyncio
    async def test_audit_logger_log_minimal_params(self, mock_db):
        """测试 AuditLogger.log 最小参数"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            await AuditLogger.log(
                operation_type=OperationType.LOGIN_FAILED,
            )

            # 验证最小字段
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "LOGIN_FAILED"
            assert audit_log_obj.response_code == 200
            assert audit_log_obj.response_message == "操作成功"
            # 其他字段应该为 None
            assert audit_log_obj.user_id is None
            assert audit_log_obj.username is None

    @pytest.mark.asyncio
    async def test_audit_logger_log_with_error(self, mock_user, mock_db):
        """测试 AuditLogger.log 记录错误"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            await AuditLogger.log(
                operation_type=OperationType.SCRIPT_EXECUTE,
                user=mock_user,
                detail="脚本执行失败",
                response_code=500,
                response_message="连接超时",
            )

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.response_code == 500
            assert audit_log_obj.response_message == "连接超时"

    def test_audit_logger_log_sync_basic(self, mock_user, mock_request, mock_db):
        """测试 AuditLogger.log_sync 基本功能"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            AuditLogger.log_sync(
                operation_type=OperationType.USER_CREATE,
                user=mock_user,
                request=mock_request,
                detail="创建用户 account1",
                response_code=201,
            )

            # 验证数据库写入
            mock_db.add.assert_called_once()

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "USER_CREATE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.operation_detail == "创建用户 account1"
            assert audit_log_obj.response_code == 201

    def test_audit_logger_log_sync_no_request(self, mock_user, mock_db):
        """测试 AuditLogger.log_sync 无 Request"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            AuditLogger.log_sync(
                operation_type=OperationType.SYSTEM_CONFIG_UPDATE,
                user=mock_user,
                detail="更新配置文件",
            )

            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "SYSTEM_CONFIG_UPDATE"
            # 请求相关字段应该为 None
            assert audit_log_obj.request_method is None
            assert audit_log_obj.request_path is None
            assert audit_log_obj.request_ip is None

    def test_audit_logger_log_sync_full_params(self, mock_user, mock_request, mock_db):
        """测试 AuditLogger.log_sync 完整参数"""
        with patch('app.utils.audit_decorator.SessionLocal', return_value=mock_db):
            AuditLogger.log_sync(
                operation_type=OperationType.MONITOR_SWITCH_ENABLE,
                user=mock_user,
                instance_id=50,
                instance_name="app-server-01",
                environment_id=1,
                environment_name="production",
                detail="启用性能监控",
                request=mock_request,
                response_code=200,
                response_message="监控已启用",
            )

            # 验证所有字段
            audit_log_obj = mock_db.add.call_args[0][0]
            assert audit_log_obj.operation_type == "MONITOR_SWITCH_ENABLE"
            assert audit_log_obj.user_id == 1
            assert audit_log_obj.instance_id == 50
            assert audit_log_obj.instance_name == "app-server-01"
            assert audit_log_obj.environment_id == 1
            assert audit_log_obj.environment_name == "production"
            assert audit_log_obj.operation_detail == "启用性能监控"
            assert audit_log_obj.request_method == "POST"
            assert audit_log_obj.request_path == "/api/v1/instances"
            assert audit_log_obj.request_ip == "192.168.1.100"
            assert audit_log_obj.response_code == 200
            assert audit_log_obj.response_message == "监控已启用"
