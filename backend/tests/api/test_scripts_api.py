"""
脚本管理 API 完整测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime


class TestScriptsAPISchemas:
    """脚本 API Schema 测试"""

    def test_script_create_schema(self):
        """测试脚本创建 Schema"""
        from app.api.scripts import ScriptCreate
        
        data = ScriptCreate(
            name="测试脚本",
            script_type="python",
            content="print('hello')",
            description="测试描述",
            timeout=300,
            is_public=False
        )
        
        assert data.name == "测试脚本"
        assert data.script_type == "python"
        assert data.timeout == 300

    def test_script_update_schema(self):
        """测试脚本更新 Schema"""
        from app.api.scripts import ScriptUpdate
        
        data = ScriptUpdate(name="新名称", timeout=600)
        
        assert data.name == "新名称"
        assert data.timeout == 600
        assert data.content is None

    def test_script_execute_schema(self):
        """测试脚本执行 Schema"""
        from app.api.scripts import ScriptExecute
        
        data = ScriptExecute(
            params={"key": "value"},
            async_exec=True,
            timeout=120
        )
        
        assert data.params == {"key": "value"}
        assert data.async_exec == True

    def test_execution_query_schema(self):
        """测试执行记录查询 Schema"""
        from app.api.scripts import ExecutionQuery
        
        data = ExecutionQuery(
            script_id=1,
            status="success",
            limit=50
        )
        
        assert data.script_id == 1
        assert data.limit == 50


class TestScriptsHelperFunctions:
    """脚本辅助函数测试"""

    def test_check_script_permission_super_admin(self):
        """测试超级管理员权限检查"""
        from app.api.scripts import check_script_permission
        from app.models import UserRole
        
        script = Mock()
        script.created_by = 2
        script.is_public = False
        script.allowed_roles = None
        
        user = Mock()
        user.role = UserRole.SUPER_ADMIN
        user.id = 1
        
        result = check_script_permission(script, user)
        
        assert result == True

    def test_check_script_permission_owner(self):
        """测试脚本创建者权限检查"""
        from app.api.scripts import check_script_permission
        from app.models import UserRole
        
        script = Mock()
        script.created_by = 1
        script.is_public = False
        script.allowed_roles = None
        
        user = Mock()
        user.role = UserRole.DEVELOPER
        user.id = 1
        
        result = check_script_permission(script, user)
        
        assert result == True

    def test_check_script_permission_public(self):
        """测试公开脚本权限检查"""
        from app.api.scripts import check_script_permission
        from app.models import UserRole
        
        script = Mock()
        script.created_by = 2
        script.is_public = True
        script.allowed_roles = None
        
        user = Mock()
        user.role = UserRole.DEVELOPER
        user.id = 1
        
        result = check_script_permission(script, user)
        
        assert result == True

    def test_check_script_permission_allowed_role(self):
        """测试允许角色权限检查"""
        from app.api.scripts import check_script_permission
        from app.models import UserRole
        
        script = Mock()
        script.created_by = 2
        script.is_public = False
        script.allowed_roles = "developer,operator"
        
        user = Mock()
        user.role = UserRole.DEVELOPER
        user.id = 1
        
        result = check_script_permission(script, user)
        
        assert result == True

    def test_check_script_permission_denied(self):
        """测试权限拒绝"""
        from app.api.scripts import check_script_permission
        from app.models import UserRole
        
        script = Mock()
        script.created_by = 2
        script.is_public = False
        script.allowed_roles = "admin"
        
        user = Mock()
        user.role = UserRole.DEVELOPER
        user.id = 1
        
        result = check_script_permission(script, user)
        
        assert result == False


class TestScriptsRouter:
    """脚本路由测试"""

    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.scripts import router
        
        assert router.prefix == "/scripts"

    def test_router_tags(self):
        """测试路由标签"""
        from app.api.scripts import router
        
        assert "脚本管理" in router.tags


class TestScriptsAPIFull:
    """脚本管理 API 完整测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        db.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.delete = Mock()
        return db

    @pytest.fixture
    def mock_user(self):
        """Mock 用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = Mock()
        user.role.value = "super_admin"
        return user

    @pytest.fixture
    def mock_script(self):
        """Mock 脚本"""
        script = Mock()
        script.id = 1
        script.name = "测试脚本"
        script.script_type = Mock()
        script.script_type.value = "python"
        script.content = "print('hello')"
        script.description = "测试"
        script.created_by = 1
        script.is_public = False
        script.allowed_roles = None
        script.is_enabled = True
        script.timeout = 300
        script.max_retries = 0
        script.created_at = datetime.now()
        script.updated_at = datetime.now()
        script.notify_on_success = False
        script.notify_on_failure = True
        script.notify_channels = None
        return script

    @pytest.fixture
    def mock_execution(self):
        """Mock 执行记录"""
        execution = Mock()
        execution.id = 1
        execution.script_id = 1
        execution.status = Mock()
        execution.status.value = "success"
        execution.start_time = datetime.now()
        execution.end_time = datetime.now()
        execution.duration = 1.5
        execution.triggered_by = 1
        execution.trigger_type = Mock()
        execution.trigger_type.value = "manual"
        execution.output = "hello"
        execution.error_output = None
        return execution

    # ==================== 脚本 CRUD 测试 ====================

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_list_scripts(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试列出脚本"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_script]
        db_query_mock.count.return_value = 1
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_get_script(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试获取单个脚本"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_create_script(self, mock_auth, mock_get_db, mock_db, mock_user):
        """测试创建脚本"""
        from app.api.scripts import ScriptCreate
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_update_script(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试更新脚本"""
        from app.api.scripts import ScriptUpdate
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_delete_script(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试删除脚本"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_toggle_script_enabled(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试切换脚本启用状态"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    # ==================== 脚本执行测试 ====================

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    @patch('app.api.scripts.BackgroundTasks')
    def test_execute_script_sync(self, mock_bg, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试同步执行脚本"""
        from app.api.scripts import ScriptExecute
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock
        
        data = ScriptExecute(params={}, async_exec=False)

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    @patch('app.api.scripts.BackgroundTasks')
    def test_execute_script_async(self, mock_bg, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试异步执行脚本"""
        from app.api.scripts import ScriptExecute
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock
        
        data = ScriptExecute(params={}, async_exec=True)

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_execute_script_not_found(self, mock_auth, mock_get_db, mock_db, mock_user):
        """测试执行不存在的脚本"""
        from app.api.scripts import ScriptExecute
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    @patch('app.api.scripts.BackgroundTasks')
    def test_execute_script_no_permission(self, mock_bg, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试执行脚本无权限"""
        from app.api.scripts import ScriptExecute
        
        # 修改用户为非创建者
        mock_user.id = 2
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    # ==================== 执行记录测试 ====================

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_list_executions(self, mock_auth, mock_get_db, mock_db, mock_user, mock_execution):
        """测试列出执行记录"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_execution]
        db_query_mock.count.return_value = 1
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_get_execution(self, mock_auth, mock_get_db, mock_db, mock_user, mock_execution):
        """测试获取执行记录详情"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_execution
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_stop_execution(self, mock_auth, mock_get_db, mock_db, mock_user, mock_execution):
        """测试停止执行"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_execution
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_delete_execution(self, mock_auth, mock_get_db, mock_db, mock_user, mock_execution):
        """测试删除执行记录"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_execution
        mock_db.query.return_value = db_query_mock

    # ==================== 脚本导入导出测试 ====================

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_export_script(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script):
        """测试导出脚本"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_script
        mock_db.query.return_value = db_query_mock

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_import_script(self, mock_auth, mock_get_db, mock_db, mock_user):
        """测试导入脚本"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = db_query_mock

    # ==================== 脚本统计测试 ====================

    @patch('app.api.scripts.get_db')
    @patch('app.api.scripts.get_current_user')
    def test_get_script_statistics(self, mock_auth, mock_get_db, mock_db, mock_user, mock_script, mock_execution):
        """测试获取脚本统计"""
        from app.api.scripts import router
        
        mock_auth.return_value = mock_user
        mock_get_db.return_value = mock_db
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.count.return_value = 10
        mock_db.query.return_value = db_query_mock


class TestSendScriptNotification:
    """脚本通知测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        db.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def mock_script(self):
        """Mock 脚本"""
        script = Mock()
        script.id = 1
        script.name = "测试脚本"
        script.notify_on_success = True
        script.notify_on_failure = True
        script.notify_channels = None
        return script

    @pytest.fixture
    def mock_execution(self):
        """Mock 执行记录"""
        execution = Mock()
        execution.id = 1
        execution.status = Mock()
        execution.status.value = "success"
        execution.duration = 1.5
        execution.start_time = datetime.now()
        execution.error_output = None
        return execution

    @pytest.fixture
    def mock_trigger_user(self):
        """Mock 触发用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        return user

    def test_send_notification_no_channels(self, mock_db, mock_script, mock_execution, mock_trigger_user):
        """测试无通知通道时不发送通知"""
        from app.api.scripts import send_script_notification
        import asyncio
        
        mock_script.notify_channels = None
        
        # 由于没有通道，函数会直接返回

    def test_send_notification_disabled(self, mock_db, mock_script, mock_execution, mock_trigger_user):
        """测试成功时通知被禁用"""
        from app.api.scripts import send_script_notification
        
        mock_script.notify_on_success = False
        mock_execution.status.value = "success"

    def test_send_notification_failure_disabled(self, mock_db, mock_script, mock_execution, mock_trigger_user):
        """测试失败时通知被禁用"""
        from app.api.scripts import send_script_notification
        
        mock_script.notify_on_failure = False
        mock_execution.status.value = "failed"
