"""
变更时间窗口模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ChangeWindow(Base):
    """变更时间窗口表"""
    __tablename__ = "change_windows"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="窗口名称")
    description = Column(String(500), comment="描述")
    
    # 环境范围（支持多环境）
    environment_ids = Column(JSON, comment="应用环境ID列表，为空则全局")
    
    # 日期范围（可选，用于临时窗口）
    start_date = Column(Date, comment="生效开始日期")
    end_date = Column(Date, comment="生效结束日期")
    
    # 时间配置（每天的时间范围）
    start_time = Column(String(5), comment="开始时间 HH:MM")
    end_time = Column(String(5), comment="结束时间 HH:MM")
    weekdays = Column(JSON, comment="允许的星期几 [0-6]，0=周一，如[0,1,2,3,4]表示工作日")
    
    # 如果是跨天窗口（如22:00-02:00）
    cross_day = Column(Boolean, default=False, comment="是否跨天")
    
    # 窗口类型
    window_type = Column(String(20), default="allowed", comment="窗口类型: allowed(允许变更)/forbidden(禁止变更)")
    
    # 审批配置
    allow_emergency = Column(Boolean, default=False, comment="允许紧急变更")
    require_approval = Column(Boolean, default=True, comment="需要审批")
    min_approvers = Column(Integer, default=1, comment="最小审批人数")
    auto_reject_outside = Column(Boolean, default=False, comment="自动拒绝窗口外变更")
    
    # 生效配置
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级，数字越大优先级越高")
    
    # 创建信息
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    creator = relationship("User", foreign_keys=[created_by])


# 星期几的标签（0=周一，符合前端习惯）
WEEKDAY_LABELS = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日"
}

# 窗口类型标签
WINDOW_TYPE_LABELS = {
    "allowed": "允许变更",
    "forbidden": "禁止变更"
}
