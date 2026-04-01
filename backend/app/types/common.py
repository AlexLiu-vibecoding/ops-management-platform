"""
类型定义

提供项目中常用的类型定义，确保类型安全
"""
from typing import (
    TypeVar, Generic, Optional, List, Dict, Any, 
    Callable, Awaitable, Union, Tuple, Type
)
from typing_extensions import TypedDict, NotRequired
from datetime import datetime
from enum import Enum


# ==================== 通用类型变量 ====================

T = TypeVar('T')
TModel = TypeVar('TModel')
TSchema = TypeVar('TSchema')


# ==================== 数据库连接类型 ====================

import pymysql
import psycopg2
from psycopg2 import extensions as pg_extensions

# 数据库连接类型
DBConnection = Union[pymysql.Connection, pg_extensions.connection]

# 数据库游标类型
DBCursor = Union[pymysql.cursors.Cursor, pg_extensions.cursor]


# ==================== 分页类型 ====================

class PaginatedResult(TypedDict, Generic[T]):
    """分页结果"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginationParams(TypedDict):
    """分页参数"""
    page: NotRequired[int]
    page_size: NotRequired[int]
    order_by: NotRequired[str]
    order: NotRequired[str]  # 'asc' or 'desc'


# ==================== API 响应类型 ====================

class APIResponse(TypedDict, Generic[T]):
    """标准 API 响应"""
    success: bool
    data: NotRequired[T]
    message: NotRequired[str]
    error: NotRequired[str]


class ListResponse(TypedDict, Generic[T]):
    """列表响应"""
    items: List[T]
    total: int


class MessageResponse(TypedDict):
    """消息响应"""
    message: str


class ErrorResponse(TypedDict):
    """错误响应"""
    error: str
    message: str
    details: NotRequired[Any]


# ==================== 数据库操作结果类型 ====================

class QueryResult(TypedDict, Generic[T]):
    """查询结果"""
    success: bool
    data: List[T]
    affected_rows: int
    columns: NotRequired[List[str]]
    message: NotRequired[str]


class ExecutionResult(TypedDict):
    """执行结果"""
    success: bool
    affected_rows: int
    message: str
    last_insert_id: NotRequired[int]


class ScriptResult(TypedDict):
    """脚本执行结果"""
    success: bool
    results: List[Dict[str, Any]]
    total_affected: int
    summary: str


# ==================== 用户与权限类型 ====================

class UserInfo(TypedDict):
    """用户信息"""
    id: int
    username: str
    real_name: str
    email: str
    role: str
    status: bool
    created_at: datetime
    updated_at: datetime


class Permission(TypedDict):
    """权限"""
    code: str
    name: str
    description: str
    resource: str
    action: str


class RoleInfo(TypedDict):
    """角色信息"""
    name: str
    permissions: List[str]


# ==================== 实例类型 ====================

class InstanceConnectionInfo(TypedDict):
    """实例连接信息"""
    host: str
    port: int
    username: str
    password: str
    database: str


class InstanceStatus(TypedDict):
    """实例状态"""
    id: int
    name: str
    status: bool
    last_check: datetime
    version: str
    connections: int
    uptime: int


class InstanceTestResult(TypedDict):
    """实例连接测试结果"""
    success: bool
    message: str
    version: NotRequired[str]
    latency_ms: NotRequired[int]


# ==================== 监控类型 ====================

class MetricPoint(TypedDict):
    """监控指标点"""
    timestamp: datetime
    value: float


class MetricSeries(TypedDict):
    """监控指标序列"""
    name: str
    unit: str
    points: List[MetricPoint]


class PerformanceMetrics(TypedDict):
    """性能指标"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    connections: int
    qps: int
    tps: int
    slow_queries: int


# ==================== 告警类型 ====================

class AlertRule(TypedDict):
    """告警规则"""
    id: int
    name: str
    metric_type: str
    operator: str
    threshold: float
    severity: str
    enabled: bool
    cooldown: int


class AlertEvent(TypedDict):
    """告警事件"""
    id: int
    rule_id: int
    rule_name: str
    severity: str
    status: str
    message: str
    value: float
    threshold: float
    triggered_at: datetime
    acknowledged_at: NotRequired[datetime]
    resolved_at: NotRequired[datetime]


# ==================== 审批类型 ====================

class ApprovalInfo(TypedDict):
    """审批信息"""
    id: int
    title: str
    type: str
    status: str
    applicant: str
    approver: NotRequired[str]
    created_at: datetime
    scheduled_at: NotRequired[datetime]
    executed_at: NotRequired[datetime]


class ApprovalAction(TypedDict):
    """审批操作"""
    action: str  # 'approve', 'reject', 'execute'
    comment: NotRequired[str]


# ==================== 函数类型别名 ====================

# 同步函数类型
SyncFunc = Callable[..., T]

# 异步函数类型
AsyncFunc = Callable[..., Awaitable[T]]

# 数据库会话工厂
SessionFactory = Callable[[], Any]


# ==================== 枚举类型 ====================

class DBType(str, Enum):
    """数据库类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    REDIS = "redis"


class Environment(str, Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ==================== 工具函数 ====================

def ensure_datetime(value: Union[str, datetime]) -> datetime:
    """确保值为 datetime 类型"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    raise ValueError(f"Cannot convert {type(value)} to datetime")


def ensure_int(value: Union[str, int]) -> int:
    """确保值为 int 类型"""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Cannot convert {type(value)} to int")


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
