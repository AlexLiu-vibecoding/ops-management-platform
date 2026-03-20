"""
数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


def get_local_timezone():
    """获取服务器本地时区"""
    try:
        return datetime.now().astimezone().tzinfo.key or "Asia/Shanghai"
    except Exception:
        return "Asia/Shanghai"


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    SUPER_ADMIN = "super_admin"  # 超级管理员
    APPROVAL_ADMIN = "approval_admin"  # 审批管理员
    OPERATOR = "operator"  # 普通运维
    READONLY = "readonly"  # 只读用户


class EnvironmentType(str, enum.Enum):
    """环境类型枚举"""
    DEVELOPMENT = "development"  # 开发环境
    TESTING = "testing"  # 测试环境
    STAGING = "staging"  # 预发环境
    PRODUCTION = "production"  # 生产环境


class ApprovalStatus(str, enum.Enum):
    """审批状态枚举"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已拒绝
    EXECUTED = "executed"  # 已执行
    FAILED = "failed"  # 执行失败


class MonitorType(str, enum.Enum):
    """监控类型枚举"""
    SLOW_QUERY = "slow_query"  # 慢查询监控
    CPU_SQL = "cpu_sql"  # 高CPU SQL监控
    PERFORMANCE = "performance"  # 性能监控
    INSPECTION = "inspection"  # 实例巡检


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), comment="真实姓名")
    email = Column(String(100), unique=True, comment="邮箱")
    phone = Column(String(20), comment="手机号")
    role = Column(SQLEnum(UserRole), default=UserRole.READONLY, comment="角色")
    status = Column(Boolean, default=True, comment="状态：True启用，False禁用")
    failed_login_count = Column(Integer, default=0, comment="登录失败次数")
    locked_until = Column(DateTime, comment="锁定到期时间")
    last_login_time = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    user_environments = relationship("UserEnvironment", back_populates="user")
    approval_requests = relationship("ApprovalRecord", back_populates="requester", foreign_keys="ApprovalRecord.requester_id")
    approval_actions = relationship("ApprovalRecord", back_populates="approver", foreign_keys="ApprovalRecord.approver_id")


class Environment(Base):
    """环境表"""
    __tablename__ = "environments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="环境名称")
    code = Column(String(20), unique=True, nullable=False, comment="环境编码")
    color = Column(String(10), default="#52C41A", comment="颜色标记")
    description = Column(String(200), comment="描述")
    require_approval = Column(Boolean, default=True, comment="是否需要审批")
    status = Column(Boolean, default=True, comment="状态")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    instances = relationship("Instance", back_populates="environment")
    user_environments = relationship("UserEnvironment", back_populates="environment")


class UserEnvironment(Base):
    """用户-环境关联表"""
    __tablename__ = "user_environments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False, comment="环境ID")
    created_at = Column(DateTime, default=datetime.now, comment="绑定时间")
    
    # 关联
    user = relationship("User", back_populates="user_environments")
    environment = relationship("Environment", back_populates="user_environments")


