"""
数据库模型 - 重构版本

架构变更：
- 将 Instance 表拆分为 RDBInstance 和 RedisInstance
- 关联表根据业务类型引用不同的实例表
- 保留公共模型不变

迁移策略：
- migration_006: 创建新表结构
- migration_007: 数据迁移
- migration_008: 清理旧表
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum

# 导入新的实例模型
from app.models.instances import (
    RDBInstance, RedisInstance,
    RDBType, RedisMode,
    RedisSlowLog, RedisMemoryStats, RedisKeyAnalysis
)


def get_local_timezone():
    """获取服务器本地时区"""
    try:
        return datetime.now().astimezone().tzinfo.key or "Asia/Shanghai"
    except Exception:
        return "Asia/Shanghai"


# ==================== 枚举定义 ====================

class UserRole(str, enum.Enum):
    """用户角色枚举"""
    SUPER_ADMIN = "super_admin"
    APPROVAL_ADMIN = "approval_admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    READONLY = "readonly"


class EnvironmentType(str, enum.Enum):
    """环境类型枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ApprovalStatus(str, enum.Enum):
    """审批状态枚举"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class MonitorType(str, enum.Enum):
    """监控类型枚举"""
    SLOW_QUERY = "slow_query"
    CPU_SQL = "cpu_sql"
    PERFORMANCE = "performance"
    INSPECTION = "inspection"
    AI_ANALYSIS = "ai_analysis"


class ScriptType(str, enum.Enum):
    """脚本类型枚举"""
    PYTHON = "python"
    BASH = "bash"
    SQL = "sql"


class ExecutionStatus(str, enum.Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TriggerType(str, enum.Enum):
    """触发类型枚举"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    API = "api"


