"""
Redis客户端工具
"""
import redis.asyncio as aioredis
from typing import Optional, Any
import json
from app.config import settings


class RedisClient:
    """Redis客户端封装"""
    
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """建立Redis连接"""
        if self.client is None:
            self.client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """关闭Redis连接"""
        if self.client:
            await self.client.close()
            self.client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """获取值"""
        if not self.client:
            await self.connect()
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        """设置值"""
        if not self.client:
            await self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value)
        if expire:
            await self.client.expire(key, expire)
    
    async def delete(self, key: str):
        """删除键"""
        if not self.client:
            await self.connect()
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            await self.connect()
        return await self.client.exists(key) > 0
    
    async def setex(self, key: str, ttl: int, value: Any):
        """设置带过期时间的值"""
        if not self.client:
            await self.connect()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.setex(key, ttl, value)
    
    async def incr(self, key: str) -> int:
        """自增"""
        if not self.client:
            await self.connect()
        return await self.client.incr(key)
    
    async def expire(self, key: str, ttl: int):
        """设置过期时间"""
        if not self.client:
            await self.connect()
        await self.client.expire(key, ttl)
    
    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.client:
            await self.connect()
        return await self.client.ttl(key)


# 全局Redis客户端实例
redis_client = RedisClient()