class InstanceGroup(Base):
    """实例分组表"""
    __tablename__ = "instance_groups"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="分组名称")
    description = Column(String(200), comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    instances = relationship("Instance", back_populates="group")


class Instance(Base):
    """MySQL实例表"""
    __tablename__ = "instances"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="实例名称")
    host = Column(String(100), nullable=False, comment="主机地址")
    port = Column(Integer, default=3306, comment="端口")
    username = Column(String(50), nullable=False, comment="用户名")
    password_encrypted = Column(String(255), nullable=False, comment="加密后的密码")
    environment_id = Column(Integer, ForeignKey("environments.id"), comment="环境ID")
    group_id = Column(Integer, ForeignKey("instance_groups.id"), comment="分组ID")
    description = Column(String(200), comment="描述")
    status = Column(Boolean, default=True, comment="在线状态")
    last_check_time = Column(DateTime, comment="最后检测时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    environment = relationship("Environment", back_populates="instances")
    group = relationship("InstanceGroup", back_populates="instances")
    monitor_switches = relationship("MonitorSwitch", back_populates="instance")
    performance_metrics = relationship("PerformanceMetric", back_populates="instance")
    slow_queries = relationship("SlowQuery", back_populates="instance")
    snapshots = relationship("OperationSnapshot", back_populates="instance")


class MonitorSwitch(Base):
    """监控开关表"""
    __tablename__ = "monitor_switches"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    monitor_type = Column(SQLEnum(MonitorType), nullable=False, comment="监控类型")
    enabled = Column(Boolean, default=True, comment="启用状态")
    config = Column(JSON, comment="配置参数JSON")
    configured_by = Column(Integer, ForeignKey("users.id"), comment="配置人ID")
    configured_at = Column(DateTime, default=datetime.now, comment="配置时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    instance = relationship("Instance", back_populates="monitor_switches")


class GlobalConfig(Base):
    """全局配置表"""
    __tablename__ = "global_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置键")
    config_value = Column(String(500), nullable=False, comment="配置值")
    description = Column(String(200), comment="描述")
    updated_by = Column(Integer, ForeignKey("users.id"), comment="更新人ID")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class DingTalkChannel(Base):
    """钉钉通道表"""
    __tablename__ = "dingtalk_channels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="通道名称")
    webhook_encrypted = Column(String(500), nullable=False, comment="加密后的Webhook地址")
    auth_type = Column(String(20), default="none", comment="验证类型：none/keyword/sign")
    secret_encrypted = Column(String(200), comment="加密后的加签密钥")
    keywords = Column(JSON, comment="关键词列表")
    description = Column(String(200), comment="描述")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    notification_bindings = relationship("NotificationBinding", back_populates="channel")


class NotificationBinding(Base):
    """通知绑定表"""
    __tablename__ = "notification_bindings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("dingtalk_channels.id", ondelete="CASCADE"), nullable=False, comment="通道ID")
    notification_type = Column(String(50), nullable=False, comment="通知类型：approval/alert/scheduled_task/operation")
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), comment="环境ID（可选）")
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), comment="实例ID（可选）")
    scheduled_task_id = Column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), comment="定时任务ID（可选）")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    channel = relationship("DingTalkChannel", back_populates="notification_bindings")


