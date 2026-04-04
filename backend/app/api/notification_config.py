"""
通知配置管理API - 静默规则、频率限制等配置管理
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.models import (
    AlertSilenceRule, AlertRateLimitRule,
    User, RDBInstance, RedisInstance
)
from app.models.permissions import PermissionCode
from app.schemas import MessageResponse
from app.deps import get_current_user, require_permissions


router = APIRouter(prefix="/notification/config", tags=["通知配置管理"])


# ==================== Schemas ====================

class SilenceRuleCreate(BaseModel):
    """创建静默规则"""
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    
    # 匹配条件
    metric_type: Optional[str] = Field(None, description="指标类型")
    alert_level: Optional[str] = Field(None, description="告警级别")
    rdb_instance_id: Optional[int] = Field(None, description="RDB实例ID")
    redis_instance_id: Optional[int] = Field(None, description="Redis实例ID")
    
    # 静默配置
    silence_type: str = Field("once", description="静默类型: once/daily/weekly")
    start_date: Optional[datetime] = Field(None, description="生效开始日期")
    end_date: Optional[datetime] = Field(None, description="生效结束日期")
    time_start: Optional[str] = Field(None, description="开始时间 HH:MM")
    time_end: Optional[str] = Field(None, description="结束时间 HH:MM")
    weekdays: Optional[list[int]] = Field(None, description="允许的星期几 [0-6]，0=周一")
    
    is_enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class SilenceRuleUpdate(BaseModel):
    """更新静默规则"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    
    metric_type: Optional[str] = None
    alert_level: Optional[str] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    
    silence_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    weekdays: Optional[list[int]] = None
    
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class RateLimitRuleCreate(BaseModel):
    """创建频率限制规则"""
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    
    # 匹配条件
    metric_type: Optional[str] = Field(None, description="指标类型")
    alert_level: Optional[str] = Field(None, description="告警级别")
    rdb_instance_id: Optional[int] = Field(None, description="RDB实例ID")
    redis_instance_id: Optional[int] = Field(None, description="Redis实例ID")
    
    # 频率限制配置
    limit_window: int = Field(300, description="限制时间窗口(秒)")
    max_notifications: int = Field(5, description="时间窗口内最大通知数量")
    cooldown_period: int = Field(600, description="冷却期(秒)")
    
    is_enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class RateLimitRuleUpdate(BaseModel):
    """更新频率限制规则"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    
    metric_type: Optional[str] = None
    alert_level: Optional[str] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    
    limit_window: Optional[int] = None
    max_notifications: Optional[int] = None
    cooldown_period: Optional[int] = None
    
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


# ==================== Helper Functions ====================

def enrich_rule_with_instance_names(db: Session, rule_dict: dict) -> dict:
    """为规则添加实例名称"""
    if rule_dict.get("rdb_instance_id"):
        instance = db.query(RDBInstance).filter_by(id=rule_dict["rdb_instance_id"]).first()
        if instance:
            rule_dict["rdb_instance_name"] = instance.name
    
    if rule_dict.get("redis_instance_id"):
        instance = db.query(RedisInstance).filter_by(id=rule_dict["redis_instance_id"]).first()
        if instance:
            rule_dict["redis_instance_name"] = instance.name
    
    return rule_dict


# ==================== 静默规则管理 ====================

@router.get("/silence-rules")
async def list_silence_rules(
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取静默规则列表"""
    query = db.query(AlertSilenceRule)
    
    if is_enabled is not None:
        query = query.filter_by(is_enabled=is_enabled)
    
    rules = query.order_by(AlertSilenceRule.priority.desc(), AlertSilenceRule.created_at.desc()).all()
    
    result = []
    for rule in rules:
        rule_dict = {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "metric_type": rule.metric_type,
            "alert_level": rule.alert_level,
            "rdb_instance_id": rule.rdb_instance_id,
            "redis_instance_id": rule.redis_instance_id,
            "silence_type": rule.silence_type,
            "start_date": rule.start_date,
            "end_date": rule.end_date,
            "time_start": rule.time_start,
            "time_end": rule.time_end,
            "weekdays": rule.weekdays,
            "is_enabled": rule.is_enabled,
            "priority": rule.priority,
            "created_by": rule.created_by,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        }
        result.append(enrich_rule_with_instance_names(db, rule_dict))
    
    return result


