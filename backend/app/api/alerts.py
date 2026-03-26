"""
告警中心API - 告警记录管理、告警确认、告警统计
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import AlertRecord, RDBInstance, RedisInstance, User
from app.schemas import MessageResponse
from app.deps import get_current_user, get_super_admin

router = APIRouter(prefix="/alerts", tags=["告警中心"])


# ==================== Schemas ====================

class AlertRecordResponse(BaseModel):
    """告警记录响应"""
    id: int
    instance_id: Optional[int]
    instance_name: Optional[str]
    metric_type: str
    alert_level: str
    alert_title: str
    alert_content: Optional[str]
    status: str
    acknowledged_by_name: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_by_name: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    """告警统计"""
    total: int
    pending: int
    acknowledged: int
    resolved: int
    critical: int
    warning: int
    info: int


class AlertAcknowledge(BaseModel):
    """确认告警请求"""
    note: Optional[str] = Field(None, description="确认说明")


class AlertResolve(BaseModel):
    """解决告警请求"""
    note: str = Field(..., description="解决说明")


# ==================== Constants ====================

METRIC_TYPE_LABELS = {
    "slow_query": "慢查询",
    "cpu_sql": "高CPU SQL",
    "performance": "性能指标",
    "lock": "锁等待",
    "repl": "主从复制",
    "capacity": "容量告警"
}

ALERT_LEVEL_LABELS = {
    "info": "信息",
    "warning": "警告",
    "critical": "严重"
}

STATUS_LABELS = {
    "pending": "待处理",
    "acknowledged": "已确认",
    "resolved": "已解决",
    "ignored": "已忽略"
}


# ==================== APIs ====================

@router.get("", response_model=dict)
async def list_alerts(
    instance_id: Optional[int] = None,
    metric_type: Optional[str] = None,
    alert_level: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警记录列表"""
    query = db.query(AlertRecord)
    
    if instance_id:
        query = query.filter(AlertRecord.instance_id == instance_id)
    if metric_type:
        query = query.filter(AlertRecord.metric_type == metric_type)
    if alert_level:
        query = query.filter(AlertRecord.alert_level == alert_level)
    if status:
        query = query.filter(AlertRecord.status == status)
    if start_time:
        query = query.filter(AlertRecord.created_at >= start_time)
    if end_time:
        query = query.filter(AlertRecord.created_at <= end_time)
    
    total = query.count()
    alerts = query.order_by(desc(AlertRecord.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例名称
    instance_ids = [a.instance_id for a in alerts if a.instance_id]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    # 获取用户名称
    user_ids = set()
    for a in alerts:
        if a.acknowledged_by:
            user_ids.add(a.acknowledged_by)
        if a.resolved_by:
            user_ids.add(a.resolved_by)
    users = {u.id: u.real_name or u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    items = []
    for a in alerts:
        items.append({
            "id": a.id,
            "instance_id": a.instance_id,
            "instance_name": instances.get(a.instance_id) if a.instance_id else None,
            "metric_type": a.metric_type,
            "metric_type_label": METRIC_TYPE_LABELS.get(a.metric_type, a.metric_type),
            "alert_level": a.alert_level,
            "alert_level_label": ALERT_LEVEL_LABELS.get(a.alert_level, a.alert_level),
            "alert_title": a.alert_title,
            "alert_content": a.alert_content,
            "status": a.status,
            "status_label": STATUS_LABELS.get(a.status, a.status),
            "acknowledged_by": a.acknowledged_by,
            "acknowledged_by_name": users.get(a.acknowledged_by) if a.acknowledged_by else None,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "resolved_by": a.resolved_by,
            "resolved_by_name": users.get(a.resolved_by) if a.resolved_by else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "resolve_note": a.resolve_note,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })
    
    return {"total": total, "items": items}


@router.get("/stats", response_model=AlertStats)
async def get_alert_stats(
    instance_id: Optional[int] = None,
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警统计"""
    start_time = datetime.now() - timedelta(days=days)
    
    query = db.query(AlertRecord).filter(AlertRecord.created_at >= start_time)
    if instance_id:
        query = query.filter(AlertRecord.instance_id == instance_id)
    
    total = query.count()
    pending = query.filter(AlertRecord.status == "pending").count()
    acknowledged = query.filter(AlertRecord.status == "acknowledged").count()
    resolved = query.filter(AlertRecord.status == "resolved").count()
    critical = query.filter(AlertRecord.alert_level == "critical").count()
    warning = query.filter(AlertRecord.alert_level == "warning").count()
    info = query.filter(AlertRecord.alert_level == "info").count()
    
    return AlertStats(
        total=total,
        pending=pending,
        acknowledged=acknowledged,
        resolved=resolved,
        critical=critical,
        warning=warning,
        info=info
    )


@router.get("/{alert_id}", response_model=dict)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警详情"""
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录不存在")
    
    instance_name = None
    if alert.instance_id:
        instance = db.query(RDBInstance).filter(RDBInstance.id == alert.instance_id).first()
        instance_name = instance.name if instance else None
    
    acknowledged_by_name = None
    if alert.acknowledged_by:
        user = db.query(User).filter(User.id == alert.acknowledged_by).first()
        acknowledged_by_name = user.real_name or user.username if user else None
    
    resolved_by_name = None
    if alert.resolved_by:
        user = db.query(User).filter(User.id == alert.resolved_by).first()
        resolved_by_name = user.real_name or user.username if user else None
    
    return {
        "id": alert.id,
        "instance_id": alert.instance_id,
        "instance_name": instance_name,
        "metric_type": alert.metric_type,
        "metric_type_label": METRIC_TYPE_LABELS.get(alert.metric_type, alert.metric_type),
        "alert_level": alert.alert_level,
        "alert_level_label": ALERT_LEVEL_LABELS.get(alert.alert_level, alert.alert_level),
        "alert_title": alert.alert_title,
        "alert_content": alert.alert_content,
        "alert_source": alert.alert_source,
        "status": alert.status,
        "status_label": STATUS_LABELS.get(alert.status, alert.status),
        "acknowledged_by": alert.acknowledged_by,
        "acknowledged_by_name": acknowledged_by_name,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "resolved_by": alert.resolved_by,
        "resolved_by_name": resolved_by_name,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "resolve_note": alert.resolve_note,
        "notification_sent": alert.notification_sent,
        "created_at": alert.created_at.isoformat() if alert.created_at else None
    }


@router.post("/{alert_id}/acknowledge", response_model=MessageResponse)
async def acknowledge_alert(
    alert_id: int,
    data: AlertAcknowledge,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """确认告警"""
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录不存在")
    
    if alert.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该告警已被处理")
    
    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now()
    
    db.commit()
    return MessageResponse(message="告警已确认")


@router.post("/{alert_id}/resolve", response_model=MessageResponse)
async def resolve_alert(
    alert_id: int,
    data: AlertResolve,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """解决告警"""
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录不存在")
    
    if alert.status == "resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该告警已解决")
    
    alert.status = "resolved"
    alert.resolved_by = current_user.id
    alert.resolved_at = datetime.now()
    alert.resolve_note = data.note
    
    db.commit()
    return MessageResponse(message="告警已解决")


@router.post("/{alert_id}/ignore", response_model=MessageResponse)
async def ignore_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """忽略告警"""
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="告警记录不存在")
    
    if alert.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该告警已被处理")
    
    alert.status = "ignored"
    alert.resolved_by = current_user.id
    alert.resolved_at = datetime.now()
    alert.resolve_note = "已忽略"
    
    db.commit()
    return MessageResponse(message="告警已忽略")


@router.post("/batch-acknowledge", response_model=MessageResponse)
async def batch_acknowledge_alerts(
    alert_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量确认告警"""
    alerts = db.query(AlertRecord).filter(
        AlertRecord.id.in_(alert_ids),
        AlertRecord.status == "pending"
    ).all()
    
    now = datetime.now()
    for alert in alerts:
        alert.status = "acknowledged"
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = now
    
    db.commit()
    return MessageResponse(message=f"已确认 {len(alerts)} 条告警")


@router.get("/metric-types/list")
async def get_metric_types():
    """获取指标类型列表"""
    return [
        {"value": "slow_query", "label": "慢查询"},
        {"value": "cpu_sql", "label": "高CPU SQL"},
        {"value": "performance", "label": "性能指标"},
        {"value": "lock", "label": "锁等待"},
        {"value": "repl", "label": "主从复制"},
        {"value": "capacity", "label": "容量告警"}
    ]


@router.get("/levels/list")
async def get_alert_levels():
    """获取告警级别列表"""
    return [
        {"value": "info", "label": "信息", "color": "#909399"},
        {"value": "warning", "label": "警告", "color": "#E6A23C"},
        {"value": "critical", "label": "严重", "color": "#F56C6C"}
    ]


@router.get("/statuses/list")
async def get_alert_statuses():
    """获取告警状态列表"""
    return [
        {"value": "pending", "label": "待处理", "color": "#E6A23C"},
        {"value": "acknowledged", "label": "已确认", "color": "#409EFF"},
        {"value": "resolved", "label": "已解决", "color": "#67C23A"},
        {"value": "ignored", "label": "已忽略", "color": "#909399"}
    ]
