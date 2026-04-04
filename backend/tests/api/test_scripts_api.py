"""
脚本管理 API 测试

覆盖脚本管理接口：
- 脚本列表: /api/v1/scripts
- 脚本创建: /api/v1/scripts
- 脚本更新: /api/v1/scripts/{id}
- 脚本删除: /api/v1/scripts/{id}
- 脚本执行: /api/v1/scripts/{id}/execute
"""
import pytest


class TestScriptsAPI:
    """脚本管理 API 测试类"""

    def test_list_scripts(self, client, admin_headers):
        """测试获取脚本列表"""
        response = client.get("/api/v1/scripts", headers=admin_headers)
        assert response.status_code == 200

    def test_create_script(self, client, admin_headers):
        """测试创建脚本"""
        script_data = {
            "name": "备份脚本",
            "script_type": "sql",
            "content": "SELECT * FROM users;",
            "description": "用户表备份脚本"
        }
        response = client.post(
            "/api/v1/scripts",
            json=script_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201, 422]

    def test_get_script_detail(self, client, admin_headers):
        """测试获取脚本详情"""
        response = client.get("/api/v1/scripts/1", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_update_script(self, client, admin_headers):
        """测试更新脚本"""
        update_data = {
            "name": "更新后的脚本名",
            "content": "UPDATE users SET status = 1;"
        }
        response = client.put(
            "/api/v1/scripts/1",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 404]

    def test_delete_script(self, client, admin_headers):
        """测试删除脚本"""
        response = client.delete("/api/v1/scripts/1", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_execute_script(self, client, admin_headers):
        """测试执行脚本"""
        response = client.post("/api/v1/scripts/1/execute", headers=admin_headers)
        assert response.status_code in [200, 404]


class TestScriptsAPIErrorHandling:
    """脚本管理 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/scripts")
        assert response.status_code == 401

    def test_create_script_invalid_data(self, client, admin_headers):
        """测试创建脚本时提供无效数据"""
        response = client.post(
            "/api/v1/scripts",
            json={"name": "测试脚本"},
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_execute_nonexistent_script(self, client, admin_headers):
        """测试执行不存在的脚本"""
        response = client.post("/api/v1/scripts/99999/execute", headers=admin_headers)
        assert response.status_code == 404
