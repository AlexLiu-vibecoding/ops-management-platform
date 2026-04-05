"""
Redis 实例管理 API

提供 Redis 实例的增删改查、连接测试、慢日志查询、内存分析等功能
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models import RedisInstance, InstanceGroup, RedisMode, RedisSlowLog, RedisMemoryStats, Environment, GlobalConfig
from app.services.instance_service import RedisInstanceService
from app.utils.auth import encrypt_instance_password
from app.deps import get_operator, get_current_user, require_permission
from app.models import User

router = APIRouter(prefix="/redis-instances", tags=["Redis实例管理"])
logger = logging.getLogger(__name__)


def check_db_type_enabled(db: Session, db_type: str) -> bool:
    """检查数据库类型是否启用"""
    config = db.query(GlobalConfig).filter(
        GlobalConfig.config_key == f"db_type_{db_type}_enabled"
    ).first()
    
    if config:
        return config.config_value.lower() == "true"
    return True  # 默认启用


# ============ Schema 定义 ============

class RedisInstanceCreate(BaseModel):
    """创建 Redis 实例请求"""
    name: str
    host: str
    port: int = 6379
    password: Optional[str] = None
    redis_mode: str = "standalone"  # standalone / cluster / sentinel
    redis_db: int = 0
    # Cluster 模式配置
    cluster_nodes: Optional[str] = None
    # Sentinel 模式配置
    sentinel_master_name: Optional[str] = None
    sentinel_hosts: Optional[str] = None
    # 其他
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    status: bool = True
    # 监控配置
    slowlog_threshold: int = 10000  # 微秒
    enable_monitoring: bool = True


class RedisInstanceUpdate(BaseModel):
    """更新 Redis 实例请求"""
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    redis_mode: Optional[str] = None
    redis_db: Optional[int] = None
    cluster_nodes: Optional[str] = None
    sentinel_master_name: Optional[str] = None
    sentinel_hosts: Optional[str] = None
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    slowlog_threshold: Optional[int] = None
    enable_monitoring: Optional[bool] = None


class RedisInstanceResponse(BaseModel):
    """Redis 实例响应"""
    id: int
    name: str
    host: str
    port: int
    redis_mode: str
    redis_db: int
    cluster_nodes: Optional[str]
    sentinel_master_name: Optional[str]
    sentinel_hosts: Optional[str]
    environment_id: Optional[int]
    group_id: Optional[int]
    description: Optional[str]
    status: bool
    slowlog_threshold: int
    enable_monitoring: bool
    last_check_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InstanceTestResult(BaseModel):
    """实例连接测试结果"""
    success: bool
    message: str
    version: Optional[str] = None
    info: Optional[dict] = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


class RedisSlowLogResponse(BaseModel):
    """Redis 慢日志响应"""
    id: int
    instance_id: int
    slowlog_id: Optional[int]
    timestamp: Optional[datetime]
    duration: Optional[int]
    command: Optional[str]
    key: Optional[str]
    args: Optional[str]
    client_addr: Optional[str]
    client_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 连接测试函数 ============

async def test_redis_connection(host: str, port: int, password: str = "", redis_db: int = 0) -> dict:
    """测试 Redis 连接"""
    import redis.asyncio as redis
    
    try:
        # 创建 Redis 连接
        client = redis.Redis(
            host=host,
            port=port,
            password=password if password else None,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # 测试连接并获取信息
        info = await client.info()
        await client.close()
        
        # 获取 Redis 版本
        version = info.get("redis_version", "unknown")
        
        return {
            "success": True,
            "message": "连接成功",
            "version": f"Redis {version}",
            "info": {
                "version": version,
                "mode": info.get("redis_mode", "standalone"),
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": sum(v.get("keys", 0) for k, v in info.items() if k.startswith("db"))
            }
        }
    except redis.AuthenticationError:
        return {
            "success": False,
            "message": "认证失败: 密码错误",
            "version": None
        }
    except redis.ConnectionError as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "version": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接测试失败: {str(e)}",
            "version": None
        }


async def get_redis_client(instance: RedisInstance, db: int = None):
    """获取 Redis 客户端"""
    import redis.asyncio as redis
    from app.services.instance_service import RedisInstanceService
    from app.database import SessionLocal
    
    password = None
    if instance.password_encrypted:
        try:
            # 使用 Service 层解密密码
            with SessionLocal() as session:
                service = RedisInstanceService(session)
                password = service.get_decrypted_password(instance)
        except Exception:
            pass
    
    return redis.Redis(
        host=instance.host,
        port=instance.port,
        password=password,
        db=db if db is not None else instance.redis_db,
        decode_responses=True,
        socket_connect_timeout=10
    )


# ============ API 路由 ============

@router.get("")
async def list_redis_instances(
    environment_id: Optional[int] = None,
    group_id: Optional[int] = None,
    redis_mode: Optional[str] = None,
    status: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_permission("instance:view")),
    db: Session = Depends(get_db)
):
    """获取 Redis 实例列表"""
    service = RedisInstanceService(db)
    instances, total = service.get_multi_with_environment(
        skip=skip,
        limit=limit,
        environment_id=environment_id,
        group_id=group_id,
        redis_mode=redis_mode,
        status=status
    )
    
    # 构建返回数据，包含 environment 信息
    items = []
    for i in instances:
        # 使用预加载的 environment 关系，避免 N+1 查询
        env_data = None
        if i.environment:
            env_data = {"id": i.environment.id, "name": i.environment.name, "color": i.environment.color}
        
        items.append({
            "id": i.id,
            "name": i.name,
            "host": i.host,
            "port": i.port,
            "redis_mode": i.redis_mode.value if hasattr(i.redis_mode, 'value') else str(i.redis_mode),
            "redis_db": i.redis_db,
            "cluster_nodes": i.cluster_nodes,
            "sentinel_master_name": i.sentinel_master_name,
            "sentinel_hosts": i.sentinel_hosts,
            "environment_id": i.environment_id,
            "environment": env_data,
            "group_id": i.group_id,
            "description": i.description,
            "status": i.status,
            "slowlog_threshold": i.slowlog_threshold,
            "enable_monitoring": i.enable_monitoring,
            "last_check_time": i.last_check_time,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        })
    
    return {
        "total": total,
        "items": items
    }


@router.get("/{instance_id}")
async def get_redis_instance(
    instance_id: int,
    current_user: User = Depends(require_permission("instance:view")),
    db: Session = Depends(get_db)
):
    """获取 Redis 实例详情"""
    service = RedisInstanceService(db)
    instance = service.get_with_environment(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用预加载的 environment 关系
    env_data = None
    if instance.environment:
        env_data = {"id": instance.environment.id, "name": instance.environment.name, "color": instance.environment.color}
    
    return {
        "id": instance.id,
        "name": instance.name,
        "host": instance.host,
        "port": instance.port,
        "redis_mode": instance.redis_mode.value if hasattr(instance.redis_mode, 'value') else str(instance.redis_mode),
        "redis_db": instance.redis_db,
        "cluster_nodes": instance.cluster_nodes,
        "sentinel_master_name": instance.sentinel_master_name,
        "sentinel_hosts": instance.sentinel_hosts,
        "environment_id": instance.environment_id,
        "environment": env_data,
        "group_id": instance.group_id,
        "description": instance.description,
        "status": instance.status,
        "slowlog_threshold": instance.slowlog_threshold,
        "enable_monitoring": instance.enable_monitoring,
        "last_check_time": instance.last_check_time,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
    }


@router.post("/test", response_model=InstanceTestResult)
async def test_redis_instance_connection(
    instance_data: RedisInstanceCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """测试 Redis 实例连接"""
    result = await test_redis_connection(
        instance_data.host,
        instance_data.port or 6379,
        instance_data.password or "",
        instance_data.redis_db or 0
    )
    return InstanceTestResult(**result)


@router.post("", response_model=RedisInstanceResponse)
async def create_redis_instance(
    instance_data: RedisInstanceCreate,
    current_user: User = Depends(require_permission("instance:create")),
    db: Session = Depends(get_db)
):
    """创建 Redis 实例"""
    service = RedisInstanceService(db)
    
    # 检查 Redis 类型是否启用
    if not check_db_type_enabled(db, "redis"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redis 实例类型已被禁用，无法创建新实例"
        )
    
    # 检查名称是否已存在
    if service.get_by_name(instance_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="实例名称已存在"
        )
    
    # 必须有连接信息
    if not instance_data.host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="主机地址不能为空"
        )
    
    # 测试连接
    conn_result = await test_redis_connection(
        instance_data.host,
        instance_data.port or 6379,
        instance_data.password or "",
        instance_data.redis_db or 0
    )
    
    if not conn_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"连接测试失败: {conn_result['message']}"
        )
    
    # 创建实例
    instance = service.create({
        "name": instance_data.name,
        "host": instance_data.host,
        "port": instance_data.port or 6379,
        "password_encrypted": encrypt_instance_password(instance_data.password) if instance_data.password else None,
        "redis_mode": instance_data.redis_mode or "standalone",
        "redis_db": instance_data.redis_db or 0,
        "cluster_nodes": instance_data.cluster_nodes,
        "sentinel_master_name": instance_data.sentinel_master_name,
        "sentinel_hosts": instance_data.sentinel_hosts,
        "environment_id": instance_data.environment_id,
        "group_id": instance_data.group_id,
        "description": instance_data.description,
        "status": instance_data.status if instance_data.status is not None else True,
        "slowlog_threshold": instance_data.slowlog_threshold,
        "enable_monitoring": instance_data.enable_monitoring
    })
    
    logger.info(f"创建 Redis 实例: {instance.name} (ID: {instance.id})")
    return RedisInstanceResponse.model_validate(instance)


@router.put("/{instance_id}", response_model=RedisInstanceResponse)
async def update_redis_instance(
    instance_id: int,
    instance_data: RedisInstanceUpdate,
    current_user: User = Depends(require_permission("instance:update")),
    db: Session = Depends(get_db)
):
    """更新 Redis 实例"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 更新字段
    update_data = instance_data.model_dump(exclude_unset=True)
    
    # 如果更新了密码，需要加密
    if 'password' in update_data:
        update_data['password_encrypted'] = encrypt_instance_password(update_data.pop('password'))
    
    instance = service.update(instance_id, update_data)
    
    logger.info(f"更新 Redis 实例: {instance.name} (ID: {instance.id})")
    return RedisInstanceResponse.model_validate(instance)


