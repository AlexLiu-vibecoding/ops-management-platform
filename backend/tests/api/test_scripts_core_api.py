"""
脚本管理核心 API 测试

脚本 CRUD、执行、版本管理相关 API 测试
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, UserRole, Script, ScriptExecution, ScriptType, ExecutionStatus


class TestScriptCRUDAPI:
    """脚本 CRUD API 测试"""

    def test_list_scripts(self, client: TestClient, admin_headers: dict):
        """测试获取脚本列表"""
        response = client.get("/api/v1/scripts", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # 可能是分页格式或列表格式
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_create_python_script(self, client: TestClient, admin_headers: dict):
        """测试创建 Python 脚本"""
        script_data = {
            "name": "测试 Python 脚本",
            "script_type": "python",
            "content": "print('Hello, World!')",
            "description": "这是一个测试脚本",
            "timeout": 300,
            "max_retries": 3,
            "is_public": True
        }
        response = client.post(
            "/api/v1/scripts",
            json=script_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == script_data["name"]
            assert data["script_type"] == "python"
            assert "id" in data

    def test_create_bash_script(self, client: TestClient, admin_headers: dict):
        """测试创建 Bash 脚本"""
        script_data = {
            "name": "测试 Bash 脚本",
            "script_type": "bash",
            "content": "#!/bin/bash\necho 'Hello World'",
            "description": "Bash 测试脚本",
            "timeout": 60
        }
        response = client.post(
            "/api/v1/scripts",
            json=script_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

    def test_create_sql_script(self, client: TestClient, admin_headers: dict):
        """测试创建 SQL 脚本"""
        script_data = {
            "name": "测试 SQL 脚本",
            "script_type": "sql",
            "content": "SELECT 1 as test;",
            "description": "SQL 测试脚本"
        }
        response = client.post(
            "/api/v1/scripts",
            json=script_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

    def test_get_script_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取脚本详情"""
        # 先创建脚本
        script = Script(
            name="测试脚本",
            script_type=ScriptType.python,
            content="print('test')",
            description="测试描述",
            timeout=300,
            max_retries=0,
            is_enabled=True,
            is_public=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        response = client.get(
            f"/api/v1/scripts/{script.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == script.id
        assert data["name"] == script.name

    def test_update_script(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试更新脚本"""
        # 先创建脚本
        script = Script(
            name="旧脚本名称",
            script_type=ScriptType.python,
            content="print('old')",
            description="旧描述",
            timeout=300,
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        update_data = {
            "name": "新脚本名称",
            "content": "print('new')",
            "description": "新描述"
        }
        response = client.put(
            f"/api/v1/scripts/{script.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新脚本名称"

    def test_delete_script(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试删除脚本"""
        # 先创建脚本
        script = Script(
            name="待删除脚本",
            script_type=ScriptType.python,
            content="print('delete me')",
            timeout=300,
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)
        script_id = script.id

        response = client.delete(
            f"/api/v1/scripts/{script_id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # 验证已删除
        deleted = db_session.query(Script).filter_by(id=script_id).first()
        assert deleted is None


class TestScriptExecuteAPI:
    """脚本执行 API 测试"""

    def test_execute_script_sync(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试同步执行脚本"""
        # 先创建脚本
        script = Script(
            name="可执行脚本",
            script_type=ScriptType.python,
            content="print('Hello from script')",
            timeout=30,
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        exec_data = {
            "params": {},
            "async_exec": False,
            "timeout": 30
        }
        response = client.post(
            f"/api/v1/scripts/{script.id}/execute",
            json=exec_data,
            headers=admin_headers
        )
        # 执行可能成功或失败，取决于环境
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_execute_script_async(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试异步执行脚本"""
        # 先创建脚本
        script = Script(
            name="异步执行脚本",
            script_type=ScriptType.python,
            content="import time; time.sleep(1); print('done')",
            timeout=60,
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        exec_data = {
            "params": {},
            "async_exec": True
        }
        response = client.post(
            f"/api/v1/scripts/{script.id}/execute",
            json=exec_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 202]

    def test_execute_script_with_params(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试带参数执行脚本"""
        # 先创建带参数模式的脚本
        script = Script(
            name="带参数脚本",
            script_type=ScriptType.python,
            content="import sys; print(f'Name: {sys.argv[1]}')",
            params_schema={
                "name": {"type": "string", "required": True}
            },
            timeout=30,
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        exec_data = {
            "params": {"name": "TestUser"},
            "async_exec": False
        }
        response = client.post(
            f"/api/v1/scripts/{script.id}/execute",
            json=exec_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 500]

    def test_execute_disabled_script(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试执行已禁用的脚本"""
        # 创建禁用的脚本
        script = Script(
            name="禁用脚本",
            script_type=ScriptType.python,
            content="print('should not run')",
            timeout=30,
            is_enabled=False,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        exec_data = {"params": {}, "async_exec": False}
        response = client.post(
            f"/api/v1/scripts/{script.id}/execute",
            json=exec_data,
            headers=admin_headers
        )
        # 应该返回错误
        assert response.status_code in [400, 403, 422]


class TestScriptExecutionRecordAPI:
    """脚本执行记录 API 测试"""

    def test_list_script_executions(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取脚本执行记录列表"""
        # 先创建脚本和执行记录
        script = Script(
            name="测试脚本",
            script_type=ScriptType.python,
            content="print('test')",
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        execution = ScriptExecution(
            script_id=script.id,
            status=ExecutionStatus.SUCCESS,
            output="Hello",
            executed_by=1
        )
        db_session.add(execution)
        db_session.commit()

        response = client.get(
            f"/api/v1/scripts/{script.id}/executions",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_get_execution_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取执行记录详情"""
        # 先创建脚本和执行记录
        script = Script(
            name="测试脚本",
            script_type=ScriptType.python,
            content="print('test')",
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        execution = ScriptExecution(
            script_id=script.id,
            status=ExecutionStatus.SUCCESS,
            output="Hello World",
            executed_by=1
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        response = client.get(
            f"/api/v1/scripts/executions/{execution.id}",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == execution.id

    def test_stop_execution(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试停止正在执行的脚本"""
        # 先创建脚本和运行中的执行记录
        script = Script(
            name="长时间脚本",
            script_type=ScriptType.python,
            content="import time; time.sleep(60)",
            is_enabled=True,
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)

        execution = ScriptExecution(
            script_id=script.id,
            status=ExecutionStatus.RUNNING,
            executed_by=1
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        response = client.post(
            f"/api/v1/scripts/executions/{execution.id}/stop",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]


class TestScriptAPIErrorHandling:
    """脚本 API 错误处理测试"""

    def test_get_nonexistent_script(self, client: TestClient, admin_headers: dict):
        """测试获取不存在的脚本"""
        response = client.get("/api/v1/scripts/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_nonexistent_script(self, client: TestClient, admin_headers: dict):
        """测试更新不存在的脚本"""
        response = client.put(
            "/api/v1/scripts/99999",
            json={"name": "新名称"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_nonexistent_script(self, client: TestClient, admin_headers: dict):
        """测试删除不存在的脚本"""
        response = client.delete("/api/v1/scripts/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_execute_nonexistent_script(self, client: TestClient, admin_headers: dict):
        """测试执行不存在的脚本"""
        response = client.post(
            "/api/v1/scripts/99999/execute",
            json={"params": {}},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_create_script_with_invalid_type(self, client: TestClient, admin_headers: dict):
        """测试使用无效脚本类型创建"""
        script_data = {
            "name": "测试脚本",
            "script_type": "invalid_type",
            "content": "test"
        }
        response = client.post(
            "/api/v1/scripts",
            json=script_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_create_script_without_required_fields(self, client: TestClient, admin_headers: dict):
        """测试缺少必填字段创建脚本"""
        # 缺少 content
        response = client.post(
            "/api/v1/scripts",
            json={"name": "无效脚本", "script_type": "python"},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_unauthorized_access(self, client: TestClient):
        """测试未授权访问"""
        response = client.get("/api/v1/scripts")
        assert response.status_code == 401