class RegistrationStatus(str, enum.Enum):
    """注册申请状态枚举"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== 基础模型 ====================

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
    status = Column(Boolean, default=True, comment="状态")
    failed_login_count = Column(Integer, default=0, comment="登录失败次数")
    locked_until = Column(DateTime, comment="锁定到期时间")
    last_login_time = Column(DateTime, comment="最后登录时间")
    last_login_ip = Column(String(50), comment="最后登录IP")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
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
    
    # 保护级别：0-普通，1-重要，2-核心（批量操作受限）
    protection_level = Column(Integer, default=0, comment="保护级别: 0-普通, 1-重要, 2-核心")
    
    # AWS 配置（用于 RDS CloudWatch 指标采集）
    aws_region = Column(String(50), comment="AWS 区域")
    aws_access_key_id = Column(String(100), comment="AWS Access Key ID")
    aws_secret_access_key = Column(String(100), comment="AWS Secret Access Key (加密存储)")
    aws_configured = Column(Boolean, default=False, comment="AWS 凭证是否已配置")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联 - 拆分后的实例
    rdb_instances = relationship("RDBInstance", back_populates="environment")
    redis_instances = relationship("RedisInstance", back_populates="environment")
    user_environments = relationship("UserEnvironment", back_populates="environment")


class UserEnvironment(Base):
    """用户-环境关联表"""
    __tablename__ = "user_environments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
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
    
    # 关联 - 拆分后的实例
    rdb_instances = relationship("RDBInstance", back_populates="group")
    redis_instances = relationship("RedisInstance", back_populates="group")


# ==================== 监控配置 ====================

class MonitorSwitch(Base):
    """监控开关表 - 仅适用于 RDB 实例"""
    __tablename__ = "monitor_switches"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    monitor_type = Column(SQLEnum(MonitorType), nullable=False, comment="监控类型")
    enabled = Column(Boolean, default=True, comment="启用状态")
    config = Column(JSON, comment="配置参数JSON")
    configured_by = Column(Integer, ForeignKey("users.id"), comment="配置人ID")
    configured_at = Column(DateTime, default=datetime.now, comment="配置时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="monitor_switches")


class GlobalConfig(Base):
    """全局配置表"""
    __tablename__ = "global_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置键")
    config_value = Column(String(500), nullable=False, comment="配置值")
    description = Column(String(200), comment="描述")
    updated_by = Column(Integer, ForeignKey("users.id"), comment="更新人ID")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


# ==================== 通知配置 ====================

class NotificationBinding(Base):
    """通知绑定表"""
    __tablename__ = "notification_bindings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(Integer, nullable=False, comment="通道ID (notification_channels.id)")
    notification_type = Column(String(50), nullable=False, comment="通知类型")
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), comment="环境ID")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID")
    scheduled_task_id = Column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), comment="定时任务ID")
    created_at = Column(DateTime, default=datetime.now)


class NotificationLog(Base):
    """通知历史记录表"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 通知类型
    notification_type = Column(String(50), nullable=False, comment="通知类型: approval/alert/scheduled_task")
    sub_type = Column(String(50), comment="细分类型: DDL/DML/critical/warning等")
    
    # 通知渠道 - 支持多种通道类型（钉钉/企微/飞书/邮件/Webhook）
    channel_id = Column(Integer, comment="通道ID (notification_channels.id)")
    channel_name = Column(String(100), comment="通道名称(冗余)")
    
    # 关联资源
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="SET NULL"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="SET NULL"), comment="Redis实例ID")
    approval_id = Column(Integer, ForeignKey("approval_records.id", ondelete="SET NULL"), comment="审批记录ID")
    alert_id = Column(Integer, comment="告警记录ID")
    
    # 通知内容
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, comment="通知内容")
    
    # 发送状态
    status = Column(String(20), default="pending", comment="状态: pending/success/failed")
    error_message = Column(String(500), comment="错误信息")
    
    # 响应信息
    response_code = Column(Integer, comment="HTTP响应码")
    response_data = Column(JSON, comment="响应数据")
    
    # 时间信息
    sent_at = Column(DateTime, comment="发送时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class NotificationTemplate(Base):
    """通知模板表"""
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 基本信息
    name = Column(String(100), nullable=False, unique=True, comment="模板名称")
    description = Column(String(200), comment="模板描述")
    
    # 通知类型
    notification_type = Column(String(50), nullable=False, comment="通知类型: approval/alert/scheduled_task")
    sub_type = Column(String(50), comment="细分类型: DDL/DML/critical/warning等")
    
    # 模板内容
    title_template = Column(String(200), nullable=False, comment="标题模板")
    content_template = Column(Text, nullable=False, comment="内容模板(Markdown)")
    
    # 变量说明（JSON格式）
    variables = Column(JSON, comment="可用变量列表")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否默认模板")
    
    # 时间
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


# ==================== 审批管理 ====================

class ApprovalRecord(Base):
    """审批记录表 - 支持 RDB 和 Redis 实例"""
    __tablename__ = "approval_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="审批标题")
    change_type = Column(String(50), nullable=False, comment="变更类型: DDL/DML/REDIS/CUSTOM")
    
    # 实例引用 - 支持两种类型
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id"), comment="Redis实例ID")
    
    # RDB 相关字段
    database_mode = Column(String(20), default="single", comment="数据库选择模式")
    database_name = Column(String(100), comment="数据库名")
    database_list = Column(JSON, comment="多库列表")
    database_pattern = Column(String(100), comment="通配符模式")
    matched_database_count = Column(Integer, default=0, comment="匹配的数据库数量")
    
    # SQL/命令内容
    sql_content = Column(Text, comment="SQL内容（小文件）")
    sql_file_path = Column(String(500), comment="SQL文件存储路径")
    sql_line_count = Column(Integer, default=0, comment="SQL行数")
    sql_risk_level = Column(String(20), comment="风险等级")
    rollback_sql = Column(Text, comment="回滚SQL")
    rollback_file_path = Column(String(500), comment="回滚SQL文件路径")
    rollback_generated = Column(Boolean, default=False, comment="是否已生成回滚SQL")
    file_storage_type = Column(String(20), default="database", comment="存储类型")
    
    affected_rows_estimate = Column(Integer, default=0, comment="预估影响行数")
    affected_rows_actual = Column(Integer, comment="实际影响行数")
    auto_execute = Column(Boolean, default=False, comment="审批通过后自动执行")
    is_emergency = Column(Boolean, default=False, comment="是否紧急变更")
    
    # 多人审批相关字段
    min_approvers = Column(Integer, default=1, comment="最小审批人数")
    approval_count = Column(Integer, default=0, comment="已审批人数")
    approver_ids = Column(JSON, default=list, comment="已审批人ID列表")
    
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
    rdb_instance = relationship("RDBInstance", back_populates="approval_records")
    redis_instance = relationship("RedisInstance", back_populates="approval_records")
    optimization_suggestions = relationship("OptimizationSuggestion", back_populates="approval")
    approval_flows = relationship("ApprovalFlow", back_populates="approval", cascade="all, delete-orphan")


class ApprovalFlow(Base):
    """审批流程记录表 - 记录每次审批操作"""
    __tablename__ = "approval_flows"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    approval_id = Column(Integer, ForeignKey("approval_records.id", ondelete="CASCADE"), nullable=False, comment="审批记录ID")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="审批人ID")
    action = Column(String(20), nullable=False, comment="操作: approve/reject")
    comment = Column(String(500), comment="审批意见")
    created_at = Column(DateTime, default=datetime.now, comment="审批时间")
    
    # 关联
    approval = relationship("ApprovalRecord", back_populates="approval_flows")
    approver = relationship("User")


