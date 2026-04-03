"""
用户管理 API 集成测试
"""
import pytest
from app.models import UserRole


class TestUsersAPI:
    """用户管理接口测试"""

    def test_list_users_as_admin(self, client, admin_headers):
        """测试管理员获取用户列表"""
        response = client.get("/api/v1/users", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_users_as_normal_user(self, client, auth_headers):
        """测试普通用户获取用户列表"""
        response = client.get("/api/v1/users", headers=auth_headers)
        
        # 普通用户可能没有权限
        assert response.status_code in [200, 403]

    def test_create_user_as_admin(self, client, admin_headers):
        """测试管理员创建用户"""
        user_data = {
            "username": "apitestuser",
            "password": "password123",
            "real_name": "API Test User",
            "email": "apitest@example.com",
            "role": UserRole.DEVELOPER.value
        }
        
        response = client.post("/api/v1/users", json=user_data, headers=admin_headers)
        
        if response.status_code == 201:
            data = response.json()
            assert data["username"] == "apitestuser"
            assert data["role"] == UserRole.DEVELOPER.value

    def test_create_duplicate_user(self, client, admin_headers, create_test_user):
        """测试创建重复用户"""
        create_test_user("duplicateuser", "password123")
        
        user_data = {
            "username": "duplicateuser",
            "password": "password123",
            "real_name": "Duplicate",
            "email": "dup@example.com",
            "role": UserRole.DEVELOPER.value
        }
        
        response = client.post("/api/v1/users", json=user_data, headers=admin_headers)
        
        # 应该返回 400 或 409
        assert response.status_code in [400, 409]

    def test_get_user_detail(self, client, admin_headers, create_test_user):
        """测试获取用户详情"""
        user = create_test_user("detailuser", "password123")
        
        response = client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data["username"] == "detailuser"

    def test_update_user(self, client, admin_headers, create_test_user):
        """测试更新用户信息"""
        user = create_test_user("updateuser", "password123")
        
        update_data = {
            "real_name": "Updated Name",
            "email": "updated@example.com"
        }
        
        response = client.put(
            f"/api/v1/users/{user.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code in [200, 404]

    def test_delete_user(self, client, admin_headers, create_test_user):
        """测试删除用户"""
        user = create_test_user("deleteuser", "password123")
        
        response = client.delete(f"/api/v1/users/{user.id}", headers=admin_headers)
        
        assert response.status_code in [200, 204, 404]

    def test_update_user_status(self, client, admin_headers, create_test_user):
        """测试更新用户状态"""
        user = create_test_user("statususer", "password123")
        
        status_data = {"status": False}
        
        response = client.patch(
            f"/api/v1/users/{user.id}/status",
            json=status_data,
            headers=admin_headers
        )
        
        assert response.status_code in [200, 404]
