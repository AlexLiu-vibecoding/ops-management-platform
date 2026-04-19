"""
权限模型

权限设计：RBAC + 数据权限混合模型
- 功能权限：菜单、按钮级别的权限控制
- 数据权限：基于环境的数据访问控制（绑定到角色）

核心原则：权限绑定角色，用户继承角色权限
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnvironment(Base):
    """角色-环境关联表：角色能访问哪些环境"""
    __tablename__ = "role_environments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role = Column(String(50), nullable=False, comment="角色")
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False, comment="环境ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 唯一约束：一个角色对一个环境只有一条记录
    __table_args__ = (
        UniqueConstraint('role', 'environment_id', name='uq_role_environment'),
    )
    
    environment = relationship("Environment")


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限编码")
    name = Column(String(100), nullable=False, comment="权限名称")
    category = Column(String(50), comment="权限类别：menu/button/api")
    module = Column(String(50), comment="所属模块")
    description = Column(String(200), comment="描述")
    parent_id = Column(Integer, ForeignKey("permissions.id", ondelete="SET NULL"), comment="父权限ID")
    sort_order = Column(Integer, default=0, comment="排序")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    children = relationship("Permission", backref="parent", remote_side=[id])
    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role = Column(String(50), nullable=False, comment="角色")
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, comment="权限ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    permission = relationship("Permission", back_populates="role_permissions")


class BatchOperationLog(Base):
    """批量操作日志表"""
    __tablename__ = "batch_operation_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="操作人ID")
    username = Column(String(50), comment="操作人用户名")
    operation_type = Column(String(50), nullable=False, comment="操作类型")
    resource_type = Column(String(50), nullable=False, comment="资源类型：instance/environment/approval")
    resource_ids = Column(JSON, comment="资源ID列表")
    total_count = Column(Integer, default=0, comment="总数")
    success_count = Column(Integer, default=0, comment="成功数")
    failed_count = Column(Integer, default=0, comment="失败数")
    no_permission_count = Column(Integer, default=0, comment="无权限数")
    details = Column(JSON, comment="详细结果")
    request_ip = Column(String(50), comment="请求IP")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# ==================== 权限常量定义 ====================

class PermissionCode:
    """权限编码常量"""
    
    # 实例管理
    INSTANCE_VIEW = "instance:view"
    INSTANCE_CREATE = "instance:create"
    INSTANCE_UPDATE = "instance:update"
    INSTANCE_DELETE = "instance:delete"
    INSTANCE_TEST = "instance:test"
    INSTANCE_BATCH_DELETE = "instance:batch_delete"
    INSTANCE_BATCH_ENABLE = "instance:batch_enable"
    INSTANCE_BATCH_DISABLE = "instance:batch_disable"
    
    # 环境管理
    ENVIRONMENT_VIEW = "environment:view"
    ENVIRONMENT_CREATE = "environment:create"
    ENVIRONMENT_UPDATE = "environment:update"
    ENVIRONMENT_DELETE = "environment:delete"
    ENVIRONMENT_BATCH_DELETE = "environment:batch_delete"
    
    # 变更管理
    APPROVAL_VIEW = "approval:view"
    APPROVAL_CREATE = "approval:create"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_EXECUTE = "approval:execute"
    APPROVAL_REVOKE = "approval:revoke"
    APPROVAL_DELETE = "approval:delete"
    APPROVAL_BATCH_APPROVE = "approval:batch_approve"
    APPROVAL_BATCH_REJECT = "approval:batch_reject"
    APPROVAL_BATCH_DELETE = "approval:batch_delete"
    
    # 监控管理
    MONITOR_VIEW = "monitor:view"
    MONITOR_CONFIG = "monitor:config"
    
    # 脚本管理
    SCRIPT_VIEW = "script:view"
    SCRIPT_CREATE = "script:create"
    SCRIPT_EXECUTE = "script:execute"
    SCRIPT_DELETE = "script:delete"
    
    # 通知管理
    NOTIFICATION_VIEW = "notification:view"
    NOTIFICATION_CHANNEL_MANAGE = "notification:channel_manage"
    NOTIFICATION_BINDING_MANAGE = "notification:binding_manage"
    NOTIFICATION_TEMPLATE_MANAGE = "notification:template_manage"
    NOTIFICATION_SILENCE_MANAGE = "notification:silence_manage"
    NOTIFICATION_RATE_LIMIT_MANAGE = "notification:rate_limit_manage"
    
    # 系统管理
    USER_MANAGE = "system:user_manage"
    ROLE_MANAGE = "system:role_manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_LOG = "system:audit_log"
    
    # 调度器管理
    SCHEDULER_VIEW = "scheduler:view"
    SCHEDULER_MANAGE = "scheduler:manage"
    
    # AI 模型管理
    AI_MODEL_VIEW = "ai:model_view"
    AI_MODEL_MANAGE = "ai:model_manage"


# ==================== 默认角色权限配置 ====================

DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": [
        # 实例管理 - 全部权限
        PermissionCode.INSTANCE_VIEW,
        PermissionCode.INSTANCE_CREATE,
        PermissionCode.INSTANCE_UPDATE,
        PermissionCode.INSTANCE_DELETE,
        PermissionCode.INSTANCE_TEST,
        PermissionCode.INSTANCE_BATCH_DELETE,
        PermissionCode.INSTANCE_BATCH_ENABLE,
        PermissionCode.INSTANCE_BATCH_DISABLE,
        # 环境管理 - 全部权限
        PermissionCode.ENVIRONMENT_VIEW,
        PermissionCode.ENVIRONMENT_CREATE,
        PermissionCode.ENVIRONMENT_UPDATE,
        PermissionCode.ENVIRONMENT_DELETE,
        PermissionCode.ENVIRONMENT_BATCH_DELETE,
        # 变更管理 - 全部权限
        PermissionCode.APPROVAL_VIEW,
        PermissionCode.APPROVAL_CREATE,
        PermissionCode.APPROVAL_APPROVE,
        PermissionCode.APPROVAL_EXECUTE,
        PermissionCode.APPROVAL_REVOKE,
        PermissionCode.APPROVAL_DELETE,
        PermissionCode.APPROVAL_BATCH_APPROVE,
        PermissionCode.APPROVAL_BATCH_REJECT,
        PermissionCode.APPROVAL_BATCH_DELETE,
        # 监控管理
        PermissionCode.MONITOR_VIEW,
        PermissionCode.MONITOR_CONFIG,
        # 脚本管理
        PermissionCode.SCRIPT_VIEW,
        PermissionCode.SCRIPT_CREATE,
        PermissionCode.SCRIPT_EXECUTE,
        PermissionCode.SCRIPT_DELETE,
        # 通知管理 - 全部权限
        PermissionCode.NOTIFICATION_VIEW,
        PermissionCode.NOTIFICATION_CHANNEL_MANAGE,
        PermissionCode.NOTIFICATION_BINDING_MANAGE,
        PermissionCode.NOTIFICATION_TEMPLATE_MANAGE,
        PermissionCode.NOTIFICATION_SILENCE_MANAGE,
        PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE,
        # 系统管理
        PermissionCode.USER_MANAGE,
        PermissionCode.ROLE_MANAGE,
        PermissionCode.SYSTEM_CONFIG,
        PermissionCode.AUDIT_LOG,
        # 调度器管理
        PermissionCode.SCHEDULER_VIEW,
        PermissionCode.SCHEDULER_MANAGE,
        # AI 模型管理
        PermissionCode.AI_MODEL_VIEW,
        PermissionCode.AI_MODEL_MANAGE,
    ],
    "approval_admin": [
        # 实例管理 - 查看、测试
        PermissionCode.INSTANCE_VIEW,
        PermissionCode.INSTANCE_CREATE,
        PermissionCode.INSTANCE_UPDATE,
        PermissionCode.INSTANCE_TEST,
        # 环境管理 - 查看
        PermissionCode.ENVIRONMENT_VIEW,
        # 变更管理 - 审批执行
        PermissionCode.APPROVAL_VIEW,
        PermissionCode.APPROVAL_CREATE,
        PermissionCode.APPROVAL_APPROVE,
        PermissionCode.APPROVAL_EXECUTE,
        PermissionCode.APPROVAL_REVOKE,
        PermissionCode.APPROVAL_BATCH_APPROVE,
        PermissionCode.APPROVAL_BATCH_REJECT,
        # 监控管理
        PermissionCode.MONITOR_VIEW,
        PermissionCode.MONITOR_CONFIG,
        # 脚本管理
        PermissionCode.SCRIPT_VIEW,
        PermissionCode.SCRIPT_CREATE,
        PermissionCode.SCRIPT_EXECUTE,
        # 通知管理 - 查看、模板管理
        PermissionCode.NOTIFICATION_VIEW,
        PermissionCode.NOTIFICATION_TEMPLATE_MANAGE,
        # 审计日志
        PermissionCode.AUDIT_LOG,
        # 调度器管理
        PermissionCode.SCHEDULER_VIEW,
        PermissionCode.SCHEDULER_MANAGE,
    ],
    "operator": [
        # 实例管理 - 查看、创建、编辑、测试
        PermissionCode.INSTANCE_VIEW,
        PermissionCode.INSTANCE_CREATE,
        PermissionCode.INSTANCE_UPDATE,
        PermissionCode.INSTANCE_TEST,
        # 环境管理 - 查看
        PermissionCode.ENVIRONMENT_VIEW,
        # 变更管理 - 申请、撤回
        PermissionCode.APPROVAL_VIEW,
        PermissionCode.APPROVAL_CREATE,
        PermissionCode.APPROVAL_REVOKE,
        # 监控管理 - 查看
        PermissionCode.MONITOR_VIEW,
        # 脚本管理 - 查看、执行
        PermissionCode.SCRIPT_VIEW,
        PermissionCode.SCRIPT_EXECUTE,
        # 通知管理 - 查看
        PermissionCode.NOTIFICATION_VIEW,
        # 调度器管理 - 查看
        PermissionCode.SCHEDULER_VIEW,
    ],
    "developer": [
        # 实例管理 - 仅查看
        PermissionCode.INSTANCE_VIEW,
        PermissionCode.INSTANCE_TEST,
        # 环境管理 - 仅查看
        PermissionCode.ENVIRONMENT_VIEW,
        # 变更管理 - 申请、撤回（开发人员需要提交SQL变更）
        PermissionCode.APPROVAL_VIEW,
        PermissionCode.APPROVAL_CREATE,
        PermissionCode.APPROVAL_REVOKE,
        # 监控管理 - 查看
        PermissionCode.MONITOR_VIEW,
        # 脚本管理 - 仅查看
        PermissionCode.SCRIPT_VIEW,
        # 通知管理 - 查看
        PermissionCode.NOTIFICATION_VIEW,
        # 调度器管理 - 查看
        PermissionCode.SCHEDULER_VIEW,
    ],
    "readonly": [
        # 实例管理 - 仅查看
        PermissionCode.INSTANCE_VIEW,
        # 环境管理 - 仅查看
        PermissionCode.ENVIRONMENT_VIEW,
        # 变更管理 - 仅查看
        PermissionCode.APPROVAL_VIEW,
        # 监控管理 - 仅查看
        PermissionCode.MONITOR_VIEW,
        # 脚本管理 - 仅查看
        PermissionCode.SCRIPT_VIEW,
        # 调度器管理 - 仅查看
        PermissionCode.SCHEDULER_VIEW,
    ]
}
