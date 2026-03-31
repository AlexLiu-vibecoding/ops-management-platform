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
    # AWS 配置（可选）
    aws_region: Optional[str] = Field(None, max_length=50, description="AWS 区域")
    aws_access_key_id: Optional[str] = Field(None, max_length=100, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")


class EnvironmentUpdate(BaseModel):
    """更新环境请求"""
    name: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=200)
    require_approval: Optional[bool] = None
    status: Optional[bool] = None
    # AWS 配置（可选）
    aws_region: Optional[str] = Field(None, max_length=50, description="AWS 区域")
    aws_access_key_id: Optional[str] = Field(None, max_length=100, description="AWS Access Key ID")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")


class EnvironmentResponse(BaseModel):
    """环境响应"""
    id: int
    name: str
    code: str
    color: str
    description: Optional[str]
    require_approval: bool
    status: bool
    # AWS 配置状态
    aws_region: Optional[str]
    aws_configured: Optional[bool] = False
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 实例相关 ============
class InstanceCreate(BaseModel):
    """创建实例请求"""
    name: str = Field(..., max_length=100)
    db_type: str = Field("mysql", pattern="^(mysql|postgresql|redis)$")
    host: Optional[str] = Field(None, max_length=100, description="主机地址，RDS实例可选")
    port: Optional[int] = Field(None, ge=1, le=65535, description="端口，RDS实例可选")
    username: Optional[str] = Field(None, max_length=50, description="用户名，RDS实例可选，Redis不需要")
    password: Optional[str] = Field(None, description="密码，RDS实例可选，Redis可选")
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=200)
    status: Optional[bool] = Field(True, description="状态")
    # AWS RDS 相关
    is_rds: bool = Field(False, description="是否为 AWS RDS 实例")
    rds_instance_id: Optional[str] = Field(None, max_length=100, description="AWS RDS 实例标识符")
    aws_region: Optional[str] = Field(None, max_length=50, description="AWS 区域")
    # Redis 特有字段
    redis_mode: Optional[str] = Field("standalone", pattern="^(standalone|cluster|sentinel)$", description="Redis模式")
    redis_db: Optional[int] = Field(0, ge=0, le=15, description="Redis数据库索引")


class InstanceUpdate(BaseModel):
    """更新实例请求"""
    name: Optional[str] = Field(None, max_length=100)
    db_type: Optional[str] = Field(None, pattern="^(mysql|postgresql|redis)$")
    host: Optional[str] = Field(None, max_length=100)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=50)
    password: Optional[str] = Field(None, description="密码，Redis可选")
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=200)
    status: Optional[bool] = None
    # AWS RDS 相关
    is_rds: Optional[bool] = None
    rds_instance_id: Optional[str] = Field(None, max_length=100)
    aws_region: Optional[str] = Field(None, max_length=50)
    # Redis 特有字段
    redis_mode: Optional[str] = Field(None, pattern="^(standalone|cluster|sentinel)$")
    redis_db: Optional[int] = Field(None, ge=0, le=15)


class InstanceResponse(BaseModel):
    """实例响应"""
    id: int
    name: str
    db_type: str = "mysql"
    host: str
    port: int
    username: Optional[str]
    environment_id: Optional[int]
    group_id: Optional[int]
    description: Optional[str]
    status: bool
    # AWS RDS 相关
    is_rds: bool = False
    rds_instance_id: Optional[str] = None
    aws_region: Optional[str] = None
    # Redis 特有字段
    redis_mode: Optional[str] = "standalone"
    redis_db: Optional[int] = 0
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
    change_type: str  # DDL/DML/OPERATION/CUSTOM/REDIS
    instance_id: int
    database_mode: Optional[str] = Field("single", description="数据库选择模式: single/multiple/pattern/all/auto")
    database_name: Optional[str] = Field(None, description="单库模式时的数据库名")
    database_list: Optional[List[str]] = Field(None, description="多库模式时的数据库列表")
    database_pattern: Optional[str] = Field(None, description="通配符模式")
    matched_database_count: Optional[int] = Field(None, description="通配符匹配的数据库数量")
    parsed_databases: Optional[List[str]] = Field(None, description="SQL解析出的数据库列表")
    sql_content: str
    sql_line_count: Optional[int] = Field(None, description="SQL行数")
    affected_rows_estimate: Optional[int] = Field(None, description="预估影响行数")
    auto_execute: Optional[bool] = Field(False, description="审批通过后自动执行")
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
    database_mode: Optional[str] = Field(None, description="数据库选择模式")
    database_name: Optional[str]
    database_list: Optional[List[str]] = Field(None, description="多库列表")
    database_pattern: Optional[str] = Field(None, description="通配符模式")
    matched_database_count: Optional[int] = Field(None, description="匹配数量")
    database_target: Optional[str] = Field(None, description="目标数据库描述")
    sql_content: Optional[str] = Field(None, description="SQL内容（详情时返回）")
    sql_content_preview: Optional[str] = Field(None, description="SQL预览（前100行）")
    sql_file_path: Optional[str] = Field(None, description="SQL文件路径")
    sql_download_url: Optional[str] = Field(None, description="SQL文件下载URL")
    sql_line_count: Optional[int] = Field(None, description="SQL总行数")
    sql_risk_level: Optional[str]
    rollback_sql: Optional[str] = Field(None, description="回滚SQL")
    rollback_file_path: Optional[str] = Field(None, description="回滚SQL文件路径")
    rollback_download_url: Optional[str] = Field(None, description="回滚SQL下载URL")
    rollback_generated: Optional[bool] = Field(False, description="是否已生成回滚SQL")
    file_storage_type: Optional[str] = Field("database", description="存储类型")
    affected_rows_estimate: Optional[int] = Field(None, description="预估影响行数")
    affected_rows_actual: Optional[int] = Field(None, description="实际影响行数")
    auto_execute: Optional[bool] = Field(False, description="审批通过后自动执行")
    status: ApprovalStatus
    requester_id: int
    requester_name: Optional[str] = Field(None, description="申请人姓名")
    approver_id: Optional[int]
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    approve_comment: Optional[str]
    scheduled_time: Optional[datetime]
    execute_time: Optional[datetime] = Field(None, description="执行时间")
    execute_result: Optional[str] = Field(None, description="执行结果")
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


