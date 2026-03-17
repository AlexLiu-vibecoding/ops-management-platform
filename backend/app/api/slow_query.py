"""
慢查询监控API
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    SlowQuery, Instance, MonitorSwitch, 
    MonitorType, User
)
from app.schemas import SlowQueryResponse, MessageResponse
from app.deps import get_current_user

router = APIRouter(prefix="/slow-query", tags=["慢查询监控"])


@router.get("/{instance_id}", response_model=List[SlowQueryResponse])
async def list_slow_queries(
    instance_id: int,
    min_time: Optional[float] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 检查监控开关
    switch = db.query(MonitorSwitch).filter(
        MonitorSwitch.instance_id == instance_id,
        MonitorSwitch.monitor_type == MonitorType.SLOW_QUERY
    ).first()
    
    if not switch or not switch.enabled:
        return []
    
    # 查询慢查询
    query = db.query(SlowQuery).filter(
        SlowQuery.instance_id == instance_id
    )
    
    if min_time:
        query = query.filter(SlowQuery.query_time >= min_time)
    
    queries = query.order_by(SlowQuery.query_time.desc()).limit(limit).all()
    return [SlowQueryResponse.from_orm(q) for q in queries]


@router.get("/{instance_id}/top", response_model=List[SlowQueryResponse])
async def get_top_slow_queries(
    instance_id: int,
    hours: int = 24,
    top_n: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取Top N慢查询"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 按执行时间或执行次数排序
    queries = db.query(SlowQuery).filter(
        SlowQuery.instance_id == instance_id,
        SlowQuery.last_seen >= start_time
    ).order_by(SlowQuery.query_time.desc()).limit(top_n).all()
    
    return [SlowQueryResponse.from_orm(q) for q in queries]


@router.get("/{instance_id}/statistics", response_model=dict)
async def get_slow_query_statistics(
    instance_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询统计"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 统计
    stats = db.query(
        func.count(SlowQuery.id).label('total_count'),
        func.sum(SlowQuery.execution_count).label('total_executions'),
        func.max(SlowQuery.query_time).label('max_time'),
        func.avg(SlowQuery.query_time).label('avg_time')
    ).filter(
        SlowQuery.instance_id == instance_id,
        SlowQuery.last_seen >= start_time
    ).first()
    
    return {
        "total_count": stats.total_count or 0,
        "total_executions": stats.total_executions or 0,
        "max_time": float(stats.max_time) if stats.max_time else 0,
        "avg_time": float(stats.avg_time) if stats.avg_time else 0
    }


@router.get("/{instance_id}/analysis/{query_id}", response_model=dict)
async def analyze_slow_query(
    instance_id: int,
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分析慢查询"""
    slow_query = db.query(SlowQuery).filter(
        SlowQuery.id == query_id,
        SlowQuery.instance_id == instance_id
    ).first()
    
    if not slow_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="慢查询记录不存在"
        )
    
    # TODO: 执行EXPLAIN分析
    # 这里需要连接到实际实例执行EXPLAIN
    
    return {
        "query": slow_query,
        "explanation": "待实现EXPLAIN分析",
        "suggestions": [
            "检查是否缺少索引",
            "检查是否全表扫描",
            "检查WHERE条件是否使用了函数",
            "检查是否使用了SELECT *"
        ]
    }
