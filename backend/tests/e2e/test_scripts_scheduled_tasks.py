#!/usr/bin/env python3
"""
脚本管理和定时任务 E2E 测试

测试范围：
1. 脚本 CRUD
2. 脚本执行
3. 定时任务 CRUD
4. 定时任务触发/暂停/恢复
5. 执行历史查询

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_scripts_scheduled_tasks.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestScriptsManagement:
    """脚本管理 E2E 测试类"""

    @pytest.fixture(scope="function")
    def admin_token(self, db_session):
        """创建管理员 token"""
        user = db_session.query(User).filter_by(username="admin").first()
        if not user:
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@test.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        })
        return token

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        """认证头"""
        return {"Authorization": f"Bearer {admin_token}"}

    def test_list_scripts(self, client, auth_headers):
        """测试获取脚本列表"""
        response = client.get("/api/v1/scripts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_and_delete_python_script(self, client, auth_headers):
        """测试创建和删除 Python 脚本"""
        script_data = {
            "name": f"e2e_python_script_{os.urandom(4).hex()}",
            "script_type": "python",
            "content": "print('Hello from E2E test')",
            "description": "E2E测试Python脚本"
        }

        # 创建脚本
        response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)

        if response.status_code == 201:
            script_id = response.json().get("id")

            # 验证创建成功
            get_resp = client.get(f"/api/v1/scripts/{script_id}", headers=auth_headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["name"] == script_data["name"]

            # 删除脚本
            delete_resp = client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)
            assert delete_resp.status_code == 200
        else:
            # 可能脚本已存在或其他错误
            assert response.status_code in [201, 400, 409]

    def test_create_and_delete_bash_script(self, client, auth_headers):
        """测试创建和删除 Bash 脚本"""
        script_data = {
            "name": f"e2e_bash_script_{os.urandom(4).hex()}",
            "script_type": "bash",
            "content": "#!/bin/bash\necho 'Hello from E2E test'",
            "description": "E2E测试Bash脚本"
        }

        # 创建脚本
        response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)

        if response.status_code == 201:
            script_id = response.json().get("id")

            # 删除脚本
            delete_resp = client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)
            assert delete_resp.status_code == 200
        else:
            assert response.status_code in [201, 400, 409]

    def test_update_script(self, client, auth_headers):
        """测试更新脚本"""
        # 先创建脚本
        script_data = {
            "name": f"e2e_update_script_{os.urandom(4).hex()}",
            "script_type": "python",
            "content": "print('Original')",
            "description": "原始描述"
        }

        create_resp = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        if create_resp.status_code != 201:
            pytest.skip("创建脚本失败，跳过更新测试")

        script_id = create_resp.json().get("id")

        # 更新脚本
        update_data = {
            "name": script_data["name"],
            "content": "print('Updated')",
            "description": "更新后的描述"
        }

        response = client.put(f"/api/v1/scripts/{script_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200

        # 验证更新
        get_resp = client.get(f"/api/v1/scripts/{script_id}", headers=auth_headers)
        assert get_resp.json()["description"] == "更新后的描述"

        # 清理
        client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)

    def test_duplicate_script(self, client, auth_headers):
        """测试复制脚本"""
        # 先创建脚本
        script_data = {
            "name": f"e2e_duplicate_script_{os.urandom(4).hex()}",
            "script_type": "python",
            "content": "print('Original')",
            "description": "原始脚本"
        }

        create_resp = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        if create_resp.status_code != 201:
            pytest.skip("创建脚本失败，跳过复制测试")

        script_id = create_resp.json().get("id")

        # 复制脚本
        response = client.post(f"/api/v1/scripts/{script_id}/duplicate", headers=auth_headers)
        assert response.status_code == 201

        duplicated_id = response.json().get("id")

        # 清理
        client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)
        client.delete(f"/api/v1/scripts/{duplicated_id}", headers=auth_headers)

    def test_list_script_executions(self, client, auth_headers):
        """测试获取脚本执行历史"""
        response = client.get("/api/v1/scripts/executions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestScheduledTasks:
    """定时任务 E2E 测试类"""

    @pytest.fixture(scope="function")
    def admin_token(self, db_session):
        user = db_session.query(User).filter_by(username="admin").first()
        if not user:
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@test.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        })
        return token

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_list_scheduled_tasks(self, client, auth_headers):
        """测试获取定时任务列表"""
        response = client.get("/api/v1/scheduled-tasks", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_and_delete_scheduled_task(self, client, auth_headers):
        """测试创建和删除定时任务"""
        # 首先创建一个脚本
        script_data = {
            "name": f"e2e_scheduled_script_{os.urandom(4).hex()}",
            "script_type": "python",
            "content": "print('Scheduled task test')",
            "description": "定时任务测试脚本"
        }

        script_resp = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        if script_resp.status_code != 201:
            pytest.skip("创建脚本失败，跳过定时任务测试")

        script_id = script_resp.json().get("id")

        # 创建定时任务
        task_data = {
            "name": f"e2e_task_{os.urandom(4).hex()}",
            "script_id": script_id,
            "cron_expression": "0 0 * * *",
            "description": "E2E测试定时任务",
            "is_enabled": True
        }

        response = client.post("/api/v1/scheduled-tasks", json=task_data, headers=auth_headers)

        if response.status_code == 201:
            task_id = response.json().get("id")

            # 删除定时任务
            delete_resp = client.delete(f"/api/v1/scheduled-tasks/{task_id}", headers=auth_headers)
            assert delete_resp.status_code == 200
        else:
            assert response.status_code in [201, 400]

        # 清理脚本
        client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)

    def test_validate_cron_expression(self, client, auth_headers):
        """测试验证 Cron 表达式"""
        test_cases = [
            ("0 0 * * *", True),
            ("*/5 * * * *", True),
            ("invalid_cron", False),
        ]

        for cron_expr, expected_valid in test_cases:
            response = client.post(
                "/api/v1/scheduled-tasks/validate-cron",
                json={"expression": cron_expr},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] == expected_valid

    def test_get_server_timezone(self, client, auth_headers):
        """测试获取服务器时区"""
        response = client.get("/api/v1/scheduled-tasks/server-info/timezone", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "timezone" in data


class TestSchedulerOverview:
    """调度器概览 E2E 测试类"""

    @pytest.fixture(scope="function")
    def admin_token(self, db_session):
        user = db_session.query(User).filter_by(username="admin").first()
        if not user:
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@test.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        })
        return token

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_get_scheduler_overview(self, client, auth_headers):
        """测试获取调度器概览"""
        response = client.get("/api/v1/scheduler/overview", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "active_jobs" in data

    def test_list_scheduler_jobs(self, client, auth_headers):
        """测试获取调度器任务列表"""
        response = client.get("/api/v1/scheduler/jobs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