# ==================== RDB 性能监控 ====================

class PerformanceMetric(Base):
    """性能监控数据表 - 仅适用于 RDB 实例"""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
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
    
    rdb_instance = relationship("RDBInstance", back_populates="performance_metrics")


class SlowQuery(Base):
    """慢查询记录表 - 仅适用于 RDB 实例"""
    __tablename__ = "slow_queries"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), comment="数据库名")
    sql_fingerprint = Column(String(500), nullable=False, comment="SQL指纹")
    sql_sample = Column(Text, comment="SQL样例")
    digest = Column(String(100), index=True, comment="SQL摘要")
    query_time = Column(Float, comment="执行耗时（秒）")
    lock_time = Column(Float, comment="锁等待时间")
    rows_sent = Column(Integer, comment="返回行数")
    rows_examined = Column(Integer, comment="扫描行数")
    execution_count = Column(Integer, default=1, comment="执行次数")
    first_seen = Column(DateTime, comment="首次发现时间")
    last_seen = Column(DateTime, comment="最后发现时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="slow_queries")
    optimization_suggestions = relationship("OptimizationSuggestion", back_populates="slow_query")


class HighCPUSQL(Base):
    """高CPU SQL记录表 - 仅适用于 RDB 实例"""
    __tablename__ = "high_cpu_sqls"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    process_id = Column(Integer, comment="进程ID")
    sql_content = Column(Text, comment="SQL内容")
    cpu_usage = Column(Float, comment="CPU使用率")
    execution_time = Column(Float, comment="已执行时间（秒）")
    status = Column(String(20), comment="状态")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="high_cpu_sqls")


class OperationSnapshot(Base):
    """操作快照表 - 仅适用于 RDB 实例"""
    __tablename__ = "operation_snapshots"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), comment="数据库名")
    table_name = Column(String(100), comment="表名")
    operation_type = Column(String(20), comment="操作类型")
    original_sql = Column(Text, comment="原始SQL")
    snapshot_data = Column(Text, comment="快照数据")
    row_count = Column(Integer, comment="影响行数")
    approval_id = Column(Integer, ForeignKey("approval_records.id"), comment="关联审批ID")
    status = Column(String(20), default="active", comment="状态")
    expire_at = Column(DateTime, comment="过期时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="snapshots")


# ==================== RDB 监控扩展 ====================

class AlertRecord(Base):
    """告警记录表 - 支持 RDB 和 Redis 实例"""
    __tablename__ = "alert_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID")
    metric_type = Column(String(32), nullable=False, comment="指标类型")
    alert_level = Column(String(16), nullable=False, comment="告警级别")
    alert_title = Column(String(200), nullable=False, comment="告警标题")
    alert_content = Column(Text, comment="告警详情")
    alert_source = Column(String(100), comment="告警来源")
    status = Column(String(16), default="pending", comment="状态")
    acknowledged_by = Column(Integer, ForeignKey("users.id"), comment="确认人ID")
    acknowledged_at = Column(DateTime, comment="确认时间")
    resolved_by = Column(Integer, ForeignKey("users.id"), comment="解决人ID")
    resolved_at = Column(DateTime, comment="解决时间")
    resolve_note = Column(Text, comment="解决说明")
    notification_sent = Column(Boolean, default=False, comment="是否已发送通知")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="alert_records")
    redis_instance = relationship("RedisInstance", back_populates="alert_records")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    resolver = relationship("User", foreign_keys=[resolved_by])


