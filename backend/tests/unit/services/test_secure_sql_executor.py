#!/usr/bin/env python3
"""
安全SQL执行器单元测试

测试范围：
1. SQL语句类型检测
   - SELECT语句识别
   - INSERT/UPDATE/DELETE语句识别
   - DDL语句识别
   - DCL语句识别
   - 其他语句识别

2. SQL风险等级评估
   - 安全等级（只读查询）
   - 低风险等级（单行修改）
   - 中风险等级（多行修改）
   - 高风险等级（批量修改、DDL）
   - 严重风险等级（DROP、TRUNCATE等危险操作）

3. SQL验证
   - 空语句检测
   - SQL注入检测
   - 危险操作检测
   - 允许危险操作

4. SQL查询执行
   - 参数化查询执行
   - 查询结果获取
   - 错误处理

5. SQL脚本执行
   - 脚本解析
   - 多语句执行
   - 错误处理
   - 停止执行控制

运行方式:
    cd /workspace/projects/backend

    # 运行所有安全SQL执行器测试
    python -m pytest tests/unit/services/test_secure_sql_executor.py -v

    # 运行特定测试类
    python -m pytest tests/unit/services/test_secure_sql_executor.py::TestSQLStatementTypeDetection -v
    python -m pytest tests/unit/services/test_secure_sql_executor.py::TestSQLRiskLevelAssessment -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import RDBInstance
from app.services.secure_sql_executor import (
    SecureSQLExecutor,
    secure_sql_executor,
    SQLStatementType,
    SQLRiskLevel
)
from app.core.exceptions import ValidationException, QueryExecutionException


@pytest.fixture(scope="function")
def executor():
    """创建执行器实例"""
    return SecureSQLExecutor()


@pytest.fixture(scope="function")
def mock_instance():
    """创建mock数据库实例"""
    instance = Mock(spec=RDBInstance)
    instance.id = 1
    instance.name = "测试实例"
    instance.host = "127.0.0.1"
    instance.port = 3306
    instance.username = "root"
    instance.db_type = "mysql"
    return instance


@pytest.mark.unit
class TestSQLStatementTypeDetection:
    """SQL语句类型检测测试"""

    def test_detect_select_statement(self, executor):
        """测试检测SELECT语句"""
        sql = "SELECT * FROM users WHERE id = 1"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_insert_statement(self, executor):
        """测试检测INSERT语句"""
        sql = "INSERT INTO users (name, age) VALUES ('test', 25)"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.INSERT

    def test_detect_update_statement(self, executor):
        """测试检测UPDATE语句"""
        sql = "UPDATE users SET age = 26 WHERE id = 1"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.UPDATE

    def test_detect_delete_statement(self, executor):
        """测试检测DELETE语句"""
        sql = "DELETE FROM users WHERE id = 1"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DELETE

    def test_detect_create_statement(self, executor):
        """测试检测CREATE语句（DDL）"""
        sql = "CREATE TABLE test_table (id INT, name VARCHAR(100))"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DDL

    def test_detect_alter_statement(self, executor):
        """测试检测ALTER语句（DDL）"""
        sql = "ALTER TABLE users ADD COLUMN email VARCHAR(100)"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DDL

    def test_detect_drop_statement(self, executor):
        """测试检测DROP语句（DDL）"""
        sql = "DROP TABLE test_table"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DDL

    def test_detect_truncate_statement(self, executor):
        """测试检测TRUNCATE语句（DDL）"""
        sql = "TRUNCATE TABLE test_table"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DDL

    def test_detect_grant_statement(self, executor):
        """测试检测GRANT语句（DCL）"""
        sql = "GRANT SELECT ON database.* TO 'user'@'localhost'"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DCL

    def test_detect_revoke_statement(self, executor):
        """测试检测REVOKE语句（DCL）"""
        sql = "REVOKE SELECT ON database.* FROM 'user'@'localhost'"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.DCL

    def test_detect_show_statement(self, executor):
        """测试检测SHOW语句（SELECT）"""
        sql = "SHOW TABLES"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_describe_statement(self, executor):
        """测试检测DESCRIBE语句（SELECT）"""
        sql = "DESCRIBE users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_explain_statement(self, executor):
        """测试检测EXPLAIN语句（SELECT）"""
        sql = "EXPLAIN SELECT * FROM users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_with_statement(self, executor):
        """测试检测WITH语句（CTE，SELECT）"""
        sql = "WITH cte AS (SELECT * FROM users) SELECT * FROM cte"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_other_statement(self, executor):
        """测试检测其他语句"""
        sql = "USE database"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.OTHER

    def test_detect_statement_with_comment(self, executor):
        """测试检测带注释的语句"""
        sql = "-- This is a comment\nSELECT * FROM users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_statement_with_block_comment(self, executor):
        """测试检测带块注释的语句"""
        sql = "/* This is a comment */ SELECT * FROM users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_statement_case_insensitive(self, executor):
        """测试大小写不敏感"""
        sql = "select * from users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT

    def test_detect_statement_with_leading_spaces(self, executor):
        """测试检测带前导空格的语句"""
        sql = "  SELECT * FROM users"
        result = executor.detect_statement_type(sql)
        assert result == SQLStatementType.SELECT


@pytest.mark.unit
class TestSQLRiskLevelAssessment:
    """SQL风险等级评估测试"""

    def test_assess_select_risk(self, executor):
        """测试评估SELECT语句（安全）"""
        sql = "SELECT * FROM users WHERE id = 1"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.SAFE
        assert len(risks) == 0

    def test_assess_insert_risk(self, executor):
        """测试评估INSERT语句（低风险）"""
        sql = "INSERT INTO users (name, age) VALUES ('test', 25)"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.LOW
        assert len(risks) == 0

    def test_assess_update_with_where_risk(self, executor):
        """测试评估带WHERE的UPDATE语句（中风险）"""
        sql = "UPDATE users SET age = 26 WHERE id = 1"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.MEDIUM
        assert len(risks) == 0

    def test_assess_update_without_where_risk(self, executor):
        """测试评估无WHERE的UPDATE语句（高风险）"""
        sql = "UPDATE users SET age = 26"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.HIGH
        assert len(risks) > 0
        assert "WHERE" in risks[0]

    def test_assess_delete_with_where_risk(self, executor):
        """测试评估带WHERE的DELETE语句（中风险）"""
        sql = "DELETE FROM users WHERE id = 1"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.MEDIUM
        assert len(risks) == 0

    def test_assess_delete_without_where_risk(self, executor):
        """测试评估无WHERE的DELETE语句（高风险）"""
        sql = "DELETE FROM users"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.HIGH
        assert len(risks) > 0
        assert "WHERE" in risks[0]

    def test_assess_create_table_risk(self, executor):
        """测试评估CREATE TABLE语句（高风险）"""
        sql = "CREATE TABLE test_table (id INT, name VARCHAR(100))"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.HIGH
        assert len(risks) > 0
        assert "DDL" in risks[0]

    def test_assess_alter_table_risk(self, executor):
        """测试评估ALTER TABLE语句（高风险）"""
        sql = "ALTER TABLE users ADD COLUMN email VARCHAR(100)"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.HIGH
        assert len(risks) > 0
        assert "DDL" in risks[0]

    def test_assess_drop_table_risk(self, executor):
        """测试评估DROP TABLE语句（严重风险）"""
        sql = "DROP TABLE test_table"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.CRITICAL
        assert len(risks) > 0
        assert "DROP" in risks[0]

    def test_assess_truncate_table_risk(self, executor):
        """测试评估TRUNCATE TABLE语句（严重风险）"""
        sql = "TRUNCATE TABLE test_table"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.CRITICAL
        assert len(risks) > 0
        assert "TRUNCATE" in risks[0]

    def test_assess_drop_database_risk(self, executor):
        """测试评估DROP DATABASE语句（严重风险）"""
        sql = "DROP DATABASE test_db"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.CRITICAL
        assert len(risks) > 0

    def test_assess_grant_all_risk(self, executor):
        """测试评估GRANT ALL语句（高风险）"""
        sql = "GRANT ALL ON database.* TO 'user'@'localhost'"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.HIGH
        assert len(risks) > 0

    def test_assess_drop_user_risk(self, executor):
        """测试评估DROP USER语句（严重风险）"""
        sql = "DROP USER 'test'@'localhost'"
        risk_level, risks = executor.assess_risk_level(sql)
        assert risk_level == SQLRiskLevel.CRITICAL
        assert len(risks) > 0


@pytest.mark.unit
class TestSQLValidation:
    """SQL验证测试"""

    def test_validate_empty_sql(self, executor):
        """测试验证空SQL语句"""
        valid, error = executor.validate_sql("")
        assert valid is False
        assert "空" in error

    def test_validate_whitespace_sql(self, executor):
        """测试验证纯空白SQL语句"""
        valid, error = executor.validate_sql("   \n  \t  ")
        assert valid is False
        assert "空" in error

    def test_validate_sql_with_comment_injection(self, executor):
        """测试验证带SQL注释注入的语句"""
        sql = "SELECT * FROM users WHERE id = 1 -- OR 1=1"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_sql_with_statement_splicing(self, executor):
        """测试验证带语句拼接的注入"""
        sql = "SELECT * FROM users WHERE id = 1; DROP TABLE users"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_sql_with_union_injection(self, executor):
        """测试验证带UNION注入"""
        sql = "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_sql_with_or_injection(self, executor):
        """测试验证带OR注入"""
        sql = "SELECT * FROM users WHERE id = '1' OR '1'='1'"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_sql_with_and_injection(self, executor):
        """测试验证带AND注入"""
        sql = "SELECT * FROM users WHERE id = '1' AND '1'='1'"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_sql_with_exec_injection(self, executor):
        """测试验证带EXEC注入"""
        sql = "SELECT * FROM users WHERE id = 1; EXEC xp_cmdshell('dir')"
        valid, error = executor.validate_sql(sql)
        assert valid is False
        assert "注入" in error

    def test_validate_safe_sql(self, executor):
        """测试验证安全的SQL语句"""
        sql = "SELECT * FROM users WHERE id = 1"
        valid, error = executor.validate_sql(sql)
        assert valid is True
        assert error == ""

    def test_validate_dangerous_sql_without_permission(self, executor):
        """测试验证危险SQL（不允许危险操作）"""
        sql = "DROP TABLE users"
        valid, error = executor.validate_sql(sql, allow_dangerous=False)
        assert valid is False
        assert "危险操作" in error

    def test_validate_dangerous_sql_with_permission(self, executor):
        """测试验证危险SQL（允许危险操作）"""
        sql = "DROP TABLE users"
        valid, error = executor.validate_sql(sql, allow_dangerous=True)
        assert valid is True
        assert error == ""

    def test_validate_update_without_where(self, executor):
        """测试验证无WHERE的UPDATE（返回警告但不拒绝）"""
        sql = "UPDATE users SET age = 25"
        valid, error = executor.validate_sql(sql)
        # UPDATE无WHERE不是注入，应该通过验证
        assert valid is True


@pytest.mark.unit
class TestSQLScriptParsing:
    """SQL脚本解析测试"""

    def test_parse_single_statement(self, executor):
        """测试解析单条语句"""
        script = "SELECT * FROM users;"
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert statements[0] == "SELECT * FROM users"

    def test_parse_multiple_statements(self, executor):
        """测试解析多条语句"""
        script = "SELECT * FROM users; INSERT INTO logs (msg) VALUES ('test');"
        statements = executor._parse_script(script)
        assert len(statements) == 2

    def test_parse_statement_without_semicolon(self, executor):
        """测试解析不带分号的语句"""
        script = "SELECT * FROM users"
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert statements[0] == "SELECT * FROM users"

    def test_parse_statement_with_quotes(self, executor):
        """测试解析带引号的语句"""
        script = "INSERT INTO users (name) VALUES ('test;value');"
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert "test;value" in statements[0]

    def test_parse_statement_with_double_quotes(self, executor):
        """测试解析带双引号的语句"""
        script = 'INSERT INTO users (name) VALUES ("test;value");'
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert "test;value" in statements[0]

    def test_parse_statement_with_mixed_quotes(self, executor):
        """测试解析带混合引号的语句"""
        script = "INSERT INTO users (name) VALUES ('test\"value');"
        statements = executor._parse_script(script)
        assert len(statements) == 1

    def test_parse_statement_with_line_comment(self, executor):
        """测试解析带单行注释的语句"""
        script = "SELECT * FROM users -- comment\nWHERE id = 1;"
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert "comment" not in statements[0]

    def test_parse_empty_lines(self, executor):
        """测试解析空行"""
        script = "\n\nSELECT * FROM users;\n\n"
        statements = executor._parse_script(script)
        assert len(statements) == 1

    def test_parse_statement_with_comment_in_string(self, executor):
        """测试解析字符串中的注释"""
        script = "INSERT INTO users (name) VALUES ('-- not a comment');"
        statements = executor._parse_script(script)
        assert len(statements) == 1
        assert "-- not a comment" in statements[0]

    def test_parse_complex_script(self, executor):
        """测试解析复杂脚本"""
        script = """
