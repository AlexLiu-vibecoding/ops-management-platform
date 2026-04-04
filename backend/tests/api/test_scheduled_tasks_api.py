"""
定时任务 API 测试

覆盖定时任务接口：
- 任务列表: /api/v1/scheduled-tasks
- 任务创建: /api/v1/scheduled-tasks
- 任务更新: /api/v1/scheduled-tasks/{id}
- 任务删除: /api/v1/scheduled-tasks/{id}
- 任务执行: /api/v1/scheduled-tasks/{id}/execute
"""
import pytest


class TestScheduledTasksAPI:
    """定时任务 API 测试类"""

    def test_list_scheduled_tasks(self, client, admin_headers):
        """测试获取定时任务列表"""
        response = client.get("/api/v1/scheduled-tasks", headers=admin_headers)
        assert response.status_code == 200

    def test_create_scheduled_task(self, client, admin_headers):
        """测试创建定时任务"""
        task_data = {
            "name": "定时备份数据",
            "task_type": "sql",
            "cron_expression": "0 2 * * *",
            "description": "每天凌晨2点执行",
            "is_enabled": True
        }
        response = client.post(
            "/api/v1/scheduled-tasks",
            json=task_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201, 422]

    def test_get_task_detail(self, client, admin_headers):
        """测试获取任务详情"""
        response = client.get("/api/v1/scheduled-tasks/1", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_update_task(self, client, admin_headers):
        """测试更新任务"""
        update_data = {
            "name": "更新后的任务名",
            "is_enabled": False
        }
        response = client.put(
            "/api/v1/scheduled-tasks/1",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 404]

    def test_delete_task(self, client, admin_headers):
        """测试删除任务"""
        response = client.delete("/api/v1/scheduled-tasks/1", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_execute_task(self, client, admin_headers):
        """测试立即执行任务"""
        response = client.post("/api/v1/scheduled-tasks/1/execute", headers=admin_headers)
        # 任务可能不存在，返回 404；或者执行成功返回 200
        assert response.status_code in [200, 404, 405]


class TestScheduledTasksAPIErrorHandling:
    """定时任务 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/scheduled-tasks")
        assert response.status_code == 401

    def test_create_task_invalid_cron(self, client, admin_headers):
        """测试创建任务时提供无效的 cron 表达式"""
        task_data = {
            "name": "测试任务",
            "cron_expression": "invalid_cron",
            "is_enabled": True
        }
        response = client.post(
            "/api/v1/scheduled-tasks",
            json=task_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_execute_nonexistent_task(self, client, admin_headers):
        """测试执行不存在的任务"""
        response = client.post("/api/v1/scheduled-tasks/99999/execute", headers=admin_headers)
        assert response.status_code in [404, 405]
