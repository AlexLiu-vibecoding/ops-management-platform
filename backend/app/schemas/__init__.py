"""
Pydantic模型（请求/响应模型）
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from app.models import UserRole, EnvironmentType, ApprovalStatus, MonitorType, RegistrationStatus


# ============ 用户相关 ============
class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    captcha: Optional[str] = Field(None, description="验证码")


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)
    real_name: str = Field(..., max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.READONLY


class UserUpdate(BaseModel):
    """更新用户请求"""
    real_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[UserRole] = None
    status: Optional[bool] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    real_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    role: UserRole
    status: bool
    last_login_time: Optional[datetime]
    last_login_ip: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============ 注册相关 ============
class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    real_name: str = Field(..., max_length=50, description="真实姓名")
    email: EmailStr = Field(..., description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    reason: Optional[str] = Field(None, max_length=500, description="申请理由")


class RegistrationAction(BaseModel):
    """注册审批操作请求"""
    approved: bool
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")


class RegistrationResponse(BaseModel):
    """注册申请响应"""
    id: int
    username: str
    real_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    reason: Optional[str]
    status: RegistrationStatus
    reviewer_id: Optional[int]
    reviewer_name: Optional[str] = Field(None, description="审批人姓名")
    review_time: Optional[datetime]
    review_comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 环境相关 ============
class EnvironmentCreate(BaseModel):
    """创建环境请求"""
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=20)
    color: str = Field("#52C41A", max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    require_approval: bool = True


class EnvironmentUpdate(BaseModel):
    """更新环境请求"""
    name: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    require_approval: Optional[bool] = None
    status: Optional[bool] = None


class EnvironmentResponse(BaseModel):
    """环境响应"""
    id: int
    name: str
    code: str
    color: str
    description: Optional[str]
    require_approval: bool
    status: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 实例相关 ============
class InstanceCreate(BaseModel):
    """创建实例请求"""
    name: str = Field(..., max_length=100)
    host: str = Field(..., max_length=100)
    port: int = Field(3306, ge=1, le=65535)
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=1)
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=200)


class InstanceUpdate(BaseModel):
    """更新实例请求"""
    name: Optional[str] = Field(None, max_length=100)
    host: Optional[str] = Field(None, max_length=100)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, min_length=1)
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=200)
    status: Optional[bool] = None


class InstanceResponse(BaseModel):
    """实例响应"""
    id: int
    name: str
    host: str
    port: int
    username: str
    environment_id: Optional[int]
    group_id: Optional[int]
    description: Optional[str]
    status: bool
    last_check_time: Optional[datetime]
    created_at: datetime
    environment: Optional[EnvironmentResponse] = None
    
    class Config:
        from_attributes = True


class InstanceTestResult(BaseModel):
    """实例连接测试结果"""
    success: bool
    message: str
    version: Optional[str] = None


# ============ 监控开关相关 ============
class MonitorSwitchUpdate(BaseModel):
    """更新监控开关请求"""
    enabled: bool
    config: Optional[Dict[str, Any]] = None


class MonitorSwitchResponse(BaseModel):
    """监控开关响应"""
    id: int
    instance_id: int
    monitor_type: MonitorType
    enabled: bool
    config: Optional[Dict[str, Any]]
    configured_at: datetime
    
    class Config:
        from_attributes = True


class GlobalMonitorSwitchUpdate(BaseModel):
    """全局监控开关更新"""
    monitor_type: MonitorType
    enabled: bool


# ============ 钉钉通道相关 ============
class DingTalkChannelCreate(BaseModel):
    """创建钉钉通道请求"""
    name: str = Field(..., max_length=100)
    webhook: str = Field(..., max_length=500)
    auth_type: str = Field("none", description="验证类型：none/keyword/sign")
    secret: Optional[str] = Field(None, max_length=100, description="加签密钥")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    description: Optional[str] = Field(None, max_length=200)


class DingTalkChannelUpdate(BaseModel):
    """更新钉钉通道请求"""
    name: Optional[str] = Field(None, max_length=100)
    webhook: Optional[str] = Field(None, max_length=500)
    auth_type: Optional[str] = Field(None, description="验证类型：none/keyword/sign")
    secret: Optional[str] = Field(None, max_length=100, description="加签密钥")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    description: Optional[str] = Field(None, max_length=200)
    is_enabled: Optional[bool] = None


class DingTalkChannelResponse(BaseModel):
    """钉钉通道响应"""
    id: int
    name: str
    description: Optional[str]
    auth_type: str
    keywords: Optional[List[str]]
    is_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationBindingCreate(BaseModel):
    """创建通知绑定请求"""
    channel_id: int
    notification_type: str  # approval/alert/operation
    environment_id: Optional[int] = None
    instance_id: Optional[int] = None


# ============ 审批相关 ============
class ApprovalCreate(BaseModel):
    """创建审批请求"""
    title: str = Field(..., max_length=200)
    change_type: str  # DDL/DML/OPERATION/CUSTOM
    instance_id: int
    database_name: Optional[str] = None
    sql_content: str
    sql_line_count: Optional[int] = Field(None, description="SQL行数")
    scheduled_time: Optional[datetime] = None
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class ApprovalAction(BaseModel):
    """审批操作请求"""
    approved: bool
    comment: Optional[str] = Field(None, max_length=500)


class ApprovalResponse(BaseModel):
    """审批响应"""
    id: int
    title: str
    change_type: str
    instance_id: int
    database_name: Optional[str]
    sql_content: Optional[str] = Field(None, description="SQL内容（详情时返回）")
    sql_content_preview: Optional[str] = Field(None, description="SQL预览（前100行）")
    sql_line_count: Optional[int] = Field(None, description="SQL总行数")
    sql_risk_level: Optional[str]
    status: ApprovalStatus
    requester_id: int
    requester_name: Optional[str] = Field(None, description="申请人姓名")
    approver_id: Optional[int]
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    approve_comment: Optional[str]
    scheduled_time: Optional[datetime]
    created_at: datetime
    approved_at: Optional[datetime] = Field(None, description="审批时间")
    instance_name: Optional[str] = Field(None, description="实例名称")
    
    class Config:
        from_attributes = True


# ============ 性能监控相关 ============
class PerformanceMetricResponse(BaseModel):
    """性能指标响应"""
    id: int
    instance_id: int
    collect_time: datetime
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    disk_io_read: Optional[float]
    disk_io_write: Optional[float]
    connections: Optional[int]
    qps: Optional[float]
    tps: Optional[float]
    lock_wait_count: Optional[int]
    
    class Config:
        from_attributes = True


class PerformanceAlertCreate(BaseModel):
    """创建性能告警规则"""
    metric_type: str  # cpu/memory/disk/connections/qps/tps/lock_wait
    threshold: float
    operator: str  # >/</>=/<=/==


# ============ SQL执行相关 ============
class SQLExecuteRequest(BaseModel):
    """SQL执行请求"""
    instance_id: int
    database_name: Optional[str] = None
    sql: str
    need_snapshot: bool = False  # 是否需要生成快照


class SQLExecuteResponse(BaseModel):
    """SQL执行响应"""
    success: bool
    message: str
    affected_rows: Optional[int] = None
    columns: Optional[List[str]] = None
    data: Optional[List[Dict[str, Any]]] = None
    execution_time: Optional[float] = None
    snapshot_id: Optional[int] = None


# ============ 慢查询相关 ============
class SlowQueryResponse(BaseModel):
    """慢查询响应"""
    id: int
    instance_id: int
    database_name: Optional[str]
    sql_fingerprint: str
    sql_sample: Optional[str]
    query_time: Optional[float]
    lock_time: Optional[float]
    rows_sent: Optional[int]
    rows_examined: Optional[int]
    execution_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============ 索引管理相关 ============
class IndexAnalysisResponse(BaseModel):
    """索引分析响应"""
    id: int
    instance_id: int
    database_name: Optional[str]
    table_name: Optional[str]
    index_name: Optional[str]
    index_type: Optional[str]
    columns: Optional[str]
    issue_type: Optional[str]
    risk_level: Optional[str]
    suggestion: Optional[str]
    
    class Config:
        from_attributes = True


class IndexOperationRequest(BaseModel):
    """索引操作请求"""
    instance_id: int
    database_name: str
    table_name: str
    operation: str  # create/drop
    index_name: Optional[str] = None
    columns: Optional[List[str]] = None
    index_type: str = "BTREE"


# ============ 操作回滚相关 ============
class SnapshotResponse(BaseModel):
    """快照响应"""
    id: int
    instance_id: int
    database_name: Optional[str]
    table_name: Optional[str]
    operation_type: Optional[str]
    original_sql: Optional[str]
    row_count: Optional[int]
    status: str
    expire_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RollbackRequest(BaseModel):
    """回滚请求"""
    snapshot_id: int
    reason: str = Field(..., max_length=500)


# ============ 审计日志相关 ============
class AuditLogResponse(BaseModel):
    """审计日志响应"""
    id: int
    user_id: Optional[int]
    username: Optional[str]
    instance_id: Optional[int]
    instance_name: Optional[str]
    environment_id: Optional[int]
    environment_name: Optional[str]
    operation_type: str
    operation_detail: Optional[str]
    request_ip: Optional[str]
    request_method: Optional[str]
    request_path: Optional[str]
    response_code: Optional[int]
    response_message: Optional[str]
    execution_time: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 通用响应 ============
class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int
    data: List[Any]


# ============ 菜单配置相关 ============
class MenuConfigCreate(BaseModel):
    """创建菜单配置请求"""
    parent_id: Optional[int] = Field(None, description="父菜单ID")
    name: str = Field(..., max_length=50, description="菜单名称")
    path: Optional[str] = Field(None, max_length=200, description="路由路径")
    icon: Optional[str] = Field(None, max_length=50, description="图标名称")
    component: Optional[str] = Field(None, max_length=200, description="组件路径")
    sort_order: int = Field(0, description="排序")
    is_visible: bool = Field(True, description="是否显示")
    is_enabled: bool = Field(True, description="是否启用")
    roles: Optional[str] = Field(None, max_length=200, description="可见角色，逗号分隔")
    meta: Optional[Dict[str, Any]] = Field(None, description="其他配置")


class MenuConfigUpdate(BaseModel):
    """更新菜单配置请求"""
    parent_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=50)
    path: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = Field(None, max_length=50)
    component: Optional[str] = Field(None, max_length=200)
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    is_enabled: Optional[bool] = None
    roles: Optional[str] = Field(None, max_length=200)
    meta: Optional[Dict[str, Any]] = None


class MenuConfigResponse(BaseModel):
    """菜单配置响应"""
    id: int
    parent_id: Optional[int]
    name: str
    path: Optional[str]
    icon: Optional[str]
    component: Optional[str]
    sort_order: int
    is_visible: bool
    is_enabled: bool
    roles: Optional[str]
    meta: Optional[Dict[str, Any]]
    created_at: datetime
    children: Optional[List['MenuConfigResponse']] = None
    
    class Config:
        from_attributes = True


class MenuItemResponse(BaseModel):
    """前端菜单项响应"""
    id: int
    name: str
    path: str
    icon: Optional[str]
    children: Optional[List['MenuItemResponse']] = None
