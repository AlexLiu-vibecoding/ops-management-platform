"""
密钥轮换相关数据模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class KeyRotationLog(Base):
    """密钥轮换日志"""
    __tablename__ = "key_rotation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False, comment="操作类型: preview/migrate/switch")
    from_version = Column(String(10), nullable=True, comment="源版本")
    to_version = Column(String(10), nullable=True, comment="目标版本")
    status = Column(String(20), nullable=False, comment="状态: success/failed")
    total_records = Column(Integer, default=0, comment="总记录数")
    migrated_records = Column(Integer, default=0, comment="成功迁移数")
    failed_records = Column(Integer, default=0, comment="失败数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="操作人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关系
    operator = relationship("User", back_populates="key_rotation_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "status": self.status,
            "total_records": self.total_records,
            "migrated_records": self.migrated_records,
            "failed_records": self.failed_records,
            "error_message": self.error_message,
            "operator_id": self.operator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class KeyRotationConfig(Base):
    """密钥轮换配置"""
    __tablename__ = "key_rotation_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=False, comment="是否启用自动轮换")
    schedule_type = Column(String(20), default="monthly", comment="周期: weekly/monthly/quarterly")
    schedule_day = Column(Integer, default=1, comment="执行日(周几/每月几号)")
    schedule_time = Column(String(10), default="02:00", comment="执行时间")
    current_key_id = Column(String(10), default="v1", comment="当前密钥版本")
    v2_key = Column(String(64), nullable=True, comment="V2 密钥（自动生成的下一版本密钥）")
    auto_switch = Column(Boolean, default=False, comment="迁移后自动切换版本")
    last_rotation_at = Column(DateTime, nullable=True, comment="上次轮换时间")
    next_rotation_at = Column(DateTime, nullable=True, comment="下次轮换时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        return {
            "id": self.id,
            "enabled": self.enabled,
            "schedule_type": self.schedule_type,
            "schedule_day": self.schedule_day,
            "schedule_time": self.schedule_time,
            "current_key_id": self.current_key_id,
            "v2_key": self.v2_key,
            "has_v2_key": bool(self.v2_key),
            "auto_switch": self.auto_switch,
            "last_rotation_at": self.last_rotation_at.isoformat() if self.last_rotation_at else None,
            "next_rotation_at": self.next_rotation_at.isoformat() if self.next_rotation_at else None
        }
