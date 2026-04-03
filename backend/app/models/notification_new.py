"""
通知系统模型 - 统一的通知通道管理
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class NotificationChannel(Base):
    """统一的通知通道表"""
    __tablename__ = "notification_channels"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="通道名称")
    channel_type = Column(String(20), nullable=False, comment="通道类型: dingtalk/wechat/feishu/email/webhook")
    config = Column(JSON, nullable=False, default={}, comment="通道配置(JSON)")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    description = Column(String(200), comment="描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    silence_rules = relationship("ChannelSilenceRule", back_populates="channel", cascade="all, delete-orphan")
    rate_limits = relationship("ChannelRateLimit", back_populates="channel", cascade="all, delete-orphan")


class ChannelSilenceRule(Base):
    """通道静默规则"""
    __tablename__ = "channel_silence_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False, comment="通道ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(String(200), comment="规则描述")

    # 匹配条件 (可选)
    instance_type = Column(String(20), comment="实例类型: rdb/redis")
    instance_id = Column(Integer, comment="实例ID")
    metric_type = Column(String(32), comment="指标类型")

    # 静默配置
    silence_type = Column(String(20), default="once", comment="静默类型: once/daily/weekly")
    start_time = Column(DateTime, comment="开始时间(一次性)")
    end_time = Column(DateTime, comment="结束时间(一次性)")
    time_start = Column(String(5), comment="每日开始时间 HH:MM")
    time_end = Column(String(5), comment="每日结束时间 HH:MM")
    weekdays = Column(JSON, comment="星期几 [0-6], 0=周一")
    
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    channel = relationship("NotificationChannel", back_populates="silence_rules")


class ChannelRateLimit(Base):
    """通道频率限制"""
    __tablename__ = "channel_rate_limits"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False, comment="通道ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(String(200), comment="规则描述")

    # 匹配条件 (可选)
    instance_type = Column(String(20), comment="实例类型: rdb/redis")
    instance_id = Column(Integer, comment="实例ID")
    metric_type = Column(String(32), comment="指标类型")

    # 频率限制
    limit_window = Column(Integer, default=300, comment="时间窗口(秒)")
    max_notifications = Column(Integer, default=5, comment="最大通知数")
    cooldown_period = Column(Integer, default=600, comment="冷却期(秒)")
    
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    channel = relationship("NotificationChannel", back_populates="rate_limits")
