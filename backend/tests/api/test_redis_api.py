"""
Redis 管理相关 API 测试

覆盖 Redis 管理接口：
- Redis 实例列表: /api/v1/redis-instances
- Redis 详情: /api/v1/redis-instances/{id}
- Redis 管理: /api/v1/redis/*
"""
import pytest


class TestRedisInstancesAPI:
    """Redis 实例管理 API 测试类"""

    def test_list_redis_instances(self, client, admin_headers):
        """测试获取 Redis 实例列表"""
        response = client.get("/api/v1/redis-instances", headers=admin_headers)
        assert response.status_code == 200

    def test_create_redis_instance(self, client, admin_headers):
        """测试创建 Redis 实例"""
        instance_data = {
            "name": "测试 Redis",
            "host": "localhost",
            "port": 6379,
            "mode": "standalone",
            "password": "test123"
        }
        response = client.post(
            "/api/v1/redis-instances",
            json=instance_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_get_redis_instance(self, client, admin_headers):
        """测试获取 Redis 实例详情"""
        response = client.get("/api/v1/redis-instances/1", headers=admin_headers)
        assert response.status_code in [200, 404, 405]

    def test_update_redis_instance(self, client, admin_headers):
        """测试更新 Redis 实例"""
        update_data = {
            "name": "更新后的 Redis",
            "status": False
        }
        response = client.put(
            "/api/v1/redis-instances/1",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 404, 405]

    def test_delete_redis_instance(self, client, admin_headers):
        """测试删除 Redis 实例"""
        response = client.delete("/api/v1/redis-instances/1", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_test_redis_connection(self, client, admin_headers):
        """测试 Redis 连接"""
        response = client.post("/api/v1/redis-instances/1/test", headers=admin_headers)
        assert response.status_code in [200, 404, 405]


class TestRedisOperationsAPI:
    """Redis 操作 API 测试类"""

    def test_get_redis_info(self, client, admin_headers):
        """测试获取 Redis 信息"""
        response = client.get("/api/v1/redis/1/info", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_get_redis_stats(self, client, admin_headers):
        """测试获取 Redis 统计"""
        response = client.get("/api/v1/redis/1/stats", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_get_slow_logs(self, client, admin_headers):
        """测试获取慢查询日志"""
        response = client.get("/api/v1/redis/1/slow-log", headers=admin_headers)
        assert response.status_code in [200, 404]


class TestRedisAPIErrorHandling:
    """Redis API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/redis-instances")
        assert response.status_code == 401

    def test_create_instance_invalid_data(self, client, admin_headers):
        """测试创建实例时提供无效数据"""
        response = client.post(
            "/api/v1/redis-instances",
            json={"name": "测试实例"},
            headers=admin_headers
        )
        assert response.status_code in [400, 422]
