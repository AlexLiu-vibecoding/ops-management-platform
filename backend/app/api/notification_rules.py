"""
通道静默规则和频率限制 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.models import User
from app.models.notification_new import NotificationChannel, ChannelSilenceRule, ChannelRateLimit
from app.models.permissions import PermissionCode
from app.deps import get_current_user, require_permissions


router = APIRouter(prefix="/notification", tags=["通知规则管理"])


# ==================== Schemas ====================

class SilenceRuleCreate(BaseModel):
    """创建静默规则"""
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    
    # 匹配条件
    alert_level: Optional[str] = Field(None, description="告警级别")
    instance_type: Optional[str] = Field(None, description="实例类型: rdb/redis")
    instance_id: Optional[int] = Field(None, description="实例ID")
    metric_type: Optional[str] = Field(None, description="指标类型")
    
    # 静默配置
    silence_type: str = Field("once", description="静默类型: once/daily/weekly")
    start_time: Optional[datetime] = Field(None, description="开始时间(一次性)")
    end_time: Optional[datetime] = Field(None, description="结束时间(一次性)")
    time_start: Optional[str] = Field(None, description="开始时间 HH:MM")
    time_end: Optional[str] = Field(None, description="结束时间 HH:MM")
    weekdays: Optional[List[int]] = Field(None, description="星期几 [0-6], 0=周一")
    
    is_enabled: bool = Field(True, description="是否启用")


class SilenceRuleUpdate(BaseModel):
    """更新静默规则"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    alert_level: Optional[str] = None
    instance_type: Optional[str] = None
    instance_id: Optional[int] = None
    metric_type: Optional[str] = None
    silence_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    weekdays: Optional[List[int]] = None
    is_enabled: Optional[bool] = None


class RateLimitCreate(BaseModel):
    """创建频率限制"""
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    
    # 匹配条件
    alert_level: Optional[str] = Field(None, description="告警级别")
    instance_type: Optional[str] = Field(None, description="实例类型: rdb/redis")
    instance_id: Optional[int] = Field(None, description="实例ID")
    metric_type: Optional[str] = Field(None, description="指标类型")
    
    # 频率限制
    limit_window: int = Field(300, description="时间窗口(秒)")
    max_notifications: int = Field(5, description="最大通知数")
    cooldown_period: int = Field(600, description="冷却期(秒)")
    
    is_enabled: bool = Field(True, description="是否启用")


class RateLimitUpdate(BaseModel):
    """更新频率限制"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    alert_level: Optional[str] = None
    instance_type: Optional[str] = None
    instance_id: Optional[int] = None
    metric_type: Optional[str] = None
    limit_window: Optional[int] = None
    max_notifications: Optional[int] = None
    cooldown_period: Optional[int] = None
    is_enabled: Optional[bool] = None


# ==================== 静默规则 ====================

SILENCE_TYPE_LABELS = {
    "once": "一次性",
    "daily": "每日",
    "weekly": "每周"
}

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def silence_rule_to_dict(rule: ChannelSilenceRule) -> dict:
    """转换静默规则为字典"""
    return {
        "id": rule.id,
        "channel_id": rule.channel_id,
        "name": rule.name,
        "description": rule.description,
        "alert_level": rule.alert_level,
        "instance_type": rule.instance_type,
        "instance_id": rule.instance_id,
        "metric_type": rule.metric_type,
        "silence_type": rule.silence_type,
        "silence_type_label": SILENCE_TYPE_LABELS.get(rule.silence_type, rule.silence_type),
        "start_time": rule.start_time,
        "end_time": rule.end_time,
        "time_start": rule.time_start,
        "time_end": rule.time_end,
        "weekdays": rule.weekdays,
        "weekdays_label": format_weekdays(rule.weekdays),
        "is_enabled": rule.is_enabled,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at
    }


def format_weekdays(weekdays: List[int]) -> str:
    """格式化星期几"""
    if not weekdays:
        return "-"
    return ", ".join([WEEKDAY_NAMES[i] for i in weekdays if 0 <= i < 7])


@router.get("/channels/{channel_id}/silence-rules", tags=["通道静默规则"])
async def list_silence_rules(
    channel_id: int,
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通道的静默规则列表"""
    # 验证通道存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")
    
    query = db.query(ChannelSilenceRule).filter_by(channel_id=channel_id)
    
    if is_enabled is not None:
        query = query.filter_by(is_enabled=is_enabled)
    
    rules = query.order_by(ChannelSilenceRule.created_at.desc()).all()
    
    return {"items": [silence_rule_to_dict(r) for r in rules], "total": len(rules)}


