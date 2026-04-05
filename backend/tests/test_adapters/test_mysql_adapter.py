"""
MySQL 适配器单元测试

使用 mock 测试 MySQL 适配器的核心功能，避免依赖真实的 MySQL 连接。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from app.adapters.datasource.mysql_adapter import MySQLAdapter


class TestMySQLAdapter:
    """MySQL 适配器测试"""

    def test_init(self):
        """测试初始化"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.get_adapter_type() == "mysql"
        assert adapter.config == config
        assert adapter._pool is None
        assert adapter._connected is False

    @patch('pymysql.connect')
    def test_connect_success(self, mock_connect):
        """测试成功连接"""
        # 模拟连接
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        result = adapter.connect()

        assert result is True
        assert adapter._connected is True
        mock_connect.assert_called_once_with(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset="utf8mb4"
        )

    @patch('pymysql.connect')
    def test_connect_failure(self, mock_connect):
        """测试连接失败"""
        # 模拟连接失败
        mock_connect.side_effect = Exception("Connection failed")

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        result = adapter.connect()

        assert result is False
        assert adapter._connected is False

    def test_disconnect(self):
        """测试断开连接"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter._connected = True
        adapter._connection = Mock()

        result = adapter.disconnect()

        assert result is True
        assert adapter._connected is False

    @patch('pymysql.connect')
    def test_test_connection_success(self, mock_connect):
        """测试连接测试成功"""
        # 模拟连接和查询
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("8.0.32",)
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        result = adapter.test_connection()

        assert result["success"] is True
        assert result["version"] == "8.0.32"
        assert "latency" in result
        assert result["latency"] > 0

    @patch('pymysql.connect')
    def test_test_connection_failure(self, mock_connect):
        """测试连接测试失败"""
        mock_connect.side_effect = Exception("Connection failed")

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        result = adapter.test_connection()

        assert result["success"] is False
        assert "message" in result

    @patch('pymysql.connect')
    def test_execute_query(self, mock_connect):
        """测试执行查询"""
        # 模拟连接和查询
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("name",), ("age",)]
        mock_cursor.fetchall.return_value = [
            (1, "Alice", 25),
            (2, "Bob", 30)
        ]
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.execute_query("SELECT * FROM users")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Alice"
        assert result[1]["id"] == 2
        assert result[1]["name"] == "Bob"

    @patch('pymysql.connect')
    def test_execute_query_with_params(self, mock_connect):
        """测试带参数的查询"""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "Alice")]
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.execute_query(
            "SELECT * FROM users WHERE id = %(id)s",
            {"id": 1}
        )

        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_execute_query_not_connected(self):
        """测试未连接时执行查询"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        with pytest.raises(Exception, match="未连接到数据库"):
            adapter.execute_query("SELECT 1")

    @patch('pymysql.connect')
    def test_get_metrics(self, mock_connect):
        """测试获取监控指标"""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        metrics = adapter.get_metrics()

        assert "adapter_type" in metrics
        assert metrics["adapter_type"] == "mysql"
        assert "connected" in metrics
        assert metrics["connected"] is True
        assert "host" in metrics
        assert "port" in metrics

    def test_is_connected(self):
        """测试连接状态检查"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.is_connected() is False

        adapter._connected = True
        assert adapter.is_connected() is True

    def test_connection_context(self):
        """测试连接上下文管理器"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        with adapter.connection_context():
            assert adapter.is_connected() is True

    @patch('pymysql.connect')
    def test_to_dict(self, mock_connect):
        """测试转换为字典"""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.to_dict()

        assert result["type"] == "mysql"
        assert result["connected"] is True
        assert "metrics" in result

    def test_get_adapter_type(self):
        """测试获取适配器类型"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.get_adapter_type() == "mysql"
