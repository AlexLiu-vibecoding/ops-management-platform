"""
权限管理 API 测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime


class TestPermissionsAPI:
    """权限管理 API 测试"""

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
    def mock_user(self):
        """Mock 超级管理员用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = "super_admin"
        user.is_super_admin = True
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

    # ==================== Schema 测试 ====================

    def test_permission_create_schema(self):
        """测试权限创建 Schema"""
        from app.api.permissions import PermissionCreate
        
        data = PermissionCreate(
            code="test:create",
            name="测试创建",
            category="button",
            module="test"
        )
        
        assert data.code == "test:create"
        assert data.name == "测试创建"
        assert data.category == "button"
        assert data.module == "test"

    def test_permission_update_schema(self):
        """测试权限更新 Schema"""
        from app.api.permissions import PermissionUpdate
        
        data = PermissionUpdate(name="新名称")
        
        assert data.name == "新名称"
        assert data.category is None

    def test_role_create_schema(self):
        """测试角色创建 Schema"""
        from app.api.permissions import RoleCreate
        
        data = RoleCreate(role="test_role", permission_ids=[1, 2, 3])
        
        assert data.role == "test_role"
        assert len(data.permission_ids) == 3

    def test_role_permission_update_schema(self):
        """测试角色权限更新 Schema"""
        from app.api.permissions import RolePermissionUpdate
        
        data = RolePermissionUpdate(role="admin", permission_ids=[1, 2])
        
        assert data.role == "admin"
        assert len(data.permission_ids) == 2

    def test_role_environment_update_schema(self):
        """测试角色环境权限更新 Schema"""
        from app.api.permissions import RoleEnvironmentUpdate
        
        data = RoleEnvironmentUpdate(environment_ids=[1, 2, 3])
        
        assert len(data.environment_ids) == 3

    def test_batch_add_users_schema(self):
        """测试批量添加用户 Schema"""
        from app.api.permissions import BatchAddUsersToRole
        
        data = BatchAddUsersToRole(user_ids=[1, 2, 3])
        
        assert len(data.user_ids) == 3

    # ==================== 角色定义测试 ====================

    def test_get_role_info(self):
        """测试获取角色信息"""
        from app.api.permissions import get_role_info, ROLES
        
        # 测试 super_admin
        result = get_role_info("super_admin")
        assert result is not None
        assert result["role"] == "super_admin"
        assert result["name"] == "超级管理员"
        
        # 测试不存在的角色
        result = get_role_info("nonexistent")
        assert result is None

    def test_roles_defined(self):
        """测试所有角色都已定义"""
        from app.api.permissions import ROLES
        
        expected_roles = ["super_admin", "approval_admin", "operator", "developer", "readonly"]
        
        for role in expected_roles:
            found = any(r["role"] == role for r in ROLES)
            assert found, f"角色 {role} 未定义"

    # ==================== 路由注册测试 ====================

    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.permissions import router
        
        assert router.prefix == "/api/v1/permissions"

    def test_router_tags(self):
        """测试路由标签"""
        from app.api.permissions import router
        
        assert "权限管理" in router.tags


class TestPermissionService:
    """权限服务测试"""

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

    def test_get_permissions(self, service, mock_db, mock_permission):
        """测试获取权限列表"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_permission]
        
        result = service.get_permissions()
        
        assert len(result) == 1
        assert result[0] == mock_permission

    def test_get_permission_by_code(self, service, mock_db, mock_permission):
        """测试根据编码获取权限"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission
        
        result = service.get_permission_by_code("test:view")
        
        assert result == mock_permission

    def test_create_permission(self, service, mock_db):
        """测试创建权限"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = service.create_permission(
            code="test:create",
            name="测试创建",
            category="button",
            module="test"
        )
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_update_permission(self, service, mock_db, mock_permission):
        """测试更新权限"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission
        
        result = service.update_permission(1, name="新名称")
        
        mock_db.commit.assert_called()

    def test_delete_permission(self, service, mock_db, mock_permission):
        """测试删除权限"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission
        
        result = service.delete_permission(1)
        
        mock_db.delete.assert_called_with(mock_permission)
        mock_db.commit.assert_called()
