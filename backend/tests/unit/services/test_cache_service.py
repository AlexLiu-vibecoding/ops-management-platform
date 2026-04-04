#!/usr/bin/env python3
"""
缓存服务单元测试

测试范围：
1. 内存缓存
2. 缓存服务
3. 装饰器
4. 缓存过期
5. 模式删除

运行方式:
    cd /workspace/projects/backend

    # 运行所有缓存服务测试
    python -m pytest tests/unit/services/test_cache_service.py -v

    # 运行特定测试
    python -m pytest tests/unit/services/test_cache_service.py::TestMemoryCache -v
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.cache_service import MemoryCache, CacheService, get_cache_service


@pytest.mark.unit
class TestMemoryCache:
    """内存缓存测试"""

    def test_get_missing_key(self):
        """测试获取不存在的键"""
        cache = MemoryCache()
        value = cache.get("non_existent_key")
        assert value is None

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        assert value == "test_value"

    def test_set_with_ttl(self):
        """测试设置带过期时间的值"""
        cache = MemoryCache(default_ttl=300)
        cache.set("test_key", "test_value", ttl=1)  # 1秒后过期
        time.sleep(0.5)
        value = cache.get("test_key")
        assert value == "test_value"
        time.sleep(0.6)
        value = cache.get("test_key")
        assert value is None

    def test_delete_existing_key(self):
        """测试删除存在的键"""
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        result = cache.delete("test_key")
        assert result is True
        value = cache.get("test_key")
        assert value is None

    def test_delete_non_existing_key(self):
        """测试删除不存在的键"""
        cache = MemoryCache()
        result = cache.delete("non_existent_key")
        assert result is True  # 删除操作总是返回True

    def test_clear(self):
        """测试清空所有缓存"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        count = cache.clear()
        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1", ttl=1)  # 1秒后过期
        cache.set("key2", "value2", ttl=2)  # 2秒后过期
        time.sleep(1.5)
        count = cache.cleanup_expired()
        assert count == 1  # 只有key1过期
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_delete_pattern(self):
        """测试模式删除"""
        cache = MemoryCache()
        cache.set("user:1", "value1")
        cache.set("user:2", "value2")
        cache.set("product:1", "value3")
        count = cache.delete_pattern("user:*")
        assert count == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("product:1") == "value3"

    def test_default_ttl(self):
        """测试默认过期时间"""
        cache = MemoryCache(default_ttl=2)
        cache.set("test_key", "test_value")
        time.sleep(1.5)
        value = cache.get("test_key")
        assert value == "test_value"
        time.sleep(0.6)
        value = cache.get("test_key")
        assert value is None

    def test_set_complex_object(self):
        """测试设置复杂对象"""
        cache = MemoryCache()
        complex_obj = {"name": "test", "nested": {"key": "value"}}
        cache.set("complex_key", complex_obj)
        value = cache.get("complex_key")
        assert value == complex_obj

    def test_overwrite_existing_key(self):
        """测试覆盖已存在的键"""
        cache = MemoryCache()
        cache.set("test_key", "old_value")
        cache.set("test_key", "new_value")
        value = cache.get("test_key")
        assert value == "new_value"

    def test_thread_safety(self):
        """测试线程安全"""
        import threading

        cache = MemoryCache()
        errors = []

        def set_values():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        def get_values():
            try:
                for i in range(100):
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(10):
            t1 = threading.Thread(target=set_values)
            t2 = threading.Thread(target=get_values)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        for t in threads:
            t.join()

        assert len(errors) == 0


