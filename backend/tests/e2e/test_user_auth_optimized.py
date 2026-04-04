#!/usr/bin/env python3
"""
用户认证 E2E 测试（优化版）

测试范围：
1. 用户登录
2. Token 刷新
3. 权限验证
4. 用户管理

改进：
1. 添加 pytest 标记
2. 测试隔离和清理
3. 更好的错误处理
4. 清晰的测试文档

运行方式:
    cd /workspace/projects/backend

    # 运行所有测试
    python -m pytest tests/e2e/test_user_auth.py -v

    # 只运行认证相关测试
    python -m pytest tests/e2e/test_user_auth.py::TestUserAuth -v

    # 运行带标记的测试
    python -m pytest tests/e2e/test_user_auth.py -m "not slow" -v
"""

import pytest
import sys
import os
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token, decode_access_token


@pytest.mark.e2e
class TestUserAuth:
    """用户认证 E2E 测试类"""

    @pytest.fixture(scope="function")
    def test_user(self, db_session):
        """创建测试用户"""
        username = f"testuser_{os.urandom(4).hex()}"
        user = User(
            username=username,
            password_hash=hash_password("testpass123"),
            real_name="测试用户",
            email=f"{username}@test.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        yield user
        # 清理
        db_session.delete(user)
        db_session.commit()

    @pytest.fixture(scope="function")
    def admin_user(self, db_session):
        """创建管理员用户"""
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
        yield user

    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == test_user.username

    def test_login_wrong_password(self, client, test_user):
        """测试密码错误登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "wrongpass"
            }
        )
        assert response.status_code == 401
        data = response.json()
        # 错误响应格式：{"error": "HTTP_401", "message": "用户名或密码错误"}
        assert "error" in data or "detail" in data

    def test_login_nonexistent_user(self, client):
        """测试不存在用户登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "testpass123"
            }
        )
        assert response.status_code == 401

    def test_login_with_status_false(self, client, db_session):
        """测试禁用用户登录"""
        # 创建禁用用户
        username = f"disabled_{os.urandom(4).hex()}"
        user = User(
            username=username,
            password_hash=hash_password("testpass123"),
            real_name="禁用用户",
            email=f"{username}@test.com",
            role=UserRole.OPERATOR,
            status=False  # 禁用状态
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        try:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": username,
                    "password": "testpass123"
                }
            )
            # 禁用用户登录返回 403（账户已被禁用）
            assert response.status_code == 403
        finally:
            db_session.delete(user)
            db_session.commit()

    def test_token_validation(self, client, test_user):
        """测试 Token 验证"""
        # 登录获取 token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "testpass123"
            }
        )
        token = login_response.json()["access_token"]

        # 使用 token 访问受保护的 API
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username

    def test_token_expired(self, client, test_user):
        """测试过期 Token"""
        # 创建一个立即过期的 token
        token = create_access_token(
            data={
                "sub": str(test_user.id),
                "username": test_user.username,
                "role": test_user.role.value
            },
            expires_delta=timedelta(seconds=-1)  # 已过期
        )

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_token_invalid_format(self, client):
        """测试无效格式的 Token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_token_missing(self, client):
        """测试缺少 Token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_decode_token(self, test_user):
        """测试解码 Token"""
        token = create_access_token({
            "sub": str(test_user.id),
            "username": test_user.username,
            "role": test_user.role.value
        })

        decoded = decode_access_token(token)
        assert decoded["username"] == test_user.username
        assert decoded["sub"] == str(test_user.id)
        assert decoded["role"] == test_user.role.value


@pytest.mark.e2e
@pytest.mark.slow
class TestUserManagement:
    """用户管理 E2E 测试类（需要管理员权限）"""

    @pytest.fixture(scope="function")
    def admin_token(self, client, admin_user):
        """获取管理员 Token"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": admin_user.username,
                "password": "admin123"
            }
        )
        return response.json()["access_token"]

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        """管理员认证头"""
        return {"Authorization": f"Bearer {admin_token}"}

    def test_create_user(self, client, auth_headers, db_session):
        """测试创建用户"""
        username = f"newuser_{os.urandom(4).hex()}"
        user_data = {
            "username": username,
            "password": "newpass123",
            "real_name": "新用户",
            "email": f"{username}@test.com",
            "role": "operator",
            "status": True
        }

        response = client.post("/api/v1/users", json=user_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert data["real_name"] == "新用户"

        # 清理
        user = db_session.query(User).filter_by(username=username).first()
        if user:
            db_session.delete(user)
            db_session.commit()

    def test_list_users(self, client, auth_headers):
        """测试列出用户"""
        response = client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data

    def test_update_user(self, client, auth_headers, db_session):
        """测试更新用户"""
        # 先创建一个用户
        username = f"updateuser_{os.urandom(4).hex()}"
        user = User(
            username=username,
            password_hash=hash_password("testpass123"),
            real_name="原名称",
            email=f"{username}@test.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        try:
            # 更新用户
            update_data = {"real_name": "更新后名称"}
            response = client.put(
                f"/api/v1/users/{user.id}",
                json=update_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["real_name"] == "更新后名称"
        finally:
            db_session.delete(user)
            db_session.commit()

    def test_delete_user(self, client, auth_headers, db_session):
        """测试删除用户"""
        # 先创建一个用户
        username = f"deleteuser_{os.urandom(4).hex()}"
        user = User(
            username=username,
            password_hash=hash_password("testpass123"),
            real_name="待删除用户",
            email=f"{username}@test.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 删除用户
        response = client.delete(f"/api/v1/users/{user.id}", headers=auth_headers)
        assert response.status_code == 200

        # 验证删除
        deleted_user = db_session.query(User).filter_by(id=user.id).first()
        assert deleted_user is None

    def test_change_password(self, client, auth_headers, test_user):
        """测试修改密码"""
        password_data = {
            "old_password": "testpass123",
            "new_password": "newpass456"
        }
        response = client.put(
            f"/api/v1/users/{test_user.id}/change-password",
            json=password_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        # 验证新密码可以登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "newpass456"
            }
        )
        assert login_response.status_code == 200

        # 恢复原密码（方便其他测试）
        reset_password = {
            "old_password": "newpass456",
            "new_password": "testpass123"
        }
        client.put(
            f"/api/v1/users/{test_user.id}/change-password",
            json=reset_password,
            headers=auth_headers
        )

    def test_permission_denied_for_operator(self, client, test_user):
        """测试操作员权限受限"""
        # 操作员登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "testpass123"
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 尝试创建用户（应该失败）
        user_data = {
            "username": "hacker",
            "password": "hackpass123",
            "real_name": "黑客",
            "email": "hacker@test.com",
            "role": "operator",
            "status": True
        }
        response = client.post("/api/v1/users", json=user_data, headers=headers)
        assert response.status_code in [401, 403]
