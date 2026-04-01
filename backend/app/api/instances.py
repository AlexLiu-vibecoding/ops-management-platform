"""
数据库实例管理API（向后兼容 - 统一入口）

推荐使用新的 API：
- /api/v1/rdb-instances - MySQL/PostgreSQL 实例管理
- /api/v1/redis-instances - Redis 实例管理

此 API 保留用于向后兼容
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services.instance_service import RDBInstanceService, RedisInstanceService, InstanceGroupService
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
    
    rdb_service = RDBInstanceService(db)
    redis_service = RedisInstanceService(db)
    
    # 如果没有指定 db_type 或指定的是 mysql/postgresql，查询 RDB 实例
    if not db_type or db_type.lower() in ('mysql', 'postgresql'):
        # 构建过滤条件
        filter_db_type = None
        if db_type and db_type.lower() in ('mysql', 'postgresql'):
            filter_db_type = 'MYSQL' if db_type.lower() == 'mysql' else 'POSTGRESQL'
        
        rdb_instances = rdb_service.get_all_with_environment(
            environment_id=environment_id,
            group_id=group_id,
            db_type=filter_db_type,
            status=status
        )
        
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
        redis_instances = redis_service.get_all_with_environment(
            environment_id=environment_id,
            group_id=group_id,
            status=status
        )
        
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
    rdb_service = RDBInstanceService(db)
    redis_service = RedisInstanceService(db)
    
    # 先尝试从 RDB 表查找
    instance = rdb_service.get_with_environment(instance_id)
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
    instance = redis_service.get_with_environment(instance_id)
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
    rdb_service = RDBInstanceService(db)
    redis_service = RedisInstanceService(db)
    
    # 先尝试从 RDB 表查找
    instance = rdb_service.get(instance_id)
    if instance:
        # RDS 实例不检查连接
        if instance.is_rds:
            return InstanceTestResult(success=True, message="RDS 实例，跳过连接检查", version=None)
        
        # 尝试解密密码
        try:
            password = rdb_service.get_decrypted_password(instance)
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
        rdb_service.update(instance_id, {
            "status": result["success"],
            "last_check_time": datetime.now()
        })
        
        return InstanceTestResult(**result)
    
    # 再尝试从 Redis 表查找
    instance = redis_service.get(instance_id)
    if instance:
        # 尝试解密密码
        password = None
        if instance.password_encrypted:
            try:
                password = redis_service.get_decrypted_password(instance)
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
        redis_service.update(instance_id, {
            "status": result["success"],
            "last_check_time": datetime.now()
        })
        
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
    group_service = InstanceGroupService(db)
    groups = group_service.get_all()
    return [group_service.to_dict(g) for g in groups]


@router.post("/groups/", response_model=MessageResponse)
async def create_instance_group(
    name: str,
    description: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建实例分组"""
    group_service = InstanceGroupService(db)
    group_service.create(name=name, description=description)
    
    return MessageResponse(message="分组创建成功")
