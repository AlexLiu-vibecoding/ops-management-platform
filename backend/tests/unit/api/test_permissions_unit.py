"""
权限管理API测试
"""
import pytest
from datetime import datetime


class TestPermissionSchemas:
    """测试权限Schema"""
    
    def test_permission_create_fields(self):
        """测试权限创建Schema字段"""
        from app.api.permissions import PermissionCreate
        
        fields = PermissionCreate.model_fields
        assert 'code' in fields
        assert 'name' in fields
        assert 'category' in fields
        assert 'module' in fields
        assert 'description' in fields
    
    def test_permission_update_fields(self):
        """测试权限更新Schema字段"""
        from app.api.permissions import PermissionUpdate
        
        fields = PermissionUpdate.model_fields
        assert 'name' in fields
        assert 'category' in fields
        assert 'is_enabled' in fields
    
    def test_role_permission_update_fields(self):
        """测试角色权限更新Schema"""
        from app.api.permissions import RolePermissionUpdate
        
        fields = RolePermissionUpdate.model_fields
        assert 'role' in fields
        assert 'permission_ids' in fields
    
    def test_role_create_fields(self):
        """测试角色创建Schema"""
        from app.api.permissions import RoleCreate
        
        fields = RoleCreate.model_fields
        assert 'role' in fields
        assert 'permission_ids' in fields
    
    def test_role_environment_update_fields(self):
        """测试角色环境更新Schema"""
        from app.api.permissions import RoleEnvironmentUpdate
        
        fields = RoleEnvironmentUpdate.model_fields
        assert 'environment_ids' in fields
    
    def test_role_users_update_fields(self):
        """测试角色用户更新Schema"""
        from app.api.permissions import RoleUsersUpdate
        
        fields = RoleUsersUpdate.model_fields
        assert 'user_ids' in fields
    
    def test_batch_add_users_fields(self):
        """测试批量添加用户Schema"""
        from app.api.permissions import BatchAddUsersToRole
        
        fields = BatchAddUsersToRole.model_fields
        assert 'user_ids' in fields


class TestRoleDefinitions:
    """测试角色定义"""
    
    def test_roles_defined(self):
        """测试角色列表已定义"""
        from app.api.permissions import ROLES
        
        assert len(ROLES) == 5
    
    def test_super_admin_role(self):
        """测试超级管理员角色"""
        from app.api.permissions import ROLES, get_role_info
        
        role = get_role_info("super_admin")
        assert role is not None
        assert role["role"] == "super_admin"
        assert "name" in role
        assert "description" in role
        assert "color" in role
    
    def test_approval_admin_role(self):
        """测试审批管理员角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("approval_admin")
        assert role is not None
        assert role["role"] == "approval_admin"
    
    def test_operator_role(self):
        """测试运维人员角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("operator")
        assert role is not None
        assert role["role"] == "operator"
    
    def test_developer_role(self):
        """测试开发人员角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("developer")
        assert role is not None
        assert role["role"] == "developer"
    
    def test_readonly_role(self):
        """测试只读用户角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("readonly")
        assert role is not None
        assert role["role"] == "readonly"
    
    def test_unknown_role(self):
        """测试未知角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("unknown_role")
        assert role is None


class TestRoleInfoFunction:
    """测试角色信息函数"""
    
    def test_get_existing_role(self):
        """测试获取已存在的角色"""
        from app.api.permissions import get_role_info
        
        for role_code in ["super_admin", "approval_admin", "operator", "developer", "readonly"]:
            role = get_role_info(role_code)
            assert role is not None
            assert role["role"] == role_code
    
    def test_get_nonexistent_role(self):
        """测试获取不存在的角色"""
        from app.api.permissions import get_role_info
        
        role = get_role_info("nonexistent")
        assert role is None


class TestPermissionRouter:
    """测试路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.permissions import router
        
        assert router.prefix == "/api/v1/permissions"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.permissions import router
        
        assert "权限管理" in router.tags


class TestPermissionModels:
    """测试权限模型"""
    
    def test_permission_model(self):
        """测试权限模型"""
        from app.models.permissions import Permission
        
        assert Permission is not None
    
    def test_role_permission_model(self):
        """测试角色权限模型"""
        from app.models.permissions import RolePermission
        
        assert RolePermission is not None
    
    def test_role_environment_model(self):
        """测试角色环境模型"""
        from app.models.permissions import RoleEnvironment
        
        assert RoleEnvironment is not None
    
    def test_permission_code_model(self):
        """测试权限码模型"""
        from app.models.permissions import PermissionCode
        
        assert PermissionCode is not None


class TestPermissionService:
    """测试权限服务"""
    
    def test_permission_service_import(self):
        """测试权限服务可导入"""
        from app.services.permission_service import PermissionService
        
        assert PermissionService is not None


class TestDefaultPermissions:
    """测试默认权限"""
    
    def test_default_role_permissions(self):
        """测试默认角色权限"""
        from app.models.permissions import DEFAULT_ROLE_PERMISSIONS
        
        assert isinstance(DEFAULT_ROLE_PERMISSIONS, dict)
        assert "super_admin" in DEFAULT_ROLE_PERMISSIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