@router.delete("/{instance_id}", response_model=MessageResponse)
async def delete_redis_instance(
    instance_id: int,
    current_user: User = Depends(require_permission("instance:delete")),
    db: Session = Depends(get_db)
):
    """删除 Redis 实例"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    instance_name = instance.name
    service.delete(instance_id)
    
    logger.info(f"删除 Redis 实例: {instance_name} (ID: {instance_id})")
    return MessageResponse(message="实例删除成功")


@router.post("/{instance_id}/check", response_model=InstanceTestResult)
async def check_redis_instance_status(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查 Redis 实例状态"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 尝试解密密码
    password = None
    if instance.password_encrypted:
        try:
            password = service.get_decrypted_password(instance)
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
    service.update(instance_id, {
        "status": result["success"],
        "last_check_time": datetime.now()
    })
    
    return InstanceTestResult(**result)


# ============ Redis 慢日志 API ============

@router.get("/{instance_id}/slowlog", response_model=list[RedisSlowLogResponse])
async def get_redis_slowlog(
    instance_id: int,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Redis 慢日志"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        client = await get_redis_client(instance)
        slowlog = await client.slowlog_get(limit)
        await client.close()
        
        result = []
        for entry in slowlog:
            # 解析慢日志条目
            if isinstance(entry, dict):
                slowlog_id = entry.get('id')
                timestamp = datetime.fromtimestamp(entry.get('start_time', 0))
                duration = entry.get('duration', 0)
                command_list = entry.get('command', [])
                client_addr = entry.get('client_address', '')
                client_name = entry.get('client_name', '')
            else:
                # 旧版 redis-py 返回的是元组
                slowlog_id = entry[0]
                timestamp = datetime.fromtimestamp(entry[1])
                duration = entry[2]
                command_list = entry[3] if len(entry) > 3 else []
                client_addr = entry[4] if len(entry) > 4 else ''
                client_name = entry[5] if len(entry) > 5 else ''
            
            # 解析命令
            command = command_list[0] if command_list else ''
            key = command_list[1] if len(command_list) > 1 else ''
            args = ' '.join(str(c) for c in command_list[2:]) if len(command_list) > 2 else ''
            
            result.append(RedisSlowLogResponse(
                id=0,  # 临时ID
                instance_id=instance_id,
                slowlog_id=slowlog_id,
                timestamp=timestamp,
                duration=duration,
                command=command,
                key=key,
                args=args,
                client_addr=client_addr,
                client_name=client_name,
                created_at=datetime.now()
            ))
        
        return result
    except Exception as e:
        logger.error(f"获取 Redis 慢日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取慢日志失败: {str(e)}"
        )


# ============ Redis 信息 API ============

@router.get("/{instance_id}/info")
async def get_redis_info(
    instance_id: int,
    section: str = Query("default", description="信息部分: server/memory/stats/clients/default/all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Redis 信息"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        client = await get_redis_client(instance)
        info = await client.info(section)
        await client.close()
        
        # 转换为可序列化的格式
        result = {}
        for key, value in info.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            else:
                result[key] = str(value)
        
        return {
            "instance_id": instance_id,
            "instance_name": instance.name,
            "section": section,
            "info": result
        }
    except Exception as e:
        logger.error(f"获取 Redis 信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取信息失败: {str(e)}"
        )


# ============ Redis Key 分析 API ============

@router.get("/{instance_id}/keys")
async def get_redis_keys(
    instance_id: int,
    pattern: str = Query("*", description="Key 匹配模式"),
    count: int = Query(100, ge=1, le=1000, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Redis Key 列表"""
    service = RedisInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        client = await get_redis_client(instance)
        keys = []
        cursor = 0
        
        while len(keys) < count:
            cursor, batch = await client.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        
        keys = keys[:count]
        
        # 获取 Key 类型和 TTL
        result = []
        for key in keys:
            key_type = await client.type(key)
            ttl = await client.ttl(key)
            result.append({
                "key": key,
                "type": key_type,
                "ttl": ttl
            })
        
        await client.close()
        
        return {
            "instance_id": instance_id,
            "pattern": pattern,
            "count": len(result),
            "keys": result
        }
    except Exception as e:
        logger.error(f"获取 Redis Keys 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 Keys 失败: {str(e)}"
        )
