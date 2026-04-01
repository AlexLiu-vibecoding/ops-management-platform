"""
告警聚合与升级模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AggregationMethod(str, enum.Enum):
    """聚合方法枚举"""
    COUNT = "count"
    SUMMARY = "summary"


class SilenceType(str, enum.Enum):
    """静默类型枚举"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class AlertAggregationRule(Base):
    """告警聚合规则表"""
    __tablename__ = "alert_aggregation_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    
    # 聚合条件
    metric_type = Column(String(32), comment="指标类型，空表示所有类型")
    alert_level = Column(String(16), comment="告警级别，空表示所有级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID，空表示所有")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID，空表示所有")
    
    # 聚合配置
    aggregation_window = Column(Integer, default=300, comment="聚合时间窗口(秒)")
    min_alert_count = Column(Integer, default=2, comment="最小告警数量才聚合")
    aggregation_method = Column(String(20), default="count", comment="聚合方法: count/summary")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级(数字越大优先级越高)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")
    aggregations = relationship("AlertAggregation", back_populates="rule", cascade="all, delete-orphan")


class AlertAggregation(Base):
    """告警聚合记录表"""
    __tablename__ = "alert_aggregations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_aggregation_rules.id", ondelete="CASCADE"), comment="规则ID")
    
    # 聚合信息
    metric_type = Column(String(32), comment="指标类型")
    alert_level = Column(String(16), comment="告警级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID")
    
    # 聚合数据
    alert_count = Column(Integer, default=1, comment="告警数量")
    alert_ids = Column(JSON, comment="告警ID列表")
    aggregated_content = Column(Text, comment="聚合后的内容")
    notification_sent = Column(Boolean, default=False, comment="是否已发送通知")
    
    # 时间
    started_at = Column(DateTime, nullable=False, comment="聚合开始时间")
    ended_at = Column(DateTime, comment="聚合结束时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    rule = relationship("AlertAggregationRule", back_populates="aggregations")
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")


class AlertSilenceRule(Base):
    """告警静默规则表"""
    __tablename__ = "alert_silence_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    
    # 静默条件
    silence_type = Column(String(20), default="once", comment="静默类型: once/daily/weekly")
    metric_type = Column(String(32), comment="指标类型，空表示所有类型")
    alert_level = Column(String(16), comment="告警级别，空表示所有级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID，空表示所有")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID，空表示所有")
    
    # 时间配置
    start_time = Column(String(5), comment="开始时间 HH:MM")
    end_time = Column(String(5), comment="结束时间 HH:MM")
    weekdays = Column(JSON, comment="允许的星期几 [0-6]，0=周一，如[0,1,2,3,4]表示工作日")
    start_date = Column(DateTime, comment="生效开始日期")
    end_date = Column(DateTime, comment="生效结束日期")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    creator = relationship("User", foreign_keys=[created_by])
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")


class AlertEscalationRule(Base):
    """告警升级规则表"""
    __tablename__ = "alert_escalation_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="规则名称")
    description = Column(String(200), comment="规则描述")
    
    # 触发条件
    metric_type = Column(String(32), comment="指标类型，空表示所有类型")
    alert_level = Column(String(16), comment="告警级别，空表示所有级别")
    rdb_instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), comment="RDB实例ID，空表示所有")
    redis_instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), comment="Redis实例ID，空表示所有")
    
    # 升级配置
    escalation_wait_minutes = Column(Integer, default=30, comment="等待多少分钟后升级")
    target_alert_level = Column(String(16), comment="目标告警级别")
    additional_notify_channels = Column(String(500), comment="额外通知通道ID列表(逗号分隔)")
    escalation_message = Column(String(500), comment="升级消息内容")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    creator = relationship("User", foreign_keys=[created_by])
    rdb_instance = relationship("RDBInstance")
    redis_instance = relationship("RedisInstance")


# 聚合方法标签
AGGREGATION_METHOD_LABELS = {
    "count": "计数",
    "summary": "摘要"
}

# 静默类型标签
SILENCE_TYPE_LABELS = {
    "once": "一次性",
    "daily": "每日重复",
    "weekly": "每周重复"
}
