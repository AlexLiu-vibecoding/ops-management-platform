"""告警规则管理 API - 聚合、静默、升级"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import (
    AlertAggregationRule, AlertSilenceRule, AlertEscalationRule,
    AlertAggregation
)
from app.schemas import MessageResponse
from app.deps import get_super_admin


router = APIRouter(prefix="/alert-rules", tags=["告警规则"])


# ==================== Schemas ====================

class AlertAggregationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    metric_type: Optional[str] = Field(None, description="指标类型")
    alert_level: Optional[str] = Field(None, description="告警级别")
    rdb_instance_id: Optional[int] = Field(None, description="RDB实例ID")
    redis_instance_id: Optional[int] = Field(None, description="Redis实例ID")
    aggregation_window: int = Field(300, ge=60, description="聚合时间窗口(秒)")
    min_alert_count: int = Field(2, ge=1, description="最小告警数量")
    aggregation_method: str = Field("count", description="聚合方法: count/summary")
    is_enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class AlertAggregationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    metric_type: Optional[str] = None
    alert_level: Optional[str] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    aggregation_window: Optional[int] = Field(None, ge=60)
    min_alert_count: Optional[int] = Field(None, ge=1)
    aggregation_method: Optional[str] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class AlertSilenceRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    metric_type: Optional[str] = Field(None, description="指标类型")
    alert_level: Optional[str] = Field(None, description="告警级别")
    rdb_instance_id: Optional[int] = Field(None, description="RDB实例ID")
    redis_instance_id: Optional[int] = Field(None, description="Redis实例ID")
    start_time: Optional[datetime] = Field(None, description="静默开始时间")
    end_time: Optional[datetime] = Field(None, description="静默结束时间")
    recurrence_type: str = Field("once", description="重复类型: once/daily/weekly")
    is_enabled: bool = Field(True, description="是否启用")


class AlertSilenceRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    metric_type: Optional[str] = None
    alert_level: Optional[str] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    recurrence_type: Optional[str] = None
    is_enabled: Optional[bool] = None


class AlertEscalationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    description: Optional[str] = Field(None, max_length=200, description="规则描述")
    alert_level: str = Field(..., description="告警级别")
    trigger_condition: str = Field("time", description="触发条件: time/acknowledge")
    trigger_minutes: int = Field(30, ge=5, description="触发时间(分钟)")
    escalation_level: Optional[str] = Field(None, description="升级后的级别")
    escalation_notification: bool = Field(True, description="是否发送升级通知")
    additional_channel_id: Optional[int] = Field(None, description="额外通知通道ID")
    is_enabled: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class AlertEscalationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=200)
    alert_level: Optional[str] = None
    trigger_condition: Optional[str] = None
    trigger_minutes: Optional[int] = Field(None, ge=5)
    escalation_level: Optional[str] = None
    escalation_notification: Optional[bool] = None
    additional_channel_id: Optional[int] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


# ==================== 聚合规则 API ====================

@router.get("/aggregations", response_model=dict)
async def list_aggregation_rules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取聚合规则列表"""
    query = db.query(AlertAggregationRule)
    if is_enabled is not None:
        query = query.filter(AlertAggregationRule.is_enabled == is_enabled)
    
    total = query.count()
    rules = query.order_by(desc(AlertAggregationRule.priority), desc(AlertAggregationRule.created_at)) \
        .offset((page - 1) * limit) \
        .limit(limit) \
        .all()
    
    return {
        "code": 0,
        "message": "获取成功",
        "data": {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "metric_type": r.metric_type,
                    "alert_level": r.alert_level,
                    "aggregation_window": r.aggregation_window,
                    "min_alert_count": r.min_alert_count,
                    "aggregation_method": r.aggregation_method,
                    "is_enabled": r.is_enabled,
                    "priority": r.priority,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in rules
            ],
            "total": total,
            "page": page,
            "limit": limit
        }
    }


