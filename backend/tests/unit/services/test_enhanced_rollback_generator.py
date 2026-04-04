"""
增强版回滚SQL生成服务测试
"""
import pytest
from unittest.mock import Mock, patch
from app.services.enhanced_rollback_generator import (
    EnhancedRollbackGenerator,
    RollbackResult,
    RedisRollbackResult,
    SQLType
)


class TestRollbackResult:
    """回滚结果数据类测试"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        result = RollbackResult(
            success=True,
            sql_type=SQLType.INSERT,
            rollback_sql="DELETE FROM users WHERE id = 1",
            affected_table="users",
            affected_rows=1
        )

        assert result.success is True
        assert result.sql_type == SQLType.INSERT
        assert result.rollback_sql is not None
        assert result.affected_table == "users"

    def test_create_failure_result(self):
        """测试创建失败结果"""
        result = RollbackResult(
            success=False,
            sql_type=SQLType.UNKNOWN,
            error="无法解析SQL"
        )

        assert result.success is False
        assert result.error == "无法解析SQL"


class TestRedisRollbackResult:
    """Redis回滚结果数据类测试"""

    def test_create_redis_result(self):
        """测试创建Redis回滚结果"""
        result = RedisRollbackResult(
            success=True,
            rollback_commands=["SET key1 value1"],
            affected_keys=["key1"]
        )

        assert result.success is True
        assert len(result.rollback_commands) == 1
        assert "key1" in result.affected_keys


class TestEnhancedRollbackGenerator:
    """增强版回滚生成器测试"""

    @pytest.fixture
    def generator(self):
        """创建生成器实例"""
        return EnhancedRollbackGenerator()

    @pytest.fixture
    def generator_with_db(self):
        """创建带数据库连接的生成器"""
        mock_conn = Mock()
        return EnhancedRollbackGenerator(db_connection=mock_conn, db_type="mysql")

    def test_init(self):
        """测试初始化"""
        generator = EnhancedRollbackGenerator()
        assert generator.db_connection is None
        assert generator.db_type == "mysql"

    def test_init_with_db(self):
        """测试初始化（带数据库）"""
        mock_conn = Mock()
        generator = EnhancedRollbackGenerator(
            db_connection=mock_conn,
            db_type="postgresql"
        )
        assert generator.db_connection == mock_conn
        assert generator.db_type == "postgresql"

    def test_analyze_sql_create_table(self, generator):
        """测试分析CREATE TABLE"""
        sql = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.CREATE_TABLE
        assert results[0][1] == "users"

    def test_analyze_sql_drop_table(self, generator):
        """测试分析DROP TABLE"""
        sql = "DROP TABLE IF EXISTS users"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.DROP_TABLE
        assert results[0][1] == "users"

    def test_analyze_sql_insert(self, generator):
        """测试分析INSERT"""
        sql = "INSERT INTO users (id, name) VALUES (1, 'John')"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.INSERT
        assert results[0][1] == "users"

    def test_analyze_sql_update(self, generator):
        """测试分析UPDATE"""
        sql = "UPDATE users SET name = 'Jane' WHERE id = 1"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.UPDATE
        assert results[0][1] == "users"

    def test_analyze_sql_delete(self, generator):
        """测试分析DELETE"""
        sql = "DELETE FROM users WHERE id = 1"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.DELETE
        assert results[0][1] == "users"

    def test_analyze_sql_multiple_statements(self, generator):
        """测试分析多条SQL语句"""
        sql = """
        INSERT INTO users (id, name) VALUES (1, 'John');
        UPDATE users SET name = 'Jane' WHERE id = 1;
        DELETE FROM users WHERE id = 1;
        """
        results = generator.analyze_sql(sql)

        assert len(results) == 3
        assert results[0][0] == SQLType.INSERT
        assert results[1][0] == SQLType.UPDATE
        assert results[2][0] == SQLType.DELETE

    def test_analyze_sql_unknown(self, generator):
        """测试分析未知SQL"""
        sql = "SHOW TABLES"
        results = generator.analyze_sql(sql)

        assert len(results) == 1
        assert results[0][0] == SQLType.UNKNOWN
        assert results[0][1] is None

    def test_extract_where_clause(self, generator):
        """测试提取WHERE条件"""
        sql = "DELETE FROM users WHERE id = 1 AND name = 'John' LIMIT 10"
        where = generator.extract_where_clause(sql)

        assert where == "id = 1 AND name = 'John'"

    def test_extract_where_clause_none(self, generator):
        """测试提取WHERE条件（无WHERE）"""
        sql = "SELECT * FROM users"
        where = generator.extract_where_clause(sql)

        assert where is None

    def test_extract_set_clause(self, generator):
        """测试提取SET子句"""
        sql = "UPDATE users SET name = 'Jane', age = 30 WHERE id = 1"
        set_clause = generator.extract_set_clause(sql)

        assert set_clause["name"] == "'Jane'"
        assert set_clause["age"] == "30"

    def test_extract_set_clause_none(self, generator):
        """测试提取SET子句（无SET）"""
        sql = "SELECT * FROM users"
        set_clause = generator.extract_set_clause(sql)

        assert set_clause == {}

    def test_extract_insert_values(self, generator):
        """测试提取INSERT列和值"""
        sql = "INSERT INTO users (id, name, age) VALUES (1, 'John', 30)"
        cols, vals = generator.extract_insert_values(sql)

        assert cols == ["id", "name", "age"]
        assert len(vals) == 1
        assert vals[0] == ["1", "'John'", "30"]

    def test_extract_insert_values_no_columns(self, generator):
        """测试提取INSERT值（无列名）"""
        sql = "INSERT INTO users VALUES (1, 'John', 30)"
        cols, vals = generator.extract_insert_values(sql)

        assert cols == []
        assert len(vals) == 1
        assert vals[0] == ["1", "'John'", "30"]

    def test_extract_insert_values_invalid(self, generator):
        """测试提取INSERT值（无效SQL）"""
        sql = "INSERT INTO users"
        cols, vals = generator.extract_insert_values(sql)

        assert cols == []
        assert vals == []

    def test_get_primary_key_no_connection(self, generator):
        """测试获取主键（无数据库连接）"""
        primary_keys = generator.get_primary_key("users")

        assert primary_keys == ["id"]

    def test_get_primary_key_mysql(self, generator_with_db):
        """测试获取主键（MySQL）"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("id",), ("user_id",)]
        generator_with_db.db_connection.cursor.return_value = mock_cursor

        primary_keys = generator_with_db.get_primary_key("users")

        assert primary_keys == ["id", "user_id"]
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_get_primary_key_postgresql(self):
        """测试获取主键（PostgreSQL）"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [("id",)]
        mock_conn.cursor.return_value = mock_cursor

        generator = EnhancedRollbackGenerator(
            db_connection=mock_conn,
            db_type="postgresql"
        )

        primary_keys = generator.get_primary_key("users")

        assert primary_keys == ["id"]
        assert "pg_index" in mock_cursor.execute.call_args[0][0]

    def test_get_primary_key_exception(self, generator_with_db):
        """测试获取主键（异常情况）"""
        generator_with_db.db_connection.cursor.side_effect = Exception("DB error")

        primary_keys = generator_with_db.get_primary_key("users")

        # 应该返回默认值
        assert primary_keys == ["id"]

    def test_get_table_columns_no_connection(self, generator):
        """测试获取表列（无数据库连接）"""
        columns = generator.get_table_columns("users")

        assert columns == []

    def test_get_table_columns(self, generator_with_db):
        """测试获取表列"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("id", "INT"),
            ("name", "VARCHAR(100)"),
            ("age", "INT")
        ]
        generator_with_db.db_connection.cursor.return_value = mock_cursor

        columns = generator_with_db.get_table_columns("users")

        assert len(columns) == 3
        assert "id" in columns
        assert "name" in columns
        assert "age" in columns
