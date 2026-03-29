"""
定时巡检模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ScheduledInspection(Base):
    """定时巡检任务表"""
    __tablename__ = "scheduled_inspections"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="任务名称")
    description = Column(String(500), comment="描述")
    
    # 实例范围：all 或指定实例ID列表
    instance_scope = Column(String(20), default="all", comment="实例范围: all/selected")
    instance_ids = Column(JSON, comment="选中的实例ID列表")
    
    # 巡检模块
    modules = Column(JSON, comment="检查模块列表")
    
    # 调度配置
    cron_expression = Column(String(100), nullable=False, comment="Cron表达式")
    timezone = Column(String(50), default="Asia/Shanghai", comment="时区")
    status = Column(String(20), default="enabled", comment="状态: enabled/disabled")
    
    # 执行统计
    last_run_time = Column(DateTime, comment="上次执行时间")
    last_run_status = Column(String(20), comment="上次执行状态")
    next_run_time = Column(DateTime, comment="下次执行时间")
    run_count = Column(Integer, default=0, comment="执行次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    fail_count = Column(Integer, default=0, comment="失败次数")
    
    # 通知配置
    notify_on_complete = Column(Boolean, default=True, comment="完成时通知")
    notify_on_warning = Column(Boolean, default=True, comment="发现警告时通知")
    notify_on_critical = Column(Boolean, default=True, comment="发现严重问题时通知")
    notify_channels = Column(String(500), comment="通知通道ID列表(逗号分隔)")
    
    # 创建信息
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    creator = relationship("User", foreign_keys=[created_by])


class InspectionExecution(Base):
    """巡检执行记录表"""
    __tablename__ = "inspection_executions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scheduled_inspection_id = Column(Integer, ForeignKey("scheduled_inspections.id", ondelete="CASCADE"), comment="定时巡检ID")
    
    # 执行信息
    trigger_type = Column(String(20), default="scheduled", comment="触发类型: scheduled/manual")
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration = Column(Integer, comment="执行时长(秒)")
    status = Column(String(20), default="running", comment="状态: running/completed/failed")
    
    # 统计信息
    total_instances = Column(Integer, default=0, comment="检查的实例总数")
    normal_count = Column(Integer, default=0, comment="正常数量")
    warning_count = Column(Integer, default=0, comment="警告数量")
    critical_count = Column(Integer, default=0, comment="严重数量")
    error_count = Column(Integer, default=0, comment="错误数量")
    
    # 结果摘要
    summary = Column(JSON, comment="结果摘要")
    details = Column(JSON, comment="详细结果")
    error_message = Column(Text, comment="错误信息")
    
    # 触发信息
    triggered_by = Column(Integer, ForeignKey("users.id"), comment="触发人ID(手动执行时)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    scheduled_inspection = relationship("ScheduledInspection", foreign_keys=[scheduled_inspection_id])
    trigger_user = relationship("User", foreign_keys=[triggered_by])