# ============ SQL优化器相关 ============
class TableSchemaSyncRequest(BaseModel):
    """表结构同步请求"""
    instance_id: int = Field(..., description="实例ID")
    database_name: Optional[str] = Field(None, description="数据库名，不传则同步所有库")
    table_names: Optional[List[str]] = Field(None, description="指定表名列表")


class ColumnInfo(BaseModel):
    """列信息"""
    name: str
    data_type: str
    nullable: bool
    default: Optional[str]
    comment: Optional[str]
    is_primary: bool = False
    extra: Optional[str] = None


class IndexInfo(BaseModel):
    """索引信息"""
    name: str
    columns: List[str]
    unique: bool = False
    primary: bool = False
    type: Optional[str] = None
    comment: Optional[str] = None


class TableSchemaResponse(BaseModel):
    """表结构响应"""
    id: int
    instance_id: int
    database_name: str
    table_name: str
    table_type: str
    engine: Optional[str]
    row_count: int
    data_size: int
    index_size: int
    table_comment: Optional[str]
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    sync_time: datetime
    
    class Config:
        from_attributes = True


class SQLAnalyzeRequest(BaseModel):
    """SQL分析请求"""
    instance_id: int = Field(..., description="实例ID")
    database_name: str = Field(..., description="数据库名")
    sql_text: str = Field(..., description="待分析的SQL")
    enable_llm: bool = Field(True, description="是否启用LLM深度分析")


class ExplainRow(BaseModel):
    """EXPLAIN单行结果"""
    id: Optional[int] = None
    select_type: Optional[str] = None
    table: Optional[str] = None
    partitions: Optional[str] = None
    type: Optional[str] = None
    possible_keys: Optional[str] = None
    key: Optional[str] = None
    key_len: Optional[str] = None
    ref: Optional[str] = None
    rows: Optional[int] = None
    filtered: Optional[float] = None
    Extra: Optional[str] = None


class RuleIssue(BaseModel):
    """规则检测结果"""
    severity: str = Field(..., description="严重级别：info/warning/error/critical")
    category: str = Field(..., description="问题分类：index/performance/syntax/risk")
    title: str = Field(..., description="问题标题")
    description: str = Field(..., description="问题描述")
    suggestion: str = Field(..., description="优化建议")
    related_table: Optional[str] = None
    related_index: Optional[str] = None


class SQLAnalysisResponse(BaseModel):
    """SQL分析响应"""
    sql_text: str
    sql_normalized: str
    explain_result: List[ExplainRow]
    rule_issues: List[RuleIssue]
    llm_suggestions: Optional[str] = None
    optimized_sql: Optional[str] = None
    risk_level: str
    analysis_time: float
    summary: Dict[str, Any] = Field(default_factory=dict, description="分析摘要")
    auto_sync_info: Optional[Dict[str, Any]] = Field(default=None, description="自动同步表结构信息")


# ============ SQL 优化闭环相关 ============

# ==================== 优化建议 ====================