class AlertAggregationRule(Base):
    """告警聚合规则表"""
    __tablename__ = "alert_aggregation_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    metric_type = Column(String(32), comment="指标类型")
    alert_level = Column(String(16), comment="告警级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID")
    aggregation_window = Column(Integer, default=300, comment="聚合时间窗口(秒)")
    min_alert_count = Column(Integer, default=2, comment="最小告警数量")
    aggregation_method = Column(String(20), default="count", comment="聚合方法: count/summary")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")
    aggregations = relationship("AlertAggregation", back_populates="rule", cascade="all, delete-orphan")


class AlertAggregation(Base):
    """告警聚合记录表"""
    __tablename__ = "alert_aggregations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_aggregation_rules.id", ondelete="CASCADE"), comment="规则ID")
    metric_type = Column(String(32), comment="指标类型")
    alert_level = Column(String(16), comment="告警级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID")
    alert_count = Column(Integer, default=1, comment="告警数量")
    alert_ids = Column(JSON, comment="告警ID列表")
    aggregated_content = Column(Text, comment="聚合后的内容")
    notification_sent = Column(Boolean, default=False, comment="是否已发送通知")
    started_at = Column(DateTime, nullable=False, comment="聚合开始时间")
    ended_at = Column(DateTime, comment="聚合结束时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rule = relationship("AlertAggregationRule", back_populates="aggregations")
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")


class AlertSilenceRule(Base):
    """告警静默规则表"""
    __tablename__ = "alert_silence_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    
    # 匹配条件
    metric_type = Column(String(32), comment="指标类型，空表示所有类型")
    alert_level = Column(String(16), comment="告警级别，空表示所有级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID，空表示所有")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID，空表示所有")
    
    # 时间配置
    silence_type = Column(String(20), default="once", comment="静默类型: once/daily/weekly")
    time_start = Column(String(5), comment="开始时间 HH:MM（用于每日/每周重复）")
    time_end = Column(String(5), comment="结束时间 HH:MM（用于每日/每周重复）")
    weekdays = Column(JSON, comment="允许的星期几 [0-6]，0=周一，如[0,1,2,3,4]表示工作日")
    start_date = Column(DateTime, comment="生效开始日期（用于一次性静默）")
    end_date = Column(DateTime, comment="生效结束日期（用于一次性静默）")
    
    # 优先级
    priority = Column(Integer, default=0, comment="优先级，数值越大优先级越高")
    
    # 状态和创建信息
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")
    creator = relationship("User", foreign_keys=[created_by])


class AlertRateLimitRule(Base):
    """告警频率限制规则表"""
    __tablename__ = "alert_rate_limit_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    
    # 匹配条件
    metric_type = Column(String(32), comment="指标类型，空表示所有类型")
    alert_level = Column(String(16), comment="告警级别，空表示所有级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID，空表示所有")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID，空表示所有")
    
    # 频率限制配置
    limit_window = Column(Integer, default=300, comment="限制时间窗口(秒)")
    max_notifications = Column(Integer, default=5, comment="时间窗口内最大通知数量")
    cooldown_period = Column(Integer, default=600, comment="冷却期(秒)，达到限制后的静默时间")
    
    # 状态和创建信息
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级(数字越大优先级越高)")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")
    creator = relationship("User", foreign_keys=[created_by])