@router.post("/silence-rules")
async def create_silence_rule(
    data: SilenceRuleCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """创建静默规则"""
    # 检查名称是否重复
    existing = db.query(AlertSilenceRule).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="规则名称已存在"
        )
    
    # 验证实例ID
    if data.rdb_instance_id:
        instance = db.query(RDBInstance).filter_by(id=data.rdb_instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RDB实例不存在"
            )
    
    if data.redis_instance_id:
        instance = db.query(RedisInstance).filter_by(id=data.redis_instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis实例不存在"
            )
    
    # 创建规则
    rule = AlertSilenceRule(
        name=data.name,
        description=data.description,
        metric_type=data.metric_type,
        alert_level=data.alert_level,
        rdb_instance_id=data.rdb_instance_id,
        redis_instance_id=data.redis_instance_id,
        silence_type=data.silence_type,
        start_date=data.start_date,
        end_date=data.end_date,
        time_start=data.time_start,
        time_end=data.time_end,
        weekdays=data.weekdays,
        is_enabled=data.is_enabled,
        priority=data.priority,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "message": "创建成功"}


@router.put("/silence-rules/{rule_id}")
async def update_silence_rule(
    rule_id: int,
    data: SilenceRuleUpdate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """更新静默规则"""
    rule = db.query(AlertSilenceRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    # 更新字段
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/silence-rules/{rule_id}")
async def delete_silence_rule(
    rule_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_SILENCE_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除静默规则"""
    rule = db.query(AlertSilenceRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


# ==================== 频率限制规则管理 ====================

@router.get("/rate-limit-rules")
async def list_rate_limit_rules(
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取频率限制规则列表"""
    query = db.query(AlertRateLimitRule)
    
    if is_enabled is not None:
        query = query.filter_by(is_enabled=is_enabled)
    
    rules = query.order_by(AlertRateLimitRule.priority.desc(), AlertRateLimitRule.created_at.desc()).all()
    
    result = []
    for rule in rules:
        rule_dict = {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "metric_type": rule.metric_type,
            "alert_level": rule.alert_level,
            "rdb_instance_id": rule.rdb_instance_id,
            "redis_instance_id": rule.redis_instance_id,
            "limit_window": rule.limit_window,
            "max_notifications": rule.max_notifications,
            "cooldown_period": rule.cooldown_period,
            "is_enabled": rule.is_enabled,
            "priority": rule.priority,
            "created_by": rule.created_by,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at
        }
        result.append(enrich_rule_with_instance_names(db, rule_dict))
    
    return result


@router.post("/rate-limit-rules")
async def create_rate_limit_rule(
    data: RateLimitRuleCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """创建频率限制规则"""
    # 检查名称是否重复
    existing = db.query(AlertRateLimitRule).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="规则名称已存在"
        )
    
    # 验证实例ID
    if data.rdb_instance_id:
        instance = db.query(RDBInstance).filter_by(id=data.rdb_instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RDB实例不存在"
            )
    
    if data.redis_instance_id:
        instance = db.query(RedisInstance).filter_by(id=data.redis_instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redis实例不存在"
            )
    
    # 创建规则
    rule = AlertRateLimitRule(
        name=data.name,
        description=data.description,
        metric_type=data.metric_type,
        alert_level=data.alert_level,
        rdb_instance_id=data.rdb_instance_id,
        redis_instance_id=data.redis_instance_id,
        limit_window=data.limit_window,
        max_notifications=data.max_notifications,
        cooldown_period=data.cooldown_period,
        is_enabled=data.is_enabled,
        priority=data.priority,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "message": "创建成功"}


@router.put("/rate-limit-rules/{rule_id}")
async def update_rate_limit_rule(
    rule_id: int,
    data: RateLimitRuleUpdate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """更新频率限制规则"""
    rule = db.query(AlertRateLimitRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    # 更新字段
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/rate-limit-rules/{rule_id}")
async def delete_rate_limit_rule(
    rule_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_RATE_LIMIT_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除频率限制规则"""
    rule = db.query(AlertRateLimitRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}