class OptimizationSuggestionItem(BaseModel):
    """单个优化建议"""
    type: str = Field(..., description="建议类型: add_index/rewrite_sql/parameter/config")
    description: str = Field(..., description="建议描述")
    sql: Optional[str] = Field(None, description="相关SQL（如CREATE INDEX）")
    reason: str = Field(..., description="建议原因")
    priority: str = Field("medium", description="优先级: high/medium/low")


class OptimizationIssueItem(BaseModel):
    """发现的问题"""
    type: str = Field(..., description="问题类型")
    description: str = Field(..., description="问题描述")
    severity: str = Field("warning", description="严重级别: critical/warning/info")


class OptimizationSuggestionCreate(BaseModel):
    """创建优化建议"""
    instance_id: int
    database_name: Optional[str] = None
    slow_query_id: Optional[int] = None
    sql_fingerprint: str
    sql_sample: Optional[str] = None
    issues: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    suggested_sql: Optional[str] = None
    index_ddl: Optional[str] = None
    rollback_sql: Optional[str] = None
    risk_level: str = "low"
    confidence: Optional[float] = None
    expected_improvement: Optional[str] = None
    table_schemas_used: Optional[List[Dict]] = None
    analysis_time: Optional[float] = None
    llm_model: Optional[str] = None


class OptimizationSuggestionUpdate(BaseModel):
    """更新优化建议"""
    status: Optional[str] = None
    before_avg_time: Optional[float] = None
    after_avg_time: Optional[float] = None
    actual_improvement: Optional[float] = None


class OptimizationSuggestionResponse(BaseModel):
    """优化建议响应"""
    id: int
    instance_id: int
    instance_name: Optional[str] = None
    database_name: Optional[str]
    slow_query_id: Optional[int]
    sql_fingerprint: str
    sql_sample: Optional[str]
    issues: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]
    suggested_sql: Optional[str]
    index_ddl: Optional[str]
    rollback_sql: Optional[str]
    risk_level: str
    confidence: Optional[float]
    expected_improvement: Optional[str]
    status: str
    approval_id: Optional[int]
    adopted_by: Optional[int]
    adopted_at: Optional[datetime]
    before_avg_time: Optional[float]
    after_avg_time: Optional[float]
    actual_improvement: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 采集任务 ====================

class CollectionTaskCreate(BaseModel):
    """创建采集任务"""
    instance_id: int
    enabled: bool = True
    cron_expression: str = "0 */5 * * *"
    min_exec_time: float = Field(1.0, ge=0.1, le=3600, description="最小执行时间阈值")
    top_n: int = Field(100, ge=1, le=1000, description="每次采集Top N")
    auto_analyze: bool = True
    analyze_threshold: int = Field(3, ge=1, le=100, description="执行次数超过阈值才分析")
    llm_analysis: bool = True


class CollectionTaskUpdate(BaseModel):
    """更新采集任务"""
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    min_exec_time: Optional[float] = Field(None, ge=0.1, le=3600)
    top_n: Optional[int] = Field(None, ge=1, le=1000)
    auto_analyze: Optional[bool] = None
    analyze_threshold: Optional[int] = Field(None, ge=1, le=100)
    llm_analysis: Optional[bool] = None


class CollectionTaskResponse(BaseModel):
    """采集任务响应"""
    id: int
    instance_id: int
    instance_name: Optional[str] = None
    enabled: bool
    cron_expression: str
    min_exec_time: float
    top_n: int
    auto_analyze: bool
    analyze_threshold: int
    llm_analysis: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_collected_count: int
    total_collected_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CollectionTaskListResponse(BaseModel):
    """采集任务列表响应"""
    items: List[CollectionTaskResponse]
    total: int
    page: int
    page_size: int


class SuggestionListResponse(BaseModel):
    """优化建议列表响应"""
    items: List[OptimizationSuggestionResponse]
    total: int
    page: int
    page_size: int


class AdoptSuggestionResponse(BaseModel):
    """采用建议响应"""
    id: int
    status: str
    approval_id: int
    approval_url: str
    message: str


class RejectSuggestionRequest(BaseModel):
    """拒绝建议请求"""
    reason: Optional[str] = Field(None, max_length=500, description="拒绝原因")


class VerifySuggestionResponse(BaseModel):
    """验证效果响应"""
    id: int
    before_avg_time: Optional[float]
    after_avg_time: Optional[float]
    actual_improvement: Optional[float]
    message: str


class ManualAnalyzeRequest(BaseModel):
    """手动分析SQL请求"""
    instance_id: int = Field(..., description="实例ID")
    sql_text: str = Field(..., description="待分析的SQL")
    database_name: Optional[str] = Field(None, description="数据库名")


class ManualCollectionResponse(BaseModel):
    """手动触发采集响应"""
    task_id: int
    instance_id: int
    instance_name: str
    collected_count: int
    analyzed_count: int
    message: str
