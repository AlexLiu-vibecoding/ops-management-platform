"""
环境管理 API 测试用例
"""
import pytest


class TestEnvironmentsAPI:
    """环境管理 API 测试"""

    def test_get_environments_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/environments")
        assert response.status_code == 401

    def test_get_environments_success(self, client, operator_token):
        """测试获取环境列表"""
        response = client.get(
            "/api/v1/environments",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_environment_missing_fields(self, client, super_admin_token):
        """测试创建环境缺少必填字段"""
        response = client.post(
            "/api/v1/environments",
            json={},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_environment_success(self, client, super_admin_token):
        """测试创建环境"""
        response = client.post(
            "/api/v1/environments",
            json={
                "name": "新测试环境",
                "code": "new_test",
                "color": "#1890ff",
                "require_approval": True,
                "status": True,
                "description": "用于测试的新环境"
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "新测试环境"

    def test_create_environment_forbidden(self, client, operator_token):
        """测试普通用户无法创建环境"""
        response = client.post(
            "/api/v1/environments",
            json={"name": "test"},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    def test_update_environment(self, client, super_admin_token, test_environment):
        """测试更新环境"""
        response = client.put(
            f"/api/v1/environments/{test_environment.id}",
            json={"name": "更新后的环境"},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后的环境"

    def test_delete_environment(self, client, super_admin_token, db_session):
        """测试删除环境"""
        from app.models import Environment
        
        # 创建一个可删除的环境
        env = Environment(
            name="待删除环境",
            code="to_delete",
            color="#ff0000",
            status=True
        )
        db_session.add(env)
        db_session.commit()
        db_session.refresh(env)
        
        response = client.delete(
            f"/api/v1/environments/{env.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code in [200, 400]


class TestUsersAPI:
    """用户管理 API 测试"""

    def test_get_users_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/users")
        assert response.status_code == 401

    def test_get_users_success(self, client, super_admin_token):
        """测试获取用户列表"""
        response = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_user_missing_fields(self, client, super_admin_token):
        """测试创建用户缺少必填字段"""
        response = client.post(
            "/api/v1/users",
            json={},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_user_success(self, client, super_admin_token):
        """测试创建用户"""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "password": "Test123456",
                "real_name": "测试用户",
                "email": "testuser@test.com",
                "role": "operator",
                "status": True
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["username"] == "testuser"

    def test_create_user_forbidden(self, client, operator_token):
        """测试普通用户无法创建用户"""
        response = client.post(
            "/api/v1/users",
            json={"username": "test"},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    def test_update_user(self, client, super_admin_token, db_session):
        """测试更新用户"""
        from app.models import User, UserRole
        from app.utils.auth import hash_password
        
        # 创建测试用户
        user = User(
            username="updatetest",
            password_hash=hash_password("test123"),
            real_name="待更新用户",
            email="update@test.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        response = client.put(
            f"/api/v1/users/{user.id}",
            json={"real_name": "更新后的用户"},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200

    def test_reset_password(self, client, super_admin_token, db_session):
        """测试重置密码"""
        from app.models import User, UserRole
        from app.utils.auth import hash_password
        
        # 创建测试用户
        user = User(
            username="resettest",
            password_hash=hash_password("test123"),
            real_name="重置密码测试",
            email="reset@test.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        response = client.post(
            f"/api/v1/users/{user.id}/reset-password?new_password=NewPassword123",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200


class TestMenuAPI:
    """菜单配置 API 测试"""

    def test_get_menu_list_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/menu/list")
        assert response.status_code == 401

    def test_get_menu_list_success(self, client, super_admin_token):
        """测试获取菜单列表"""
        response = client.get(
            "/api/v1/menu/list",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_menu_forbidden(self, client, operator_token):
        """测试普通用户无法创建菜单"""
        response = client.post(
            "/api/v1/menu",
            json={"name": "test"},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    def test_create_menu_success(self, client, super_admin_token):
        """测试创建菜单"""
        response = client.post(
            "/api/v1/menu",
            json={
                "name": "测试菜单",
                "path": "/test",
                "icon": "Setting",
                "sort_order": 100,
                "is_visible": True,
                "is_enabled": True
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
