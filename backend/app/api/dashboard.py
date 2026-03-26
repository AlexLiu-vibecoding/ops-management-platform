"""
仪表盘统计API
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    RDBInstance, RedisInstance, ApprovalRecord, ApprovalStatus, User
)
from app.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取仪表盘统计数据"""
    
    # 1. 数据库实例统计 (RDB + Redis)
    total_rdb = db.query(RDBInstance).count()
    total_redis = db.query(RedisInstance).count()
    online_rdb = db.query(RDBInstance).filter(RDBInstance.status == True).count()
    online_redis = db.query(RedisInstance).filter(RedisInstance.status == True).count()
    total_instances = total_rdb + total_redis
    online_instances = online_rdb + online_redis
    
    # 2. 待审批数量
    pending_approvals = db.query(ApprovalRecord).filter(
        ApprovalRecord.status == ApprovalStatus.PENDING
    ).count()
    
    # 3. 告警数量（暂时返回0，后续可以接入真实告警系统）
    alert_count = 0
    
    return {
        "instance_count": total_instances,
        "online_count": online_instances,
        "pending_approval_count": pending_approvals,
        "alert_count": alert_count
    }
