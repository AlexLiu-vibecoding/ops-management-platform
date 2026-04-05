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
        assert adapter._client is None
        assert adapter._connected is False

    @patch('redis.Redis')
    def test_connect_success(self, mock_redis):
        """测试成功连接"""
        # 模拟连接
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        result = adapter.connect()

        assert result is True
        assert adapter._connected is True
        mock_redis.assert_called_once_with(
            host=config["host"],
            port=config["port"],
            password=config["password"],
            db=config["db"],
            decode_responses=True
        )

    @patch('redis.Redis')
    def test_connect_failure(self, mock_redis):
        """测试连接失败"""
        # 模拟连接失败
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        result = adapter.connect()

        assert result is False
        assert adapter._connected is False

    @patch('redis.Redis')
    def test_disconnect(self, mock_redis):
        """测试断开连接"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()
        adapter._connected = True

        result = adapter.disconnect()

        assert result is True
        assert adapter._connected is False

    @patch('redis.Redis')
    def test_test_connection_success(self, mock_redis):
        """测试连接测试成功"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.info.return_value = {"redis_version": "6.2.6"}

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.test_connection()

        assert result["success"] is True
        assert result["version"] == "6.2.6"
        assert "latency" in result
        assert result["latency"] > 0

    @patch('redis.Redis')
    def test_test_connection_failure(self, mock_redis):
        """测试连接测试失败"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.test_connection()

        assert result["success"] is False
        assert "message" in result

    @patch('redis.Redis')
    def test_execute_query_get(self, mock_redis):
        """测试执行 GET 查询"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.get.return_value = "value123"

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.execute_query("GET key1")

        assert len(result) == 1
        assert result[0]["key"] == "key1"
        assert result[0]["value"] == "value123"
        mock_client.get.assert_called_once_with("key1")

    @patch('redis.Redis')
    def test_execute_query_set(self, mock_redis):
        """测试执行 SET 查询"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.set.return_value = True

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.execute_query("SET key1 value1")

        assert len(result) == 1
        assert result[0]["key"] == "key1"
        assert result[0]["value"] == "value1"
        assert result[0]["success"] is True
        mock_client.set.assert_called_once_with("key1", "value1")

    @patch('redis.Redis')
    def test_execute_query_keys(self, mock_redis):
        """测试执行 KEYS 查询"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.keys.return_value = ["key1", "key2", "key3"]

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.execute_query("KEYS *")

        assert len(result) == 3
        assert result[0]["key"] == "key1"
        assert result[1]["key"] == "key2"
        assert result[2]["key"] == "key3"

    @patch('redis.Redis')
    def test_execute_query_info(self, mock_redis):
        """测试执行 INFO 查询"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.info.return_value = {
            "connected_clients": 10,
            "used_memory_human": "1.5M",
            "total_commands_processed": 10000
        }

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        result = adapter.execute_query("INFO")

        assert len(result) == 1
        assert "info" in result[0]

    def test_execute_query_not_connected(self):
        """测试未连接时执行查询"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)

        with pytest.raises(Exception, match="未连接到 Redis"):
            adapter.execute_query("GET key1")

    @patch('redis.Redis')
    def test_get_metrics(self, mock_redis):
        """测试获取监控指标"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.info.return_value = {
            "connected_clients": 10,
            "used_memory_human": "1.5M"
        }

        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }

        adapter = RedisAdapter(config)
        adapter.connect()

        metrics = adapter.get_metrics()

        assert "adapter_type" in metrics
        assert metrics["adapter_type"] == "redis"
        assert "connected" in metrics
        assert metrics["connected"] is True
        assert "host" in metrics
        assert "port" in metrics

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

        adapter._connected = True
        assert adapter.is_connected() is True

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
            assert adapter.is_connected() is True

    @patch('redis.Redis')
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
        adapter.connect()

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