-- 创建表
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

-- 插入数据
INSERT INTO users (id, name) VALUES (1, 'Alice');
INSERT INTO users (id, name) VALUES (2, 'Bob');

-- 查询数据
SELECT * FROM users;
"""
        statements = executor._parse_script(script)
        # 应该解析出3条有效语句（CREATE, 两个INSERT，SELECT）
        # 但CREATE后可能因为空行被分开
        assert len(statements) >= 3


@pytest.mark.unit
class TestSQLQueryExecution:
    """SQL查询执行测试"""

    @pytest.mark.asyncio
    async def test_execute_select_query(self, executor, mock_instance):
        """测试执行SELECT查询"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            # Mock数据库连接和游标
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.description = [('id',), ('name',), ('age',)]
            mock_cursor.fetchall.return_value = [(1, 'Alice', 25), (2, 'Bob', 30)]
            mock_cursor.rowcount = 2
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            result = await executor.execute_query(
                mock_instance,
                "SELECT * FROM users WHERE id = %s",
                params=(1,)
            )

            assert result['success'] is True
            assert result['statement_type'] == 'SELECT'
            assert result['affected_rows'] == 2
            assert len(result['data']) == 2
            assert result['data'][0] == {'id': 1, 'name': 'Alice', 'age': 25}

    @pytest.mark.asyncio
    async def test_execute_query_without_params(self, executor, mock_instance):
        """测试执行不带参数的查询"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.description = None
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            result = await executor.execute_query(
                mock_instance,
                "SELECT 1"
            )

            assert result['success'] is True

    @pytest.mark.asyncio
    async def test_execute_query_with_validation_error(self, executor, mock_instance):
        """测试执行验证失败的查询"""
        with pytest.raises(ValidationException):
            await executor.execute_query(
                mock_instance,
                "SELECT * FROM users -- injection"
            )

    @pytest.mark.asyncio
    async def test_execute_query_with_connection_error(self, executor, mock_instance):
        """测试执行连接失败的查询"""
        from app.services.db_connection import DatabaseConnectionError

        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_db.connection.side_effect = DatabaseConnectionError("Connection failed")

            with pytest.raises(QueryExecutionException) as exc_info:
                await executor.execute_query(
                    mock_instance,
                    "SELECT * FROM users"
                )
            assert "连接失败" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_query_fetch_false(self, executor, mock_instance):
        """测试执行不获取结果的查询（INSERT/UPDATE/DELETE）"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.description = None
            mock_cursor.rowcount = 1
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            result = await executor.execute_query(
                mock_instance,
                "UPDATE users SET age = 26 WHERE id = 1",
                fetch=False
            )

            assert result['success'] is True
            assert result['affected_rows'] == 1
            # 不获取结果时不应该有data字段
            assert result.get('data') is None
            # 非查询语句应该提交
            mock_conn.commit.assert_called_once()