class ApprovalRecord(Base):
    """审批记录表"""
    __tablename__ = "approval_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="审批标题")
    change_type = Column(String(50), nullable=False, comment="变更类型：DDL/DML/OPERATION/CUSTOM")
    instance_id = Column(Integer, ForeignKey("instances.id"), comment="实例ID")
    database_mode = Column(String(20), default="single", comment="数据库选择模式: single/multiple/pattern/all/auto")
    database_name = Column(String(100), comment="数据库名")
    database_list = Column(JSON, comment="多库列表")
    database_pattern = Column(String(100), comment="通配符模式")
    matched_database_count = Column(Integer, default=0, comment="匹配的数据库数量")
    sql_content = Column(Text, nullable=False, comment="SQL内容")
    sql_line_count = Column(Integer, default=0, comment="SQL行数")
    sql_risk_level = Column(String(20), comment="风险等级：low/medium/high/critical")
    environment_id = Column(Integer, ForeignKey("environments.id"), comment="环境ID")
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="申请人ID")
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, comment="审批状态")
    approver_id = Column(Integer, ForeignKey("users.id"), comment="审批人ID")
    approve_time = Column(DateTime, comment="审批时间")
    approve_comment = Column(String(500), comment="审批意见")
    execute_time = Column(DateTime, comment="执行时间")
    execute_result = Column(Text, comment="执行结果")
    scheduled_time = Column(DateTime, comment="定时执行时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    requester = relationship("User", back_populates="approval_requests", foreign_keys=[requester_id])
    approver = relationship("User", back_populates="approval_actions", foreign_keys=[approver_id])


class PerformanceMetric(Base):
    """性能监控数据表"""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    collect_time = Column(DateTime, nullable=False, index=True, comment="采集时间")
    cpu_usage = Column(Float, comment="CPU使用率")
    memory_usage = Column(Float, comment="内存使用率")
    disk_io_read = Column(Float, comment="磁盘IO读取")
    disk_io_write = Column(Float, comment="磁盘IO写入")
    connections = Column(Integer, comment="连接数")
    qps = Column(Float, comment="QPS")
    tps = Column(Float, comment="TPS")
    lock_wait_count = Column(Integer, comment="锁等待数")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    instance = relationship("Instance", back_populates="performance_metrics")


class SlowQuery(Base):
    """慢查询记录表"""
    __tablename__ = "slow_queries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    database_name = Column(String(100), comment="数据库名")
    sql_fingerprint = Column(String(500), nullable=False, comment="SQL指纹")
    sql_sample = Column(Text, comment="SQL样例")
    query_time = Column(Float, comment="执行耗时（秒）")
    lock_time = Column(Float, comment="锁等待时间")
    rows_sent = Column(Integer, comment="返回行数")
    rows_examined = Column(Integer, comment="扫描行数")
    execution_count = Column(Integer, default=1, comment="执行次数")
    first_seen = Column(DateTime, comment="首次发现时间")
    last_seen = Column(DateTime, comment="最后发现时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    instance = relationship("Instance", back_populates="slow_queries")


class HighCPUSQL(Base):
    """高CPU SQL记录表"""
    __tablename__ = "high_cpu_sqls"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    process_id = Column(Integer, comment="进程ID")
    sql_content = Column(Text, comment="SQL内容")
    cpu_usage = Column(Float, comment="CPU使用率")
    execution_time = Column(Float, comment="已执行时间（秒）")
    status = Column(String(20), comment="状态：running/killed")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class OperationSnapshot(Base):
    """操作快照表"""
    __tablename__ = "operation_snapshots"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    database_name = Column(String(100), comment="数据库名")
    table_name = Column(String(100), comment="表名")
    operation_type = Column(String(20), comment="操作类型：UPDATE/DELETE")
    original_sql = Column(Text, comment="原始SQL")
    snapshot_data = Column(Text, comment="快照数据（加密存储）")
    row_count = Column(Integer, comment="影响行数")
    approval_id = Column(Integer, ForeignKey("approval_records.id"), comment="关联审批ID")
    status = Column(String(20), default="active", comment="状态：active/used/expired")
    expire_at = Column(DateTime, comment="过期时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    instance = relationship("Instance", back_populates="snapshots")


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), comment="用户ID")
    username = Column(String(50), comment="用户名")
    instance_id = Column(Integer, comment="实例ID")
    instance_name = Column(String(100), comment="实例名称")
    environment_id = Column(Integer, comment="环境ID")
    environment_name = Column(String(50), comment="环境名称")
    operation_type = Column(String(50), nullable=False, comment="操作类型")
    operation_detail = Column(Text, comment="操作详情")
    request_ip = Column(String(50), comment="请求IP")
    request_method = Column(String(10), comment="请求方法")
    request_path = Column(String(200), comment="请求路径")
    request_params = Column(Text, comment="请求参数")
    response_code = Column(Integer, comment="响应码")
    response_message = Column(String(500), comment="响应消息")
    execution_time = Column(Float, comment="执行耗时（毫秒）")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")


class LoginLog(Base):
    """登录日志表"""
    __tablename__ = "login_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), comment="用户ID")
    username = Column(String(50), comment="用户名")
    login_ip = Column(String(50), comment="登录IP")
    login_device = Column(String(200), comment="登录设备")
    login_status = Column(String(20), comment="登录状态：success/failed")
    failure_reason = Column(String(200), comment="失败原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class InspectionReport(Base):
    """巡检报告表"""
    __tablename__ = "inspection_reports"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    report_type = Column(String(20), default="daily", comment="报告类型：daily/weekly/monthly")
    status = Column(String(20), default="pending", comment="状态：pending/completed/failed")
    summary = Column(JSON, comment="巡检摘要")
    details = Column(JSON, comment="巡检详情")
    risk_count_high = Column(Integer, default=0, comment="高风险数量")
    risk_count_medium = Column(Integer, default=0, comment="中风险数量")
    risk_count_low = Column(Integer, default=0, comment="低风险数量")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class IndexAnalysis(Base):
    """索引分析表"""
    __tablename__ = "index_analyses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    database_name = Column(String(100), comment="数据库名")
    table_name = Column(String(100), comment="表名")
    index_name = Column(String(100), comment="索引名")
    index_type = Column(String(50), comment="索引类型")
    columns = Column(String(500), comment="索引列")
    issue_type = Column(String(50), comment="问题类型：redundant/unused/missing")
    risk_level = Column(String(20), comment="风险等级：high/medium/low")
    suggestion = Column(Text, comment="优化建议")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class RegistrationStatus(str, enum.Enum):
    """注册申请状态枚举"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已拒绝


class UserRegistrationRequest(Base):
    """用户注册申请表"""
    __tablename__ = "user_registration_requests"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), comment="真实姓名")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="手机号")
    reason = Column(Text, comment="申请理由")
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, comment="审批状态")
    reviewer_id = Column(Integer, ForeignKey("users.id"), comment="审批人ID")
    review_time = Column(DateTime, comment="审批时间")
    review_comment = Column(String(500), comment="审批意见")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class MenuConfig(Base):
    """菜单配置表"""
    __tablename__ = "menu_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("menu_configs.id", ondelete="SET NULL"), comment="父菜单ID")
    name = Column(String(50), nullable=False, comment="菜单名称")
    path = Column(String(200), comment="路由路径")
    icon = Column(String(50), comment="图标名称")
    component = Column(String(200), comment="组件路径")
    sort_order = Column(Integer, default=0, comment="排序")
    is_visible = Column(Boolean, default=True, comment="是否显示")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    roles = Column(String(200), comment="可见角色，逗号分隔")
    meta = Column(JSON, comment="其他配置")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    children = relationship("MenuConfig", backref="parent", remote_side=[id])


class SystemConfig(Base):
    """系统配置表 - 存储数据库连接、Redis等配置"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置键")
    config_value = Column(Text, comment="配置值（加密存储敏感信息）")
    is_encrypted = Column(Boolean, default=False, comment="是否加密存储")
    description = Column(String(200), comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class SystemInitState(Base):
    """系统初始化状态表"""
    __tablename__ = "system_init_state"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    step = Column(String(50), unique=True, nullable=False, comment="初始化步骤")
    status = Column(String(20), default="pending", comment="状态: pending/completed/failed")
    error_message = Column(Text, comment="错误信息")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# ==================== 运维管理平台 - 脚本执行与定时任务 ====================

class ScriptType(str, enum.Enum):
    """脚本类型枚举"""
    PYTHON = "python"
    BASH = "bash"
    SQL = "sql"


class ExecutionStatus(str, enum.Enum):
    """执行状态枚举"""
    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"    # 失败
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 已取消


class TriggerType(str, enum.Enum):
    """触发类型枚举"""
    MANUAL = "manual"      # 手动触发
    SCHEDULED = "scheduled"  # 定时触发
    API = "api"            # API调用


class Script(Base):
    """脚本管理表"""
    __tablename__ = "scripts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="脚本名称")
    script_type = Column(SQLEnum(ScriptType), default=ScriptType.PYTHON, comment="脚本类型")
    content = Column(Text, nullable=False, comment="脚本内容")
    description = Column(String(500), comment="描述")
    params_schema = Column(JSON, comment="参数定义JSON Schema")
    timeout = Column(Integer, default=300, comment="超时时间（秒）")
    max_retries = Column(Integer, default=0, comment="最大重试次数")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_public = Column(Boolean, default=False, comment="是否公开（所有用户可见）")
    allowed_roles = Column(String(200), comment="允许执行的角色，逗号分隔")
    tags = Column(String(200), comment="标签，逗号分隔")
    version = Column(Integer, default=1, comment="版本号")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("ScriptExecution", back_populates="script")
    scheduled_tasks = relationship("ScheduledTask", back_populates="script")


class ScriptExecution(Base):
    """脚本执行记录表"""
    __tablename__ = "script_executions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), comment="脚本ID")
    script_version = Column(Integer, comment="执行时的脚本版本")
    trigger_type = Column(SQLEnum(TriggerType), default=TriggerType.MANUAL, comment="触发类型")
    scheduled_task_id = Column(Integer, ForeignKey("scheduled_tasks.id"), comment="定时任务ID")
    params = Column(JSON, comment="执行参数")
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING, comment="执行状态")
    output = Column(Text, comment="标准输出")
    error_output = Column(Text, comment="错误输出")
    exit_code = Column(Integer, comment="退出码")
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration = Column(Float, comment="执行时长（秒）")
    triggered_by = Column(Integer, ForeignKey("users.id"), comment="触发人ID")
    trigger_ip = Column(String(50), comment="触发IP")
    retry_count = Column(Integer, default=0, comment="重试次数")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    script = relationship("Script", back_populates="executions")
    trigger_user = relationship("User", foreign_keys=[triggered_by])


class ScheduledTask(Base):
    """定时任务表"""
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="任务名称")
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), comment="脚本ID")
    cron_expression = Column(String(100), nullable=False, comment="Cron表达式")
    params = Column(JSON, comment="执行参数")
    status = Column(String(20), default="enabled", comment="状态：enabled/disabled")
    timezone = Column(String(50), default=get_local_timezone, comment="时区")
    last_run_time = Column(DateTime, comment="上次执行时间")
    last_run_status = Column(String(20), comment="上次执行状态")
    next_run_time = Column(DateTime, comment="下次执行时间")
    run_count = Column(Integer, default=0, comment="执行次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    fail_count = Column(Integer, default=0, comment="失败次数")
    max_history = Column(Integer, default=100, comment="保留历史记录数")
    notify_on_success = Column(Boolean, default=False, comment="成功时通知")
    notify_on_fail = Column(Boolean, default=True, comment="失败时通知")
    notify_channels = Column(String(200), comment="通知通道ID，逗号分隔")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    script = relationship("Script", back_populates="scheduled_tasks")
    creator = relationship("User", foreign_keys=[created_by])
