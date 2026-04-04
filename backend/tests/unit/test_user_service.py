"""
用户服务层单元测试
"""
import pytest
from fastapi import HTTPException, status

from app.services.user_service import UserService
from app.models import User, UserRole
from app.utils.auth import hash_password


class TestUserService:
    """用户服务测试"""

    def test_get_by_username(self, db_session, create_test_user):
        """测试根据用户名获取用户"""
        user = create_test_user("testuser123", role=UserRole.OPERATOR)
        service = UserService(db_session)
        
        result = service.get_by_username("testuser123")
        
        assert result is not None
        assert result.username == "testuser123"
        assert result.role == UserRole.OPERATOR

    def test_get_by_username_not_found(self, db_session):
        """测试获取不存在的用户"""
        service = UserService(db_session)
        
        result = service.get_by_username("nonexistent")
        
        assert result is None

    def test_get_by_email(self, db_session, create_test_user):
        """测试根据邮箱获取用户"""
        user = create_test_user("emailuser", email="test@example.com")
        service = UserService(db_session)
        
        result = service.get_by_email("test@example.com")
        
        assert result is not None
        assert result.email == "test@example.com"

    def test_get_multi_with_count(self, db_session, create_test_user):
        """测试获取用户列表及总数"""
        # 创建多个用户
        create_test_user("user1", role=UserRole.DEVELOPER)
        create_test_user("user2", role=UserRole.OPERATOR)
        create_test_user("user3", role=UserRole.DEVELOPER, status=False)
        
        service = UserService(db_session)
        users, total = service.get_multi_with_count(skip=0, limit=10)
        
        assert total >= 3
        assert len(users) >= 3

    def test_get_multi_with_role_filter(self, db_session, create_test_user):
        """测试按角色过滤用户"""
        create_test_user("devuser1", role=UserRole.DEVELOPER)
        create_test_user("devuser2", role=UserRole.DEVELOPER)
        create_test_user("opuser", role=UserRole.OPERATOR)
        
        service = UserService(db_session)
        users, total = service.get_multi_with_count(
            skip=0, limit=10, role=UserRole.DEVELOPER
        )
        
        assert total >= 2
        for user in users:
            assert user.role == UserRole.DEVELOPER

    def test_get_multi_with_status_filter(self, db_session, create_test_user):
        """测试按状态过滤用户"""
        create_test_user("activeuser", status=True)
        create_test_user("inactiveuser", status=False)
        
        service = UserService(db_session)
        users, total = service.get_multi_with_count(
            skip=0, limit=10, status=True
        )
        
        for user in users:
            assert user.status is True

    def test_create_user_success(self, db_session):
        """测试成功创建用户"""
        service = UserService(db_session)
        
        user = service.create_user(
            username="newuser",
            password="password123",
            real_name="New User",
            email="newuser@example.com",
            role=UserRole.DEVELOPER
        )
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.real_name == "New User"
        assert user.email == "newuser@example.com"
        assert user.role == UserRole.DEVELOPER

    def test_create_user_duplicate_username(self, db_session, create_test_user):
        """测试创建重复用户名的用户"""
        create_test_user("duplicateuser")
        service = UserService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.create_user(
                username="duplicateuser",
                password="password123",
                real_name="Duplicate",
                email="dup@example.com",
                role=UserRole.DEVELOPER
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已存在" in exc_info.value.detail

    def test_create_user_duplicate_email(self, db_session, create_test_user):
        """测试创建重复邮箱的用户"""
        create_test_user("user1", email="same@example.com")
        service = UserService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.create_user(
                username="user2",
                password="password123",
                real_name="User Two",
                email="same@example.com",
                role=UserRole.DEVELOPER
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "邮箱" in exc_info.value.detail

    def test_update_user_success(self, db_session, create_test_user):
        """测试成功更新用户"""
        user = create_test_user("updateuser", real_name="Old Name")
        service = UserService(db_session)
        
        updated = service.update_user(
            user_id=user.id,
            real_name="New Name",
            phone="13800138000"
        )
        
        assert updated.real_name == "New Name"
        assert updated.phone == "13800138000"

    def test_update_password(self, db_session, create_test_user):
        """测试更新用户密码"""
        user = create_test_user("pwduser", password="oldpassword")
        service = UserService(db_session)
        
        result = service.update_password(user.id, "newpassword123")
        
        assert result is True
        # 验证新密码有效
        updated_user = service.get(user.id)
        from app.utils.auth import verify_password
        assert verify_password("newpassword123", updated_user.password_hash)

    def test_update_last_login(self, db_session, create_test_user):
        """测试更新最后登录信息"""
        user = create_test_user("loginuser")
        service = UserService(db_session)
        
        result = service.update_last_login(user.id, "192.168.1.1")
        
        assert result is True
        updated_user = service.get(user.id)
        assert updated_user.last_login_ip == "192.168.1.1"
        assert updated_user.last_login_time is not None

    def test_authenticate_success(self, db_session, create_test_user):
        """测试认证成功"""
        user = create_test_user("authuser", password="correctpass")
        service = UserService(db_session)
        
        result = service.authenticate("authuser", "correctpass")
        
        assert result is not None
        assert result.username == "authuser"

    def test_authenticate_wrong_password(self, db_session, create_test_user):
        """测试认证失败 - 密码错误"""
        user = create_test_user("authuser2", password="correctpass")
        service = UserService(db_session)
        
        result = service.authenticate("authuser2", "wrongpass")
        
        assert result is None

    def test_authenticate_user_not_found(self, db_session):
        """测试认证失败 - 用户不存在"""
        service = UserService(db_session)
        
        result = service.authenticate("nonexistent", "password")
        
        assert result is None

    def test_authenticate_disabled_user(self, db_session, create_test_user):
        """测试认证失败 - 用户被禁用"""
        user = create_test_user("disableduser", password="password", status=False)
        service = UserService(db_session)
        
        result = service.authenticate("disableduser", "password")
        
        assert result is None

    def test_is_super_admin(self, db_session):
        """测试超级管理员检查"""
        service = UserService(db_session)
        
        super_admin = User(username="admin", role=UserRole.SUPER_ADMIN)
        approval_admin = User(username="approval", role=UserRole.APPROVAL_ADMIN)
        
        assert service.is_super_admin(super_admin) is True
        assert service.is_super_admin(approval_admin) is False
