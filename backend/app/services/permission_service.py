"""
权限服务

提供功能权限和数据权限的检查与管理

权限模型：RBAC + 数据权限混合模型
- 功能权限：通过 Permission + RolePermission 管理
- 数据权限（环境权限）：通过 RoleEnvironment 管理
- 用户继承角色的所有权限
"""
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import User, UserRole, Environment
from app.models.permissions import (
    Permission, RolePermission, BatchOperationLog, RoleEnvironment,
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
        # 获取用户角色的权限列表（包括超级管理员也从数据库获取）
        # 处理 role 类型：如果是 UserRole enum，获取其字符串值
        role_value = user.role.value if isinstance(user.role, UserRole) else user.role
        permissions = self.get_role_permissions(role_value)
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

    def clear_cache(self) -> None:
        """清除权限缓存"""
        self._permission_cache.clear()

    def warmup_cache(self) -> None:
        """预热权限缓存，加载所有角色的权限"""
        all_roles = [
            'super_admin', 'approval_admin', 'operator', 
            'developer', 'readonly'
        ]
        for role in all_roles:
            self.get_role_permissions(role)

    # ==================== 数据权限 ====================
    
    def get_user_environment_ids(self, user: User) -> Set[int]:
        """
        获取用户可访问的环境ID列表
        
        用户的环境权限 = 用户所属角色的环境权限
        
        Args:
            user: 用户对象
        
        Returns:
            环境ID集合
        """
        # 从 RoleEnvironment 获取角色的环境权限（包括超级管理员也从数据库获取）
        role = user.role.value if isinstance(user.role, UserRole) else user.role
        role_envs = self.db.query(RoleEnvironment.environment_id).filter(
            RoleEnvironment.role == role
        ).all()
        return {re.environment_id for re in role_envs}
    
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
    
    # ==================== 权限管理方法 ====================
    
    def get_permissions(self, module: Optional[str] = None, category: Optional[str] = None) -> List[Permission]:
        """
        获取权限列表
        
        Args:
            module: 模块过滤
            category: 类别过滤
        
        Returns:
            权限列表
        """
        query = self.db.query(Permission)
        if module:
            query = query.filter(Permission.module == module)
        if category:
            query = query.filter(Permission.category == category)
        return query.order_by(Permission.sort_order, Permission.id).all()
    
    def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """
        根据编码获取权限
        
        Args:
            code: 权限编码
        
        Returns:
            权限对象或 None
        """
        return self.db.query(Permission).filter(Permission.code == code).first()
    
    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """
        根据 ID 获取权限
        
        Args:
            permission_id: 权限 ID
        
        Returns:
            权限对象或 None
        """
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    def create_permission(self, code: str, name: str, category: str = "button", 
                          module: Optional[str] = None, description: Optional[str] = None,
                          parent_id: Optional[int] = None, sort_order: int = 0) -> Permission:
        """
        创建权限
        
        Args:
            code: 权限编码
            name: 权限名称
            category: 权限类别
            module: 所属模块
            description: 描述
            parent_id: 父权限 ID
            sort_order: 排序
        
        Returns:
            创建的权限对象
        """
        permission = Permission(
            code=code,
            name=name,
            category=category,
            module=module,
            description=description,
            parent_id=parent_id,
            sort_order=sort_order
        )
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission
    
    def update_permission(self, permission_id: int, **kwargs) -> Optional[Permission]:
        """
        更新权限
        
        Args:
            permission_id: 权限 ID
            **kwargs: 更新字段
        
        Returns:
            更新后的权限对象或 None
        """
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            return None
        
        for key, value in kwargs.items():
            if hasattr(permission, key):
                setattr(permission, key, value)
        
        self.db.commit()
        self.db.refresh(permission)
        return permission
    
    def delete_permission(self, permission_id: int) -> bool:
        """
        删除权限
        
        Args:
            permission_id: 权限 ID
        
        Returns:
            是否删除成功
        """
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            return False
        
        # 删除关联的角色权限
        self.db.query(RolePermission).filter(RolePermission.permission_id == permission_id).delete()
        self.db.delete(permission)
        self.db.commit()
        return True
    
    # ==================== 角色权限管理方法 ====================
    
    def get_role_permission_ids(self, role: str) -> List[int]:
        """
        获取角色的权限 ID 列表
        
        Args:
            role: 角色代码
        
        Returns:
            权限 ID 列表
        """
        role_perms = self.db.query(RolePermission).filter(RolePermission.role == role).all()
        return [rp.permission_id for rp in role_perms]
    
    def get_role_permission_count(self, role: str) -> int:
        """
        获取角色的权限数量
        
        Args:
            role: 角色代码
        
        Returns:
            权限数量
        """
        return self.db.query(RolePermission).filter(RolePermission.role == role).count()
    
    def update_role_permissions(self, role: str, permission_ids: List[int]) -> None:
        """
        更新角色权限
        
        Args:
            role: 角色代码
            permission_ids: 权限 ID 列表
        """
        # 删除原有权限
        self.db.query(RolePermission).filter(RolePermission.role == role).delete()
        
        # 添加新权限
        for perm_id in permission_ids:
            role_perm = RolePermission(role=role, permission_id=perm_id)
            self.db.add(role_perm)
        
        self.db.commit()
    
    # ==================== 角色环境权限管理方法 ====================
    
    def get_role_environment_ids(self, role: str) -> List[int]:
        """
        获取角色的环境权限 ID 列表
        
        Args:
            role: 角色代码
        
        Returns:
            环境 ID 列表
        """
        env_perms = self.db.query(RoleEnvironment).filter(RoleEnvironment.role == role).all()
        return [ep.environment_id for ep in env_perms]
    
    def get_role_environment_count(self, role: str) -> int:
        """
        获取角色的环境权限数量
        
        Args:
            role: 角色代码
        
        Returns:
            环境权限数量
        """
        return self.db.query(RoleEnvironment).filter(RoleEnvironment.role == role).count()
    
    def update_role_environments(self, role: str, environment_ids: List[int]) -> None:
        """
        更新角色的环境权限
        
        Args:
            role: 角色代码
            environment_ids: 环境 ID 列表
        """
        # 删除原有环境权限
        self.db.query(RoleEnvironment).filter(RoleEnvironment.role == role).delete()
        
        # 添加新环境权限
        for env_id in environment_ids:
            role_env = RoleEnvironment(role=role, environment_id=env_id)
            self.db.add(role_env)
        
        self.db.commit()
    
    # ==================== 用户角色管理方法 ====================
    
    def get_users_by_role(self, role: str) -> List[User]:
        """
        获取指定角色的用户列表
        
        Args:
            role: 角色代码
        
        Returns:
            用户列表
        """
        return self.db.query(User).filter(User.role == UserRole(role)).all()
    
    def get_user_count_by_role(self, role: str) -> int:
        """
        获取指定角色的用户数量
        
        Args:
            role: 角色代码
        
        Returns:
            用户数量
        """
        return self.db.query(User).filter(User.role == UserRole(role)).count()
    
    def get_users_not_in_role(self, role: str, search: Optional[str] = None, limit: int = 100) -> List[User]:
        """
        获取不属于指定角色的用户列表
        
        Args:
            role: 角色代码
            search: 搜索关键词
            limit: 返回数量限制
        
        Returns:
            用户列表
        """
        query = self.db.query(User).filter(User.role != UserRole(role))
        
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%")) |
                (User.real_name.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%"))
            )
        
        return query.order_by(User.id).limit(limit).all()
    
    def update_user_role(self, user_id: int, role: str) -> bool:
        """
        更新用户角色
        
        Args:
            user_id: 用户 ID
            role: 新角色代码
        
        Returns:
            是否更新成功
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.role = UserRole(role)
        self.db.commit()
        return True


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