class AlertEscalationRule(Base):
    """告警升级规则表"""
    __tablename__ = "alert_escalation_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    alert_level = Column(String(16), nullable=False, comment="告警级别")
    trigger_condition = Column(String(20), default="time", comment="触发条件: time/acknowledge")
    trigger_minutes = Column(Integer, default=30, comment="触发时间(分钟)")
    escalation_level = Column(String(16), comment="升级后的级别")
    escalation_notification = Column(Boolean, default=True, comment="是否发送升级通知")
    additional_channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="SET NULL"), comment="额外通知通道ID")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    additional_channel = relationship("NotificationChannel")


class LockWait(Base):
    """锁等待记录表 - 仅适用于 RDB 实例"""
    __tablename__ = "lock_waits"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), comment="数据库名")
    wait_type = Column(String(32), comment="等待类型")
    waiting_thread_id = Column(Integer, comment="等待线程ID")
    waiting_sql = Column(Text, comment="等待SQL")
    waiting_time = Column(Integer, comment="等待时间(秒)")
    blocking_thread_id = Column(Integer, comment="阻塞线程ID")
    blocking_sql = Column(Text, comment="阻塞SQL")
    blocking_time = Column(Integer, comment="阻塞时长(秒)")
    status = Column(String(16), default="active", comment="状态")
    resolved_at = Column(DateTime, comment="解决时间")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="lock_waits")


class ReplicationStatus(Base):
    """主从复制状态表 - 仅适用于 RDB 实例"""
    __tablename__ = "replication_status"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID(主库)")
    slave_host = Column(String(100), comment="从库地址")
    slave_port = Column(Integer, comment="从库端口")
    slave_io_running = Column(String(16), comment="IO线程状态")
    slave_sql_running = Column(String(16), comment="SQL线程状态")
    seconds_behind_master = Column(Integer, comment="延迟秒数")
    master_log_file = Column(String(100), comment="主库日志文件")
    read_master_log_pos = Column(Integer, comment="读取位置")
    relay_master_log_file = Column(String(100), comment="中继日志文件")
    exec_master_log_pos = Column(Integer, comment="执行位置")
    last_io_error = Column(Text, comment="最后IO错误")
    last_sql_error = Column(Text, comment="最后SQL错误")
    check_time = Column(DateTime, default=datetime.now, comment="检查时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="replication_status")


class LongTransaction(Base):
    """长事务记录表 - 仅适用于 RDB 实例"""
    __tablename__ = "long_transactions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    trx_id = Column(String(64), comment="事务ID")
    trx_thread_id = Column(Integer, comment="线程ID")
    database_name = Column(String(100), comment="数据库名")
    trx_started = Column(DateTime, comment="事务开始时间")
    trx_duration = Column(Integer, comment="事务持续时间(秒)")
    trx_state = Column(String(32), comment="事务状态")
    trx_query = Column(Text, comment="当前执行的SQL")
    trx_rows_locked = Column(Integer, comment="锁定行数")
    trx_tables_locked = Column(Integer, comment="锁定表数")
    user = Column(String(64), comment="用户")
    host = Column(String(100), comment="主机")
    status = Column(String(16), default="active", comment="状态")
    killed_at = Column(DateTime, comment="Kill时间")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="long_transactions")


