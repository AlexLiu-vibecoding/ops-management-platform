"""
告警规则API - 告警规则配置、管理
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import (
    AlertRule, RDBInstance, Environment, User,
    RULE_TYPE_LABELS, OPERATOR_LABELS, AGGREGATION_LABELS, SEVERITY_CONFIG
)
from app.schemas import MessageResponse
from app.deps import get_current_user, get_operator

router = APIRouter(prefix="/alert-rules", tags=["告警规则"])


# ==================== Schemas ====================

class AlertRuleCreate(BaseModel):
    """创建告警规则"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="描述")
    rule_type: str = Field(..., description="规则类型")
    instance_scope: str = Field("all", description="实例范围")
    instance_ids: Optional[List[int]] = Field(None, description="选中的实例ID列表")
    environment_ids: Optional[List[int]] = Field(None, description="选中的环境ID列表")
    metric_name: Optional[str] = Field(None, description="指标名称")
    operator: str = Field(">", description="比较运算符")
    threshold: float = Field(..., description="阈值")
    duration: int = Field(60, description="持续时间(秒)")
    aggregation: str = Field("avg", description="聚合方式")
    severity: str = Field("warning", description="告警级别")
    silence_duration: int = Field(300, description="静默时长(秒)")
    notify_channels: Optional[str] = Field(None, description="通知通道ID列表")
    notify_enabled: bool = Field(True, description="是否启用通知")
    is_enabled: bool = Field(True, description="是否启用")


class AlertRuleUpdate(BaseModel):
    """更新告警规则"""
    name: Optional[str] = None
    description: Optional[str] = None
    instance_scope: Optional[str] = None
    instance_ids: Optional[List[int]] = None
    environment_ids: Optional[List[int]] = None
    metric_name: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    duration: Optional[int] = None
    aggregation: Optional[str] = None
    severity: Optional[str] = None
    silence_duration: Optional[int] = None
    notify_channels: Optional[str] = None
    notify_enabled: Optional[bool] = None
    is_enabled: Optional[bool] = None


# ==================== APIs ====================

