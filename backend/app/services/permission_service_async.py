"""
异步权限服务层

提供异步的权限检查和管理操作，适用于高并发场景

使用方式：
```python
from app.services.permission_service_async import AsyncPermissionService
from app.database_async import get_async_db_context

async with get_async_db_context() as db:
    perm_service = AsyncPermissionService(db)
    has_perm = await perm_service.has_permission(user, "instance:view")
```
"""
from typing import Set, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.models.permissions import Permission, RolePermission, RoleEnvironment
from app.utils.structured_logger import get_logger

logger = get_logger(__name__)

# 默认角色权限配置（从配置模块导入）
DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": [
        "instance:view", "instance:create", "instance:update", "instance:delete",
        "approval:view", "approval:create", "approval:approve", "approval:execute",
        "system:user_manage", "system:role_manage", "system:config",
        "monitor:view", "script:view", "script:execute"
    ],
    "approval_admin": [
        "approval:view", "approval:approve", "approval:execute"
    ],
    "operator": [
        "instance:view", "instance:create",
        "approval:view", "approval:create",
        "monitor:view", "script:view", "script:execute"
    ],
    "developer": [
        "instance:view", "approval:view", "monitor:view", "script:view"
    ],
    "readonly": [
        "instance:view", "approval:view", "monitor:view"
    ]
}


class AsyncPermissionService:
    """
    异步权限服务类
    
    提供功能权限和数据权限的异步检查
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._permission_cache: dict = {}
    
    async def has_permission(self, user: User, permission_code: str) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user: 用户对象
            permission_code: 权限编码
        
        Returns:
            是否有权限
        """
        permissions = await self.get_role_permissions(user.role)
        return permission_code in permissions
    
    async def get_role_permissions(self, role: str) -> Set[str]:
        """
        获取角色的权限列表（异步查询）
        
        Args:
            role: 角色代码
        
        Returns:
            权限编码集合
        """
        # 首先从缓存获取
        cache_key = f"role_permissions:{role}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        # 从数据库获取
        result = await self.db.execute(
            select(RolePermission, Permission)
            .join(Permission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role == role)
            .where(Permission.is_enabled == True)
        )
        
        rows = result.all()
        if rows:
            permissions = {row[1].code for row in rows}
        else:
            # 如果数据库没有配置，使用默认配置
            permissions = set(DEFAULT_ROLE_PERMISSIONS.get(role, []))
        
        # 缓存结果
        self._permission_cache[cache_key] = permissions
        
        logger.debug(
            "获取角色权限",
            role=role,
            permission_count=len(permissions)
        )
        
        return permissions
    
    async def get_user_environment_ids(self, user: User) -> Set[int]:
        """
        获取用户可访问的环境ID列表
        
        Args:
            user: 用户对象
        
        Returns:
            环境ID集合
        """
        result = await self.db.execute(
            select(RoleEnvironment.environment_id)
            .where(RoleEnvironment.role == user.role)
        )
        
        env_ids = {row[0] for row in result.all()}
        
        # 超级管理员可以访问所有环境
        if user.role == UserRole.SUPER_ADMIN or user.role == "super_admin":
            from app.models import Environment
            env_result = await self.db.execute(select(Environment.id))
            env_ids = {row[0] for row in env_result.all()}
        
        return env_ids
    
    async def check_environment_access(self, user: User, environment_id: int) -> bool:
        """
        检查用户是否有权限访问指定环境
        
        Args:
            user: 用户对象
            environment_id: 环境ID
        
        Returns:
            是否有权限
        """
        env_ids = await self.get_user_environment_ids(user)
        return environment_id in env_ids
    
    async def get_all_permissions(self) -> List[Permission]:
        """
        获取所有权限定义
        
        Returns:
            权限列表
        """
        result = await self.db.execute(
            select(Permission)
            .where(Permission.is_enabled == True)
            .order_by(Permission.category, Permission.code)
        )
        return list(result.scalars().all())
    
    async def get_role_permissions_with_details(self, role: str) -> List[dict]:
        """
        获取角色的权限详情（包含权限名称和描述）
        
        Args:
            role: 角色代码
        
        Returns:
            权限详情列表
        """
        result = await self.db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role == role)
            .where(Permission.is_enabled == True)
        )
        
        permissions = []
        for perm in result.scalars().all():
            permissions.append({
                "id": perm.id,
                "code": perm.code,
                "name": perm.name,
                "category": perm.category,
                "description": perm.description
            })
        
        return permissions
    
    def clear_cache(self):
        """清除权限缓存"""
        self._permission_cache.clear()
        logger.debug("权限缓存已清除")


# ==================== 导出 ====================

__all__ = [
    "AsyncPermissionService",
    "DEFAULT_ROLE_PERMISSIONS",
]