@router.post("/channels/{channel_id}/silence-rules", tags=["通道静默规则"])
async def create_silence_rule(
    channel_id: int,
    data: SilenceRuleCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """为通道创建静默规则"""
    # 验证通道存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")
    
    # 检查名称重复
    existing = db.query(ChannelSilenceRule).filter_by(channel_id=channel_id, name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则名称已存在")
    
    rule = ChannelSilenceRule(
        channel_id=channel_id,
        name=data.name,
        description=data.description,
        alert_level=data.alert_level,
        instance_type=data.instance_type,
        instance_id=data.instance_id,
        metric_type=data.metric_type,
        silence_type=data.silence_type,
        start_time=data.start_time,
        end_time=data.end_time,
        time_start=data.time_start,
        time_end=data.time_end,
        weekdays=data.weekdays,
        is_enabled=data.is_enabled
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "message": "创建成功"}


@router.put("/channels/{channel_id}/silence-rules/{rule_id}", tags=["通道静默规则"])
async def update_silence_rule(
    channel_id: int,
    rule_id: int,
    data: SilenceRuleUpdate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """更新静默规则"""
    rule = db.query(ChannelSilenceRule).filter_by(id=rule_id, channel_id=channel_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 检查名称重复
    if data.name and data.name != rule.name:
        existing = db.query(ChannelSilenceRule).filter_by(channel_id=channel_id, name=data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="规则名称已存在")
    
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/channels/{channel_id}/silence-rules/{rule_id}", tags=["通道静默规则"])
async def delete_silence_rule(
    channel_id: int,
    rule_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除静默规则"""
    rule = db.query(ChannelSilenceRule).filter_by(id=rule_id, channel_id=channel_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


# ==================== 频率限制 ====================

def rate_limit_to_dict(rule: ChannelRateLimit) -> dict:
    """转换频率限制为字典"""
    return {
        "id": rule.id,
        "channel_id": rule.channel_id,
        "name": rule.name,
        "description": rule.description,
        "alert_level": rule.alert_level,
        "instance_type": rule.instance_type,
        "instance_id": rule.instance_id,
        "metric_type": rule.metric_type,
        "limit_window": rule.limit_window,
        "max_notifications": rule.max_notifications,
        "cooldown_period": rule.cooldown_period,
        "is_enabled": rule.is_enabled,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at
    }


@router.get("/channels/{channel_id}/rate-limits", tags=["通道频率限制"])
async def list_rate_limits(
    channel_id: int,
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通道的频率限制列表"""
    # 验证通道存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")
    
    query = db.query(ChannelRateLimit).filter_by(channel_id=channel_id)
    
    if is_enabled is not None:
        query = query.filter_by(is_enabled=is_enabled)
    
    rules = query.order_by(ChannelRateLimit.created_at.desc()).all()
    
    return {"items": [rate_limit_to_dict(r) for r in rules], "total": len(rules)}


@router.post("/channels/{channel_id}/rate-limits", tags=["通道频率限制"])
async def create_rate_limit(
    channel_id: int,
    data: RateLimitCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """为通道创建频率限制"""
    # 验证通道存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")
    
    # 检查名称重复
    existing = db.query(ChannelRateLimit).filter_by(channel_id=channel_id, name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则名称已存在")
    
    rule = ChannelRateLimit(
        channel_id=channel_id,
        name=data.name,
        description=data.description,
        alert_level=data.alert_level,
        instance_type=data.instance_type,
        instance_id=data.instance_id,
        metric_type=data.metric_type,
        limit_window=data.limit_window,
        max_notifications=data.max_notifications,
        cooldown_period=data.cooldown_period,
        is_enabled=data.is_enabled
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "message": "创建成功"}


@router.put("/channels/{channel_id}/rate-limits/{rule_id}", tags=["通道频率限制"])
async def update_rate_limit(
    channel_id: int,
    rule_id: int,
    data: RateLimitUpdate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """更新频率限制"""
    rule = db.query(ChannelRateLimit).filter_by(id=rule_id, channel_id=channel_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    # 检查名称重复
    if data.name and data.name != rule.name:
        existing = db.query(ChannelRateLimit).filter_by(channel_id=channel_id, name=data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="规则名称已存在")
    
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/channels/{channel_id}/rate-limits/{rule_id}", tags=["通道频率限制"])
async def delete_rate_limit(
    channel_id: int,
    rule_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除频率限制"""
    rule = db.query(ChannelRateLimit).filter_by(id=rule_id, channel_id=channel_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}
