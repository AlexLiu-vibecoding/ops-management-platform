"""
权限服务

提供功能权限和数据权限的检查与管理
"""
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import User, UserRole, Environment, UserEnvironment
from app.models.permissions import (
    Permission, RolePermission, BatchOperationLog,
    PermissionCode, DEFAULT_ROLE_PERMISSIONS
)


class PermissionService:
    """权限服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self._permission_cache = {}  # 权限缓存
    
    # ==================== 功能权限 ====================
    
    def has_permission(self, user: User, permission_code: str) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user: 用户对象
            permission_code: 权限编码
        
        Returns:
            是否有权限
        """
        # 超级管理员拥有所有权限
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        # 获取用户角色的权限列表
        permissions = self.get_role_permissions(user.role)
        return permission_code in permissions
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """
        获取角色的权限列表
        
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
        role_perms = self.db.query(RolePermission).join(Permission).filter(
            RolePermission.role == role,
            Permission.is_enabled == True
        ).all()
        
        if role_perms:
            permissions = {rp.permission.code for rp in role_perms}
        else:
            # 如果数据库没有配置，使用默认配置
            permissions = set(DEFAULT_ROLE_PERMISSIONS.get(role, []))
        
        # 缓存结果
        self._permission_cache[cache_key] = permissions
        return permissions
    
    def check_permission(self, user: User, permission_code: str) -> None:
        """
        检查权限，无权限时抛出异常
        
        Args:
            user: 用户对象
            permission_code: 权限编码
        
        Raises:
            HTTPException: 权限不足
        """
        if not self.has_permission(user, permission_code):
            raise HTTPException(
                status_code=403,
                detail=f"无权限: {permission_code}"
            )
    
    # ==================== 数据权限 ====================
    
    def get_user_environment_ids(self, user: User) -> Set[int]:
        """
        获取用户可访问的环境ID列表
        
        Args:
            user: 用户对象
        
        Returns:
            环境ID集合
        """
        # 超级管理员可访问所有环境
        if user.role == UserRole.SUPER_ADMIN:
            envs = self.db.query(Environment.id).filter(Environment.status == True).all()
            return {env.id for env in envs}
        
        # 普通用户按关联获取
        user_envs = self.db.query(UserEnvironment.environment_id).filter(
            UserEnvironment.user_id == user.id
        ).all()
        return {ue.environment_id for ue in user_envs}
    
    def has_environment_access(self, user: User, environment_id: int) -> bool:
        """
        检查用户是否有指定环境的访问权限
        
        Args:
            user: 用户对象
            environment_id: 环境ID
        
        Returns:
            是否有权限
        """
        accessible_envs = self.get_user_environment_ids(user)
        return environment_id in accessible_envs
    
    def check_environment_access(self, user: User, environment_id: int) -> None:
        """
        检查环境访问权限，无权限时抛出异常
        
        Args:
            user: 用户对象
            environment_id: 环境ID
        
        Raises:
            HTTPException: 无权限
        """
        if not self.has_environment_access(user, environment_id):
            raise HTTPException(
                status_code=403,
                detail="无权访问此环境"
            )
    
    # ==================== 保护级别检查 ====================
    
    def check_batch_operation_allowed(
        self, 
        user: User, 
        environment_id: int,
        operation_count: int
    ) -> tuple[bool, str]:
        """
        检查批量操作是否允许
        
        Args:
            user: 用户对象
            environment_id: 环境ID
            operation_count: 操作数量
        
        Returns:
            (是否允许, 原因)
        """
        # 获取环境信息
        environment = self.db.query(Environment).filter(
            Environment.id == environment_id
        ).first()
        
        if not environment:
            return False, "环境不存在"
        
        # 根据保护级别检查
        if environment.protection_level == 2:
            # 核心环境：禁止批量操作
            return False, "核心环境禁止批量操作，请逐个处理"
        
        if environment.protection_level == 1:
            # 重要环境：批量操作需要二次确认（前端处理）
            if operation_count > 5:
                return False, "重要环境单次最多操作5条"
        
        return True, ""
    
    # ==================== 权限管理 ====================
    
    def init_default_permissions(self) -> None:
        """初始化默认权限数据"""
        # 创建权限记录
        permissions_data = [
            # 实例管理
            {"code": PermissionCode.INSTANCE_VIEW, "name": "查看实例", "module": "实例管理", "category": "menu"},
            {"code": PermissionCode.INSTANCE_CREATE, "name": "创建实例", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_UPDATE, "name": "编辑实例", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_DELETE, "name": "删除实例", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_TEST, "name": "测试连接", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_BATCH_DELETE, "name": "批量删除实例", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_BATCH_ENABLE, "name": "批量启用实例", "module": "实例管理", "category": "button"},
            {"code": PermissionCode.INSTANCE_BATCH_DISABLE, "name": "批量停用实例", "module": "实例管理", "category": "button"},
            
            # 环境管理
            {"code": PermissionCode.ENVIRONMENT_VIEW, "name": "查看环境", "module": "环境管理", "category": "menu"},
            {"code": PermissionCode.ENVIRONMENT_CREATE, "name": "创建环境", "module": "环境管理", "category": "button"},
            {"code": PermissionCode.ENVIRONMENT_UPDATE, "name": "编辑环境", "module": "环境管理", "category": "button"},
            {"code": PermissionCode.ENVIRONMENT_DELETE, "name": "删除环境", "module": "环境管理", "category": "button"},
            {"code": PermissionCode.ENVIRONMENT_BATCH_DELETE, "name": "批量删除环境", "module": "环境管理", "category": "button"},
            
            # 变更管理
            {"code": PermissionCode.APPROVAL_VIEW, "name": "查看变更", "module": "变更管理", "category": "menu"},
            {"code": PermissionCode.APPROVAL_CREATE, "name": "提交变更", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_APPROVE, "name": "审批变更", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_EXECUTE, "name": "执行变更", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_REVOKE, "name": "撤回变更", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_DELETE, "name": "删除变更", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_BATCH_APPROVE, "name": "批量通过", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_BATCH_REJECT, "name": "批量拒绝", "module": "变更管理", "category": "button"},
            {"code": PermissionCode.APPROVAL_BATCH_DELETE, "name": "批量删除变更", "module": "变更管理", "category": "button"},
            
            # 监控管理
            {"code": PermissionCode.MONITOR_VIEW, "name": "查看监控", "module": "监控管理", "category": "menu"},
            {"code": PermissionCode.MONITOR_CONFIG, "name": "配置监控", "module": "监控管理", "category": "button"},
            
            # 脚本管理
            {"code": PermissionCode.SCRIPT_VIEW, "name": "查看脚本", "module": "脚本管理", "category": "menu"},
            {"code": PermissionCode.SCRIPT_CREATE, "name": "创建脚本", "module": "脚本管理", "category": "button"},
            {"code": PermissionCode.SCRIPT_EXECUTE, "name": "执行脚本", "module": "脚本管理", "category": "button"},
            {"code": PermissionCode.SCRIPT_DELETE, "name": "删除脚本", "module": "脚本管理", "category": "button"},
            
            # 系统管理
            {"code": PermissionCode.USER_MANAGE, "name": "用户管理", "module": "系统管理", "category": "menu"},
            {"code": PermissionCode.ROLE_MANAGE, "name": "角色管理", "module": "系统管理", "category": "menu"},
            {"code": PermissionCode.SYSTEM_CONFIG, "name": "系统配置", "module": "系统管理", "category": "menu"},
            {"code": PermissionCode.AUDIT_LOG, "name": "审计日志", "module": "系统管理", "category": "menu"},
        ]
        
        for perm_data in permissions_data:
            existing = self.db.query(Permission).filter(
                Permission.code == perm_data["code"]
            ).first()
            if not existing:
                permission = Permission(**perm_data)
                self.db.add(permission)
        
        self.db.commit()
        
        # 创建角色权限关联
        self._init_role_permissions()
    
    def _init_role_permissions(self) -> None:
        """初始化角色权限关联"""
        for role, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
            for code in permission_codes:
                permission = self.db.query(Permission).filter(
                    Permission.code == code
                ).first()
                
                if permission:
                    existing = self.db.query(RolePermission).filter(
                        RolePermission.role == role,
                        RolePermission.permission_id == permission.id
                    ).first()
                    
                    if not existing:
                        role_perm = RolePermission(role=role, permission_id=permission.id)
                        self.db.add(role_perm)
        
        self.db.commit()
    
    def clear_cache(self) -> None:
        """清除权限缓存"""
        self._permission_cache.clear()


class BatchOperationService:
    """批量操作服务"""
    
    def __init__(self, db: Session, permission_service: PermissionService):
        self.db = db
        self.permission_service = permission_service
    
    def filter_by_data_permission(
        self, 
        user: User, 
        items: List, 
        environment_field: str = "environment_id"
    ) -> tuple[List, List]:
        """
        按数据权限过滤项目
        
        Args:
            user: 用户对象
            items: 项目列表
            environment_field: 环境ID字段名
        
        Returns:
            (有权限的项目, 无权限的项目)
        """
        accessible_envs = self.permission_service.get_user_environment_ids(user)
        
        has_permission = []
        no_permission = []
        
        for item in items:
            env_id = getattr(item, environment_field, None)
            if env_id in accessible_envs:
                has_permission.append(item)
            else:
                no_permission.append(item)
        
        return has_permission, no_permission
    
    def log_batch_operation(
        self,
        user: User,
        operation_type: str,
        resource_type: str,
        resource_ids: List[int],
        results: dict,
        request_ip: str = None
    ) -> BatchOperationLog:
        """
        记录批量操作日志
        
        Args:
            user: 用户对象
            operation_type: 操作类型
            resource_type: 资源类型
            resource_ids: 资源ID列表
            results: 操作结果
            request_ip: 请求IP
        
        Returns:
            操作日志记录
        """
        log = BatchOperationLog(
            user_id=user.id,
            username=user.username,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_ids=resource_ids,
            total_count=results.get("total", 0),
            success_count=results.get("succeeded", 0),
            failed_count=results.get("failed", 0),
            no_permission_count=results.get("no_permission", 0),
            details=results.get("details", []),
            request_ip=request_ip
        )
        self.db.add(log)
        self.db.commit()
        
        return log
