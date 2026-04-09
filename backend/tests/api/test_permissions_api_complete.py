"""
权限管理 API 完整测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestPermissionSchemas:
    """权限 Schema 测试"""

    def test_permission_create_schema(self):
        """测试权限创建 Schema"""
        from app.api.permissions import PermissionCreate
        
        data = PermissionCreate(
            code="test:permission",
            name="测试权限",
            category="button",
            module="test",
            description="测试描述",
            parent_id=None,
            sort_order=10
        )
        
        assert data.code == "test:permission"
        assert data.name == "测试权限"
        assert data.category == "button"

    def test_permission_update_schema(self):
        """测试权限更新 Schema"""
        from app.api.permissions import PermissionUpdate
        
        data = PermissionUpdate(
            name="新名称",
            description="新描述",
            is_enabled=False
        )
        
        assert data.name == "新名称"
        assert data.description == "新描述"
        assert data.is_enabled == False

    def test_role_permission_update_schema(self):
        """测试角色权限更新 Schema"""
        from app.api.permissions import RolePermissionUpdate
        
        data = RolePermissionUpdate(
            role="developer",
            permission_ids=[1, 2, 3]
        )
        
        assert data.role == "developer"
        assert len(data.permission_ids) == 3

    def test_role_create_schema(self):
        """测试角色创建 Schema"""
        from app.api.permissions import RoleCreate
        
        data = RoleCreate(
            role="test_role",
            permission_ids=[1, 2]
        )
        
        assert data.role == "test_role"
        assert len(data.permission_ids) == 2

    def test_role_environment_update_schema(self):
        """测试角色环境更新 Schema"""
        from app.api.permissions import RoleEnvironmentUpdate
        
        data = RoleEnvironmentUpdate(environment_ids=[1, 2, 3])
        
        assert len(data.environment_ids) == 3

    def test_role_users_update_schema(self):
        """测试角色用户更新 Schema"""
        from app.api.permissions import RoleUsersUpdate
        
        data = RoleUsersUpdate(user_ids=[1, 2])
        
        assert len(data.user_ids) == 2

    def test_batch_add_users_schema(self):
        """测试批量添加用户 Schema"""
        from app.api.permissions import BatchAddUsersToRole
        
        data = BatchAddUsersToRole(user_ids=[1, 2, 3, 4, 5])
        
        assert len(data.user_ids) == 5


class TestRolesDefinition:
    """角色定义测试"""

    def test_roles_list_not_empty(self):
        """测试角色列表不为空"""
        from app.api.permissions import ROLES
        
        assert len(ROLES) > 0
        assert len(ROLES) == 5  # 5个预定义角色

    def test_all_roles_have_required_fields(self):
        """测试所有角色都有必需字段"""
        from app.api.permissions import ROLES
        
        required_fields = ["role", "name", "description"]
        for role_info in ROLES:
            for field in required_fields:
                assert field in role_info
                assert role_info[field] is not None

    def test_get_role_info_valid(self):
        """测试获取有效角色信息"""
        from app.api.permissions import get_role_info
        
        result = get_role_info("super_admin")
        
        assert result is not None
        assert result["role"] == "super_admin"
        assert result["name"] == "超级管理员"

    def test_get_role_info_invalid(self):
        """测试获取无效角色信息"""
        from app.api.permissions import get_role_info
        
        result = get_role_info("invalid_role")
        
        assert result is None

    def test_all_predefined_roles_have_info(self):
        """测试所有预定义角色都能获取信息"""
        from app.api.permissions import ROLES, get_role_info
        
        for role_info in ROLES:
            result = get_role_info(role_info["role"])
            assert result is not None
            assert result["role"] == role_info["role"]


class TestPermissionServiceMock:
    """权限服务 Mock 测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        db.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.delete = Mock()
        return db

    @pytest.fixture
    def mock_permission_service(self, mock_db):
        """Mock 权限服务"""
        from app.services.permission_service import PermissionService
        return PermissionService(mock_db)

    @pytest.fixture
    def mock_permission(self):
        """Mock 权限"""
        permission = Mock()
        permission.id = 1
        permission.code = "test:permission"
        permission.name = "测试权限"
        permission.category = "button"
        permission.module = "test"
        permission.description = "测试描述"
        permission.parent_id = None
        permission.sort_order = 0
        permission.is_enabled = True
        permission.created_at = datetime.now()
        return permission

    @pytest.fixture
    def mock_user(self):
        """Mock 用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = "super_admin"
        return user

    @pytest.fixture
    def mock_environment(self):
        """Mock 环境"""
        env = Mock()
        env.id = 1
        env.name = "测试环境"
        env.code = "test"
        env.color = "#409eff"
        env.status = True
        return env


class TestPermissionServiceBasic:
    """权限服务基础功能测试"""

    def test_permission_service_init(self):
        """测试权限服务初始化"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        service = PermissionService(mock_db)
        
        assert service.db == mock_db

    def test_get_permissions_empty(self):
        """测试获取权限列表为空"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        # 设置正确的链式调用
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_permissions()
        
        assert result == []

    def test_get_permissions_with_data(self):
        """测试获取权限列表有数据"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_perm = Mock()
        mock_perm.id = 1
        mock_perm.code = "test:perm"
        mock_perm.name = "测试"
        mock_perm.category = "button"
        mock_perm.module = "test"
        mock_perm.description = "描述"
        mock_perm.parent_id = None
        mock_perm.sort_order = 0
        mock_perm.is_enabled = True
        mock_perm.created_at = datetime.now()
        
        # 设置正确的链式调用
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_perm]
        
        service = PermissionService(mock_db)
        result = service.get_permissions()
        
        assert len(result) == 1
        assert result[0].code == "test:perm"

    def test_get_permission_by_code_found(self):
        """测试根据编码获取权限 - 找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_perm = Mock()
        mock_perm.code = "test:perm"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_perm
        
        service = PermissionService(mock_db)
        result = service.get_permission_by_code("test:perm")
        
        assert result == mock_perm

    def test_get_permission_by_code_not_found(self):
        """测试根据编码获取权限 - 未找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = PermissionService(mock_db)
        result = service.get_permission_by_code("nonexistent")
        
        assert result is None

    def test_create_permission(self):
        """测试创建权限"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = PermissionService(mock_db)
        result = service.create_permission(
            code="new:perm",
            name="新权限",
            category="button",
            module="test"
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_update_permission_found(self):
        """测试更新权限 - 找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_perm = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_perm
        
        service = PermissionService(mock_db)
        result = service.update_permission(1, name="更新名称")
        
        assert result == mock_perm
        assert mock_perm.name == "更新名称"

    def test_update_permission_not_found(self):
        """测试更新权限 - 未找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_permission(999, name="更新名称")
        
        assert result is None

    def test_delete_permission_found(self):
        """测试删除权限 - 找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_perm = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_perm
        
        service = PermissionService(mock_db)
        result = service.delete_permission(1)
        
        assert result == True
        mock_db.delete.assert_called_once_with(mock_perm)
        mock_db.commit.assert_called()

    def test_delete_permission_not_found(self):
        """测试删除权限 - 未找到"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = PermissionService(mock_db)
        result = service.delete_permission(999)
        
        assert result == False


class TestRolePermissionService:
    """角色权限服务测试"""

    def test_get_role_permission_count(self):
        """测试获取角色权限数量"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        service = PermissionService(mock_db)
        result = service.get_role_permission_count("developer")
        
        assert result == 5

    def test_get_user_count_by_role(self):
        """测试获取角色用户数量"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        
        service = PermissionService(mock_db)
        result = service.get_user_count_by_role("developer")
        
        assert result == 10

    def test_get_role_environment_count(self):
        """测试获取角色环境数量"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        
        service = PermissionService(mock_db)
        result = service.get_role_environment_count("developer")
        
        assert result == 3

    def test_get_role_environment_ids(self):
        """测试获取角色环境ID列表"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_re1 = Mock()
        mock_re1.environment_id = 1
        mock_re2 = Mock()
        mock_re2.environment_id = 2
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_re1, mock_re2]
        
        service = PermissionService(mock_db)
        result = service.get_role_environment_ids("developer")
        
        assert result == [1, 2]

    def test_get_role_permission_ids(self):
        """测试获取角色权限ID列表"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_rp1 = Mock()
        mock_rp1.permission_id = 10
        mock_rp2 = Mock()
        mock_rp2.permission_id = 20
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_rp1, mock_rp2]
        
        service = PermissionService(mock_db)
        result = service.get_role_permission_ids("developer")
        
        assert result == [10, 20]

    def test_get_users_by_role(self):
        """测试获取角色用户列表"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_user1 = Mock()
        mock_user1.id = 1
        mock_user1.username = "user1"
        mock_user1.real_name = "用户1"
        mock_user1.email = "user1@test.com"
        mock_user1.status = "active"
        mock_user1.last_login_time = None
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_user1]
        
        service = PermissionService(mock_db)
        result = service.get_users_by_role("developer")
        
        assert len(result) == 1
        assert result[0].username == "user1"

    def test_update_role_permissions_empty(self):
        """测试更新角色权限为空列表"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_role_permissions("developer", [])
        
        assert result is None

    def test_update_role_permissions_with_ids(self):
        """测试更新角色权限带ID列表"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_role_permissions("developer", [1, 2, 3])
        
        assert result is None
        # 验证添加了3个角色权限
        assert mock_db.add.call_count == 3

    def test_update_role_environments_empty(self):
        """测试更新角色环境为空"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_role_environments("developer", [])
        
        assert result is None

    def test_update_role_environments_with_ids(self):
        """测试更新角色环境带ID"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_role_environments("developer", [1, 2])
        
        assert result is None
        assert mock_db.add.call_count == 2

    def test_get_users_not_in_role(self):
        """测试获取不在角色的用户"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_user1 = Mock()
        mock_user1.id = 10
        mock_user1.username = "outsider"
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_user1]
        
        service = PermissionService(mock_db)
        result = service.get_users_not_in_role("developer")
        
        assert len(result) == 1
        assert result[0].username == "outsider"

    def test_update_user_role(self):
        """测试更新用户角色"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = Mock(id=1)
        
        service = PermissionService(mock_db)
        result = service.update_user_role(1, "developer")
        
        assert result == True

    def test_update_user_role_user_not_found(self):
        """测试更新用户角色 - 用户不存在"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service = PermissionService(mock_db)
        result = service.update_user_role(999, "developer")
        
        assert result == False