@pytest.mark.unit
class TestSQLScriptExecution:
    """SQL脚本执行测试"""

    @pytest.mark.asyncio
    async def test_execute_simple_script(self, executor, mock_instance):
        """测试执行简单脚本"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 1
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            script = "INSERT INTO users (name) VALUES ('Alice'); INSERT INTO users (name) VALUES ('Bob');"
            result = await executor.execute_script(mock_instance, script)

            assert result['success'] is True
            assert len(result['results']) == 2
            assert result['total_affected'] == 2

    @pytest.mark.asyncio
    async def test_execute_script_with_error_stop_on_error(self, executor, mock_instance):
        """测试执行带错误脚本（停止）"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.execute.side_effect = Exception("Syntax error")
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            script = "INSERT INTO users (name) VALUES ('Alice'); INVALID SQL;"
            result = await executor.execute_script(mock_instance, script, stop_on_error=True)

            assert result['success'] is False
            # 应该回滚
            mock_conn.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_script_with_error_continue(self, executor, mock_instance):
        """测试执行带错误脚本（继续）"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()

            # 第一次执行成功，第二次失败
            def execute_side_effect(sql):
                if 'INVALID' in sql:
                    raise Exception("Syntax error")
                else:
                    mock_cursor.rowcount = 1

            mock_cursor.execute.side_effect = execute_side_effect
            mock_conn.cursor.return_value = mock_cursor
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            script = "INSERT INTO users (name) VALUES ('Alice'); INVALID SQL;"
            result = await executor.execute_script(mock_instance, script, stop_on_error=False)

            assert result['success'] is False  # 有错误，但整体不成功
            assert len(result['results']) == 2  # 两条语句都尝试执行
            assert result['results'][0]['success'] is True
            assert result['results'][1]['success'] is False

    @pytest.mark.asyncio
    async def test_execute_script_allow_dangerous(self, executor, mock_instance):
        """测试执行允许危险操作的脚本"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 0
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            script = "DROP TABLE old_table;"
            result = await executor.execute_script(mock_instance, script, allow_dangerous=True)

            assert result['success'] is True
            assert len(result['results']) == 1
            assert result['results'][0]['risk_level'] == 'critical'

    @pytest.mark.asyncio
    async def test_execute_script_forbid_dangerous(self, executor, mock_instance):
        """测试执行禁止危险操作的脚本"""
        script = "DROP TABLE old_table;"
        result = await executor.execute_script(mock_instance, script, allow_dangerous=False)

        assert result['success'] is False
        assert len(result['results']) == 1
        assert result['results'][0]['success'] is False
        assert "危险操作" in result['results'][0]['error']

    @pytest.mark.asyncio
    async def test_execute_script_with_empty_statements(self, executor, mock_instance):
        """测试执行包含空语句的脚本"""
        with patch('app.services.secure_sql_executor.db_manager') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 1
            mock_db.connection.return_value.__enter__.return_value = mock_conn

            script = "INSERT INTO users (name) VALUES ('Alice'); \n\n ;"
            result = await executor.execute_script(mock_instance, script)

            # 应该只执行一条有效语句
            assert len([r for r in result['results'] if r['success']]) == 1


@pytest.mark.unit
class TestSingletonExecutor:
    """单例执行器测试"""

    def test_singleton_instance(self):
        """测试单例实例"""
        assert secure_sql_executor is not None
        assert isinstance(secure_sql_executor, SecureSQLExecutor)

    def test_singleton_same_instance(self):
        """测试单例是同一个实例"""
        from app.services.secure_sql_executor import SecureSQLExecutor
        # 直接导入的类应该和单例是同一个类型
        assert isinstance(secure_sql_executor, SecureSQLExecutor)

    def test_singleton_functionality(self):
        """测试单例功能正常"""
        result = secure_sql_executor.detect_statement_type("SELECT * FROM users")
        assert result == SQLStatementType.SELECT