@router.get("", response_model=dict)
async def list_alert_rules(
    rule_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警规则列表"""
    query = db.query(AlertRule)
    
    if rule_type:
        query = query.filter(AlertRule.rule_type == rule_type)
    if is_enabled is not None:
        query = query.filter(AlertRule.is_enabled == is_enabled)
    if search:
        query = query.filter(AlertRule.name.ilike(f"%{search}%"))
    
    total = query.count()
    items = query.order_by(desc(AlertRule.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取创建人名称
    user_ids = [r.created_by for r in items if r.created_by]
    users = {u.id: u.real_name or u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    return {
        "total": total,
        "items": [{
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "rule_type_label": RULE_TYPE_LABELS.get(r.rule_type, r.rule_type),
            "instance_scope": r.instance_scope,
            "operator": r.operator,
            "operator_label": OPERATOR_LABELS.get(r.operator, r.operator),
            "threshold": r.threshold,
            "duration": r.duration,
            "aggregation": r.aggregation,
            "aggregation_label": AGGREGATION_LABELS.get(r.aggregation, r.aggregation),
            "severity": r.severity,
            "severity_label": SEVERITY_CONFIG.get(r.severity, {}).get("label", r.severity),
            "severity_color": SEVERITY_CONFIG.get(r.severity, {}).get("color", "#909399"),
            "silence_duration": r.silence_duration,
            "notify_enabled": r.notify_enabled,
            "is_enabled": r.is_enabled,
            "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
            "trigger_count": r.trigger_count,
            "created_by": r.created_by,
            "created_by_name": users.get(r.created_by),
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in items]
    }


@router.post("", response_model=MessageResponse)
async def create_alert_rule(
    data: AlertRuleCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """创建告警规则"""
    # 验证规则类型
    if data.rule_type not in RULE_TYPE_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的规则类型")
    
    # 验证运算符
    if data.operator not in OPERATOR_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的比较运算符")
    
    # 验证聚合方式
    if data.aggregation not in AGGREGATION_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的聚合方式")
    
    # 验证告警级别
    if data.severity not in SEVERITY_CONFIG:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的告警级别")
    
    rule = AlertRule(
        name=data.name,
        description=data.description,
        rule_type=data.rule_type,
        instance_scope=data.instance_scope,
        instance_ids=data.instance_ids,
        environment_ids=data.environment_ids,
        metric_name=data.metric_name,
        operator=data.operator,
        threshold=data.threshold,
        duration=data.duration,
        aggregation=data.aggregation,
        severity=data.severity,
        silence_duration=data.silence_duration,
        notify_channels=data.notify_channels,
        notify_enabled=data.notify_enabled,
        is_enabled=data.is_enabled,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    
    return MessageResponse(message="创建成功")


@router.get("/{rule_id}", response_model=dict)
async def get_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警规则详情"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    
    created_by_name = None
    if rule.created_by:
        user = db.query(User).filter(User.id == rule.created_by).first()
        created_by_name = user.real_name or user.username if user else None
    
    # 获取实例名称
    instance_names = []
    if rule.instance_ids:
        instances = db.query(RDBInstance).filter(RDBInstance.id.in_(rule.instance_ids)).all()
        instance_names = [{"id": i.id, "name": i.name} for i in instances]
    
    # 获取环境名称
    environment_names = []
    if rule.environment_ids:
        environments = db.query(Environment).filter(Environment.id.in_(rule.environment_ids)).all()
        environment_names = [{"id": e.id, "name": e.name} for e in environments]
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "rule_type_label": RULE_TYPE_LABELS.get(rule.rule_type, rule.rule_type),
        "instance_scope": rule.instance_scope,
        "instance_ids": rule.instance_ids,
        "instance_names": instance_names,
        "environment_ids": rule.environment_ids,
        "environment_names": environment_names,
        "metric_name": rule.metric_name,
        "operator": rule.operator,
        "operator_label": OPERATOR_LABELS.get(rule.operator, rule.operator),
        "threshold": rule.threshold,
        "duration": rule.duration,
        "aggregation": rule.aggregation,
        "aggregation_label": AGGREGATION_LABELS.get(rule.aggregation, rule.aggregation),
        "severity": rule.severity,
        "severity_label": SEVERITY_CONFIG.get(rule.severity, {}).get("label", rule.severity),
        "severity_color": SEVERITY_CONFIG.get(rule.severity, {}).get("color", "#909399"),
        "silence_duration": rule.silence_duration,
        "silence_until": rule.silence_until.isoformat() if rule.silence_until else None,
        "notify_channels": rule.notify_channels,
        "notify_enabled": rule.notify_enabled,
        "is_enabled": rule.is_enabled,
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
        "trigger_count": rule.trigger_count,
        "created_by": rule.created_by,
        "created_by_name": created_by_name,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
    }


@router.put("/{rule_id}", response_model=MessageResponse)
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """更新告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    
    if data.name is not None:
        rule.name = data.name
    if data.description is not None:
        rule.description = data.description
    if data.instance_scope is not None:
        rule.instance_scope = data.instance_scope
    if data.instance_ids is not None:
        rule.instance_ids = data.instance_ids
    if data.environment_ids is not None:
        rule.environment_ids = data.environment_ids
    if data.metric_name is not None:
        rule.metric_name = data.metric_name
    if data.operator is not None:
        rule.operator = data.operator
    if data.threshold is not None:
        rule.threshold = data.threshold
    if data.duration is not None:
        rule.duration = data.duration
    if data.aggregation is not None:
        rule.aggregation = data.aggregation
    if data.severity is not None:
        rule.severity = data.severity
    if data.silence_duration is not None:
        rule.silence_duration = data.silence_duration
    if data.notify_channels is not None:
        rule.notify_channels = data.notify_channels
    if data.notify_enabled is not None:
        rule.notify_enabled = data.notify_enabled
    if data.is_enabled is not None:
        rule.is_enabled = data.is_enabled
    
    db.commit()
    return MessageResponse(message="更新成功")


@router.delete("/{rule_id}", response_model=MessageResponse)
async def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """删除告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    
    db.delete(rule)
    db.commit()
    return MessageResponse(message="删除成功")


@router.post("/{rule_id}/toggle", response_model=MessageResponse)
async def toggle_alert_rule(
    rule_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """启用/禁用告警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    
    rule.is_enabled = not rule.is_enabled
    db.commit()
    
    return MessageResponse(message=f"规则已{'禁用' if not rule.is_enabled else '启用'}")


@router.get("/types/list")
async def get_rule_types():
    """获取规则类型列表"""
    return [
        {"value": k, "label": v} for k, v in RULE_TYPE_LABELS.items()
    ]


@router.get("/operators/list")
async def get_operators():
    """获取比较运算符列表"""
    return [
        {"value": k, "label": v} for k, v in OPERATOR_LABELS.items()
    ]


@router.get("/aggregations/list")
async def get_aggregations():
    """获取聚合方式列表"""
    return [
        {"value": k, "label": v} for k, v in AGGREGATION_LABELS.items()
    ]


@router.get("/severities/list")
async def get_severities():
    """获取告警级别列表"""
    return [
        {"value": k, "label": v["label"], "color": v["color"]} 
        for k, v in SEVERITY_CONFIG.items()
    ]