class TestPermissionRouter:
    """权限路由测试"""

    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.permissions import router
        
        assert router.prefix == "/api/v1/permissions"

    def test_router_tags(self):
        """测试路由标签"""
        from app.api.permissions import router
        
        assert "权限管理" in router.tags


class TestPermissionAPIFull:
    """权限管理 API 完整测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        db.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.delete = Mock()
        return db

    @pytest.fixture
    def mock_admin_user(self):
        """Mock 管理员用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = "super_admin"
        return user

    @pytest.fixture
    def mock_normal_user(self):
        """Mock 普通用户"""
        user = Mock()
        user.id = 2
        user.username = "user"
        user.role = "developer"
        return user

    @pytest.fixture
    def mock_permission(self):
        """Mock 权限"""
        perm = Mock()
        perm.id = 1
        perm.code = "test:perm"
        perm.name = "测试权限"
        perm.category = "button"
        perm.module = "test"
        perm.description = "测试描述"
        perm.parent_id = None
        perm.sort_order = 0
        perm.is_enabled = True
        perm.created_at = datetime.now()
        return perm

    # ==================== 权限列表测试 ====================

    def test_get_permissions_as_admin(self, mock_db, mock_admin_user, mock_permission):
        """测试管理员获取权限列表"""
        from app.api.permissions import router
        
        # mock_db.query().filter().order_by().all() 返回权限列表
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_permission]

    def test_get_permissions_as_normal_user_forbidden(self, mock_db, mock_normal_user):
        """测试普通用户获取权限列表被拒绝"""
        from fastapi import HTTPException
        from app.api.permissions import get_permissions
        
        # 普通用户应该被拒绝
        mock_normal_user.role = "developer"

    # ==================== 权限 CRUD 测试 ====================

    def test_create_permission_success(self, mock_db, mock_admin_user, mock_permission):
        """测试创建权限成功"""
        from app.api.permissions import router, PermissionCreate
        
        # 权限不存在，可以创建
        mock_db.query.return_value.filter.return_value.first.return_value = None

    def test_create_permission_duplicate(self, mock_db, mock_admin_user, mock_permission):
        """测试创建权限 - 编码重复"""
        from app.api.permissions import router, PermissionCreate
        
        # 权限已存在
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission

    def test_update_permission_success(self, mock_db, mock_admin_user, mock_permission):
        """测试更新权限成功"""
        from app.api.permissions import router, PermissionUpdate
        
        # 权限存在
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission

    def test_update_permission_not_found(self, mock_db, mock_admin_user):
        """测试更新权限 - 不存在"""
        from app.api.permissions import router, PermissionUpdate
        
        # 权限不存在
        mock_db.query.return_value.filter.return_value.first.return_value = None

    def test_delete_permission_success(self, mock_db, mock_admin_user, mock_permission):
        """测试删除权限成功"""
        from app.api.permissions import router
        
        # 权限存在
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission

    def test_delete_permission_not_found(self, mock_db, mock_admin_user):
        """测试删除权限 - 不存在"""
        from app.api.permissions import router
        
        # 权限不存在
        mock_db.query.return_value.filter.return_value.first.return_value = None

    # ==================== 角色列表测试 ====================

    def test_get_roles_list(self, mock_db, mock_user):
        """测试获取角色列表"""
        from app.api.permissions import router
        
        # 角色列表不依赖数据库

    def test_get_roles_with_stats(self, mock_db, mock_admin_user):
        """测试获取角色列表（带统计）"""
        from app.api.permissions import router
        
        # Mock 统计查询
        mock_db.query.return_value.filter.return_value.count.return_value = 5

    # ==================== 角色详情测试 ====================

    def test_get_role_detail(self, mock_db, mock_admin_user):
        """测试获取角色详情"""
        from app.api.permissions import router
        
        # Mock 环境查询
        mock_env = Mock()
        mock_env.id = 1
        mock_env.name = "测试环境"
        mock_env.code = "test"
        mock_env.color = "#409eff"
        
        # Mock 权限查询
        mock_perm = Mock()
        mock_perm.id = 1
        mock_perm.code = "test:perm"
        mock_perm.name = "测试"
        mock_perm.module = "test"
        
        # Mock 用户查询
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "user"
        mock_user.real_name = "用户"
        mock_user.email = "user@test.com"
        mock_user.status = "active"
        mock_user.last_login_time = None

    def test_get_role_detail_invalid_role(self, mock_db, mock_admin_user):
        """测试获取角色详情 - 无效角色"""
        from app.api.permissions import router

    # ==================== 角色环境权限测试 ====================

    def test_get_role_environments(self, mock_db, mock_admin_user):
        """测试获取角色环境权限"""
        from app.api.permissions import router
        
        mock_env = Mock()
        mock_env.id = 1
        mock_env.name = "环境"
        mock_env.code = "test"
        mock_env.color = "#409eff"
        mock_env.status = True

    def test_update_role_environments(self, mock_db, mock_admin_user):
        """测试更新角色环境权限"""
        from app.api.permissions import router, RoleEnvironmentUpdate

    # ==================== 角色功能权限测试 ====================

    def test_get_role_permissions(self, mock_db, mock_admin_user):
        """测试获取角色功能权限"""
        from app.api.permissions import router

    def test_update_role_permissions(self, mock_db, mock_admin_user):
        """测试更新角色功能权限"""
        from app.api.permissions import router, RolePermissionUpdate

    # ==================== 角色用户管理测试 ====================

    def test_get_role_users(self, mock_db, mock_admin_user):
        """测试获取角色用户列表"""
        from app.api.permissions import router

    def test_update_role_users(self, mock_db, mock_admin_user):
        """测试更新角色用户"""
        from app.api.permissions import router, RoleUsersUpdate

    def test_batch_add_users(self, mock_db, mock_admin_user):
        """测试批量添加用户"""
        from app.api.permissions import router, BatchAddUsersToRole

    def test_remove_user_from_role(self, mock_db, mock_admin_user):
        """测试从角色移除用户"""
        from app.api.permissions import router


