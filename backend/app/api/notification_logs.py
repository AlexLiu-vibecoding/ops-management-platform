"""通知历史记录 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.models import NotificationLog
from pydantic import BaseModel, Field


router = APIRouter(prefix="/notification-logs", tags=["通知历史"])


# ==================== Schemas ====================

class BaseResponse(BaseModel):
    """基础响应"""
    code: int = 0
    message: str = "success"


class NotificationLogResponse(BaseModel):
    id: int
    notification_type: str
    sub_type: Optional[str] = None
    channel_id: Optional[int] = None
    channel_name: Optional[str] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    approval_id: Optional[int] = None
    alert_id: Optional[int] = None
    title: str
    content: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    response_code: Optional[int] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginationData(BaseModel):
    """分页数据"""
    items: list[Any]
    total: int
    page: int
    page_size: int


class NotificationLogListResponse(BaseResponse):
    data: PaginationData


class NotificationLogDetailResponse(BaseResponse):
    data: Optional[NotificationLogResponse] = None


class NotificationStats(BaseModel):
    total: int
    success: int
    failed: int
    pending: int
    by_type: dict
    by_channel: dict


class NotificationStatsResponse(BaseResponse):
    data: NotificationStats


# ==================== APIs ====================

@router.get("", response_model=NotificationLogListResponse)
async def list_notification_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    notification_type: Optional[str] = Query(None, description="通知类型: approval/alert/scheduled_task"),
    status: Optional[str] = Query(None, description="状态: pending/success/failed"),
    channel_id: Optional[int] = Query(None, description="通道ID"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: Session = Depends(get_db)
):
    """获取通知历史列表"""
    
    query = db.query(NotificationLog)
    
    # 类型过滤
    if notification_type:
        query = query.filter(NotificationLog.notification_type == notification_type)
    
    # 状态过滤
    if status:
        query = query.filter(NotificationLog.status == status)
    
    # 通道过滤
    if channel_id:
        query = query.filter(NotificationLog.channel_id == channel_id)
    
    # 日期过滤
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(NotificationLog.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(NotificationLog.created_at < end_dt)
        except ValueError:
            pass
    
    # 关键词搜索
    if keyword:
        query = query.filter(
            (NotificationLog.title.contains(keyword)) |
            (NotificationLog.content.contains(keyword))
        )
    
    # 统计总数
    total = query.count()
    
    # 分页查询
    logs = query.order_by(desc(NotificationLog.created_at)) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()
    
    return NotificationLogListResponse(
        code=0,
        message="获取成功",
        data=PaginationData(
            items=[NotificationLogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size
        )
    )


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    db: Session = Depends(get_db)
):
    """获取通知统计信息"""
    
    # 计算时间范围
    start_time = datetime.now() - timedelta(days=days)
    
    query = db.query(NotificationLog).filter(NotificationLog.created_at >= start_time)
    
    # 总数统计
    total = query.count()
    success = query.filter(NotificationLog.status == "success").count()
    failed = query.filter(NotificationLog.status == "failed").count()
    pending = query.filter(NotificationLog.status == "pending").count()
    
    # 按类型统计
    from sqlalchemy import func
    type_stats = db.query(
        NotificationLog.notification_type,
        func.count(NotificationLog.id)
    ).filter(
        NotificationLog.created_at >= start_time
    ).group_by(NotificationLog.notification_type).all()
    
    by_type = {row[0]: row[1] for row in type_stats}
    
    # 按通道统计
    channel_stats = db.query(
        NotificationLog.channel_name,
        func.count(NotificationLog.id)
    ).filter(
        NotificationLog.created_at >= start_time,
        NotificationLog.channel_name.isnot(None)
    ).group_by(NotificationLog.channel_name).all()
    
    by_channel = {row[0]: row[1] for row in channel_stats}
    
    return NotificationStatsResponse(
        code=0,
        message="获取成功",
        data=NotificationStats(
            total=total,
            success=success,
            failed=failed,
            pending=pending,
            by_type=by_type,
            by_channel=by_channel
        )
    )


@router.get("/{log_id}", response_model=NotificationLogDetailResponse)
async def get_notification_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """获取通知详情"""
    
    log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
    
    if not log:
        return NotificationLogDetailResponse(
            code=404,
            message="通知记录不存在"
        )
    
    return NotificationLogDetailResponse(
        code=0,
        message="获取成功",
        data=NotificationLogResponse.model_validate(log)
    )


@router.delete("/{log_id}", response_model=BaseResponse)
async def delete_notification_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """删除通知记录"""
    
    log = db.query(NotificationLog).filter(NotificationLog.id == log_id).first()
    
    if not log:
        return BaseResponse(code=404, message="通知记录不存在")
    
    db.delete(log)
    db.commit()
    
    return BaseResponse(code=0, message="删除成功")


@router.post("/clear", response_model=BaseResponse)
async def clear_notification_logs(
    days: int = Query(30, ge=7, description="保留最近N天的记录"),
    db: Session = Depends(get_db)
):
    """清理历史通知记录"""
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    deleted_count = db.query(NotificationLog).filter(
        NotificationLog.created_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return BaseResponse(
        code=0,
        message=f"已清理 {deleted_count} 条历史记录"
    )
