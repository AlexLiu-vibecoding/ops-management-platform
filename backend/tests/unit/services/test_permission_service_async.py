#!/usr/bin/env python3
"""
异步权限服务单元测试

测试范围：
1. 权限检查
2. 角色权限查询
3. 环境权限管理
4. 缓存管理
5. 权限详情查询

改进：
1. 完整的异步权限检查流程测试
2. 缓存机制测试
3. 边界条件测试
4. 错误处理测试

运行方式:
    cd /workspace/projects/backend

    # 运行所有异步权限服务测试
    python -m pytest tests/unit/services/test_permission_service_async.py -v

    # 运行特定测试
    python -m pytest tests/unit/services/test_permission_service_async.py::TestAsyncPermissionService -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.models import User, UserRole, Environment
from app.models.permissions import Permission, RolePermission, RoleEnvironment
from app.services.permission_service_async import AsyncPermissionService


# 创建异步数据库连接
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function")
async def async_db():
    """异步数据库会话"""
    from app.database import Base

    # 创建所有表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session

    # 清理
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def admin_user():
    """管理员用户"""
    return User(
        id=1,
        username="admin",
        real_name="超级管理员",
        role=UserRole.SUPER_ADMIN,
        status=True
    )


@pytest.fixture(scope="function")
def operator_user():
    """操作员用户"""
    return User(
        id=2,
        username="operator",
        real_name="操作员",
        role=UserRole.OPERATOR,
        status=True
    )


@pytest.fixture(scope="function")
def developer_user():
    """开发用户"""
    return User(
        id=3,
        username="developer",
        real_name="开发人员",
        role=UserRole.DEVELOPER,
        status=True
    )


@pytest.mark.asyncio
class TestAsyncPermissionService:
    """异步权限服务测试"""

    async def test_has_permission_from_cache(self, async_db, operator_user):
        """测试从缓存获取权限"""
        service = AsyncPermissionService(async_db)
        service._permission_cache["role_permissions:developer"] = {"instance:view", "user:view"}

        result = await service.has_permission(operator_user, "instance:view")
        assert result is True

    async def test_has_permission_not_in_cache(self, async_db, operator_user):
        """测试从数据库获取权限"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm = Permission(code="test:async", name="测试异步", is_enabled=True)
        async_db.add(perm)
        await async_db.commit()
        await async_db.refresh(perm)

        # 创建角色权限关联
        role_perm = RolePermission(role="developer", permission_id=perm.id)
        async_db.add(role_perm)
        await async_db.commit()

        # 测试权限
        result = await service.has_permission(operator_user, "test:async")
        assert result is True

        # 验证缓存
        assert "role_permissions:developer" in service._permission_cache

    async def test_has_permission_from_default(self, async_db, developer_user):
        """测试从默认配置获取权限"""
        service = AsyncPermissionService(async_db)

        # readonly 角色有默认权限
        readonly_user = User(
            id=4,
            username="readonly",
            real_name="只读用户",
            role=UserRole.READONLY,
            status=True
        )

        result = await service.has_permission(readonly_user, "instance:view")
        assert result is True

    async def test_has_permission_no_permission(self, async_db, developer_user):
        """测试无权限"""
        service = AsyncPermissionService(async_db)

        result = await service.has_permission(developer_user, "admin:delete")
        assert result is False

    async def test_get_role_permissions_from_cache(self, async_db):
        """测试从缓存获取角色权限"""
        service = AsyncPermissionService(async_db)
        service._permission_cache["role_permissions:operator"] = {"instance:view", "user:view"}

        permissions = await service.get_role_permissions("operator")
        assert "instance:view" in permissions
        assert "user:view" in permissions

    async def test_get_role_permissions_from_db(self, async_db):
        """测试从数据库获取角色权限"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm = Permission(code="test:db", name="测试数据库", is_enabled=True)
        async_db.add(perm)
        await async_db.commit()
        await async_db.refresh(perm)

        # 创建角色权限关联
        role_perm = RolePermission(role="operator", permission_id=perm.id)
        async_db.add(role_perm)
        await async_db.commit()

        # 获取权限
        permissions = await service.get_role_permissions("operator")
        assert "test:db" in permissions

        # 验证缓存
        assert "role_permissions:operator" in service._permission_cache

    async def test_get_role_permissions_default(self, async_db):
        """测试获取默认角色权限"""
        service = AsyncPermissionService(async_db)

        permissions = await service.get_role_permissions("readonly")
        assert len(permissions) > 0

    async def test_get_user_environment_ids(self, async_db, operator_user):
        """测试获取用户环境权限"""
        service = AsyncPermissionService(async_db)

        # 创建环境
        env = Environment(name="测试环境", code="test_env", color="#1890FF")
        async_db.add(env)
        await async_db.commit()
        await async_db.refresh(env)

        # 创建角色环境权限
        role_env = RoleEnvironment(role="operator", environment_id=env.id)
        async_db.add(role_env)
        await async_db.commit()

        # 获取环境权限
        env_ids = await service.get_user_environment_ids(operator_user)
        assert env.id in env_ids

    async def test_get_user_environment_ids_superuser(self, async_db, admin_user):
        """测试超级管理员获取所有环境"""
        service = AsyncPermissionService(async_db)

        # 创建多个环境
        env1 = Environment(name="环境1", code="env1", color="#1890FF")
        env2 = Environment(name="环境2", code="env2", color="#1890FF")
        async_db.add_all([env1, env2])
        await async_db.commit()

        # 超级管理员应该有所有环境
        env_ids = await service.get_user_environment_ids(admin_user)
        assert env1.id in env_ids
        assert env2.id in env_ids

    async def test_check_environment_access(self, async_db, operator_user):
        """测试环境访问权限检查"""
        service = AsyncPermissionService(async_db)

        # 创建环境
        env = Environment(name="测试环境", code="test_env", color="#1890FF")
        async_db.add(env)
        await async_db.commit()
        await async_db.refresh(env)

        # 创建角色环境权限
        role_env = RoleEnvironment(role="operator", environment_id=env.id)
        async_db.add(role_env)
        await async_db.commit()

        # 检查访问权限
        has_access = await service.check_environment_access(operator_user, env.id)
        assert has_access is True

    async def test_check_environment_access_denied(self, async_db, operator_user):
        """测试环境访问被拒绝"""
        service = AsyncPermissionService(async_db)

        # 创建环境（不关联权限）
        env = Environment(name="测试环境", code="test_env", color="#1890FF")
        async_db.add(env)
        await async_db.commit()
        await async_db.refresh(env)

        # 检查访问权限
        has_access = await service.check_environment_access(operator_user, env.id)
        assert has_access is False

    async def test_get_all_permissions(self, async_db):
        """测试获取所有权限"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm1 = Permission(code="test:perm1", name="测试权限1", is_enabled=True)
        perm2 = Permission(code="test:perm2", name="测试权限2", is_enabled=False)  # 禁用
        async_db.add_all([perm1, perm2])
        await async_db.commit()

        # 获取所有权限（只返回启用的）
        permissions = await service.get_all_permissions()
        assert len(permissions) >= 1  # 至少有 perm1

        # 验证禁用的权限不在列表中
        perm_codes = [p.code for p in permissions]
        assert "test:perm1" in perm_codes
        assert "test:perm2" not in perm_codes

    async def test_get_role_permissions_with_details(self, async_db):
        """测试获取角色权限详情"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm = Permission(
            code="test:detail",
            name="测试详情",
            category="button",
            description="测试描述",
            is_enabled=True
        )
        async_db.add(perm)
        await async_db.commit()
        await async_db.refresh(perm)

        # 创建角色权限关联
        role_perm = RolePermission(role="developer", permission_id=perm.id)
        async_db.add(role_perm)
        await async_db.commit()

        # 获取权限详情
        permissions = await service.get_role_permissions_with_details("developer")
        assert len(permissions) > 0

        # 验证权限详情
        perm_detail = permissions[0]
        assert "id" in perm_detail
        assert "code" in perm_detail
        assert "name" in perm_detail
        assert "category" in perm_detail
        assert "description" in perm_detail

    async def test_clear_cache(self, async_db):
        """测试清除缓存"""
        service = AsyncPermissionService(async_db)
        service._permission_cache["test"] = {"permission"}

        service.clear_cache()

        assert len(service._permission_cache) == 0

    async def test_cache_effectiveness(self, async_db, operator_user):
        """测试缓存有效性"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm = Permission(code="test:cache", name="测试缓存", is_enabled=True)
        async_db.add(perm)
        await async_db.commit()
        await async_db.refresh(perm)

        # 创建角色权限关联
        role_perm = RolePermission(role="developer", permission_id=perm.id)
        async_db.add(role_perm)
        await async_db.commit()

        # 第一次查询（从数据库）
        permissions1 = await service.get_role_permissions("developer")
        assert "test:cache" in permissions1

        # 修改数据库（模拟权限变化）
        perm.is_enabled = False
        await async_db.commit()

        # 第二次查询（从缓存，应该还是旧数据）
        permissions2 = await service.get_role_permissions("developer")
        assert "test:cache" in permissions2  # 仍然存在，因为从缓存读取

        # 清除缓存
        service.clear_cache()

        # 第三次查询（从数据库，应该没有权限了）
        permissions3 = await service.get_role_permissions("developer")
        assert "test:cache" not in permissions3  # 已禁用

    async def test_multiple_role_caching(self, async_db):
        """测试多角色缓存"""
        service = AsyncPermissionService(async_db)

        # 创建权限
        perm1 = Permission(code="test:role1", name="角色1权限", is_enabled=True)
        perm2 = Permission(code="test:role2", name="角色2权限", is_enabled=True)
        async_db.add_all([perm1, perm2])
        await async_db.commit()

        # 创建角色权限关联
        role_perm1 = RolePermission(role="developer", permission_id=perm1.id)
        role_perm2 = RolePermission(role="operator", permission_id=perm2.id)
        async_db.add_all([role_perm1, role_perm2])
        await async_db.commit()

        # 获取不同角色的权限
        dev_perms = await service.get_role_permissions("developer")
        op_perms = await service.get_role_permissions("operator")

        # 验证缓存
        assert "test:role1" in dev_perms
        assert "test:role2" not in dev_perms
        assert "test:role1" not in op_perms
        assert "test:role2" in op_perms

        # 验证缓存独立
        assert "role_permissions:developer" in service._permission_cache
        assert "role_permissions:operator" in service._permission_cache