class InspectMetric(Base):
    """巡检指标配置表"""
    __tablename__ = "inspect_metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    module = Column(String(32), nullable=False, comment="模块")
    metric_name = Column(String(128), nullable=False, comment="指标名称")
    metric_code = Column(String(64), unique=True, nullable=False, comment="指标编码")
    check_freq = Column(String(16), default="daily", comment="检查频率")
    warn_threshold = Column(String(64), comment="告警阈值")
    critical_threshold = Column(String(64), comment="严重阈值")
    collect_sql = Column(Text, comment="采集SQL")
    auto_fix_sql = Column(Text, comment="自动修复SQL")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    description = Column(String(500), comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class InspectResult(Base):
    """巡检结果表 - 仅适用于 RDB 实例"""
    __tablename__ = "inspect_results"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    metric_id = Column(Integer, ForeignKey("inspect_metrics.id"), nullable=False, comment="指标ID")
    check_time = Column(DateTime, default=datetime.now, index=True, comment="检查时间")
    status = Column(String(16), nullable=False, comment="状态")
    actual_value = Column(String(255), comment="实际值")
    result_detail = Column(JSON, comment="结果详情JSON")
    suggestion = Column(Text, comment="优化建议")
    is_fixed = Column(Boolean, default=False, comment="是否已修复")
    fixed_at = Column(DateTime, comment="修复时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="inspect_results")
    metric = relationship("InspectMetric")


# ==================== 审计与日志 ====================

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
    login_status = Column(String(20), comment="登录状态")
    failure_reason = Column(String(200), comment="失败原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# ==================== 巡检报告 ====================

class InspectionReport(Base):
    """巡检报告表 - 仅适用于 RDB 实例"""
    __tablename__ = "inspection_reports"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    report_type = Column(String(20), default="daily", comment="报告类型")
    status = Column(String(20), default="pending", comment="状态")
    summary = Column(JSON, comment="巡检摘要")
    details = Column(JSON, comment="巡检详情")
    risk_count_high = Column(Integer, default=0, comment="高风险数量")
    risk_count_medium = Column(Integer, default=0, comment="中风险数量")
    risk_count_low = Column(Integer, default=0, comment="低风险数量")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="inspection_reports")


class IndexAnalysis(Base):
    """索引分析表 - 仅适用于 RDB 实例"""
    __tablename__ = "index_analyses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), comment="数据库名")
    table_name = Column(String(100), comment="表名")
    index_name = Column(String(100), comment="索引名")
    index_type = Column(String(50), comment="索引类型")
    columns = Column(String(500), comment="索引列")
    issue_type = Column(String(50), comment="问题类型")
    risk_level = Column(String(20), comment="风险等级")
    suggestion = Column(Text, comment="优化建议")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    rdb_instance = relationship("RDBInstance", back_populates="index_analyses")


# ==================== 用户注册 ====================

class UserRegistrationRequest(Base):
    """用户注册申请表"""
    __tablename__ = "user_registration_requests"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20))
    reason = Column(Text)
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING)
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    review_time = Column(DateTime)
    review_comment = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    reviewer = relationship("User", foreign_keys=[reviewer_id])


# ==================== 菜单配置 ====================

class MenuConfig(Base):
    """菜单配置表"""
    __tablename__ = "menu_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("menu_configs.id", ondelete="SET NULL"))
    name = Column(String(50), nullable=False)
    path = Column(String(200))
    icon = Column(String(50))
    component = Column(String(200))
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)
    is_enabled = Column(Boolean, default=True)
    permission = Column(String(100))  # 访问菜单所需的权限码
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    children = relationship("MenuConfig", backref="parent", remote_side=[id])


# ==================== 系统配置 ====================

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text)
    is_encrypted = Column(Boolean, default=False)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SystemInitState(Base):
    """系统初始化状态表"""
    __tablename__ = "system_init_state"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    step = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


# ==================== 脚本执行与定时任务 ====================

class Script(Base):
    """脚本管理表"""
    __tablename__ = "scripts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    script_type = Column(SQLEnum(ScriptType), default=ScriptType.PYTHON)
    content = Column(Text, nullable=False)
    description = Column(String(500))
    params_schema = Column(JSON)
    timeout = Column(Integer, default=300)
    max_retries = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    allowed_roles = Column(String(200))
    tags = Column(String(200))
    version = Column(Integer, default=1)
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notify_channels = Column(String(500))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("ScriptExecution", back_populates="script")
    scheduled_tasks = relationship("ScheduledTask", back_populates="script")


