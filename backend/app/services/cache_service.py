"""
缓存服务

提供统一的缓存能力：
- Redis 缓存后端
- 内存缓存降级
- 装饰器支持
- 自动过期
"""
import json
import logging
import threading
import time
from typing import Optional, Any, Callable, TypeVar, Union
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MemoryCache:
    """
    内存缓存（降级方案）
    
    当 Redis 不可用时使用内存缓存
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化内存缓存
        
        Args:
            default_ttl: 默认过期时间（秒）
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expire_at = self._cache[key]
            if time.time() > expire_at:
                del self._cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        ttl = ttl or self._default_ttl
        expire_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = (value, expire_at)
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            return True
    
    def clear(self) -> int:
        """清空所有缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        now = time.time()
        count = 0
        
        with self._lock:
            expired_keys = [
                k for k, (_, expire_at) in self._cache.items()
                if now > expire_at
            ]
            for key in expired_keys:
                del self._cache[key]
                count += 1
        
        return count


class CacheService:
    """
    统一缓存服务
    
    支持 Redis 缓存，内存缓存降级
    """
    
    # 缓存键前缀
    KEY_PREFIX = "ops:"
    
    def __init__(self, redis_client=None, default_ttl: int = 300):
        """
        初始化缓存服务
        
        Args:
            redis_client: Redis 客户端（可选）
            default_ttl: 默认过期时间（秒）
        """
        self._redis = redis_client
        self._memory_cache = MemoryCache(default_ttl)
        self._default_ttl = default_ttl
        self._use_redis = redis_client is not None
    
    def _make_key(self, key: str) -> str:
        """生成完整缓存键"""
        return f"{self.KEY_PREFIX}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，不存在返回 None
        """
        full_key = self._make_key(key)
        
        # 尝试 Redis
        if self._use_redis:
            try:
                value = self._redis.get(full_key)
                if value is not None:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis 获取失败，降级到内存缓存: {e}")
        
        # 降级到内存缓存
        return self._memory_cache.get(full_key)
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        
        Returns:
            是否成功
        """
        full_key = self._make_key(key)
        ttl = ttl or self._default_ttl
        
        # 尝试 Redis
        if self._use_redis:
            try:
                self._redis.setex(
                    full_key,
                    ttl,
                    json.dumps(value, ensure_ascii=False)
                )
                return True
            except Exception as e:
                logger.warning(f"Redis 设置失败，降级到内存缓存: {e}")
        
        # 降级到内存缓存
        return self._memory_cache.set(full_key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            是否成功
        """
        full_key = self._make_key(key)
        
        if self._use_redis:
            try:
                self._redis.delete(full_key)
            except Exception as e:
                logger.warning(f"Redis 删除失败: {e}")
        
        return self._memory_cache.delete(full_key)
    
    def get_or_set(
        self,
        key: str,
        getter: Callable[[], T],
        ttl: Optional[int] = None
    ) -> T:
        """
        获取缓存，不存在则执行 getter 并缓存结果
        
        Args:
            key: 缓存键
            getter: 获取数据的函数
            ttl: 过期时间
        
        Returns:
            缓存值或 getter 结果
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = getter()
        self.set(key, value, ttl)
        return value
    
    async def aget_or_set(
        self,
        key: str,
        getter: Callable[[], T],
        ttl: Optional[int] = None
    ) -> T:
        """
        异步获取缓存，不存在则执行 getter 并缓存结果
        """
        value = self.get(key)
        if value is not None:
            return value
        
        # 支持异步 getter
        import asyncio
        if asyncio.iscoroutinefunction(getter):
            value = await getter()
        else:
            value = getter()
        
        self.set(key, value, ttl)
        return value
    
    def cached(
        self,
        key_prefix: str,
        ttl: Optional[int] = None,
        key_builder: Optional[Callable[..., str]] = None
    ):
        """
        缓存装饰器
        
        使用示例:
            @cache_service.cached("user", ttl=60)
            def get_user(user_id: int):
                return db.query(User).get(user_id)
        
        Args:
            key_prefix: 缓存键前缀
            ttl: 过期时间
            key_builder: 自定义键生成函数
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # 默认使用参数生成键
                    params = "_".join(str(a) for a in args)
                    kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = f"{key_prefix}:{params}:{kwargs_str}"
                
                return self.get_or_set(cache_key, lambda: func(*args, **kwargs), ttl)
            
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        使匹配模式的所有缓存失效
        
        Args:
            pattern: 键模式（支持通配符 *）
        
        Returns:
            删除的键数量
        """
        count = 0
        
        if self._use_redis:
            try:
                keys = self._redis.keys(f"{self.KEY_PREFIX}{pattern}")
                if keys:
                    count = self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis 批量删除失败: {e}")
        
        return count


# 全局缓存服务实例（延迟初始化）
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """获取缓存服务实例"""
    global _cache_service
    
    if _cache_service is None:
        # 尝试使用 Redis
        try:
            from app.utils.redis_client import redis_client
            if redis_client.is_connected:
                _cache_service = CacheService(redis_client.client)
                logger.info("缓存服务使用 Redis 后端")
            else:
                _cache_service = CacheService()
                logger.info("缓存服务使用内存后端（Redis 未连接）")
        except Exception as e:
            _cache_service = CacheService()
            logger.warning(f"缓存服务初始化失败，使用内存后端: {e}")
    
    return _cache_service


# 便捷函数
def cache_get(key: str) -> Optional[Any]:
    """获取缓存"""
    return get_cache_service().get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存"""
    return get_cache_service().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """删除缓存"""
    return get_cache_service().delete(key)


def cached(key_prefix: str, ttl: Optional[int] = None):
    """缓存装饰器"""
    return get_cache_service().cached(key_prefix, ttl)


__all__ = [
    'CacheService',
    'MemoryCache',
    'get_cache_service',
    'cache_get',
    'cache_set',
    'cache_delete',
    'cached'
]