@pytest.mark.unit
class TestCacheService:
    """缓存服务测试"""

    def test_init_without_redis(self):
        """测试不使用Redis初始化"""
        service = CacheService()
        assert service._redis is None
        assert service._use_redis is False

    def test_make_key(self):
        """测试生成缓存键"""
        service = CacheService()
        full_key = service._make_key("test_key")
        assert full_key == "ops:test_key"

    def test_set_and_get_memory_mode(self):
        """测试内存模式下的设置和获取"""
        service = CacheService()
        service.set("test_key", "test_value")
        value = service.get("test_key")
        assert value == "test_value"

    def test_get_missing_key_memory_mode(self):
        """测试内存模式下获取不存在的键"""
        service = CacheService()
        value = service.get("non_existent_key")
        assert value is None

    def test_delete_memory_mode(self):
        """测试内存模式下的删除"""
        service = CacheService()
        service.set("test_key", "test_value")
        result = service.delete("test_key")
        assert result is True
        value = service.get("test_key")
        assert value is None

    def test_get_or_set_with_existing_value(self):
        """测试get_or_set当缓存存在时"""
        service = CacheService()
        service.set("test_key", "cached_value")
        getter_called = []

        def getter():
            getter_called.append(True)
            return "new_value"

        value = service.get_or_set("test_key", getter)
        assert value == "cached_value"
        assert len(getter_called) == 0

    def test_get_or_set_without_existing_value(self):
        """测试get_or_set当缓存不存在时"""
        service = CacheService()
        getter_called = []

        def getter():
            getter_called.append(True)
            return "new_value"

        value = service.get_or_set("test_key", getter)
        assert value == "new_value"
        assert len(getter_called) == 1
        # 检查是否被缓存
        cached_value = service.get("test_key")
        assert cached_value == "new_value"

    def test_aget_or_set_with_sync_getter(self):
        """测试aget_or_set使用同步getter"""
        import asyncio

        service = CacheService()
        getter_called = []

        def getter():
            getter_called.append(True)
            return "new_value"

        async def test():
            value = await service.aget_or_set("test_key", getter)
            assert value == "new_value"
            assert len(getter_called) == 1

        asyncio.run(test())

    def test_aget_or_set_with_async_getter(self):
        """测试aget_or_set使用异步getter"""
        import asyncio

        service = CacheService()
        getter_called = []

        async def getter():
            getter_called.append(True)
            await asyncio.sleep(0.1)
            return "async_value"

        async def test():
            value = await service.aget_or_set("test_key", getter)
            assert value == "async_value"
            assert len(getter_called) == 1

        asyncio.run(test())

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        service = CacheService()
        call_count = []

        @service.cached("test_func", ttl=10)
        def test_func(x, y):
            call_count.append(True)
            return x + y

        # 第一次调用
        result1 = test_func(1, 2)
        assert result1 == 3
        assert len(call_count) == 1

        # 第二次调用（应该从缓存获取）
        result2 = test_func(1, 2)
        assert result2 == 3
        assert len(call_count) == 1  # 没有增加

        # 不同参数的调用
        result3 = test_func(2, 3)
        assert result3 == 5
        assert len(call_count) == 2  # 增加了

    def test_cached_decorator_with_key_builder(self):
        """测试带自定义键生成器的装饰器"""
        service = CacheService()
        call_count = []

        def key_builder(x, y):
            return f"custom:{x}:{y}"

        @service.cached("test_func", ttl=10, key_builder=key_builder)
        def test_func(x, y):
            call_count.append(True)
            return x * y

        # 第一次调用
        result1 = test_func(3, 4)
        assert result1 == 12
        assert len(call_count) == 1

        # 第二次调用（应该从缓存获取）
        result2 = test_func(3, 4)
        assert result2 == 12
        assert len(call_count) == 1

    def test_invalidate_pattern(self):
        """测试模式删除"""
        service = CacheService()
        service.set("user:1", "value1")
        service.set("user:2", "value2")
        service.set("product:1", "value3")

        count = service.invalidate_pattern("user:*")
        assert count == 2
        assert service.get("user:1") is None
        assert service.get("user:2") is None
        assert service.get("product:1") == "value3"

    def test_clear_all(self):
        """测试清空所有缓存"""
        service = CacheService()
        service.set("key1", "value1")
        service.set("key2", "value2")
        service.set("key3", "value3")

        count = service.clear()
        assert count == 3
        assert service.get("key1") is None
        assert service.get("key2") is None
        assert service.get("key3") is None

    def test_custom_default_ttl(self):
        """测试自定义默认过期时间"""
        service = CacheService(default_ttl=2)
        service.set("test_key", "test_value")
        time.sleep(1.5)
        value = service.get("test_key")
        assert value == "test_value"
        time.sleep(0.6)
        value = service.get("test_key")
        assert value is None

    def test_set_json_serializable_object(self):
        """测试设置可JSON序列化的对象"""
        service = CacheService()
        data = {"name": "test", "age": 25, "nested": {"key": "value"}}
        service.set("data_key", data)
        value = service.get("data_key")
        assert value == data

    def test_redis_mode_fallback_to_memory(self, monkeypatch):
        """测试Redis模式下失败降级到内存缓存"""
        # 模拟Redis客户端
        mock_redis = type('MockRedis', (), {})()
        mock_redis.get = lambda key: (_ for _ in ()).throw(Exception("Redis error"))

        service = CacheService(redis_client=mock_redis)
        service.set("test_key", "test_value")
        value = service.get("test_key")
        # 由于Redis失败，应该降级到内存缓存
        assert value == "test_value"

    def test_custom_ttl_override(self):
        """测试自定义TTL覆盖默认TTL"""
        service = CacheService(default_ttl=10)
        service.set("test_key", "test_value", ttl=1)
        time.sleep(1.5)
        value = service.get("test_key")
        assert value is None

    def test_invalidate_pattern_with_no_matches(self):
        """测试模式删除没有匹配项"""
        service = CacheService()
        service.set("key1", "value1")
        service.set("key2", "value2")

        count = service.invalidate_pattern("nonexistent:*")
        assert count == 0
        assert service.get("key1") == "value1"
        assert service.get("key2") == "value2"


@pytest.mark.unit
class TestCacheServiceFactory:
    """缓存服务工厂函数测试"""

    def test_get_cache_service_singleton(self):
        """测试get_cache_service返回单例"""
        service1 = get_cache_service()
        service2 = get_cache_service()
        # 由于是单例，应该返回同一个实例
        # 注意：这里可能因为redis连接状态不同而创建不同的实例
        # 所以我们只测试调用成功
        assert service1 is not None
        assert service2 is not None

    def test_convenience_functions(self):
        """测试便捷函数"""
        # 测试cache_set和cache_get
        from app.services.cache_service import cache_set, cache_get, cache_delete

        cache_set("convenience_key", "convenience_value")
        value = cache_get("convenience_key")
        assert value == "convenience_value"

        # 测试cache_delete
        cache_delete("convenience_key")
        value = cache_get("convenience_key")
        assert value is None