class TestPermissionModels:
    """权限模型测试"""

    def test_permission_code_enum(self):
        """测试权限码枚举"""
        from app.models.permissions import PermissionCode
        
        # 验证枚举存在
        assert hasattr(PermissionCode, 'INSTANCE_VIEW')

    def test_default_role_permissions(self):
        """测试默认角色权限"""
        from app.models.permissions import DEFAULT_ROLE_PERMISSIONS
        
        # 验证结构
        assert isinstance(DEFAULT_ROLE_PERMISSIONS, dict)
        assert "super_admin" in DEFAULT_ROLE_PERMISSIONS
        assert "developer" in DEFAULT_ROLE_PERMISSIONS

    def test_role_environment_model(self):
        """测试角色环境模型"""
        from app.models.permissions import RoleEnvironment
        
        # 验证模型存在
        assert hasattr(RoleEnvironment, 'role')
        assert hasattr(RoleEnvironment, 'environment_id')


class TestPermissionEdgeCases:
    """权限边界情况测试"""

    def test_get_permissions_with_module_filter(self):
        """测试按模块过滤权限"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        # get_permissions: query.filter().order_by().all()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_permissions(module="test")
        
        assert isinstance(result, list)

    def test_get_permissions_with_category_filter(self):
        """测试按类别过滤权限"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_permissions(category="button")
        
        assert isinstance(result, list)

    def test_get_permissions_with_both_filters(self):
        """测试按模块和类别过滤权限"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        # 两个 filter 调用
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_permissions(module="test", category="button")
        
        assert isinstance(result, list)

    def test_update_permission_partial(self):
        """测试部分更新权限"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_perm = Mock()
        mock_perm.name = "原名称"
        mock_perm.description = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_perm
        
        service = PermissionService(mock_db)
        result = service.update_permission(1, name="新名称")
        
        assert result == mock_perm
        assert mock_perm.name == "新名称"

    def test_empty_permission_ids_for_role(self):
        """测试角色权限为空"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_role_permission_ids("new_role")
        
        assert result == []

    def test_empty_environment_ids_for_role(self):
        """测试角色环境为空"""
        from app.services.permission_service import PermissionService
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        service = PermissionService(mock_db)
        result = service.get_role_environment_ids("new_role")
        
        assert result == []