class ScriptExecution(Base):
    """脚本执行记录表"""
    __tablename__ = "script_executions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"))
    script_version = Column(Integer)
    trigger_type = Column(SQLEnum(TriggerType), default=TriggerType.MANUAL)
    scheduled_task_id = Column(Integer, ForeignKey("scheduled_tasks.id"))
    params = Column(JSON)
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    output = Column(Text)
    error_output = Column(Text)
    exit_code = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    triggered_by = Column(Integer, ForeignKey("users.id"))
    trigger_ip = Column(String(50))
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    script = relationship("Script", back_populates="executions")
    trigger_user = relationship("User", foreign_keys=[triggered_by])


class ScheduledTask(Base):
    """定时任务表"""
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"))
    cron_expression = Column(String(100), nullable=False)
    params = Column(JSON)
    status = Column(String(20), default="enabled")
    timezone = Column(String(50), default=get_local_timezone)
    last_run_time = Column(DateTime)
    last_run_status = Column(String(20))
    next_run_time = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    max_history = Column(Integer, default=100)
    notify_on_success = Column(Boolean, default=False)
    notify_on_fail = Column(Boolean, default=True)
    notify_channels = Column(String(200))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    script = relationship("Script", back_populates="scheduled_tasks")
    creator = relationship("User", foreign_keys=[created_by])


# ==================== SQL优化器 ====================

class TableSchema(Base):
    """表结构信息表 - 仅适用于 RDB 实例"""
    __tablename__ = "table_schemas"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), nullable=False)
    table_name = Column(String(100), nullable=False)
    table_type = Column(String(20), default="BASE TABLE")
    engine = Column(String(50))
    row_format = Column(String(20))
    row_count = Column(Integer, default=0)
    data_size = Column(Integer, default=0)
    index_size = Column(Integer, default=0)
    table_comment = Column(String(500))
    columns_json = Column(JSON, nullable=False)
    indexes_json = Column(JSON)
    create_time = Column(DateTime)
    update_time = Column(DateTime)
    sync_time = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    rdb_instance = relationship("RDBInstance", back_populates="table_schemas")


# ==================== SQL分析历史表 - 仅适用于 RDB 实例 ====================

class SQLAnalysisHistory(Base):
    """SQL分析历史表 - 仅适用于 RDB 实例
    
    数据保留策略：1年自动清理
    """
    __tablename__ = "sql_analysis_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    database_name = Column(String(100))
    
    # SQL信息
    sql_text = Column(Text, nullable=False)
    sql_normalized = Column(Text, comment="SQL标准化后的指纹")
    sql_fingerprint = Column(String(64), index=True, comment="SQL指纹(MD5)")
    
    # 分析类型
    analysis_type = Column(String(20), default='manual', comment="分析类型: manual/file_upload/auto_collect")
    source_file_id = Column(Integer, ForeignKey("slow_log_files.id", ondelete="SET NULL"), comment="来源文件ID")
    
    # 分析结果
    explain_json = Column(JSON, comment="EXPLAIN结果")
    rule_issues = Column(JSON, comment="规则检查发现的问题")
    llm_suggestions = Column(Text, comment="LLM优化建议")
    optimized_sql = Column(Text, comment="优化后的SQL")
    suggested_index = Column(Text, comment="建议添加的索引DDL")
    rollback_sql = Column(Text, comment="回滚SQL")
    
    # 风险评估
    risk_level = Column(String(20), comment="风险等级: low/medium/high")
    confidence = Column(Float, comment="LLM置信度")
    
    # 分析元数据
    analysis_time = Column(Float, comment="分析耗时(秒)")
    llm_model = Column(String(50), comment="使用的LLM模型")
    analyzed_by = Column(Integer, ForeignKey("users.id"), comment="分析人")
    
    # 保留策略：1年后自动删除
    expire_at = Column(DateTime, comment="过期时间（创建后1年）")
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    rdb_instance = relationship("RDBInstance", back_populates="sql_analysis_history")
    analyzer = relationship("User", foreign_keys=[analyzed_by])
    source_file = relationship("SlowLogFile", foreign_keys=[source_file_id])


# ==================== AWS 配置 ====================

