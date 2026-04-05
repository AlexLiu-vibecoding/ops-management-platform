"""
审批回滚生成单元测试
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.models import RDBInstance, RedisInstance
from app.api.approval.rollback import (
    generate_sql_rollback_with_data,
    generate_redis_rollback_with_data
)


class TestGenerateSQLRollbackWithData:
    """generate_sql_rollback_with_data 测试"""

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_success(self, mock_generator_class, mock_get_conn):
        """测试成功生成 SQL 回滚"""
        # Mock 连接
        mock_conn = MagicMock()
        mock_get_conn.return_value = (mock_conn, "mysql")

        # Mock 生成器
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        # Mock 回滚结果
        mock_result1 = MagicMock()
        mock_result1.success = True
        mock_result1.rollback_sql = "DELETE FROM users WHERE id = 1;"
        mock_result1.sql_type.value = "INSERT"
        mock_result1.affected_table = "users"
        mock_result1.affected_rows = 1
        mock_result1.warning = None

        mock_result2 = MagicMock()
        mock_result2.success = True
        mock_result2.rollback_sql = "DELETE FROM products WHERE id = 2;"
        mock_result2.sql_type.value = "UPDATE"
        mock_result2.affected_table = "products"
        mock_result2.affected_rows = 2
        mock_result2.warning = None

        mock_generator.generate_rollback_sql.return_value = [mock_result1, mock_result2]

        # 执行
        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        sql_content = "INSERT INTO users VALUES (1, 'test');"
        result = await generate_sql_rollback_with_data(instance, sql_content, "testdb")

        # 验证
        assert result is not None
        rollback_sql, affected_rows = result
        assert "-- 自动生成的回滚SQL" in rollback_sql
        assert "DELETE FROM users WHERE id = 1;" in rollback_sql
        assert "DELETE FROM products WHERE id = 2;" in rollback_sql
        assert affected_rows == 3
        assert "test-mysql" in rollback_sql
        assert "testdb" in rollback_sql

        mock_get_conn.assert_called_once_with(instance, "testdb")
        mock_generator_class.assert_called_once_with(db_connection=mock_conn, db_type="mysql")
        mock_generator.generate_rollback_sql.assert_called_once_with(sql_content)
        mock_conn.close.assert_called_once()

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_no_results(self, mock_generator_class, mock_get_conn):
        """测试无回滚结果"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = (mock_conn, "postgresql")

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_rollback_sql.return_value = []

        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="localhost",
            port=5432,
            username="postgres"
        )

        result = await generate_sql_rollback_with_data(instance, "SELECT 1;", "testdb")

        assert result is not None
        rollback_sql, affected_rows = result
        assert rollback_sql is None
        assert affected_rows == 0

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_with_warning(self, mock_generator_class, mock_get_conn):
        """测试带警告的回滚"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = (mock_conn, "mysql")

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_sql = "DELETE FROM users WHERE id = 1;"
        mock_result.sql_type.value = "INSERT"
        mock_result.affected_table = "users"
        mock_result.affected_rows = 1
        mock_result.warning = "This is a warning"

        mock_generator.generate_rollback_sql.return_value = [mock_result]

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        result = await generate_sql_rollback_with_data(instance, "INSERT INTO users VALUES (1, 'test');")

        assert result is not None
        rollback_sql, affected_rows = result
        assert "-- 警告: This is a warning" in rollback_sql

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_failed_result(self, mock_generator_class, mock_get_conn):
        """测试失败的回滚结果"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = (mock_conn, "mysql")

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result1 = MagicMock()
        mock_result1.success = True
        mock_result1.rollback_sql = "DELETE FROM users WHERE id = 1;"
        mock_result1.sql_type.value = "INSERT"
        mock_result1.affected_table = "users"
        mock_result1.affected_rows = 1
        mock_result1.warning = None

        mock_result2 = MagicMock()
        mock_result2.success = False
        mock_result2.rollback_sql = None

        mock_generator.generate_rollback_sql.return_value = [mock_result1, mock_result2]

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        result = await generate_sql_rollback_with_data(instance, "INSERT INTO users VALUES (1, 'test');")

        assert result is not None
        rollback_sql, affected_rows = result
        assert "DELETE FROM users WHERE id = 1;" in rollback_sql
        assert affected_rows == 1

    @patch('app.api.approval.rollback.get_rdb_connection')
    async def test_generate_sql_rollback_exception(self, mock_get_conn):
        """测试异常处理"""
        mock_get_conn.side_effect = Exception("Connection error")

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        with pytest.raises(Exception, match="Connection error"):
            await generate_sql_rollback_with_data(instance, "INSERT INTO users VALUES (1, 'test');")

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_connection_cleanup(self, mock_generator_class, mock_get_conn):
        """测试连接清理"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = (mock_conn, "mysql")

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_rollback_sql.return_value = []

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        await generate_sql_rollback_with_data(instance, "SELECT 1;")

        # 确保连接被关闭
        mock_conn.close.assert_called_once()

    @patch('app.api.approval.rollback.get_rdb_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_sql_rollback_close_exception(self, mock_generator_class, mock_get_conn):
        """测试关闭连接异常"""
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("Close error")
        mock_get_conn.return_value = (mock_conn, "mysql")

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_rollback_sql.return_value = []

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        # 不应该抛出异常
        result = await generate_sql_rollback_with_data(instance, "SELECT 1;")
        assert result is not None


class TestGenerateRedisRollbackWithData:
    """generate_redis_rollback_with_data 测试"""

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_success(self, mock_generator_class, mock_get_conn):
        """测试成功生成 Redis 回滚"""
        # Mock 连接
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        # Mock 生成器
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        # Mock 回滚结果
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = [
            "DEL old_key",
            "SET old_key old_value"
        ]
        mock_result.affected_keys = ["old_key"]
        mock_result.warning = None

        mock_generator.generate_redis_rollback.return_value = mock_result

        # 执行
        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        commands = "SET new_key new_value"
        result = await generate_redis_rollback_with_data(instance, commands)

        # 验证
        assert result is not None
        rollback_content, affected_keys = result
        assert "-- 自动生成的Redis回滚命令" in rollback_content
        assert "DEL old_key" in rollback_content
        assert "SET old_key old_value" in rollback_content
        assert affected_keys == ["old_key"]
        assert "test-redis" in rollback_content
        assert "受影响键数量: 1" in rollback_content

        mock_get_conn.assert_called_once_with(instance)
        mock_generator_class.assert_called_once_with()
        mock_generator.generate_redis_rollback.assert_called_once_with(commands, redis_connection=mock_redis)
        mock_redis.close.assert_called_once()

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_failed(self, mock_generator_class, mock_get_conn):
        """测试失败的 Redis 回滚"""
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Invalid command"
        mock_result.rollback_commands = []

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        result = await generate_redis_rollback_with_data(instance, "INVALID COMMAND")

        assert result is not None
        rollback_content, affected_keys = result
        assert rollback_content is None
        assert affected_keys == []

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_no_commands(self, mock_generator_class, mock_get_conn):
        """测试无回滚命令"""
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = []
        mock_result.affected_keys = []

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        result = await generate_redis_rollback_with_data(instance, "GET key")

        assert result is not None
        rollback_content, affected_keys = result
        assert rollback_content is None
        assert affected_keys == []

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_with_warning(self, mock_generator_class, mock_get_conn):
        """测试带警告的 Redis 回滚"""
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = ["DEL key1"]
        mock_result.affected_keys = ["key1"]
        mock_result.warning = "Key will be deleted"

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        result = await generate_redis_rollback_with_data(instance, "SET key1 value1")

        assert result is not None
        rollback_content, affected_keys = result
        assert "-- 警告: Key will be deleted" in rollback_content

    @patch('app.api.approval.rollback.get_redis_connection')
    async def test_generate_redis_rollback_exception(self, mock_get_conn):
        """测试异常处理"""
        mock_get_conn.side_effect = Exception("Redis connection error")

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        with pytest.raises(Exception, match="Redis connection error"):
            await generate_redis_rollback_with_data(instance, "SET key value")

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_cleanup(self, mock_generator_class, mock_get_conn):
        """测试连接清理"""
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = []
        mock_result.affected_keys = []

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        await generate_redis_rollback_with_data(instance, "GET key")

        mock_redis.close.assert_called_once()

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_multiple_keys(self, mock_generator_class, mock_get_conn):
        """测试多个键的 Redis 回滚"""
        mock_redis = MagicMock()
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = [
            "DEL key1",
            "SET key1 old_value1",
            "DEL key2",
            "SET key2 old_value2"
        ]
        mock_result.affected_keys = ["key1", "key2"]
        mock_result.warning = None

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        result = await generate_redis_rollback_with_data(instance, "MSET key1 new1 key2 new2")

        assert result is not None
        rollback_content, affected_keys = result
        assert len(affected_keys) == 2
        assert "key1" in rollback_content
        assert "key2" in rollback_content
        assert "受影响键数量: 2" in rollback_content

    @patch('app.api.approval.rollback.get_redis_connection')
    @patch('app.api.approval.rollback.EnhancedRollbackGenerator')
    async def test_generate_redis_rollback_close_exception(self, mock_generator_class, mock_get_conn):
        """测试关闭连接异常"""
        mock_redis = MagicMock()
        mock_redis.close.side_effect = Exception("Close error")
        mock_get_conn.return_value = mock_redis

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.rollback_commands = []
        mock_result.affected_keys = []

        mock_generator.generate_redis_rollback.return_value = mock_result

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379
        )

        # 不应该抛出异常
        result = await generate_redis_rollback_with_data(instance, "GET key")
        assert result is not None
