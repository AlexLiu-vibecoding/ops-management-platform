#!/usr/bin/env python3
"""
缓存服务单元测试

测试范围：
1. MemoryCache 内存缓存
   - 基本CRUD操作（get、set、delete、clear）
   - TTL过期机制
   - 并发安全
   - 模式匹配删除
   - 过期缓存清理

2. CacheService 统一缓存服务
   - Redis缓存模式
   - 内存缓存降级
   - get_or_set 缓存获取或设置
   - 异步aget_or_set
   - cached装饰器
   - 模式匹配失效
   - 清空缓存

3. 全局函数
   - get_cache_service
   - cache_get、cache_set、cache_delete
   - cached装饰器

运行方式:
    cd /workspace/projects/backend

    # 运行所有缓存服务测试
    python -m pytest tests/unit/services/test_cache_service.py -v

    # 运行特定测试类
    python -m pytest tests/unit/services/test_cache_service.py::TestMemoryCache -v
    python -m pytest tests/unit/services/test_cache_service.py::TestCacheService -v
"""

import pytest
import sys
import os
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.cache_service import (
    MemoryCache,
    CacheService,
    get_cache_service,
    cache_get,
    cache_set,
    cache_delete,
    cached
)


@pytest.mark.unit
class TestMemoryCache:
    """内存缓存测试"""

    def test_init(self):
        """测试初始化"""
        cache = MemoryCache(default_ttl=300)
        assert cache._default_ttl == 300
        assert len(cache._cache) == 0

    def test_get_existing_key(self):
        """测试获取已存在的键"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1", ttl=10)
        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        cache = MemoryCache(default_ttl=300)
        result = cache.get("nonexistent")
        assert result is None

    def test_get_expired_key(self):
        """测试获取已过期的键"""
        cache = MemoryCache(default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)  # 等待过期
        result = cache.get("key1")
        assert result is None

    def test_set_with_ttl(self):
        """测试设置缓存并指定TTL"""
        cache = MemoryCache(default_ttl=300)
        result = cache.set("key1", "value1", ttl=10)
        assert result is True
        assert cache.get("key1") == "value1"

    def test_set_without_ttl(self):
        """测试设置缓存使用默认TTL"""
        cache = MemoryCache(default_ttl=300)
        result = cache.set("key1", "value1")
        assert result is True
        assert cache.get("key1") == "value1"

    def test_set_overwrite_existing(self):
        """测试覆盖已存在的键"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_set_complex_object(self):
        """测试设置复杂对象"""
        cache = MemoryCache(default_ttl=300)
        complex_obj = {"key": "value", "list": [1, 2, 3]}
        cache.set("key1", complex_obj)
        result = cache.get("key1")
        assert result == complex_obj

    def test_delete_existing_key(self):
        """测试删除已存在的键"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1")
        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self):
        """测试删除不存在的键"""
        cache = MemoryCache(default_ttl=300)
        result = cache.delete("nonexistent")
        assert result is True  # 删除不存在的键也返回True

    def test_clear(self):
        """测试清空所有缓存"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        result = cache.clear()
        assert result == 3
        assert len(cache._cache) == 0

    def test_clear_empty_cache(self):
        """测试清空空缓存"""
        cache = MemoryCache(default_ttl=300)
        result = cache.clear()
        assert result == 0

    def test_cleanup_expired(self):
        """测试清理过期缓存"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1", ttl=1)  # 即将过期
        cache.set("key2", "value2", ttl=10)  # 未过期
        time.sleep(1.1)  # 等待第一个过期
        result = cache.cleanup_expired()
        assert result == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cleanup_expired_none(self):
        """测试清理过期缓存（无过期项）"""
        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1", ttl=10)
        result = cache.cleanup_expired()
        assert result == 0

    def test_delete_pattern_exact_match(self):
        """测试模式匹配删除（精确匹配）"""
        cache = MemoryCache(default_ttl=300)
        cache.set("user:1", "Alice")
        cache.set("user:2", "Bob")
        cache.set("session:1", "xyz")
        result = cache.delete_pattern("user:*")
        assert result == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("session:1") == "xyz"

    def test_delete_pattern_no_match(self):
        """测试模式匹配删除（无匹配）"""
        cache = MemoryCache(default_ttl=300)
        cache.set("user:1", "Alice")
        result = cache.delete_pattern("admin:*")
        assert result == 0

    def test_delete_pattern_complex(self):
        """测试复杂模式匹配删除"""
        cache = MemoryCache(default_ttl=300)
        cache.set("cache:user:1:profile", "Alice")
        cache.set("cache:user:2:profile", "Bob")
        cache.set("cache:user:1:settings", "settings1")
        cache.set("cache:session:1", "session1")
        result = cache.delete_pattern("cache:user:*")
        assert result == 3
        assert cache.get("cache:session:1") == "session1"


@pytest.mark.unit
class TestCacheService:
    """统一缓存服务测试"""

    def test_init_with_redis(self):
        """测试使用Redis初始化"""
        redis_mock = Mock()
        service = CacheService(redis_client=redis_mock, default_ttl=300)
        assert service._redis == redis_mock
        assert service._use_redis is True
        assert service._default_ttl == 300

    def test_init_without_redis(self):
        """测试不使用Redis初始化"""
        service = CacheService(default_ttl=300)
        assert service._redis is None
        assert service._use_redis is False
        assert service._default_ttl == 300

    def test_make_key(self):
        """测试生成完整缓存键"""
        service = CacheService()
        assert service._make_key("user:1") == "ops:user:1"
        assert service._make_key("session") == "ops:session"

    def test_get_with_redis_success(self):
        """测试从Redis获取数据（成功）"""
        redis_mock = Mock()
        redis_mock.get.return_value = b'{"name": "Alice"}'
        service = CacheService(redis_client=redis_mock)

        result = service.get("user:1")
        assert result == {"name": "Alice"}
        redis_mock.get.assert_called_once_with("ops:user:1")

    def test_get_with_redis_none(self):
        """测试从Redis获取数据（不存在）"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        service = CacheService(redis_client=redis_mock)

        result = service.get("user:1")
        assert result is None

    def test_get_with_redis_error_fallback_to_memory(self):
        """测试从Redis获取数据（错误，降级到内存）"""
        redis_mock = Mock()
        redis_mock.get.side_effect = Exception("Redis error")
        service = CacheService(redis_client=redis_mock)
        # 预先设置内存缓存
        service._memory_cache.set("ops:user:1", {"name": "Alice"})

        result = service.get("user:1")
        assert result == {"name": "Alice"}

    def test_get_without_redis(self):
        """测试不使用Redis获取数据"""
        service = CacheService()
        service._memory_cache.set("ops:user:1", {"name": "Alice"})

        result = service.get("user:1")
        assert result == {"name": "Alice"}

    def test_set_with_redis_success(self):
        """测试设置Redis缓存（成功）"""
        redis_mock = Mock()
        redis_mock.setex.return_value = True
        service = CacheService(redis_client=redis_mock)

        result = service.set("user:1", {"name": "Alice"}, ttl=60)
        assert result is True
        redis_mock.setex.assert_called_once()

    def test_set_with_redis_error_fallback_to_memory(self):
        """测试设置Redis缓存（错误，降级到内存）"""
        redis_mock = Mock()
        redis_mock.setex.side_effect = Exception("Redis error")
        service = CacheService(redis_client=redis_mock)

        result = service.set("user:1", {"name": "Alice"}, ttl=60)
        assert result is True
        # 验证内存缓存中有数据
        assert service._memory_cache.get("ops:user:1") == {"name": "Alice"}

    def test_set_without_redis(self):
        """测试不使用Redis设置数据"""
        service = CacheService()
        result = service.set("user:1", {"name": "Alice"}, ttl=60)
        assert result is True
        assert service._memory_cache.get("ops:user:1") == {"name": "Alice"}

    def test_delete_with_redis(self):
        """测试从Redis删除数据"""
        redis_mock = Mock()
        service = CacheService(redis_client=redis_mock)
        service._memory_cache.set("ops:user:1", {"name": "Alice"})

        result = service.delete("user:1")
        assert result is True
        redis_mock.delete.assert_called_once_with("ops:user:1")
        # 内存缓存也应该被删除
        assert service._memory_cache.get("ops:user:1") is None

    def test_delete_with_redis_error(self):
        """测试从Redis删除数据（错误）"""
        redis_mock = Mock()
        redis_mock.delete.side_effect = Exception("Redis error")
        service = CacheService(redis_client=redis_mock)
        service._memory_cache.set("ops:user:1", {"name": "Alice"})

        result = service.delete("user:1")
        assert result is True
        # 内存缓存应该仍然被删除
        assert service._memory_cache.get("ops:user:1") is None

    def test_get_or_set_cache_hit(self):
        """测试get_or_set（缓存命中）"""
        service = CacheService()
        service.set("user:1", {"name": "Alice"}, ttl=60)

        getter_called = False
        def getter():
            nonlocal getter_called
            getter_called = True
            return {"name": "Bob"}

        result = service.get_or_set("user:1", getter, ttl=60)
        assert result == {"name": "Alice"}
        assert getter_called is False  # getter不应该被调用

    def test_get_or_set_cache_miss(self):
        """测试get_or_set（缓存未命中）"""
        service = CacheService()

        getter_called = False
        def getter():
            nonlocal getter_called
            getter_called = True
            return {"name": "Bob"}

        result = service.get_or_set("user:1", getter, ttl=60)
        assert result == {"name": "Bob"}
        assert getter_called is True  # getter应该被调用
        # 验证结果被缓存
        assert service.get("user:1") == {"name": "Bob"}

    @pytest.mark.asyncio
    async def test_aget_or_set_async_getter(self):
        """测试异步aget_or_set（异步getter）"""
        service = CacheService()

        getter_called = False
        async def async_getter():
            nonlocal getter_called
            getter_called = True
            await asyncio.sleep(0.01)
            return {"name": "Bob"}

        result = await service.aget_or_set("user:1", async_getter, ttl=60)
        assert result == {"name": "Bob"}
        assert getter_called is True

    @pytest.mark.asyncio
    async def test_aget_or_set_sync_getter(self):
        """测试异步aget_or_set（同步getter）"""
        service = CacheService()

        getter_called = False
        def sync_getter():
            nonlocal getter_called
            getter_called = True
            return {"name": "Bob"}

        result = await service.aget_or_set("user:1", sync_getter, ttl=60)
        assert result == {"name": "Bob"}
        assert getter_called is True

    @pytest.mark.asyncio
    async def test_aget_or_set_cache_hit(self):
        """测试异步aget_or_set（缓存命中）"""
        service = CacheService()
        service.set("user:1", {"name": "Alice"}, ttl=60)

        getter_called = False
        async def async_getter():
            nonlocal getter_called
            getter_called = True
            return {"name": "Bob"}

        result = await service.aget_or_set("user:1", async_getter, ttl=60)
        assert result == {"name": "Alice"}
        assert getter_called is False

    def test_cached_decorator(self):
        """测试缓存装饰器"""
        service = CacheService()
        call_count = 0

        @service.cached("user", ttl=60)
        def get_user(user_id: int):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": f"User{user_id}"}

        # 第一次调用，应该执行函数
        result1 = get_user(1)
        assert result1 == {"id": 1, "name": "User1"}
        assert call_count == 1

        # 第二次调用，应该从缓存获取
        result2 = get_user(1)
        assert result2 == {"id": 1, "name": "User1"}
        assert call_count == 1  # 不应该增加

        # 不同参数，应该执行函数
        result3 = get_user(2)
        assert result3 == {"id": 2, "name": "User2"}
        assert call_count == 2

    def test_cached_decorator_with_key_builder(self):
        """测试缓存装饰器（自定义键生成器）"""
        service = CacheService()
        call_count = 0

        def custom_key_builder(user_id: int, role: str):
            return f"user:{user_id}:{role}"

        @service.cached("user", ttl=60, key_builder=custom_key_builder)
        def get_user(user_id: int, role: str):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "role": role}

        # 第一次调用
        result1 = get_user(1, "admin")
        assert result1 == {"id": 1, "role": "admin"}
        assert call_count == 1

        # 相同参数，应该从缓存获取
        result2 = get_user(1, "admin")
        assert call_count == 1

        # 不同参数，应该执行函数
        result3 = get_user(1, "user")
        assert call_count == 2

    def test_invalidate_pattern_with_redis(self):
        """测试模式匹配失效（使用Redis）"""
        redis_mock = Mock()
        redis_mock.keys.return_value = [b"ops:user:1", b"ops:user:2"]
        redis_mock.delete.return_value = 2
        service = CacheService(redis_client=redis_mock)

        # 预先设置内存缓存
        service._memory_cache.set("ops:user:1", "Alice")
        service._memory_cache.set("ops:user:2", "Bob")

        result = service.invalidate_pattern("user:*")
        assert result == 2
        redis_mock.keys.assert_called_once_with("ops:user:*")
        redis_mock.delete.assert_called_once_with(b"ops:user:1", b"ops:user:2")

    def test_invalidate_pattern_without_redis(self):
        """测试模式匹配失效（不使用Redis）"""
        service = CacheService()
        service._memory_cache.set("ops:user:1", "Alice")
        service._memory_cache.set("ops:user:2", "Bob")
        service._memory_cache.set("ops:session:1", "xyz")

        result = service.invalidate_pattern("user:*")
        assert result == 2
        assert service._memory_cache.get("ops:user:1") is None
        assert service._memory_cache.get("ops:user:2") is None
        assert service._memory_cache.get("ops:session:1") == "xyz"

    def test_invalidate_pattern_redis_error(self):
        """测试模式匹配失效（Redis错误）"""
        redis_mock = Mock()
        redis_mock.keys.side_effect = Exception("Redis error")
        service = CacheService(redis_client=redis_mock)
        service._memory_cache.set("ops:user:1", "Alice")

        result = service.invalidate_pattern("user:*")
        assert result == 1  # 内存缓存应该被清理

    def test_clear_with_redis(self):
        """测试清空缓存（使用Redis）"""
        redis_mock = Mock()
        redis_mock.keys.return_value = [b"ops:user:1", b"ops:session:1"]
        service = CacheService(redis_client=redis_mock)
        service._memory_cache.set("ops:user:1", "Alice")

        result = service.clear()
        assert result == 1  # 内存缓存的清理数量
        redis_mock.keys.assert_called_once_with("ops:*")
        redis_mock.delete.assert_called_once_with(b"ops:user:1", b"ops:session:1")

    def test_clear_without_redis(self):
        """测试清空缓存（不使用Redis）"""
        service = CacheService()
        service._memory_cache.set("ops:user:1", "Alice")
        service._memory_cache.set("ops:session:1", "xyz")

        result = service.clear()
        assert result == 2
        assert len(service._memory_cache._cache) == 0

    def test_clear_redis_error(self):
        """测试清空缓存（Redis错误）"""
        redis_mock = Mock()
        redis_mock.keys.side_effect = Exception("Redis error")
        service = CacheService(redis_client=redis_mock)
        service._memory_cache.set("ops:user:1", "Alice")

        result = service.clear()
        assert result == 1  # 内存缓存应该被清理


