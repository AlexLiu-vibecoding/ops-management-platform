"""
权限服务单元测试
"""
import pytest
from fastapi import HTTPException

from app.services.permission_service import PermissionService
from app.models import User, UserRole, Environment
from app.models.permissions import Permission, RolePermission, PermissionCode


class TestPermissionService:
    """权限服务测试"""

    def test_has_permission_super_admin(self, db_session):
        """测试超级管理员权限检查"""
        service = PermissionService(db_session)
        admin = User(username="admin", role=UserRole.SUPER_ADMIN)
        
        # 初始化默认权限
        service.init_default_permissions()
        
        result = service.has_permission(admin, PermissionCode.INSTANCE_VIEW)
        
        assert result is True

    def test_has_permission_from_cache(self, db_session):
        """测试从缓存获取权限"""
        service = PermissionService(db_session)
        service._permission_cache["role_permissions:developer"] = {"instance:view", "user:view"}
        
        user = User(username="dev", role=UserRole.DEVELOPER)
        result = service.has_permission(user, "instance:view")
        
        assert result is True

    def test_get_role_permissions_from_db(self, db_session):
        """测试从数据库获取角色权限"""
        service = PermissionService(db_session)
        
        # 创建权限
        perm = Permission(code="test:permission", name="测试权限", is_enabled=True)
        db_session.add(perm)
        db_session.flush()
        
        # 创建角色权限关联
        role_perm = RolePermission(role="operator", permission_id=perm.id)
        db_session.add(role_perm)
        db_session.commit()
        
        permissions = service.get_role_permissions("operator")
        
        assert "test:permission" in permissions

    def test_get_role_permissions_default(self, db_session):
        """测试获取默认角色权限"""
        service = PermissionService(db_session)
        
        # 清空缓存，确保从默认值获取
        service.clear_cache()
        
        permissions = service.get_role_permissions("readonly")
        
        # readonly 应该有 view 类权限
        assert len(permissions) > 0

    def test_check_permission_success(self, db_session):
        """测试成功检查权限"""
        service = PermissionService(db_session)
        service._permission_cache["role_permissions:super_admin"] = {"instance:view"}
        
        admin = User(username="admin", role=UserRole.SUPER_ADMIN)
        
        # 不抛出异常即为成功
        service.check_permission(admin, "instance:view")

    def test_check_permission_failure(self, db_session):
        """测试权限检查失败"""
        service = PermissionService(db_session)
        service._permission_cache["role_permissions:readonly"] = set()
        
        user = User(username="readonly", role=UserRole.READONLY)
        
        with pytest.raises(HTTPException) as exc_info:
            service.check_permission(user, "instance:delete")
        
        assert exc_info.value.status_code == 403

    def test_clear_cache(self, db_session):
        """测试清除缓存"""
        service = PermissionService(db_session)
        service._permission_cache["test"] = {"permission"}
        
        service.clear_cache()
        
        assert len(service._permission_cache) == 0

    def test_get_user_environment_ids(self, db_session):
        """测试获取用户环境权限"""
        from app.models.permissions import RoleEnvironment
        
        service = PermissionService(db_session)
        
        # 创建环境
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        # 创建角色环境权限
        role_env = RoleEnvironment(role="operator", environment_id=env.id)
        db_session.add(role_env)
        db_session.commit()
        
        user = User(username="op", role=UserRole.OPERATOR)
        env_ids = service.get_user_environment_ids(user)
        
        assert env.id in env_ids

    def test_has_environment_access(self, db_session):
        """测试环境访问权限检查"""
        from app.models.permissions import RoleEnvironment
        
        service = PermissionService(db_session)
        
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        role_env = RoleEnvironment(role="developer", environment_id=env.id)
        db_session.add(role_env)
        db_session.commit()
        
        user = User(username="dev", role=UserRole.DEVELOPER)
        result = service.has_environment_access(user, env.id)
        
        assert result is True

    def test_has_environment_access_denied(self, db_session):
        """测试环境访问被拒绝"""
        service = PermissionService(db_session)
        
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        user = User(username="dev", role=UserRole.DEVELOPER)
        result = service.has_environment_access(user, env.id)
        
        assert result is False

    def test_check_environment_access_failure(self, db_session):
        """测试环境访问检查失败"""
        service = PermissionService(db_session)
        
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        user = User(username="dev", role=UserRole.DEVELOPER)
        
        with pytest.raises(HTTPException) as exc_info:
            service.check_environment_access(user, env.id)
        
        assert exc_info.value.status_code == 403

    def test_check_batch_operation_allowed_protection_0(self, db_session):
        """测试保护级别 0 的批量操作"""
        service = PermissionService(db_session)
        
        env = Environment(name="Normal", code="normal", protection_level=0)
        db_session.add(env)
        db_session.commit()
        
        user = User(username="admin", role=UserRole.SUPER_ADMIN)
        allowed, reason = service.check_batch_operation_allowed(user, env.id, 100)
        
        assert allowed is True
        assert reason == ""

    def test_check_batch_operation_allowed_protection_2(self, db_session):
        """测试核心环境禁止批量操作"""
        service = PermissionService(db_session)
        
        env = Environment(name="Core", code="core", protection_level=2)
        db_session.add(env)
        db_session.commit()
        
        user = User(username="admin", role=UserRole.SUPER_ADMIN)
        allowed, reason = service.check_batch_operation_allowed(user, env.id, 5)
        
        assert allowed is False
        assert "核心环境禁止批量操作" in reason

    def test_check_batch_operation_allowed_protection_1_exceed(self, db_session):
        """测试重要环境超过批量限制"""
        service = PermissionService(db_session)
        
        env = Environment(name="Important", code="important", protection_level=1)
        db_session.add(env)
        db_session.commit()
        
        user = User(username="admin", role=UserRole.SUPER_ADMIN)
        allowed, reason = service.check_batch_operation_allowed(user, env.id, 10)
        
        assert allowed is False
        assert "单次最多操作5条" in reason

    def test_init_default_permissions(self, db_session):
        """测试初始化默认权限"""
        service = PermissionService(db_session)
        
        service.init_default_permissions()
        
        # 验证权限已创建
        perms = db_session.query(Permission).all()
        assert len(perms) > 0
        
        # 验证有实例查看权限
        instance_view = db_session.query(Permission).filter(
            Permission.code == PermissionCode.INSTANCE_VIEW
        ).first()
        assert instance_view is not None