@router.post("/aggregations", response_model=MessageResponse)
async def create_aggregation_rule(
    data: AlertAggregationRuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """创建聚合规则"""
    existing = db.query(AlertAggregationRule).filter(AlertAggregationRule.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="规则名称已存在"
        )
    
    rule = AlertAggregationRule(**data.model_dump())
    db.add(rule)
    db.commit()
    
    return MessageResponse(message="创建成功", success=True)


@router.put("/aggregations/{rule_id}", response_model=MessageResponse)
async def update_aggregation_rule(
    rule_id: int,
    data: AlertAggregationRuleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """更新聚合规则"""
    rule = db.query(AlertAggregationRule).filter(AlertAggregationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    if data.name and data.name != rule.name:
        existing = db.query(AlertAggregationRule).filter(AlertAggregationRule.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="规则名称已存在"
            )
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    return MessageResponse(message="更新成功", success=True)


@router.delete("/aggregations/{rule_id}", response_model=MessageResponse)
async def delete_aggregation_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """删除聚合规则"""
    rule = db.query(AlertAggregationRule).filter(AlertAggregationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    return MessageResponse(message="删除成功", success=True)


# ==================== 静默规则 API ====================

@router.get("/silences", response_model=dict)
async def list_silence_rules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取静默规则列表"""
    query = db.query(AlertSilenceRule)
    if is_enabled is not None:
        query = query.filter(AlertSilenceRule.is_enabled == is_enabled)
    
    total = query.count()
    rules = query.order_by(desc(AlertSilenceRule.created_at)) \
        .offset((page - 1) * limit) \
        .limit(limit) \
        .all()
    
    return {
        "code": 0,
        "message": "获取成功",
        "data": {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "metric_type": r.metric_type,
                    "alert_level": r.alert_level,
                    "start_time": r.start_time.isoformat() if r.start_time else None,
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "recurrence_type": r.recurrence_type,
                    "is_enabled": r.is_enabled,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in rules
            ],
            "total": total,
            "page": page,
            "limit": limit
        }
    }


@router.post("/silences", response_model=MessageResponse)
async def create_silence_rule(
    data: AlertSilenceRuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """创建静默规则"""
    existing = db.query(AlertSilenceRule).filter(AlertSilenceRule.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="规则名称已存在"
        )
    
    rule = AlertSilenceRule(**data.model_dump())
    db.add(rule)
    db.commit()
    
    return MessageResponse(message="创建成功", success=True)


@router.put("/silences/{rule_id}", response_model=MessageResponse)
async def update_silence_rule(
    rule_id: int,
    data: AlertSilenceRuleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """更新静默规则"""
    rule = db.query(AlertSilenceRule).filter(AlertSilenceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    if data.name and data.name != rule.name:
        existing = db.query(AlertSilenceRule).filter(AlertSilenceRule.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="规则名称已存在"
            )
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    return MessageResponse(message="更新成功", success=True)


@router.delete("/silences/{rule_id}", response_model=MessageResponse)
async def delete_silence_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """删除静默规则"""
    rule = db.query(AlertSilenceRule).filter(AlertSilenceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    return MessageResponse(message="删除成功", success=True)


# ==================== 升级规则 API ====================

@router.get("/escalations", response_model=dict)
async def list_escalation_rules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取升级规则列表"""
    query = db.query(AlertEscalationRule)
    if is_enabled is not None:
        query = query.filter(AlertEscalationRule.is_enabled == is_enabled)
    
    total = query.count()
    rules = query.order_by(desc(AlertEscalationRule.priority), desc(AlertEscalationRule.created_at)) \
        .offset((page - 1) * limit) \
        .limit(limit) \
        .all()
    
    return {
        "code": 0,
        "message": "获取成功",
        "data": {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "alert_level": r.alert_level,
                    "trigger_condition": r.trigger_condition,
                    "trigger_minutes": r.trigger_minutes,
                    "escalation_level": r.escalation_level,
                    "escalation_notification": r.escalation_notification,
                    "additional_channel_id": r.additional_channel_id,
                    "is_enabled": r.is_enabled,
                    "priority": r.priority,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None
                }
                for r in rules
            ],
            "total": total,
            "page": page,
            "limit": limit
        }
    }


@router.post("/escalations", response_model=MessageResponse)
async def create_escalation_rule(
    data: AlertEscalationRuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """创建升级规则"""
    existing = db.query(AlertEscalationRule).filter(AlertEscalationRule.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="规则名称已存在"
        )
    
    rule = AlertEscalationRule(**data.model_dump())
    db.add(rule)
    db.commit()
    
    return MessageResponse(message="创建成功", success=True)


@router.put("/escalations/{rule_id}", response_model=MessageResponse)
async def update_escalation_rule(
    rule_id: int,
    data: AlertEscalationRuleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """更新升级规则"""
    rule = db.query(AlertEscalationRule).filter(AlertEscalationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    if data.name and data.name != rule.name:
        existing = db.query(AlertEscalationRule).filter(AlertEscalationRule.name == data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="规则名称已存在"
            )
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    return MessageResponse(message="更新成功", success=True)


@router.delete("/escalations/{rule_id}", response_model=MessageResponse)
async def delete_escalation_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """删除升级规则"""
    rule = db.query(AlertEscalationRule).filter(AlertEscalationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则不存在"
        )
    
    db.delete(rule)
    db.commit()
    return MessageResponse(message="删除成功", success=True)
