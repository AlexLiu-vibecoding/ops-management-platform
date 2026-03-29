"""
告警规则模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AlertRule(Base):
    """告警规则表"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(String(500), comment="描述")
    
    # 规则类型
    rule_type = Column(String(50), nullable=False, comment="规则类型: slow_query/cpu/memory/connections/qps/delay/custom")
    
    # 实例范围
    instance_scope = Column(String(20), default="all", comment="实例范围: all/selected/environment")
    instance_ids = Column(JSON, comment="选中的实例ID列表")
    environment_ids = Column(JSON, comment="选中的环境ID列表")
    
    # 触发条件
    metric_name = Column(String(100), comment="指标名称")
    operator = Column(String(10), default=">", comment="比较运算符: >/>=/</<=/==/!=")
    threshold = Column(Float, comment="阈值")
    duration = Column(Integer, default=60, comment="持续时间(秒)，连续超过阈值多久才告警")
    aggregation = Column(String(20), default="avg", comment="聚合方式: avg/max/min/sum")
    
    # 告警级别
    severity = Column(String(20), default="warning", comment="告警级别: info/warning/critical")
    
    # 静默配置
    silence_duration = Column(Integer, default=300, comment="静默时长(秒)，同一告警静默多久")
    silence_until = Column(DateTime, comment="静默截止时间")
    
    # 通知配置
    notify_channels = Column(String(500), comment="通知通道ID列表(逗号分隔)")
    notify_enabled = Column(Boolean, default=True, comment="是否启用通知")
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    last_triggered_at = Column(DateTime, comment="上次触发时间")
    trigger_count = Column(Integer, default=0, comment="触发次数")
    
    # 创建信息
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    creator = relationship("User", foreign_keys=[created_by])


# 规则类型的标签映射
RULE_TYPE_LABELS = {
    "slow_query": "慢查询",
    "cpu": "CPU使用率",
    "memory": "内存使用率",
    "connections": "连接数",
    "qps": "QPS",
    "delay": "主从延迟",
    "disk": "磁盘使用率",
    "lock_wait": "锁等待",
    "long_trx": "长事务",
    "custom": "自定义指标"
}

# 比较运算符标签
OPERATOR_LABELS = {
    ">": "大于",
    ">=": "大于等于",
    "<": "小于",
    "<=": "小于等于",
    "==": "等于",
    "!=": "不等于"
}

# 聚合方式标签
AGGREGATION_LABELS = {
    "avg": "平均值",
    "max": "最大值",
    "min": "最小值",
    "sum": "总和"
}

# 告警级别标签和颜色
SEVERITY_CONFIG = {
    "info": {"label": "信息", "color": "#909399"},
    "warning": {"label": "警告", "color": "#E6A23C"},
    "critical": {"label": "严重", "color": "#F56C6C"}
}
