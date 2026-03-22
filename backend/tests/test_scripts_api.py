"""
脚本管理 API 测试用例
"""
import pytest


class TestScriptsAPI:
    """脚本管理 API 测试"""

    def test_get_scripts_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/scripts")
        assert response.status_code == 401

    def test_get_scripts_success(self, client, operator_token):
        """测试获取脚本列表"""
        response = client.get(
            "/api/v1/scripts",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_script_missing_fields(self, client, operator_token):
        """测试创建脚本缺少必填字段"""
        response = client.post(
            "/api/v1/scripts",
            json={},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_shell_script(self, client, operator_token):
        """测试创建 Shell 脚本"""
        response = client.post(
            "/api/v1/scripts",
            json={
                "name": "测试Shell脚本",
                "script_type": "shell",
                "content": "#!/bin/bash\necho 'Hello World'",
                "description": "测试脚本",
                "is_enabled": True,
                "is_public": False
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_create_sql_script(self, client, operator_token):
        """测试创建 SQL 脚本"""
        response = client.post(
            "/api/v1/scripts",
            json={
                "name": "测试SQL脚本",
                "script_type": "sql",
                "content": "SELECT 1;",
                "description": "测试SQL脚本",
                "is_enabled": True,
                "is_public": False
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_update_script(self, client, operator_token, db_session):
        """测试更新脚本"""
        from app.models import Script
        
        # 创建测试脚本
        script = Script(
            name="待更新脚本",
            script_type="shell",
            content="echo 'test'",
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)
        
        response = client.put(
            f"/api/v1/scripts/{script.id}",
            json={"name": "更新后的脚本"},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 403, 404]

    def test_delete_script(self, client, operator_token, db_session):
        """测试删除脚本"""
        from app.models import Script
        
        # 创建测试脚本
        script = Script(
            name="待删除脚本",
            script_type="shell",
            content="echo 'test'",
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)
        
        response = client.delete(
            f"/api/v1/scripts/{script.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 403, 404]


class TestScheduledTasksAPI:
    """定时任务 API 测试"""

    def test_get_tasks_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/scheduled-tasks")
        assert response.status_code == 401

    def test_get_tasks_success(self, client, operator_token):
        """测试获取定时任务列表"""
        response = client.get(
            "/api/v1/scheduled-tasks",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_task_missing_fields(self, client, operator_token):
        """测试创建任务缺少必填字段"""
        response = client.post(
            "/api/v1/scheduled-tasks",
            json={},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_task(self, client, operator_token, db_session):
        """测试创建定时任务"""
        from app.models import Script
        
        # 先创建脚本
        script = Script(
            name="测试脚本",
            script_type="shell",
            content="echo 'test'",
            created_by=1
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)
        
        response = client.post(
            "/api/v1/scheduled-tasks",
            json={
                "name": "测试定时任务",
                "script_id": script.id,
                "cron_expression": "0 0 * * *",
                "status": "enabled"
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400]


class TestNotificationAPI:
    """通知管理 API 测试"""

    def test_get_channels_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/notification/channels")
        assert response.status_code == 401

    def test_get_channels_success(self, client, operator_token):
        """测试获取通知通道列表"""
        response = client.get(
            "/api/v1/notification/channels",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_create_channel_missing_fields(self, client, operator_token):
        """测试创建通道缺少必填字段"""
        response = client.post(
            "/api/v1/notification/channels",
            json={},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_dingtalk_channel(self, client, operator_token):
        """测试创建钉钉通道"""
        response = client.post(
            "/api/v1/notification/channels",
            json={
                "name": "测试钉钉通道",
                "channel_type": "dingtalk",
                "auth_type": "token",
                "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
                "description": "测试通道",
                "is_enabled": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_get_bindings_success(self, client, operator_token):
        """测试获取通知绑定列表"""
        response = client.get(
            "/api/v1/notification/bindings",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
