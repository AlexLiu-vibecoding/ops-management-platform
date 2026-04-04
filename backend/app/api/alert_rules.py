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


# ==================== 选项列表 API ====================

@router.get("/types/list")
async def get_alert_types():
    """获取告警规则类型列表"""
    return [
        {"value": "metric", "label": "指标告警"},
        {"value": "log", "label": "日志告警"},
        {"value": "event", "label": "事件告警"},
        {"value": "composite", "label": "复合告警"}
    ]


@router.get("/operators/list")
async def get_operators():
    """获取运算符列表"""
    return [
        {"value": "gt", "label": "大于"},
        {"value": "gte", "label": "大于等于"},
        {"value": "lt", "label": "小于"},
        {"value": "lte", "label": "小于等于"},
        {"value": "eq", "label": "等于"},
        {"value": "neq", "label": "不等于"},
        {"value": "contains", "label": "包含"},
        {"value": "not_contains", "label": "不包含"}
    ]


@router.get("/aggregations/list")
async def get_aggregation_methods():
    """获取聚合方式列表"""
    return [
        {"value": "avg", "label": "平均值"},
        {"value": "max", "label": "最大值"},
        {"value": "min", "label": "最小值"},
        {"value": "sum", "label": "求和"},
        {"value": "count", "label": "计数"},
        {"value": "p95", "label": "P95"},
        {"value": "p99", "label": "P99"}
    ]


@router.get("/severities/list")
async def get_severities():
    """获取告警级别列表"""
    return [
        {"value": "critical", "label": "严重"},
        {"value": "high", "label": "高"},
        {"value": "medium", "label": "中"},
        {"value": "low", "label": "低"},
        {"value": "info", "label": "信息"}
    ]


# ==================== 告警规则 CRUD API ====================

from app.models.alert_rule import AlertRule, RULE_TYPE_LABELS, OPERATOR_LABELS, AGGREGATION_LABELS, SEVERITY_CONFIG
from app.deps import get_current_user


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    rule_type: str = Field(..., min_length=1)
    instance_scope: str = Field("all")
    instance_ids: Optional[list[int]] = None
    metric_name: Optional[str] = None
    operator: str = Field(">")
    threshold: float = Field(0)
    duration: int = Field(60)
    aggregation: str = Field("avg")
    severity: str = Field("warning")
    silence_duration: int = Field(300)
    notify_enabled: bool = Field(True)
    is_enabled: bool = Field(True)


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    rule_type: Optional[str] = None
    instance_scope: Optional[str] = None
    instance_ids: Optional[list[int]] = None
    metric_name: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    duration: Optional[int] = None
    aggregation: Optional[str] = None
    severity: Optional[str] = None
    silence_duration: Optional[int] = None
    notify_enabled: Optional[bool] = None
    is_enabled: Optional[bool] = None


@router.get("")
async def list_alert_rules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    rule_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取告警规则列表"""
    query = db.query(AlertRule)
    
    if search:
        query = query.filter(AlertRule.name.ilike(f"%{search}%"))
    if rule_type:
        query = query.filter(AlertRule.rule_type == rule_type)
    if is_enabled is not None:
        query = query.filter(AlertRule.is_enabled == is_enabled)
    
    total = query.count()
    rules = query.order_by(desc(AlertRule.created_at)) \
        .offset((page - 1) * limit) \
        .limit(limit) \
        .all()
    
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "rule_type": r.rule_type,
                "instance_scope": r.instance_scope,
                "instance_ids": r.instance_ids or [],
                "metric_name": r.metric_name,
                "operator": r.operator,
                "threshold": r.threshold,
                "duration": r.duration,
                "aggregation": r.aggregation,
                "severity": r.severity,
                "silence_duration": r.silence_duration,
                "notify_enabled": r.notify_enabled,
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


@router.get("/{rule_id}")
async def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取告警规则详情"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "instance_scope": rule.instance_scope,
        "instance_ids": rule.instance_ids or [],
        "metric_name": rule.metric_name,
        "operator": rule.operator,
        "threshold": rule.threshold,
        "duration": rule.duration,
        "aggregation": rule.aggregation,
        "severity": rule.severity,
        "silence_duration": rule.silence_duration,
        "notify_enabled": rule.notify_enabled,
        "is_enabled": rule.is_enabled,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
    }


@router.post("")
async def create_alert_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """创建告警规则"""
    existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="规则名称已存在")
    
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {"id": rule.id, "message": "创建成功"}


@router.put("/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """更新告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    if data.name and data.name != rule.name:
        existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="规则名称已存在")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    
    db.commit()
    return {"message": "更新成功"}


@router.delete("/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """删除告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    db.delete(rule)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{rule_id}/toggle")
async def toggle_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_super_admin)
):
    """启用/禁用告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    rule.is_enabled = not rule.is_enabled
    db.commit()
    return {"message": "操作成功", "is_enabled": rule.is_enabled}


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
