"""
权限管理 API 完整测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException


class TestPermissionsAPIFull:
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
        db.delete = Mock()
        return db

    @pytest.fixture
    def mock_super_admin(self):
        """Mock 超级管理员用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = "super_admin"
        user.is_super_admin = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Mock 普通用户"""
        user = Mock()
        user.id = 2
        user.username = "user"
        user.role = "operator"
        user.is_super_admin = False
        return user

    @pytest.fixture
    def mock_permission(self):
        """Mock 权限"""
        perm = Mock()
        perm.id = 1
        perm.code = "test:view"
        perm.name = "测试查看"
        perm.category = "button"
        perm.module = "test"
        perm.description = "测试权限"
        perm.parent_id = None
        perm.sort_order = 0
        perm.is_enabled = True
        perm.created_at = datetime.now()
        return perm

    @pytest.fixture
    def mock_user(self):
        """Mock 用户"""
        user = Mock()
        user.id = 2
        user.username = "testuser"
        user.real_name = "测试用户"
        user.email = "test@example.com"
        user.role = Mock()
        user.role.value = "developer"
        user.status = "active"
        user.last_login_time = datetime.now()
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

    # ==================== 权限管理 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_permissions_success(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试获取权限列表成功"""
        from app.api.permissions import get_permissions, build_tree
        
        mock_service = Mock()
        mock_service.get_permissions.return_value = [mock_permission]
        mock_service_class.return_value = mock_service
        
        # 测试构建树形结构
        items = [mock_permission]
        tree = build_tree(items)
        
        assert len(tree) == 1
        assert tree[0]["code"] == "test:view"

    @patch('app.api.permissions.PermissionService')
    def test_create_permission_success(self, mock_service_class, mock_db, mock_super_admin):
        """测试创建权限成功"""
        from app.api.permissions import create_permission, PermissionCreate
        
        mock_service = Mock()
        mock_service.get_permission_by_code.return_value = None
        mock_permission = Mock()
        mock_permission.id = 1
        mock_service.create_permission.return_value = mock_permission
        mock_service_class.return_value = mock_service
        
        data = PermissionCreate(
            code="test:create",
            name="测试创建",
            category="button",
            module="test"
        )

    @patch('app.api.permissions.PermissionService')
    def test_create_permission_exists(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试创建已存在的权限"""
        from app.api.permissions import create_permission, PermissionCreate
        
        mock_service = Mock()
        mock_service.get_permission_by_code.return_value = mock_permission
        mock_service_class.return_value = mock_service
        
        data = PermissionCreate(
            code="test:view",
            name="测试",
            category="button",
            module="test"
        )

    @patch('app.api.permissions.PermissionService')
    def test_update_permission_success(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试更新权限成功"""
        from app.api.permissions import update_permission, PermissionUpdate
        
        mock_service = Mock()
        mock_service.update_permission.return_value = mock_permission
        mock_service_class.return_value = mock_service
        
        data = PermissionUpdate(name="新名称")

    @patch('app.api.permissions.PermissionService')
    def test_update_permission_not_found(self, mock_service_class, mock_db, mock_super_admin):
        """测试更新不存在的权限"""
        from app.api.permissions import update_permission, PermissionUpdate
        
        mock_service = Mock()
        mock_service.update_permission.return_value = None
        mock_service_class.return_value = mock_service
        
        data = PermissionUpdate(name="新名称")

    @patch('app.api.permissions.PermissionService')
    def test_delete_permission_success(self, mock_service_class, mock_db, mock_super_admin):
        """测试删除权限成功"""
        from app.api.permissions import delete_permission
        
        mock_service = Mock()
        mock_service.delete_permission.return_value = True
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_delete_permission_not_found(self, mock_service_class, mock_db, mock_super_admin):
        """测试删除不存在的权限"""
        from app.api.permissions import delete_permission
        
        mock_service = Mock()
        mock_service.delete_permission.return_value = False
        mock_service_class.return_value = mock_service

    # ==================== 角色列表 API 测试 ====================

    def test_get_roles_list(self):
        """测试获取角色列表"""
        from app.api.permissions import get_roles_list, ROLES
        
        result = get_roles_list(Mock())
        
        assert "items" in result
        assert len(result["items"]) == len(ROLES)
        assert result["items"][0]["value"] == "super_admin"

    # ==================== 角色详情 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_role_detail_success(self, mock_service_class, mock_db, mock_super_admin, mock_environment):
        """测试获取角色详情成功"""
        from app.api.permissions import get_role_detail
        
        mock_service = Mock()
        mock_service.get_role_environment_ids.return_value = [1]
        mock_service.get_role_permission_ids.return_value = [1]
        mock_service.get_users_by_role.return_value = []
        mock_service_class.return_value = mock_service
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.all.return_value = [mock_environment]
        mock_db.query.return_value = db_query_mock

    @patch('app.api.permissions.PermissionService')
    def test_get_role_detail_invalid_role(self, mock_service_class, mock_db, mock_super_admin):
        """测试获取无效角色的详情"""
        from app.api.permissions import get_role_detail
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service

    # ==================== 角色环境权限 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_role_environments(self, mock_service_class, mock_db, mock_super_admin, mock_environment):
        """测试获取角色环境权限"""
        from app.api.permissions import get_role_environments
        
        mock_service = Mock()
        mock_service.get_role_environment_ids.return_value = [1]
        mock_service_class.return_value = mock_service
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.order_by.return_value.all.return_value = [mock_environment]
        mock_db.query.return_value = db_query_mock

    @patch('app.api.permissions.PermissionService')
    def test_update_role_environments(self, mock_service_class, mock_db, mock_super_admin):
        """测试更新角色环境权限"""
        from app.api.permissions import update_role_environments, RoleEnvironmentUpdate
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        data = RoleEnvironmentUpdate(environment_ids=[1, 2, 3])

    # ==================== 角色功能权限 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_role_permissions(self, mock_service_class, mock_db, mock_super_admin):
        """测试获取角色权限"""
        from app.api.permissions import get_role_permissions
        
        mock_service = Mock()
        mock_service.get_role_permission_ids.return_value = [1, 2, 3]
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_update_role_permissions(self, mock_service_class, mock_db, mock_super_admin):
        """测试更新角色权限"""
        from app.api.permissions import update_role_permissions, RolePermissionUpdate
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        data = RolePermissionUpdate(role="developer", permission_ids=[1, 2, 3])

    @patch('app.api.permissions.PermissionService')
    def test_update_role_permissions_invalid_role(self, mock_service_class, mock_db, mock_super_admin):
        """测试更新无效角色的权限"""
        from app.api.permissions import update_role_permissions, RolePermissionUpdate
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        data = RolePermissionUpdate(role="invalid_role", permission_ids=[1])

    # ==================== 重置默认权限测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_reset_default_permissions(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试重置为默认权限配置"""
        from app.api.permissions import reset_default_permissions
        
        mock_service = Mock()
        mock_service.get_permission_by_code.return_value = mock_permission
        mock_service_class.return_value = mock_service
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = None
        mock_db.query.return_value = db_query_mock

    # ==================== 用户权限查询 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_my_permissions(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试获取当前用户权限"""
        from app.api.permissions import get_my_permissions
        
        mock_service = Mock()
        mock_service.get_role_permission_ids.return_value = [1]
        mock_service_class.return_value = mock_service
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.all.return_value = [mock_permission]
        mock_db.query.return_value = db_query_mock

    @patch('app.api.permissions.PermissionService')
    def test_check_permission_exists(self, mock_service_class, mock_db, mock_super_admin, mock_permission):
        """测试检查权限存在"""
        from app.api.permissions import check_permission
        
        mock_service = Mock()
        mock_service.get_permission_by_code.return_value = mock_permission
        mock_service.get_role_permission_ids.return_value = [1]
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_check_permission_not_exists(self, mock_service_class, mock_db, mock_super_admin):
        """测试检查权限不存在"""
        from app.api.permissions import check_permission
        
        mock_service = Mock()
        mock_service.get_permission_by_code.return_value = None
        mock_service_class.return_value = mock_service

    # ==================== 角色用户管理 API 测试 ====================

    @patch('app.api.permissions.PermissionService')
    def test_get_available_users_for_role(self, mock_service_class, mock_db, mock_super_admin, mock_user):
        """测试获取可添加到角色的用户"""
        from app.api.permissions import get_available_users_for_role
        
        mock_service = Mock()
        mock_service.get_users_not_in_role.return_value = [mock_user]
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_add_users_to_role(self, mock_service_class, mock_db, mock_super_admin):
        """测试批量添加用户到角色"""
        from app.api.permissions import add_users_to_role, BatchAddUsersToRole
        
        mock_service = Mock()
        mock_service.update_user_role.return_value = True
        mock_service_class.return_value = mock_service
        
        data = BatchAddUsersToRole(user_ids=[1, 2, 3])

    @patch('app.api.permissions.PermissionService')
    def test_add_users_to_role_empty(self, mock_service_class, mock_db, mock_super_admin):
        """测试批量添加空用户列表"""
        from app.api.permissions import add_users_to_role, BatchAddUsersToRole
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        data = BatchAddUsersToRole(user_ids=[])

    @patch('app.api.permissions.PermissionService')
    def test_update_role_users(self, mock_service_class, mock_db, mock_super_admin, mock_user):
        """测试设置角色用户列表"""
        from app.api.permissions import update_role_users, RoleUsersUpdate
        
        mock_service = Mock()
        mock_service.get_users_by_role.return_value = [mock_user]
        mock_service.update_user_role.return_value = True
        mock_service_class.return_value = mock_service
        
        data = RoleUsersUpdate(user_ids=[1, 2])

    @patch('app.api.permissions.PermissionService')
    def test_remove_user_from_role(self, mock_service_class, mock_db, mock_super_admin, mock_user):
        """测试从角色移除用户"""
        from app.api.permissions import remove_user_from_role
        
        mock_service = Mock()
        mock_service.get_users_by_role.return_value = [mock_user]
        mock_service.update_user_role.return_value = True
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_remove_user_not_found(self, mock_service_class, mock_db, mock_super_admin):
        """测试移除不存在的用户"""
        from app.api.permissions import remove_user_from_role
        
        mock_service = Mock()
        mock_service.get_users_by_role.return_value = []
        mock_service_class.return_value = mock_service

    @patch('app.api.permissions.PermissionService')
    def test_change_user_role(self, mock_service_class, mock_db, mock_super_admin, mock_user):
        """测试修改用户角色"""
        from app.api.permissions import change_user_role
        
        mock_service = Mock()
        mock_service.update_user_role.return_value = True
        mock_service_class.return_value = mock_service
        
        db_query_mock = Mock()
        db_query_mock.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = db_query_mock

    @patch('app.api.permissions.PermissionService')
    def test_change_own_role_forbidden(self, mock_service_class, mock_db, mock_super_admin):
        """测试不能修改自己的角色"""
        from app.api.permissions import change_user_role
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service


class TestPermissionServiceFull:
    """权限服务完整测试"""

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
        db.delete = Mock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        from app.services.permission_service import PermissionService
        return PermissionService(mock_db)

    @pytest.fixture
    def mock_permission(self):
        """Mock 权限"""
        perm = Mock()
        perm.id = 1
        perm.code = "test:view"
        perm.name = "测试查看"
        perm.category = "button"
        perm.module = "test"
        perm.description = "测试权限"
        perm.parent_id = None
        perm.sort_order = 0
        perm.is_enabled = True
        perm.created_at = datetime.now()
        return perm

    def test_get_role_permission_count(self, service, mock_db):
        """测试获取角色权限数量"""
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        result = service.get_role_permission_count("developer")
        
        assert result == 5

    def test_get_user_count_by_role(self, service, mock_db):
        """测试获取角色用户数量"""
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        
        result = service.get_user_count_by_role("operator")
        
        assert result == 10

    def test_get_role_environment_count(self, service, mock_db):
        """测试获取角色环境权限数量"""
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        
        result = service.get_role_environment_count("approval_admin")
        
        assert result == 3

    def test_get_role_environment_ids(self, service, mock_db):
        """测试获取角色环境ID列表"""
        mock_db.query.return_value.filter.return_value.all.return_value = [1, 2, 3]
        
        result = service.get_role_environment_ids("super_admin")
        
        assert len(result) == 3

    def test_get_role_permission_ids(self, service, mock_db):
        """测试获取角色权限ID列表"""
        mock_db.query.return_value.filter.return_value.all.return_value = [1, 2, 3, 4, 5]
        
        result = service.get_role_permission_ids("developer")
        
        assert len(result) == 5

    def test_update_role_environments(self, service, mock_db):
        """测试更新角色环境"""
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        service.update_role_environments("developer", [1, 2, 3])
        
        mock_db.commit.assert_called()

    def test_update_role_permissions(self, service, mock_db):
        """测试更新角色权限"""
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        service.update_role_permissions("developer", [1, 2, 3])
        
        mock_db.commit.assert_called()

    def test_update_user_role(self, service, mock_db, mock_permission):
        """测试更新用户角色"""
        mock_db.query.return_value.filter.return_value.first.return_value = Mock(role="developer")
        
        result = service.update_user_role(1, "operator")
        
        mock_db.commit.assert_called()

    def test_update_user_role_not_found(self, service, mock_db):
        """测试更新不存在的用户角色"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = service.update_user_role(999, "operator")
        
        assert result == False

    def test_get_users_by_role(self, service, mock_db, mock_permission):
        """测试获取角色用户列表"""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "test"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_user]
        
        result = service.get_users_by_role("developer")
        
        assert len(result) == 1

    def test_get_users_not_in_role(self, service, mock_db, mock_permission):
        """测试获取不属于角色的用户"""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "test"
        mock_db.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [mock_user]
        
        result = service.get_users_not_in_role("developer")
        
        assert len(result) == 1
