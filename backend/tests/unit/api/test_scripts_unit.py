"""
脚本管理API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestScriptSchemas:
    """测试脚本Schema"""
    
    def test_script_create_fields(self):
        """测试创建脚本Schema字段"""
        from app.api.scripts import ScriptCreate
        
        fields = ScriptCreate.model_fields
        assert 'name' in fields
        assert 'script_type' in fields
        assert 'content' in fields
        assert 'description' in fields
        assert 'timeout' in fields
        assert 'max_retries' in fields
        assert 'is_public' in fields
        assert 'notify_on_success' in fields
        assert 'notify_on_failure' in fields
    
    def test_script_create_defaults(self):
        """测试创建脚本默认值"""
        from app.api.scripts import ScriptCreate
        
        # script_type默认值
        assert ScriptCreate.model_fields['script_type'].default == "python"
        # is_public默认值
        assert ScriptCreate.model_fields['is_public'].default is False
        # notify_on_success默认值
        assert ScriptCreate.model_fields['notify_on_success'].default is False
        # notify_on_failure默认值
        assert ScriptCreate.model_fields['notify_on_failure'].default is True
    
    def test_script_update_fields(self):
        """测试更新脚本Schema字段"""
        from app.api.scripts import ScriptUpdate
        
        fields = ScriptUpdate.model_fields
        assert 'name' in fields
        assert 'content' in fields
        assert 'description' in fields
        assert 'is_enabled' in fields
    
    def test_script_execute_fields(self):
        """测试执行脚本Schema字段"""
        from app.api.scripts import ScriptExecute
        
        fields = ScriptExecute.model_fields
        assert 'params' in fields
        assert 'async_exec' in fields
        assert 'timeout' in fields
    
    def test_execution_query_fields(self):
        """测试执行查询Schema字段"""
        from app.api.scripts import ExecutionQuery
        
        fields = ExecutionQuery.model_fields
        assert 'script_id' in fields
        assert 'status' in fields
        assert 'trigger_type' in fields
        assert 'skip' in fields
        assert 'limit' in fields


class TestScriptRouter:
    """测试脚本路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.scripts import router
        
        assert router.prefix == "/scripts"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.scripts import router
        
        assert "脚本管理" in router.tags


class TestScriptModels:
    """测试脚本模型枚举"""
    
    def test_script_type_values(self):
        """测试脚本类型枚举"""
        from app.models import ScriptType
        
        assert hasattr(ScriptType, 'PYTHON')
        assert hasattr(ScriptType, 'BASH')
        assert hasattr(ScriptType, 'SQL')
    
    def test_execution_status_values(self):
        """测试执行状态枚举"""
        from app.models import ExecutionStatus
        
        assert hasattr(ExecutionStatus, 'PENDING')
        assert hasattr(ExecutionStatus, 'RUNNING')
        assert hasattr(ExecutionStatus, 'SUCCESS')
        assert hasattr(ExecutionStatus, 'FAILED')
    
    def test_trigger_type_values(self):
        """测试触发类型枚举"""
        from app.models import TriggerType
        
        assert hasattr(TriggerType, 'MANUAL')
        assert hasattr(TriggerType, 'SCHEDULED')
        assert hasattr(TriggerType, 'API')


