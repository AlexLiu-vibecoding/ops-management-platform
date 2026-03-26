"""
数据库实例管理API（向后兼容 - 统一入口）

推荐使用新的 API：
- /api/v1/rdb-instances - MySQL/PostgreSQL 实例管理
- /api/v1/redis-instances - Redis 实例管理

此 API 保留用于向后兼容，底层使用 v_all_instances 视图
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, literal_column
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.models import RDBInstance, RedisInstance, InstanceGroup
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/instances", tags=["实例管理(兼容)"])
logger = logging.getLogger(__name__)


# ============ Schema 定义 ============

class InstanceResponse(BaseModel):
    """实例响应（兼容格式）"""
    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: Optional[str] = None
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    status: bool = True
    is_rds: bool = False
    rds_instance_id: Optional[str] = None
    aws_region: Optional[str] = None
    redis_mode: Optional[str] = None
    redis_db: Optional[int] = None
    last_check_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ============ API 路由 ============

@router.get("")
async def list_instances(
    environment_id: Optional[int] = None,
    group_id: Optional[int] = None,
    db_type: Optional[str] = None,
    status: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例列表（向后兼容）"""
    # 使用 UNION 查询两个表
    rdb_query = db.query(
        RDBInstance.id,
        RDBInstance.name,
        RDBInstance.db_type,
        RDBInstance.host,
        RDBInstance.port,
        RDBInstance.username,
        RDBInstance.environment_id,
        RDBInstance.group_id,
        RDBInstance.description,
        RDBInstance.status,
        RDBInstance.is_rds,
        RDBInstance.rds_instance_id,
        RDBInstance.aws_region,
        RDBInstance.last_check_time,
        RDBInstance.created_at,
        RDBInstance.updated_at,
    )
    
    redis_query = db.query(
        RedisInstance.id,
        RedisInstance.name,
        literal_column("'redis'").label('db_type'),
        RedisInstance.host,
        RedisInstance.port,
        literal_column("NULL").label('username'),
        RedisInstance.environment_id,
        RedisInstance.group_id,
        RedisInstance.description,
        RedisInstance.status,
        literal_column("FALSE").label('is_rds'),
        literal_column("NULL").label('rds_instance_id'),
        literal_column("NULL").label('aws_region'),
        RedisInstance.last_check_time,
        RedisInstance.created_at,
        RedisInstance.updated_at,
    )
    
    # 合并查询
    query = rdb_query.union_all(redis_query)
    
    # 应用过滤条件
    if environment_id:
        query = query.filter(text(f"environment_id = {environment_id}"))
    if group_id:
        query = query.filter(text(f"group_id = {group_id}"))
    if db_type:
        query = query.filter(text(f"db_type = '{db_type}'"))
    if status is not None:
        query = query.filter(text(f"status = {status}"))
    
    # 获取总数
    total = query.count()
    
    # 分页
    instances = query.offset(skip).limit(limit).all()
    
    # 转换为响应格式
    items = []
    for i in instances:
        items.append({
            "id": i.id,
            "name": i.name,
            "db_type": i.db_type if isinstance(i.db_type, str) else i.db_type.value if hasattr(i.db_type, 'value') else str(i.db_type),
            "host": i.host,
            "port": i.port,
            "username": i.username,
            "environment_id": i.environment_id,
            "group_id": i.group_id,
            "description": i.description,
            "status": i.status,
            "is_rds": i.is_rds if hasattr(i, 'is_rds') else False,
            "rds_instance_id": i.rds_instance_id if hasattr(i, 'rds_instance_id') else None,
            "aws_region": i.aws_region if hasattr(i, 'aws_region') else None,
            "redis_mode": None,  # 兼容字段
            "redis_db": None,
            "last_check_time": i.last_check_time,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        })
    
    return {
        "total": total,
        "items": items
    }


@router.get("/{instance_id}")
async def get_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例详情（向后兼容）"""
    # 先尝试从 RDB 表查找
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if instance:
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": instance.db_type.value if hasattr(instance.db_type, 'value') else instance.db_type,
            "host": instance.host,
            "port": instance.port,
            "username": instance.username,
            "environment_id": instance.environment_id,
            "group_id": instance.group_id,
            "description": instance.description,
            "status": instance.status,
            "is_rds": instance.is_rds,
            "rds_instance_id": instance.rds_instance_id,
            "aws_region": instance.aws_region,
            "redis_mode": None,
            "redis_db": None,
            "last_check_time": instance.last_check_time,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }
    
    # 再尝试从 Redis 表查找
    instance = db.query(RedisInstance).filter(RedisInstance.id == instance_id).first()
    if instance:
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": "redis",
            "host": instance.host,
            "port": instance.port,
            "username": None,
            "environment_id": instance.environment_id,
            "group_id": instance.group_id,
            "description": instance.description,
            "status": instance.status,
            "is_rds": False,
            "rds_instance_id": None,
            "aws_region": None,
            "redis_mode": instance.redis_mode.value if hasattr(instance.redis_mode, 'value') else instance.redis_mode,
            "redis_db": instance.redis_db,
            "last_check_time": instance.last_check_time,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="实例不存在"
    )


# ============ 实例分组相关 ============

@router.get("/groups/", response_model=List[dict])
async def list_instance_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例分组列表"""
    groups = db.query(InstanceGroup).all()
    return [{"id": g.id, "name": g.name, "description": g.description} for g in groups]


@router.post("/groups/", response_model=MessageResponse)
async def create_instance_group(
    name: str,
    description: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建实例分组"""
    if db.query(InstanceGroup).filter(InstanceGroup.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分组名称已存在"
        )
    
    group = InstanceGroup(name=name, description=description)
    db.add(group)
    db.commit()
    
    return MessageResponse(message="分组创建成功")
