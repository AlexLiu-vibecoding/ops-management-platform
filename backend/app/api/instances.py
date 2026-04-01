"""
数据库实例管理API（向后兼容 - 统一入口）

推荐使用新的 API：
- /api/v1/rdb-instances - MySQL/PostgreSQL 实例管理
- /api/v1/redis-instances - Redis 实例管理

此 API 保留用于向后兼容
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.models import RDBInstance, RedisInstance, InstanceGroup, Environment
from app.deps import get_current_user
from app.models import User
from app.utils.auth import decrypt_instance_password
from app.api.rdb_instances import test_rdb_connection, InstanceTestResult
from app.api.redis_instances import test_redis_connection

router = APIRouter(prefix="/instances", tags=["实例管理(兼容)"])
logger = logging.getLogger(__name__)


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


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
    items = []
    
    # 如果没有指定 db_type 或指定的是 mysql/postgresql，查询 RDB 实例
    if not db_type or db_type.lower() in ('mysql', 'postgresql'):
        rdb_query = db.query(RDBInstance).options(
            joinedload(RDBInstance.environment)
        )
        
        if environment_id:
            rdb_query = rdb_query.filter(RDBInstance.environment_id == environment_id)
        if group_id:
            rdb_query = rdb_query.filter(RDBInstance.group_id == group_id)
        if db_type and db_type.lower() in ('mysql', 'postgresql'):
            if db_type.lower() == 'mysql':
                rdb_query = rdb_query.filter(RDBInstance.db_type == 'MYSQL')
            elif db_type.lower() == 'postgresql':
                rdb_query = rdb_query.filter(RDBInstance.db_type == 'POSTGRESQL')
        if status is not None:
            rdb_query = rdb_query.filter(RDBInstance.status == status)
        
        rdb_instances = rdb_query.all()
        for i in rdb_instances:
            # 使用预加载的 environment 关系，避免 N+1 查询
            env_data = None
            if i.environment:
                env_data = {"id": i.environment.id, "name": i.environment.name, "color": i.environment.color}
            
            items.append({
                "id": i.id,
                "name": i.name,
                "db_type": i.db_type.value if hasattr(i.db_type, 'value') else str(i.db_type),
                "host": i.host,
                "port": i.port,
                "username": i.username,
                "environment_id": i.environment_id,
                "environment": env_data,
                "group_id": i.group_id,
                "description": i.description,
                "status": i.status,
                "is_rds": i.is_rds,
                "rds_instance_id": i.rds_instance_id,
                "aws_region": i.aws_region,
                "redis_mode": None,
                "redis_db": None,
                "last_check_time": i.last_check_time,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            })
    
    # 如果没有指定 db_type 或指定的是 redis，查询 Redis 实例
    if not db_type or db_type.lower() == 'redis':
        redis_query = db.query(RedisInstance).options(
            joinedload(RedisInstance.environment)
        )
        
        if environment_id:
            redis_query = redis_query.filter(RedisInstance.environment_id == environment_id)
        if group_id:
            redis_query = redis_query.filter(RedisInstance.group_id == group_id)
        if status is not None:
            redis_query = redis_query.filter(RedisInstance.status == status)
        
        redis_instances = redis_query.all()
        for i in redis_instances:
            # 使用预加载的 environment 关系，避免 N+1 查询
            env_data = None
            if i.environment:
                env_data = {"id": i.environment.id, "name": i.environment.name, "color": i.environment.color}
            
            items.append({
                "id": i.id,
                "name": i.name,
                "db_type": "redis",
                "host": i.host,
                "port": i.port,
                "username": None,
                "environment_id": i.environment_id,
                "environment": env_data,
                "group_id": i.group_id,
                "description": i.description,
                "status": i.status,
                "is_rds": False,
                "rds_instance_id": None,
                "aws_region": None,
                "redis_mode": i.redis_mode.value if hasattr(i.redis_mode, 'value') else str(i.redis_mode),
                "redis_db": i.redis_db,
                "last_check_time": i.last_check_time,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            })
    
    # 按 created_at 降序排序
    items.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
    
    # 计算总数和分页
    total = len(items)
    paginated_items = items[skip:skip + limit]
    
    return {
        "total": total,
        "items": paginated_items
    }


@router.get("/{instance_id}")
async def get_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例详情（向后兼容）"""
    # 先尝试从 RDB 表查找
    instance = db.query(RDBInstance).options(
        joinedload(RDBInstance.environment)
    ).filter(RDBInstance.id == instance_id).first()
    if instance:
        # 使用预加载的 environment 关系
        env_data = None
        if instance.environment:
            env_data = {"id": instance.environment.id, "name": instance.environment.name, "color": instance.environment.color}
        
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": instance.db_type.value if hasattr(instance.db_type, 'value') else instance.db_type,
            "host": instance.host,
            "port": instance.port,
            "username": instance.username,
            "environment_id": instance.environment_id,
            "environment": env_data,
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
    instance = db.query(RedisInstance).options(
        joinedload(RedisInstance.environment)
    ).filter(RedisInstance.id == instance_id).first()
    if instance:
        # 使用预加载的 environment 关系
        env_data = None
        if instance.environment:
            env_data = {"id": instance.environment.id, "name": instance.environment.name, "color": instance.environment.color}
        
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": "redis",
            "host": instance.host,
            "port": instance.port,
            "username": None,
            "environment_id": instance.environment_id,
            "environment": env_data,
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


@router.post("/{instance_id}/check", response_model=InstanceTestResult)
async def check_instance_status(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查实例状态（向后兼容）"""
    # 先尝试从 RDB 表查找
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if instance:
        # RDS 实例不检查连接
        if instance.is_rds:
            return InstanceTestResult(success=True, message="RDS 实例，跳过连接检查", version=None)
        
        # 尝试解密密码
        try:
            password = decrypt_instance_password(instance.password_encrypted)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
            )
        
        result = await test_rdb_connection(
            instance.db_type,
            instance.host,
            instance.port,
            instance.username,
            password
        )
        
        # 更新实例状态
        instance.status = result["success"]
        instance.last_check_time = datetime.now()
        db.commit()
        
        return InstanceTestResult(**result)
    
    # 再尝试从 Redis 表查找
    instance = db.query(RedisInstance).filter(RedisInstance.id == instance_id).first()
    if instance:
        # 尝试解密密码
        password = None
        if instance.password_encrypted:
            try:
                password = decrypt_instance_password(instance.password_encrypted)
            except ValueError as e:
                return InstanceTestResult(
                    success=False,
                    message=f"密码解密失败: {str(e)}"
                )
        
        result = await test_redis_connection(
            instance.host,
            instance.port,
            password or "",
            instance.redis_db
        )
        
        # 更新实例状态
        instance.status = result["success"]
        instance.last_check_time = datetime.now()
        db.commit()
        
        return InstanceTestResult(**result)
    
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
