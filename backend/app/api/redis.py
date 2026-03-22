"""
Redis 实例管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Instance
from app.schemas import MessageResponse
from app.utils.auth import decrypt_instance_password
from app.utils.redis_operations import RedisInstanceClient
from app.deps import get_current_user, get_operator
from app.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/redis", tags=["Redis管理"])


def get_redis_client(instance: Instance) -> RedisInstanceClient:
    """获取 Redis 客户端"""
    password = None
    if instance.password_encrypted:
        try:
            password = decrypt_instance_password(instance.password_encrypted)
        except Exception:
            pass
    
    return RedisInstanceClient(
        host=instance.host,
        port=instance.port or 6379,
        password=password,
        db=instance.redis_db or 0,
        redis_mode=instance.redis_mode or "standalone"
    )


class KeyValueSet(BaseModel):
    """设置键值请求"""
    key: str
    value: str
    ttl: Optional[int] = None


class KeyRename(BaseModel):
    """重命名键请求"""
    old_key: str
    new_key: str


class KeyTTL(BaseModel):
    """设置 TTL 请求"""
    key: str
    ttl: int


@router.get("/{instance_id}/info")
async def get_redis_info(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Redis 实例信息"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        server_info = client.get_server_info()
        memory_info = client.get_memory_info()
        stats_info = client.get_stats_info()
        clients_info = client.get_clients_info()
        keyspace_info = client.get_keyspace_info()
        db_size = client.get_db_size()
        
        return {
            "server": server_info,
            "memory": memory_info,
            "stats": stats_info,
            "clients": clients_info,
            "keyspace": keyspace_info,
            "db_size": db_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")
    finally:
        client.close()


@router.get("/{instance_id}/keys")
async def scan_keys(
    instance_id: int,
    pattern: str = Query("*", description="键模式"),
    cursor: int = Query(0, description="游标"),
    count: int = Query(100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """扫描键列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        new_cursor, keys = client.scan_keys(pattern=pattern, cursor=cursor, count=count)
        
        # 获取每个键的基本信息
        key_list = []
        for key in keys:
            key_info = client.get_key_info(key)
            key_list.append({
                "key": key,
                "type": key_info.get("type"),
                "ttl": key_info.get("ttl"),
                "ttl_human": key_info.get("ttl_human"),
                "length": key_info.get("length", 0)
            })
        
        return {
            "cursor": new_cursor,
            "keys": key_list,
            "has_more": new_cursor != 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"扫描失败: {str(e)}")
    finally:
        client.close()


@router.get("/{instance_id}/keys/{key:path}")
async def get_key_detail(
    instance_id: int,
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取键详情"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        key_info = client.get_key_info(key)
        if not key_info.get("exists"):
            raise HTTPException(status_code=404, detail="键不存在")
        
        value = client.get_key_value(key)
        
        return {
            "key": key,
            "info": key_info,
            "value": value
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取键失败: {str(e)}")
    finally:
        client.close()


@router.post("/{instance_id}/keys", response_model=MessageResponse)
async def set_key_value(
    instance_id: int,
    data: KeyValueSet,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """设置键值"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        success = client.set_key_value(data.key, data.value, data.ttl)
        if success:
            return MessageResponse(message="设置成功")
        raise HTTPException(status_code=500, detail="设置失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")
    finally:
        client.close()


@router.delete("/{instance_id}/keys/{key:path}", response_model=MessageResponse)
async def delete_key(
    instance_id: int,
    key: str,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """删除键"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        success = client.delete_key(key)
        if success:
            return MessageResponse(message="删除成功")
        raise HTTPException(status_code=404, detail="键不存在或删除失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
    finally:
        client.close()


@router.put("/{instance_id}/keys/rename", response_model=MessageResponse)
async def rename_key(
    instance_id: int,
    data: KeyRename,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """重命名键"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        success = client.rename_key(data.old_key, data.new_key)
        if success:
            return MessageResponse(message="重命名成功")
        raise HTTPException(status_code=500, detail="重命名失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")
    finally:
        client.close()


@router.put("/{instance_id}/keys/ttl", response_model=MessageResponse)
async def set_key_ttl(
    instance_id: int,
    data: KeyTTL,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """设置键过期时间"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        success = client.set_ttl(data.key, data.ttl)
        if success:
            return MessageResponse(message="设置成功")
        raise HTTPException(status_code=404, detail="键不存在或设置失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置失败: {str(e)}")
    finally:
        client.close()


@router.get("/{instance_id}/slowlog")
async def get_slowlog(
    instance_id: int,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询日志"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        slowlog = client.get_slowlog(limit)
        return slowlog
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取慢查询失败: {str(e)}")
    finally:
        client.close()


@router.get("/{instance_id}/clients")
async def get_clients(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取客户端列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        clients = client.get_client_list()
        return clients
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取客户端列表失败: {str(e)}")
    finally:
        client.close()


@router.get("/{instance_id}/config")
async def get_config(
    instance_id: int,
    pattern: str = Query("*", description="配置项模式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取配置"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        config = client.get_config(pattern)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")
    finally:
        client.close()


@router.post("/{instance_id}/test")
async def test_redis_connection(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试 Redis 连接"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    if instance.db_type != "redis":
        raise HTTPException(status_code=400, detail="该实例不是 Redis 类型")
    
    client = get_redis_client(instance)
    try:
        success, message, version = client.test_connection()
        return {
            "success": success,
            "message": message,
            "version": version
        }
    finally:
        client.close()
