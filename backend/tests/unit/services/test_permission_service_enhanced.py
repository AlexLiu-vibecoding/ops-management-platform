#!/usr/bin/env python3
"""
权限服务增强测试 - 补充测试覆盖率

测试范围：
1. 权限管理方法（CRUD）
2. 角色权限管理
3. 角色环境权限管理
4. 用户角色管理
5. 批量操作服务
6. 缓存管理增强
7. 单例模式

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/unit/services/test_permission_service_enhanced.py -v
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, UserRole, Environment
from app.models.permissions import Permission, RolePermission, RoleEnvironment, BatchOperationLog
from app.services.permission_service import PermissionService, BatchOperationService


class TestPermissionManagement:
    """权限管理测试"""

    def test_get_permissions_no_filter(self, db_session):
        """测试获取所有权限"""
        service = PermissionService(db_session)

        # 创建权限
        perm = Permission(code="test:get1", name="测试获取1", is_enabled=True)
        db_session.add(perm)
        db_session.commit()

        permissions = service.get_permissions()
        assert len(permissions) >= 1
        assert perm in permissions

    def test_get_permissions_with_module_filter(self, db_session):
        """测试按模块过滤权限"""
        service = PermissionService(db_session)

        # 创建不同模块的权限
        perm1 = Permission(code="test:module1", name="模块1", module="测试模块", is_enabled=True)
        perm2 = Permission(code="test:module2", name="模块2", module="其他模块", is_enabled=True)
        db_session.add_all([perm1, perm2])
        db_session.commit()

        permissions = service.get_permissions(module="测试模块")
        assert len(permissions) == 1
        assert permissions[0].code == "test:module1"

    def test_get_permissions_with_category_filter(self, db_session):
        """测试按类别过滤权限"""
        service = PermissionService(db_session)

        # 创建不同类别的权限
        perm1 = Permission(code="test:menu1", name="菜单1", category="menu", is_enabled=True)
        perm2 = Permission(code="test:button1", name="按钮1", category="button", is_enabled=True)
        db_session.add_all([perm1, perm2])
        db_session.commit()

        permissions = service.get_permissions(category="menu")
        assert len(permissions) == 1
        assert permissions[0].code == "test:menu1"

    def test_get_permission_by_code(self, db_session):
        """测试根据编码获取权限"""
        service = PermissionService(db_session)

        perm = Permission(code="test:bycode", name="按编码", is_enabled=True)
        db_session.add(perm)
        db_session.commit()

        result = service.get_permission_by_code("test:bycode")
        assert result is not None
        assert result.code == "test:bycode"

        # 测试不存在的权限
        result = service.get_permission_by_code("notexist")
        assert result is None

    def test_get_permission_by_id(self, db_session):
        """测试根据 ID 获取权限"""
        service = PermissionService(db_session)

        perm = Permission(code="test:byid", name="按ID", is_enabled=True)
        db_session.add(perm)
        db_session.commit()
        db_session.refresh(perm)

        result = service.get_permission_by_id(perm.id)
        assert result is not None
        assert result.id == perm.id

        # 测试不存在的权限
        result = service.get_permission_by_id(99999)
        assert result is None

    def test_create_permission(self, db_session):
        """测试创建权限"""
        service = PermissionService(db_session)

        perm = service.create_permission(
            code="test:create",
            name="测试创建",
            category="button",
            module="测试模块",
            description="测试描述",
            sort_order=10
        )

        assert perm.code == "test:create"
        assert perm.name == "测试创建"
        assert perm.category == "button"
        assert perm.module == "测试模块"
        assert perm.description == "测试描述"
        assert perm.sort_order == 10

    def test_update_permission(self, db_session):
        """测试更新权限"""
        service = PermissionService(db_session)

        perm = Permission(code="test:update", name="原始名称", is_enabled=True)
        db_session.add(perm)
        db_session.commit()
        db_session.refresh(perm)

        updated = service.update_permission(
            perm.id,
            name="新名称",
            description="新描述"
        )

        assert updated is not None
        assert updated.name == "新名称"
        assert updated.description == "新描述"
        assert updated.code == "test:update"  # 未修改的字段保持不变

    def test_update_permission_not_exist(self, db_session):
        """测试更新不存在的权限"""
        service = PermissionService(db_session)

        result = service.update_permission(99999, name="测试")
        assert result is None

    def test_delete_permission(self, db_session):
        """测试删除权限"""
        service = PermissionService(db_session)

        perm = Permission(code="test:delete", name="待删除", is_enabled=True)
        db_session.add(perm)
        db_session.commit()
        perm_id = perm.id

        # 创建角色权限关联
        role_perm = RolePermission(role="developer", permission_id=perm_id)
        db_session.add(role_perm)
        db_session.commit()

        result = service.delete_permission(perm_id)
        assert result is True

        # 验证权限已删除
        assert db_session.query(Permission).filter(Permission.id == perm_id).first() is None
        # 验证关联已删除
        assert db_session.query(RolePermission).filter(RolePermission.permission_id == perm_id).first() is None

    def test_delete_permission_not_exist(self, db_session):
        """测试删除不存在的权限"""
        service = PermissionService(db_session)

        result = service.delete_permission(99999)
        assert result is False


class TestRolePermissionManagement:
    """角色权限管理测试"""

    def test_get_role_permission_ids(self, db_session):
        """测试获取角色权限 ID 列表"""
        service = PermissionService(db_session)

        # 创建权限
        perm1 = Permission(code="test:role1", name="角色权限1", is_enabled=True)
        perm2 = Permission(code="test:role2", name="角色权限2", is_enabled=True)
        db_session.add_all([perm1, perm2])
        db_session.commit()

        # 创建角色权限关联
        role_perm1 = RolePermission(role="developer", permission_id=perm1.id)
        role_perm2 = RolePermission(role="developer", permission_id=perm2.id)
        db_session.add_all([role_perm1, role_perm2])
        db_session.commit()

        perm_ids = service.get_role_permission_ids("developer")
        assert len(perm_ids) == 2
        assert perm1.id in perm_ids
        assert perm2.id in perm_ids

    def test_get_role_permission_count(self, db_session):
        """测试获取角色权限数量"""
        service = PermissionService(db_session)

        # 创建权限
        perm1 = Permission(code="test:count1", name="数量1", is_enabled=True)
        perm2 = Permission(code="test:count2", name="数量2", is_enabled=True)
        db_session.add_all([perm1, perm2])
        db_session.commit()

        # 创建角色权限关联
        role_perm1 = RolePermission(role="operator", permission_id=perm1.id)
        role_perm2 = RolePermission(role="operator", permission_id=perm2.id)
        db_session.add_all([role_perm1, role_perm2])
        db_session.commit()

        count = service.get_role_permission_count("operator")
        assert count == 2

    def test_update_role_permissions(self, db_session):
        """测试更新角色权限"""
        service = PermissionService(db_session)

        # 创建权限
        perm1 = Permission(code="test:rp1", name="RP1", is_enabled=True)
        perm2 = Permission(code="test:rp2", name="RP2", is_enabled=True)
        perm3 = Permission(code="test:rp3", name="RP3", is_enabled=True)
        db_session.add_all([perm1, perm2, perm3])
        db_session.commit()

        # 初始权限
        role_perm1 = RolePermission(role="developer", permission_id=perm1.id)
        db_session.add(role_perm1)
        db_session.commit()

        # 更新权限
        service.update_role_permissions("developer", [perm2.id, perm3.id])

        # 验证旧权限已删除，新权限已添加
        role_perms = db_session.query(RolePermission).filter(RolePermission.role == "developer").all()
        assert len(role_perms) == 2
        perm_ids = [rp.permission_id for rp in role_perms]
        assert perm2.id in perm_ids
        assert perm3.id in perm_ids
        assert perm1.id not in perm_ids


class TestRoleEnvironmentManagement:
    """角色环境权限管理测试"""

    def test_get_role_environment_ids(self, db_session):
        """测试获取角色环境 ID 列表"""
        service = PermissionService(db_session)

        # 创建环境
        env1 = Environment(name="环境1", code="env1", color="#1890FF")
        env2 = Environment(name="环境2", code="env2", color="#1890FF")
        db_session.add_all([env1, env2])
        db_session.commit()

        # 创建角色环境关联
        role_env1 = RoleEnvironment(role="operator", environment_id=env1.id)
        role_env2 = RoleEnvironment(role="operator", environment_id=env2.id)
        db_session.add_all([role_env1, role_env2])
        db_session.commit()

        env_ids = service.get_role_environment_ids("operator")
        assert len(env_ids) == 2
        assert env1.id in env_ids
        assert env2.id in env_ids

    def test_get_role_environment_count(self, db_session):
        """测试获取角色环境权限数量"""
        service = PermissionService(db_session)

        # 创建环境
        env1 = Environment(name="环境1", code="env1", color="#1890FF")
        env2 = Environment(name="环境2", code="env2", color="#1890FF")
        env3 = Environment(name="环境3", code="env3", color="#1890FF")
        db_session.add_all([env1, env2, env3])
        db_session.commit()

        # 创建角色环境关联
        role_env1 = RoleEnvironment(role="developer", environment_id=env1.id)
        role_env2 = RoleEnvironment(role="developer", environment_id=env2.id)
        db_session.add_all([role_env1, role_env2])
        db_session.commit()

        count = service.get_role_environment_count("developer")
        assert count == 2

    def test_update_role_environments(self, db_session):
        """测试更新角色环境权限"""
        service = PermissionService(db_session)

        # 创建环境
        env1 = Environment(name="环境1", code="env1", color="#1890FF")
        env2 = Environment(name="环境2", code="env2", color="#1890FF")
        env3 = Environment(name="环境3", code="env3", color="#1890FF")
        db_session.add_all([env1, env2, env3])
        db_session.commit()

        # 初始环境
        role_env1 = RoleEnvironment(role="operator", environment_id=env1.id)
        db_session.add(role_env1)
        db_session.commit()

        # 更新环境
        service.update_role_environments("operator", [env2.id, env3.id])

        # 验证旧环境已删除，新环境已添加
        role_envs = db_session.query(RoleEnvironment).filter(RoleEnvironment.role == "operator").all()
        assert len(role_envs) == 2
        env_ids = [re.environment_id for re in role_envs]
        assert env2.id in env_ids
        assert env3.id in env_ids
        assert env1.id not in env_ids


class TestUserRoleManagement:
    """用户角色管理测试"""

    def test_get_users_by_role(self, db_session):
        """测试获取指定角色的用户列表"""
        service = PermissionService(db_session)

        # 创建用户
        user1 = User(username="user1", password_hash="hash1", role=UserRole.OPERATOR, status=True)
        user2 = User(username="user2", password_hash="hash2", role=UserRole.OPERATOR, status=True)
        user3 = User(username="user3", password_hash="hash3", role=UserRole.DEVELOPER, status=True)
        db_session.add_all([user1, user2, user3])
        db_session.commit()

        users = service.get_users_by_role("operator")
        assert len(users) == 2
        usernames = [u.username for u in users]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" not in usernames

    def test_get_user_count_by_role(self, db_session):
        """测试获取指定角色的用户数量"""
        service = PermissionService(db_session)

        # 创建用户
        user1 = User(username="user1", password_hash="hash1", role=UserRole.OPERATOR, status=True)
        user2 = User(username="user2", password_hash="hash2", role=UserRole.OPERATOR, status=True)
        user3 = User(username="user3", password_hash="hash3", role=UserRole.DEVELOPER, status=True)
        db_session.add_all([user1, user2, user3])
        db_session.commit()

        count = service.get_user_count_by_role("operator")
        assert count == 2

    def test_get_users_not_in_role(self, db_session):
        """测试获取不属于指定角色的用户列表"""
        service = PermissionService(db_session)

        # 创建用户
        user1 = User(username="user1", password_hash="hash1", role=UserRole.OPERATOR, status=True)
        user2 = User(username="user2", password_hash="hash2", role=UserRole.DEVELOPER, status=True)
        user3 = User(username="user3", password_hash="hash3", role=UserRole.READONLY, status=True)
        db_session.add_all([user1, user2, user3])
        db_session.commit()

        users = service.get_users_not_in_role("operator")
        assert len(users) == 2
        usernames = [u.username for u in users]
        assert "user1" not in usernames
        assert "user2" in usernames
        assert "user3" in usernames

    def test_get_users_not_in_role_with_search(self, db_session):
        """测试带搜索条件的获取用户"""
        service = PermissionService(db_session)

        # 创建用户
        user1 = User(username="alice", password_hash="hash1", role=UserRole.OPERATOR, status=True)
        user2 = User(username="bob", password_hash="hash2", role=UserRole.DEVELOPER, status=True)
        user3 = User(username="bob2", password_hash="hash3", role=UserRole.READONLY, status=True)
        db_session.add_all([user1, user2, user3])
        db_session.commit()

        users = service.get_users_not_in_role("operator", search="bob")
        assert len(users) == 2
        usernames = [u.username for u in users]
        assert "bob" in usernames
        assert "bob2" in usernames

    def test_update_user_role(self, db_session):
        """测试更新用户角色"""
        service = PermissionService(db_session)

        user = User(username="testuser", password_hash="hash", role=UserRole.OPERATOR, status=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        result = service.update_user_role(user.id, "developer")
        assert result is True

        db_session.refresh(user)
        assert user.role == UserRole.DEVELOPER

    def test_update_user_role_not_exist(self, db_session):
        """测试更新不存在的用户角色"""
        service = PermissionService(db_session)

        result = service.update_user_role(99999, "developer")
        assert result is False


class TestBatchOperationService:
    """批量操作服务测试"""

    def test_filter_by_data_permission(self, db_session):
        """测试按数据权限过滤项目"""
        perm_service = PermissionService(db_session)
        batch_service = BatchOperationService(db_session, perm_service)

        # 创建环境和用户
        env1 = Environment(name="环境1", code="env1", color="#1890FF")
        env2 = Environment(name="环境2", code="env2", color="#1890FF")
        db_session.add_all([env1, env2])
        db_session.commit()

        user = User(username="testuser", password_hash="hash", role=UserRole.OPERATOR, status=True)
        db_session.add(user)
        db_session.commit()

        # 创建角色环境关联（只允许访问 env1）
        role_env = RoleEnvironment(role="operator", environment_id=env1.id)
        db_session.add(role_env)
        db_session.commit()

        # 创建模拟项目
        class MockItem:
            def __init__(self, id, env_id):
                self.id = id
                self.environment_id = env_id

        items = [MockItem(1, env1.id), MockItem(2, env2.id), MockItem(3, env1.id)]

        has_permission, no_permission = batch_service.filter_by_data_permission(user, items)

        assert len(has_permission) == 2
        assert len(no_permission) == 1
        assert has_permission[0].id == 1
        assert has_permission[1].id == 3
        assert no_permission[0].id == 2

    def test_log_batch_operation(self, db_session):
        """测试记录批量操作日志"""
        perm_service = PermissionService(db_session)
        batch_service = BatchOperationService(db_session, perm_service)

        user = User(id=1, username="testuser", password_hash="testhash", role=UserRole.OPERATOR, status=True)
        db_session.add(user)
        db_session.commit()

        results = {
            "total": 3,
            "succeeded": 2,
            "failed": 1,
            "no_permission": 0,
            "details": ["item1 success", "item2 success", "item3 failed"]
        }

        log = batch_service.log_batch_operation(
            user=user,
            operation_type="batch_delete",
            resource_type="instance",
            resource_ids=[1, 2, 3],
            results=results,
            request_ip="127.0.0.1"
        )

        assert log is not None
        assert log.user_id == 1
        assert log.username == "testuser"
        assert log.operation_type == "batch_delete"
        assert log.resource_type == "instance"
        assert log.total_count == 3
        assert log.success_count == 2
        assert log.failed_count == 1
        assert log.request_ip == "127.0.0.1"

        # 验证日志已保存到数据库
        saved_log = db_session.query(BatchOperationLog).filter(BatchOperationLog.id == log.id).first()
        assert saved_log is not None


class TestCacheManagement:
    """缓存管理测试"""

    def test_warmup_cache(self, db_session):
        """测试预热缓存"""
        service = PermissionService(db_session)

        # 创建权限
        perm = Permission(code="test:warmup", name="预热测试", is_enabled=True)
        db_session.add(perm)
        db_session.commit()

        # 预热缓存
        service.warmup_cache(db_session)

        # 验证缓存已加载
        assert len(service._permission_cache) > 0
        assert "role_permissions:developer" in service._permission_cache
        assert "role_permissions:operator" in service._permission_cache

    def test_refresh_cache(self, db_session):
        """测试刷新缓存"""
        service = PermissionService(db_session)

        # 创建权限
        perm = Permission(code="test:refresh", name="刷新测试", is_enabled=True)
        db_session.add(perm)
        db_session.commit()

        # 添加一些缓存
        service._permission_cache["test"] = {"value"}

        # 刷新缓存
        service.refresh_cache(db_session)

        # 验证旧缓存已清除，新缓存已加载
        assert "test" not in service._permission_cache
        assert len(service._permission_cache) > 0

    def test_get_instance(self, db_session):
        """测试获取单例"""
        instance1 = PermissionService.get_instance(db_session)
        instance2 = PermissionService.get_instance(db_session)

        # 验证是同一个实例
        assert instance1 is instance2

    def test_set_instance_db(self, db_session):
        """测试设置单例的数据库会话"""
        service = PermissionService.get_instance(db_session)

        # 设置新的数据库会话
        service.set_instance_db(db_session)

        # 验证数据库会话已设置
        assert service.db is db_session


class TestEnvironmentAccess:
    """环境访问权限测试"""

    def test_check_environment_access_with_permission(self, db_session):
        """测试有环境访问权限"""
        service = PermissionService(db_session)

        # 创建环境
        env = Environment(name="测试环境", code="test_env", color="#1890FF")
        db_session.add(env)
        db_session.commit()

        # 创建用户
        user = User(username="testuser", password_hash="hash", role=UserRole.OPERATOR, status=True)
        db_session.add(user)
        db_session.commit()

        # 创建角色环境关联
        role_env = RoleEnvironment(role="operator", environment_id=env.id)
        db_session.add(role_env)
        db_session.commit()

        # 不应该抛出异常
        service.check_environment_access(user, env.id)

    def test_check_environment_access_without_permission(self, db_session):
        """测试无环境访问权限"""
        service = PermissionService(db_session)

        # 创建环境
        env = Environment(name="测试环境", code="test_env", color="#1890FF")
        db_session.add(env)
        db_session.commit()

        # 创建用户
        user = User(username="testuser", password_hash="hash", role=UserRole.OPERATOR, status=True)
        db_session.add(user)
        db_session.commit()

        # 不创建角色环境关联

        # 应该抛出异常
        with pytest.raises(HTTPException) as exc_info:
            service.check_environment_access(user, env.id)

        assert exc_info.value.status_code == 403
        assert "无权访问此环境" in exc_info.value.detail