class TestScriptPermission:
    """测试脚本权限检查"""
    
    def test_super_admin_permission(self):
        """测试超级管理员权限"""
        from app.api.scripts import check_script_permission
        from app.models import User, UserRole
        
        mock_script = MagicMock()
        mock_script.created_by = 1
        
        mock_user = MagicMock()
        mock_user.role = UserRole.SUPER_ADMIN
        mock_user.id = 999
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True
    
    def test_owner_permission(self):
        """测试所有者权限"""
        from app.api.scripts import check_script_permission
        from app.models import User, UserRole
        
        mock_script = MagicMock()
        mock_script.created_by = 1
        
        mock_user = MagicMock()
        mock_user.role = UserRole.DEVELOPER
        mock_user.id = 1
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True
    
    def test_public_script_permission(self):
        """测试公开脚本权限"""
        from app.api.scripts import check_script_permission
        from app.models import User, UserRole
        
        mock_script = MagicMock()
        mock_script.created_by = 1
        mock_script.is_public = True
        
        mock_user = MagicMock()
        mock_user.role = UserRole.DEVELOPER
        mock_user.id = 2
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True
    
    def test_no_permission(self):
        """测试无权限"""
        from app.api.scripts import check_script_permission
        from app.models import User, UserRole
        
        mock_script = MagicMock()
        mock_script.created_by = 1
        mock_script.is_public = False
        
        mock_user = MagicMock()
        mock_user.role = UserRole.DEVELOPER
        mock_user.id = 2
        
        result = check_script_permission(mock_script, mock_user)
        assert result is False


class TestScriptValidation:
    """测试脚本验证"""
    
    def test_timeout_range(self):
        """测试超时时间范围"""
        from app.api.scripts import ScriptCreate
        
        field = ScriptCreate.model_fields['timeout']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 1
        assert le == 3600
    
    def test_max_retries_range(self):
        """测试最大重试次数范围"""
        from app.api.scripts import ScriptCreate
        
        field = ScriptCreate.model_fields['max_retries']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 0
        assert le == 10


class TestScriptCreate:
    """测试创建脚本"""
    
    def test_create_python_script(self):
        """测试创建Python脚本"""
        from app.api.scripts import ScriptCreate
        
        script = ScriptCreate(
            name="测试脚本",
            script_type="python",
            content="print('hello')",
            description="测试用脚本"
        )
        
        assert script.name == "测试脚本"
        assert script.script_type == "python"
        assert script.content == "print('hello')"
    
    def test_create_bash_script(self):
        """测试创建Bash脚本"""
        from app.api.scripts import ScriptCreate
        
        script = ScriptCreate(
            name="测试脚本",
            script_type="bash",
            content="#!/bin/bash\necho hello"
        )
        
        assert script.script_type == "bash"
    
    def test_create_sql_script(self):
        """测试创建SQL脚本"""
        from app.api.scripts import ScriptCreate
        
        script = ScriptCreate(
            name="测试脚本",
            script_type="sql",
            content="SELECT * FROM users"
        )
        
        assert script.script_type == "sql"
    
    def test_create_with_params(self):
        """测试创建带参数的脚本"""
        from app.api.scripts import ScriptCreate
        
        script = ScriptCreate(
            name="带参脚本",
            script_type="python",
            content="print('{{name}}')",
            params_schema={"name": {"type": "string", "required": True}}
        )
        
        assert script.params_schema is not None
        assert "name" in script.params_schema


class TestScriptExecute:
    """测试执行脚本"""
    
    def test_execute_sync(self):
        """测试同步执行"""
        from app.api.scripts import ScriptExecute
        
        execute = ScriptExecute(
            async_exec=False,
            timeout=60
        )
        
        assert execute.async_exec is False
    
    def test_execute_async(self):
        """测试异步执行"""
        from app.api.scripts import ScriptExecute
        
        execute = ScriptExecute(
            async_exec=True,
            params={"name": "test"}
        )
        
        assert execute.async_exec is True
        assert execute.params["name"] == "test"


class TestExecutionQuery:
    """测试执行查询"""
    
    def test_default_pagination(self):
        """测试默认分页"""
        from app.api.scripts import ExecutionQuery
        
        query = ExecutionQuery()
        
        assert query.skip == 0
        assert query.limit == 20
    
    def test_filter_by_status(self):
        """测试按状态过滤"""
        from app.api.scripts import ExecutionQuery
        
        query = ExecutionQuery(status="SUCCESS")
        
        assert query.status == "SUCCESS"
    
    def test_filter_by_date_range(self):
        """测试按日期范围过滤"""
        from app.api.scripts import ExecutionQuery
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        
        query = ExecutionQuery(start_date=start, end_date=end)
        
        assert query.start_date == start
        assert query.end_date == end


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
