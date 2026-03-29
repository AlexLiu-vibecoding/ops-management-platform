"""
变更时间窗口模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Time, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ChangeWindow(Base):
    """变更时间窗口表"""
    __tablename__ = "change_windows"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="窗口名称")
    description = Column(String(500), comment="描述")
    
    # 环境范围
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="CASCADE"), comment="环境ID，为空则全局")
    
    # 时间配置
    weekdays = Column(JSON, comment="允许的星期几 [0-6]，0=周日，如[1,2,3,4,5]表示工作日")
    start_time = Column(Time, comment="开始时间")
    end_time = Column(Time, comment="结束时间")
    
    # 如果是跨天窗口（如22:00-02:00）
    cross_day = Column(Boolean, default=False, comment="是否跨天")
    
    # 窗口类型
    window_type = Column(String(20), default="allowed", comment="窗口类型: allowed(允许变更)/forbidden(禁止变更)")
    
    # 生效配置
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级，数字越大优先级越高")
    
    # 创建信息
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    environment = relationship("Environment", foreign_keys=[environment_id])
    creator = relationship("User", foreign_keys=[created_by])


# 星期几的标签
WEEKDAY_LABELS = {
    0: "周日",
    1: "周一",
    2: "周二",
    3: "周三",
    4: "周四",
    5: "周五",
    6: "周六"
}

# 窗口类型标签
WINDOW_TYPE_LABELS = {
    "allowed": "允许变更",
    "forbidden": "禁止变更"
}
