"""
类型定义模块

提供项目通用的类型定义
"""

from app.types.common import (
    # 类型变量
    T, TModel, TSchema,
    
    # 数据库类型
    DBConnection, DBCursor,
    
    # 分页类型
    PaginatedResult, PaginationParams,
    
    # API 响应类型
    APIResponse, ListResponse, MessageResponse, ErrorResponse,
    
    # 数据库操作类型
    QueryResult, ExecutionResult, ScriptResult,
    
    # 用户权限类型
    UserInfo, Permission, RoleInfo,
    
    # 实例类型
    InstanceConnectionInfo, InstanceStatus, InstanceTestResult,
    
    # 监控类型
    MetricPoint, MetricSeries, PerformanceMetrics,
    
    # 告警类型
    AlertRule, AlertEvent,
    
    # 审批类型
    ApprovalInfo, ApprovalAction,
    
    # 函数类型
    SyncFunc, AsyncFunc, SessionFactory,
    
    # 枚举类型
    DBType, Environment, ApprovalStatus, AlertSeverity,
    
    # 工具函数
    ensure_datetime, ensure_int,
)

__all__ = [
    # 类型变量
    'T', 'TModel', 'TSchema',
    
    # 数据库类型
    'DBConnection', 'DBCursor',
    
    # 分页类型
    'PaginatedResult', 'PaginationParams',
    
    # API 响应类型
    'APIResponse', 'ListResponse', 'MessageResponse', 'ErrorResponse',
    
    # 数据库操作类型
    'QueryResult', 'ExecutionResult', 'ScriptResult',
    
    # 用户权限类型
    'UserInfo', 'Permission', 'RoleInfo',
    
    # 实例类型
    'InstanceConnectionInfo', 'InstanceStatus', 'InstanceTestResult',
    
    # 监控类型
    'MetricPoint', 'MetricSeries', 'PerformanceMetrics',
    
    # 告警类型
    'AlertRule', 'AlertEvent',
    
    # 审批类型
    'ApprovalInfo', 'ApprovalAction',
    
    # 函数类型
    'SyncFunc', 'AsyncFunc', 'SessionFactory',
    
    # 枚举类型
    'DBType', 'Environment', 'ApprovalStatus', 'AlertSeverity',
    
    # 工具函数
    'ensure_datetime', 'ensure_int',
]
