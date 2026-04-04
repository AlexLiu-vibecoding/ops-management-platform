"""
缓存服务测试
"""
import pytest
import time
import json
from unittest.mock import Mock, patch
from app.services.cache_service import MemoryCache, CacheService


class TestMemoryCache:
    """内存缓存测试"""

    def test_init(self):
        """测试初始化"""
        cache = MemoryCache(default_ttl=600)
        assert cache._default_ttl == 600
        assert cache._cache == {}

    def test_get_existing_key(self):
        """测试获取存在的键"""
        cache = MemoryCache()
        cache._cache["test_key"] = ("test_value", time.time() + 300)

        result = cache.get("test_key")
        assert result == "test_value"

    def test_get_non_existing_key(self):
        """测试获取不存在的键"""
        cache = MemoryCache()
        result = cache.get("non_existing")
        assert result is None

    def test_get_expired_key(self):
        """测试获取已过期的键"""
        cache = MemoryCache()
        cache._cache["expired_key"] = ("value", time.time() - 1)

        result = cache.get("expired_key")
        assert result is None
        assert "expired_key" not in cache._cache

    def test_set(self):
        """测试设置缓存"""
        cache = MemoryCache()
        result = cache.set("key1", "value1", ttl=300)

        assert result is True
        assert "key1" in cache._cache
        assert cache._cache["key1"][0] == "value1"

    def test_set_default_ttl(self):
        """测试使用默认TTL设置缓存"""
        cache = MemoryCache(default_ttl=600)
        cache.set("key1", "value1")

        _, expire_at = cache._cache["key1"]
        expected_expire = time.time() + 600
        assert abs(expire_at - expected_expire) < 5

    def test_delete_existing_key(self):
        """测试删除存在的键"""
        cache = MemoryCache()
        cache._cache["key1"] = ("value", time.time() + 300)

        result = cache.delete("key1")
        assert result is True
        assert "key1" not in cache._cache

    def test_delete_non_existing_key(self):
        """测试删除不存在的键"""
        cache = MemoryCache()
        result = cache.delete("non_existing")
        assert result is True

    def test_clear(self):
        """测试清空缓存"""
        cache = MemoryCache()
        cache._cache["key1"] = ("value1", time.time() + 300)
        cache._cache["key2"] = ("value2", time.time() + 300)

        count = cache.clear()
        assert count == 2
        assert cache._cache == {}

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        cache = MemoryCache()
        cache._cache["valid"] = ("value1", time.time() + 300)
        cache._cache["expired1"] = ("value2", time.time() - 1)
        cache._cache["expired2"] = ("value3", time.time() - 10)

        count = cache.cleanup_expired()
        assert count == 2
        assert "valid" in cache._cache
        assert "expired1" not in cache._cache
        assert "expired2" not in cache._cache

    def test_thread_safety(self):
        """测试线程安全"""
        import threading
        cache = MemoryCache()
        results = []

        def worker():
            cache.set(f"key_{threading.current_thread().name}", "value")
            results.append(cache.get(f"key_{threading.current_thread().name}"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(r == "value" for r in results)


class TestCacheService:
    """缓存服务测试"""

    def test_init_without_redis(self):
        """测试不使用Redis初始化"""
        service = CacheService(redis_client=None, default_ttl=300)
        assert service._use_redis is False
        assert service._default_ttl == 300
        assert service._redis is None

    def test_init_with_redis(self):
        """测试使用Redis初始化"""
        mock_redis = Mock()
        service = CacheService(redis_client=mock_redis, default_ttl=600)
        assert service._use_redis is True
        assert service._default_ttl == 600
        assert service._redis == mock_redis

    def test_make_key(self):
        """测试生成缓存键"""
        service = CacheService()
        key = service._make_key("user:123")
        assert key == "ops:user:123"

    def test_get_from_memory_cache(self):
        """测试从内存缓存获取"""
        service = CacheService()
        service._memory_cache.set("ops:key1", "value1", 300)

        result = service.get("key1")
        assert result == "value1"

    def test_get_from_redis(self):
        """测试从Redis获取"""
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps({"data": "test"})
        service = CacheService(redis_client=mock_redis)

        result = service.get("key1")
        assert result == {"data": "test"}
        mock_redis.get.assert_called_once_with("ops:key1")

    def test_get_redis_fallback_to_memory(self):
        """测试Redis失败降级到内存缓存"""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")
        service = CacheService(redis_client=mock_redis)
        service._memory_cache.set("ops:key1", "memory_value", 300)

        result = service.get("key1")
        assert result == "memory_value"

    def test_set_to_memory_cache(self):
        """测试设置到内存缓存"""
        service = CacheService()
        result = service.set("key1", {"data": "test"}, ttl=300)

        assert result is True
        assert service._memory_cache.get("ops:key1") == {"data": "test"}

    def test_set_to_redis(self):
        """测试设置到Redis"""
        mock_redis = Mock()
        service = CacheService(redis_client=mock_redis)

        result = service.set("key1", {"data": "test"}, ttl=300)

        assert result is True
        mock_redis.setex.assert_called_once()

    def test_set_redis_fallback_to_memory(self):
        """测试Redis失败降级到内存缓存"""
        mock_redis = Mock()
        mock_redis.setex.side_effect = Exception("Redis error")
        service = CacheService(redis_client=mock_redis)

        result = service.set("key1", "value1", ttl=300)

        assert result is True
        assert service._memory_cache.get("ops:key1") == "value1"

    def test_delete(self):
        """测试删除缓存"""
        mock_redis = Mock()
        service = CacheService(redis_client=mock_redis)
        service._memory_cache.set("ops:key1", "value", 300)

        result = service.delete("key1")

        assert result is True
        mock_redis.delete.assert_called_once_with("ops:key1")
        assert service._memory_cache.get("ops:key1") is None

    def test_get_or_set_cache_hit(self):
        """测试get_or_set缓存命中"""
        service = CacheService()
        service._memory_cache.set("ops:key1", "cached_value", 300)

        getter = Mock(return_value="new_value")
        result = service.get_or_set("key1", getter)

        assert result == "cached_value"
        getter.assert_not_called()

    def test_get_or_set_cache_miss(self):
        """测试get_or_set缓存未命中"""
        service = CacheService()

        getter = Mock(return_value="new_value")
        result = service.get_or_set("key1", getter)

        assert result == "new_value"
        getter.assert_called_once()
        assert service._memory_cache.get("ops:key1") == "new_value"

    @pytest.mark.asyncio
    async def test_aget_or_set_cache_hit(self):
        """测试异步aget_or_set缓存命中"""
        service = CacheService()
        service._memory_cache.set("ops:key1", "cached_value", 300)

        getter = Mock(return_value="new_value")
        result = await service.aget_or_set("key1", getter)

        assert result == "cached_value"
        getter.assert_not_called()

    @pytest.mark.asyncio
    async def test_aget_or_set_async_getter(self):
        """测试异步getter"""
        service = CacheService()

        async def async_getter():
            return "async_value"

        result = await service.aget_or_set("key1", async_getter)

        assert result == "async_value"
        assert service._memory_cache.get("ops:key1") == "async_value"

    @pytest.mark.asyncio
    async def test_aget_or_set_sync_getter(self):
        """测试同步getter"""
        service = CacheService()

        def sync_getter():
            return "sync_value"

        result = await service.aget_or_set("key1", sync_getter)

        assert result == "sync_value"
        assert service._memory_cache.get("ops:key1") == "sync_value"

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        service = CacheService()

        @service.cached("user", ttl=300)
        def get_user(user_id: int):
            return {"id": user_id, "name": f"User {user_id}"}

        # 第一次调用
        result1 = get_user(123)
        assert result1["id"] == 123

        # 第二次调用（应该命中缓存）
        result2 = get_user(123)
        assert result2 == result1

    def test_cached_decorator_with_key_builder(self):
        """测试带自定义键生成器的缓存装饰器"""
        service = CacheService()

        def custom_key_builder(user_id: int, **kwargs):
            return f"custom_user_{user_id}"

        @service.cached("user", ttl=300, key_builder=custom_key_builder)
        def get_user(user_id: int):
            return {"id": user_id}

        result = get_user(123)
        assert result["id"] == 123
        assert service._memory_cache.get("ops:custom_user_123") == {"id": 123}

    def test_invalidate_pattern_memory_only(self):
        """测试仅内存缓存的失效模式"""
        service = CacheService()
        service._memory_cache.set("ops:user:1", "value1", 300)
        service._memory_cache.set("ops:user:2", "value2", 300)
        service._memory_cache.set("ops:order:1", "value3", 300)

        count = service.invalidate_pattern("user:*")

        assert count == 2
        assert service._memory_cache.get("ops:user:1") is None
        assert service._memory_cache.get("ops:user:2") is None
        assert service._memory_cache.get("ops:order:1") == "value3"

    def test_invalidate_pattern_with_redis(self):
        """测试带Redis的失效模式"""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["ops:user:1", "ops:user:2"]
        mock_redis.delete.return_value = 2
        service = CacheService(redis_client=mock_redis)

        count = service.invalidate_pattern("user:*")

        assert count == 2
        mock_redis.keys.assert_called_once_with("ops:user:*")
        mock_redis.delete.assert_called_once_with("ops:user:1", "ops:user:2")

    def test_clear(self):
        """测试清空缓存"""
        service = CacheService()
        service._memory_cache.set("ops:key1", "value1", 300)
        service._memory_cache.set("ops:key2", "value2", 300)

        count = service.clear()

        assert count == 2
        assert service._memory_cache.get("ops:key1") is None

    def test_clear_with_redis(self):
        """测试带Redis的清空缓存"""
        mock_redis = Mock()
        service = CacheService(redis_client=mock_redis)
        service._memory_cache.set("ops:key1", "value1", 300)

        count = service.clear()

        assert count == 1
        mock_redis.keys.assert_called_once_with("ops:*")
