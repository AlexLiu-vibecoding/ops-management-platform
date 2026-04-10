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
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.get_adapter_type() == "mysql"
        assert adapter.config == config
        assert adapter.connection_pool is None

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_connect_success(self, mock_pooled_db):
        """测试成功连接"""
        # 模拟连接池
        mock_pool = Mock()
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        result = adapter.connect()

        assert result is True
        assert adapter.connection_pool == mock_pool
        mock_pooled_db.assert_called_once()

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_connect_failure(self, mock_pooled_db):
        """测试连接失败"""
        # 模拟连接失败
        mock_pooled_db.side_effect = Exception("Connection failed")

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        with pytest.raises(ConnectionError, match="MySQL 连接失败"):
            adapter.connect()

    def test_disconnect(self):
        """测试断开连接"""
        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        mock_pool = Mock()
        adapter.connection_pool = mock_pool

        result = adapter.disconnect()

        assert result is True
        assert adapter.connection_pool is None
        mock_pool.close.assert_called_once()

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_test_connection_success(self, mock_pooled_db):
        """测试连接测试成功"""
        # 模拟连接池和查询
        mock_pool = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"VERSION()": "8.0.32"}
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.test_connection()

        assert result["success"] is True
        assert result["version"] == "8.0.32"
        assert "latency" in result
        assert result["latency"] >= 0

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_test_connection_failure(self, mock_pooled_db):
        """测试连接测试失败"""
        mock_pool = Mock()
        mock_pool.connection.side_effect = Exception("Connection failed")
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.test_connection()

        assert result["success"] is False
        assert "message" in result

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_execute_query(self, mock_pooled_db):
        """测试执行查询"""
        # 模拟连接池和查询
        mock_pool = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Alice", "age": 25},
            {"id": 2, "name": "Bob", "age": 30}
        ]
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
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

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_execute_query_with_params(self, mock_pooled_db):
        """测试带参数的查询"""
        mock_pool = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
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

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_execute_query_not_connected(self, mock_pooled_db):
        """测试未连接时执行查询"""
        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        with pytest.raises(RuntimeError, match="未建立连接"):
            adapter.execute_query("SELECT 1")

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_get_metrics(self, mock_pooled_db):
        """测试获取监控指标"""
        mock_pool = Mock()
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        metrics = adapter.get_metrics()

        assert "connection_pool_size" in metrics
        assert "total_queries" in metrics
        assert "total_errors" in metrics
        assert "avg_query_time" in metrics

    def test_is_connected(self):
        """测试连接状态检查"""
        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.is_connected() is False

        adapter.connection_pool = Mock()
        assert adapter.is_connected() is True

    def test_connection_context(self):
        """测试连接上下文管理器"""
        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        with adapter.connection_context():
            # connection_context 在基类中实现，会调用 connect
            pass

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_to_dict(self, mock_pooled_db):
        """测试转换为字典"""
        mock_pool = Mock()
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
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
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)

        assert adapter.get_adapter_type() == "mysql"

    @patch('app.adapters.datasource.mysql_adapter.PooledDB')
    def test_execute_insert_query(self, mock_pooled_db):
        """测试执行INSERT查询"""
        mock_pool = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_pool.connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        mock_pooled_db.return_value = mock_pool

        config = {
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "password",
            "database": "test"
        }

        adapter = MySQLAdapter(config)
        adapter.connect()

        result = adapter.execute_query("INSERT INTO users (name) VALUES ('Alice')")

        assert len(result) == 1
        assert result[0]["affected_rows"] == 1
