"""
Redis 适配器单元测试

使用 mock 测试 Redis 适配器的核心功能，避免依赖真实的 Redis 连接。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from app.adapters.datasource.redis_adapter import RedisAdapter


class TestRedisAdapter:
    """Redis 适配器测试"""

    def test_init(self):
        """测试初始化"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        assert adapter.get_adapter_type() == "redis"
        assert adapter.config == config
        assert adapter.connection is None

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_connect_success(self, mock_redis):
        """测试成功连接"""
        # 模拟连接
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        result = adapter.connect()

        assert result is True
        assert adapter.connection == mock_client
        mock_redis.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_connect_failure(self, mock_redis):
        """测试连接失败"""
        # 模拟连接失败
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        with pytest.raises(ConnectionError, match="Redis 连接失败"):
            adapter.connect()

    def test_disconnect(self):
        """测试断开连接"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        mock_client = Mock()
        adapter.connection = mock_client

        result = adapter.disconnect()

        assert result is True
        assert adapter.connection is None
        mock_client.close.assert_called_once()

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_test_connection_success(self, mock_redis):
        """测试连接测试成功"""
        mock_client = Mock()
        mock_client.info.return_value = {"redis_version": "6.2.6"}
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.test_connection()

        assert result["success"] is True
        assert result["version"] == "6.2.6"
        assert "latency" in result
        assert result["latency"] >= 0

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_test_connection_failure(self, mock_redis):
        """测试连接测试失败"""
        mock_client = Mock()
        mock_client.info.side_effect = Exception("Connection failed")
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.test_connection()

        assert result["success"] is False
        assert "message" in result

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_execute_query_get(self, mock_redis):
        """测试执行 GET 查询"""
        mock_client = Mock()
        mock_client.get.return_value = "value123"
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.execute_query("GET key1")

        assert len(result) == 1
        assert result[0]["value"] == "value123"
        mock_client.get.assert_called_once_with("key1")

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_execute_query_set(self, mock_redis):
        """测试执行 SET 查询"""
        mock_client = Mock()
        mock_client.set.return_value = True
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.execute_query("SET key1 value1")

        assert len(result) == 1
        assert result[0]["value"] is True
        mock_client.set.assert_called_once_with("key1", "value1")

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_execute_query_keys(self, mock_redis):
        """测试执行 KEYS 查询"""
        mock_client = Mock()
        mock_client.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.execute_query("KEYS *")

        assert len(result) == 3
        assert result[0]["value"] == "key1"
        assert result[1]["value"] == "key2"
        assert result[2]["value"] == "key3"

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_execute_query_hgetall(self, mock_redis):
        """测试执行 HGETALL 查询"""
        mock_client = Mock()
        mock_client.hgetall.return_value = {"field1": "value1", "field2": "value2"}
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.execute_query("HGETALL hash1")

        assert len(result) == 1
        assert result[0]["field1"] == "value1"
        assert result[0]["field2"] == "value2"

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_execute_query_info(self, mock_redis):
        """测试执行 INFO 查询"""
        mock_client = Mock()
        mock_client.info.return_value = {
            "connected_clients": 10,
            "used_memory_human": "1.5M"
        }
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.execute_query("INFO")

        assert len(result) == 1
        assert result[0]["value"] is not None

    def test_execute_query_not_connected(self):
        """测试未连接时执行查询"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        with pytest.raises(RuntimeError, match="未建立连接"):
            adapter.execute_query("GET key1")

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_get_metrics(self, mock_redis):
        """测试获取监控指标"""
        mock_client = Mock()
        mock_client.info.return_value = {
            "connected_clients": 10,
            "used_memory_human": "1.5M"
        }
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        metrics = adapter.get_metrics()

        assert "connection_pool_size" in metrics
        assert "total_queries" in metrics
        assert "total_errors" in metrics
        assert "avg_query_time" in metrics

    def test_is_connected(self):
        """测试连接状态检查"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        assert adapter.is_connected() is False

        mock_client = Mock()
        mock_client.ping.return_value = True
        adapter.connection = mock_client

        assert adapter.is_connected() is True

    def test_is_connected_ping_failed(self):
        """测试ping失败时连接状态"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Ping failed")
        adapter.connection = mock_client

        assert adapter.is_connected() is False

    def test_connection_context(self):
        """测试连接上下文管理器"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        with adapter.connection_context():
            # connection_context 在基类中实现，会调用 connect
            pass

    @patch('app.adapters.datasource.redis_adapter.redis.Redis')
    def test_to_dict(self, mock_redis):
        """测试转换为字典"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connection = mock_client

        result = adapter.to_dict()

        assert result["type"] == "redis"
        assert result["connected"] is True
        assert "metrics" in result

    def test_get_adapter_type(self):
        """测试获取适配器类型"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        assert adapter.get_adapter_type() == "redis"
