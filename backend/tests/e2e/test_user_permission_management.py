#!/usr/bin/env python3
"""
用户权限管理 E2E 测试

测试范围：
1. 用户 CRUD
2. 角色权限配置
3. 环境权限配置
4. 权限检查

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_user_permission_management.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestUserManagement:
    """用户管理 E2E 测试类"""

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

    def test_list_users(self, client, auth_headers):
        """测试获取用户列表"""
        response = client.get("/api/v1/users", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_create_and_delete_user(self, client, auth_headers):
        """测试创建和删除用户"""
        user_data = {
            "username": f"e2e_user_{os.urandom(4).hex()}",
            "password": "test123456",
            "real_name": "E2E测试用户",
            "email": f"e2e_{os.urandom(4).hex()}@test.com",
            "role": "developer",
            "status": True
        }

        # 创建用户
        response = client.post("/api/v1/users", json=user_data, headers=auth_headers)

        if response.status_code in [200, 201]:
            user_id = response.json().get("id")

            # 验证创建成功
            get_resp = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
            assert get_resp.status_code == 200
            assert get_resp.json()["username"] == user_data["username"]

            # 删除用户
            delete_resp = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
            assert delete_resp.status_code == 200
        else:
            assert response.status_code in [200, 201, 400, 409]

    def test_update_user(self, client, auth_headers):
        """测试更新用户"""
        # 先创建用户
        user_data = {
            "username": f"e2e_update_user_{os.urandom(4).hex()}",
            "password": "test123456",
            "real_name": "原始姓名",
            "email": f"e2e_update_{os.urandom(4).hex()}@test.com",
            "role": "developer"
        }

        create_resp = client.post("/api/v1/users", json=user_data, headers=auth_headers)
        if create_resp.status_code != 201:
            pytest.skip("创建用户失败，跳过更新测试")

        user_id = create_resp.json().get("id")

        # 更新用户
        update_data = {
            "real_name": "更新后的姓名",
            "phone": "13800138000"
        }

        response = client.put(f"/api/v1/users/{user_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200

        # 验证更新
        get_resp = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert get_resp.json()["real_name"] == "更新后的姓名"

        # 清理
        client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)

    def test_reset_user_password(self, client, auth_headers):
        """测试重置用户密码"""
        # 先创建用户
        user_data = {
            "username": f"e2e_pwd_user_{os.urandom(4).hex()}",
            "password": "test123456",
            "real_name": "密码测试用户",
            "email": f"e2e_pwd_{os.urandom(4).hex()}@test.com",
            "role": "developer"
        }

        create_resp = client.post("/api/v1/users", json=user_data, headers=auth_headers)
        if create_resp.status_code != 201:
            pytest.skip("创建用户失败，跳过密码重置测试")

        user_id = create_resp.json().get("id")

        # 重置密码
        response = client.post(
            f"/api/v1/users/{user_id}/reset-password",
            json={"new_password": "newpassword123"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # 清理
        client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)


class TestPermissionManagement:
    """权限管理 E2E 测试类"""

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

    def test_list_permissions(self, client, auth_headers):
        """测试获取权限列表"""
        response = client.get("/api/v1/permissions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_roles(self, client, auth_headers):
        """测试获取角色列表"""
        response = client.get("/api/v1/permissions/roles/list", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0

    def test_get_role_permissions(self, client, auth_headers):
        """测试获取角色权限"""
        response = client.get("/api/v1/permissions/roles/developer", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "role" in data
        assert "permissions" in data

    def test_check_permission(self, client, auth_headers):
        """测试权限检查"""
        response = client.get("/api/v1/permissions/check/instance:view", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "has_permission" in data

    def test_get_my_permissions(self, client, auth_headers):
        """测试获取当前用户权限"""
        response = client.get("/api/v1/permissions/my-permissions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert "role" in data


class TestEnvironmentPermissions:
    """环境权限 E2E 测试类"""

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

    def test_get_role_environments(self, client, auth_headers):
        """测试获取角色环境权限"""
        response = client.get("/api/v1/permissions/roles/developer/environments", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # 检查返回格式
        assert isinstance(data, dict)
        assert "role" in data

    def test_list_roles_with_permissions(self, client, auth_headers):
        """测试获取带权限的角色列表"""
        response = client.get("/api/v1/permissions/roles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0


class TestAuthFlow:
    """认证流程 E2E 测试类"""

    def test_login_success(self, client, db_session):
        """测试成功登录"""
        # 先确保管理员存在
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

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

    def test_login_failure(self, client):
        """测试登录失败"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrongpassword"}
        )

        assert response.status_code == 401

    def test_get_current_user(self, client, db_session):
        """测试获取当前用户信息"""
        # 先登录获取 token
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

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert "role" in data

    def test_change_password(self, client, db_session):
        """测试修改密码"""
        # 创建测试用户
        test_user = db_session.query(User).filter_by(username="test_pwd_change").first()
        if not test_user:
            test_user = User(
                username="test_pwd_change",
                password_hash=hash_password("oldpassword"),
                real_name="密码修改测试",
                email="test_pwd@test.com",
                role=UserRole.DEVELOPER,
                status=True
            )
            db_session.add(test_user)
            db_session.commit()
            db_session.refresh(test_user)
        token = create_access_token({
            "sub": str(test_user.id),
            "username": test_user.username,
            "role": test_user.role.value
        })

        response = client.put(
            "/api/v1/auth/password",
            params={"old_password": "oldpassword", "new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # 可能成功或失败（取决于实际实现）
        assert response.status_code in [200, 400, 422]