@pytest.mark.unit
class TestGlobalFunctions:
    """全局函数测试"""

    def test_get_cache_service_singleton(self):
        """测试获取缓存服务（单例）"""
        # 重置全局缓存服务
        import app.services.cache_service as cache_module
        cache_module._cache_service = None

        service1 = get_cache_service()
        service2 = get_cache_service()
        # 应该是同一个实例
        assert service1 is service2

    def test_cache_get(self):
        """测试便捷函数cache_get"""
        import app.services.cache_service as cache_module
        cache_module._cache_service = None

        service = get_cache_service()
        service.set("key1", "value1", ttl=60)

        result = cache_get("key1")
        assert result == "value1"

    def test_cache_set(self):
        """测试便捷函数cache_set"""
        import app.services.cache_service as cache_module
        cache_module._cache_service = None

        result = cache_set("key1", "value1", ttl=60)
        assert result is True

        # 验证数据已缓存
        service = get_cache_service()
        assert service.get("key1") == "value1"

    def test_cache_delete(self):
        """测试便捷函数cache_delete"""
        import app.services.cache_service as cache_module
        cache_module._cache_service = None

        service = get_cache_service()
        service.set("key1", "value1", ttl=60)

        result = cache_delete("key1")
        assert result is True
        assert service.get("key1") is None

    def test_cached_function(self):
        """测试便捷函数cached"""
        import app.services.cache_service as cache_module
        cache_module._cache_service = None

        call_count = 0

        @cached("item", ttl=60)
        def get_item(item_id: int):
            nonlocal call_count
            call_count += 1
            return {"id": item_id}

        # 第一次调用
        result1 = get_item(1)
        assert result1 == {"id": 1}
        assert call_count == 1

        # 第二次调用，应该从缓存获取
        result2 = get_item(1)
        assert result2 == {"id": 1}
        assert call_count == 1


@pytest.mark.unit
class TestConcurrency:
    """并发安全测试"""

    def test_memory_cache_concurrent_get_set(self):
        """测试内存缓存的并发读写"""
        import threading

        cache = MemoryCache(default_ttl=300)
        errors = []

        def worker():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
                    value = cache.get(f"key_{i}")
                    assert value == f"value_{i}"
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发测试失败: {errors}"

    def test_memory_cache_concurrent_delete(self):
        """测试内存缓存的并发删除"""
        import threading

        cache = MemoryCache(default_ttl=300)
        cache.set("key1", "value1")
        errors = []

        def worker():
            try:
                cache.delete("key1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发测试失败: {errors}"