class AWSRegion(Base):
    """AWS 区域配置表"""
    __tablename__ = "aws_regions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    region_code = Column(String(30), unique=True, nullable=False)
    region_name = Column(String(100), nullable=False)
    geo_group = Column(String(50), nullable=False)
    display_order = Column(Integer, default=0)
    is_enabled = Column(Boolean, default=True)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ==================== 导出所有模型 ====================

__all__ = [
    # 枚举
    'UserRole', 'EnvironmentType', 'ApprovalStatus', 'MonitorType',
    'ScriptType', 'ExecutionStatus', 'TriggerType', 'RegistrationStatus',
    'RDBType', 'RedisMode',
    
    # 基础模型
    'User', 'Environment', 'UserEnvironment', 'InstanceGroup',
    
    # 实例模型
    'RDBInstance', 'RedisInstance',
    'RedisSlowLog', 'RedisMemoryStats', 'RedisKeyAnalysis',
    
    # 监控配置
    'MonitorSwitch', 'GlobalConfig',
    
    # 通知配置
    'NotificationBinding',
    
    # 审批管理
    'ApprovalRecord',
    
    # RDB 性能监控
    'PerformanceMetric', 'SlowQuery', 'HighCPUSQL', 'OperationSnapshot',
    
    # RDB 监控扩展
    'AlertRecord', 'LockWait', 'ReplicationStatus', 'LongTransaction',
    'InspectMetric', 'InspectResult',
    
    # 告警聚合与升级
    'AlertAggregationRule', 'AlertSilenceRule', 'AlertEscalationRule', 'AlertAggregation',
    
    # 审计与日志
    'AuditLog', 'LoginLog',
    
    # 巡检报告
    'InspectionReport', 'IndexAnalysis',
    
    # 用户注册
    'UserRegistrationRequest',
    
    # 菜单配置
    'MenuConfig',
    
    # 系统配置
    'SystemConfig', 'SystemInitState',
    
    # 脚本执行与定时任务
    'Script', 'ScriptExecution', 'ScheduledTask',
    
    # SQL优化器
    'TableSchema', 'SQLAnalysisHistory',
    
    # AWS 配置
    'AWSRegion',
    
    # 权限管理
    'Permission', 'RolePermission', 'BatchOperationLog',
    'PermissionCode', 'DEFAULT_ROLE_PERMISSIONS',
    
    # 定时巡检
    'ScheduledInspection', 'InspectionExecution',
    
    # 告警规则
    'AlertRule', 'RULE_TYPE_LABELS', 'OPERATOR_LABELS', 'AGGREGATION_LABELS', 'SEVERITY_CONFIG',
    
    # 变更时间窗口
    'ChangeWindow', 'WEEKDAY_LABELS', 'WINDOW_TYPE_LABELS',
    
    # SQL 优化闭环
    'OptimizationSuggestion', 'SlowQueryCollectionTask', 'SlowLogFile',
    
    # 通知系统 (新)
    'NotificationChannel', 'ChannelSilenceRule',
    
    # AI 模型配置
    'AIModelConfig', 'AICallLog', 'AIProvider', 'AIModelType',
]

# 导入权限模型
from app.models.permissions import (
    Permission, RolePermission, BatchOperationLog,
    PermissionCode, DEFAULT_ROLE_PERMISSIONS,
    RoleEnvironment
)

# 导入定时巡检模型
from app.models.inspection_schedule import ScheduledInspection, InspectionExecution

# 导入告警规则模型
from app.models.alert_rule import AlertRule, RULE_TYPE_LABELS, OPERATOR_LABELS, AGGREGATION_LABELS, SEVERITY_CONFIG

# 导入变更时间窗口模型
from app.models.change_window import ChangeWindow, WEEKDAY_LABELS, WINDOW_TYPE_LABELS

# 导入 SQL 优化闭环模型
from app.models.sql_optimization import OptimizationSuggestion, SlowQueryCollectionTask, SlowLogFile

# 导入通知系统模型
from app.models.notification_new import NotificationChannel, ChannelSilenceRule

# 导入 AI 模型配置
from app.models.ai_model import AIModelConfig, AICallLog, AIProvider, AIModelType, PROVIDER_LABELS, USE_CASE_LABELS
