"""
SQL执行器测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from app.services.sql_executor import SQLExecutor
from app.models import ApprovalRecord, RDBInstance


class TestSQLExecutor:
    """SQL执行器测试类"""

    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return SQLExecutor()

    @pytest.fixture
    def mock_instance(self):
        """创建模拟实例"""
        instance = Mock(spec=RDBInstance)
        instance.host = "localhost"
        instance.port = 3306
        instance.username = "root"
        instance.password_encrypted = "encrypted_pass"
        instance.db_type = "mysql"
        return instance

    @pytest.fixture
    def mock_approval(self):
        """创建模拟审批记录"""
        approval = Mock(spec=ApprovalRecord)
        approval.sql_content = "SELECT * FROM users"
        approval.sql_file_path = None
        approval.database_mode = "single"
        approval.database_name = "test_db"
        approval.database_list = None
        return approval

    def test_get_target_database_single_mode(self, executor, mock_approval):
        """测试获取单数据库模式的目标数据库"""
        mock_approval.database_mode = "single"
        mock_approval.database_name = "mydb"

        result = executor._get_target_database(mock_approval)

        assert result == "mydb"

    def test_get_target_database_multiple_mode(self, executor, mock_approval):
        """测试获取多数据库模式的目标数据库"""
        mock_approval.database_mode = "multiple"
        mock_approval.database_list = ["db1", "db2", "db3"]

        result = executor._get_target_database(mock_approval)

        assert result == "db1"  # 返回第一个

    def test_get_target_database_no_database(self, executor, mock_approval):
        """测试无数据库配置时返回None"""
        mock_approval.database_mode = "single"
        mock_approval.database_name = None

        result = executor._get_target_database(mock_approval)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_sql_content_from_approval(self, executor, mock_approval):
        """测试从审批记录获取SQL内容"""
        mock_approval.sql_content = "SELECT 1"
        mock_approval.sql_file_path = None

        result = await executor._get_sql_content(mock_approval)

        assert result == "SELECT 1"

    @pytest.mark.asyncio
    async def test_get_sql_content_from_file(self, executor, mock_approval):
        """测试从文件获取SQL内容"""
        mock_approval.sql_content = ""
        mock_approval.sql_file_path = "/path/to/sql.sql"

        with patch("app.services.sql_executor.storage_manager") as mock_storage:
            mock_storage.backend.read.return_value = "SELECT * FROM file"

            result = await executor._get_sql_content(mock_approval)

            assert result == "SELECT * FROM file"

    @pytest.mark.asyncio
    async def test_get_sql_content_file_not_found(self, executor, mock_approval):
        """测试SQL文件不存在"""
        mock_approval.sql_content = ""
        mock_approval.sql_file_path = "/path/to/missing.sql"

        with patch("app.services.sql_executor.storage_manager") as mock_storage:
            mock_storage.backend.read.side_effect = Exception("文件不存在")

            with pytest.raises(Exception, match="读取SQL文件失败"):
                await executor._get_sql_content(mock_approval)

    def test_is_query_statement_select(self, executor):
        """测试SELECT查询判断"""
        assert executor._is_query_statement("SELECT * FROM users") is True
        assert executor._is_query_statement("SELECT ID FROM ORDERS") is True

    def test_is_query_statement_show(self, executor):
        """测试SHOW查询判断"""
        assert executor._is_query_statement("SHOW TABLES") is True
        assert executor._is_query_statement("SHOW DATABASES") is True

    def test_is_query_statement_desc(self, executor):
        """测试DESC查询判断"""
        assert executor._is_query_statement("DESC users") is True
        assert executor._is_query_statement("DESCRIBE orders") is True

    def test_is_query_statement_explain(self, executor):
        """测试EXPLAIN查询判断"""
        assert executor._is_query_statement("EXPLAIN SELECT * FROM users") is True

    def test_is_query_statement_with(self, executor):
        """测试WITH查询判断"""
        assert executor._is_query_statement("WITH cte AS (SELECT 1) SELECT * FROM cte") is True

    def test_is_query_statement_dml(self, executor):
        """测试DML非查询判断"""
        assert executor._is_query_statement("INSERT INTO users VALUES (1)") is False
        assert executor._is_query_statement("UPDATE users SET name='test'") is False
        assert executor._is_query_statement("DELETE FROM users") is False

    def test_build_result_message_success(self, executor):
        """测试构建成功结果消息"""
        results = ["语句1: 成功, 影响10行", "语句2: 成功, 影响5行"]

        success, message, affected = executor._build_result_message(results, 15)

        assert success is True
        assert "成功2条" in message
        assert affected == 15

    def test_build_result_message_partial(self, executor):
        """测试构建部分成功结果消息"""
        results = ["语句1: 成功, 影响10行", "语句2: 失败 - 语法错误"]

        success, message, affected = executor._build_result_message(results, 10)

        assert success is False
        assert "成功1条" in message
        assert "失败1条" in message
        assert affected == 10

    def test_build_result_message_all_failed(self, executor):
        """测试构建全部失败结果消息"""
        results = ["语句1: 失败 - 错误1", "语句2: 失败 - 错误2"]

        success, message, affected = executor._build_result_message(results, 0)

        assert success is False
        assert "成功0条" in message
        assert "失败2条" in message
        assert affected == 0

    def test_build_result_message_empty(self, executor):
        """测试构建空结果消息"""
        results = []

        success, message, affected = executor._build_result_message(results, 0)

        assert success is True
        assert "无有效SQL" in message
        assert affected == 0

    @pytest.mark.asyncio
    async def test_execute_for_approval_mysql(self, executor, mock_approval, mock_instance):
        """测试执行MySQL审批SQL"""
        with patch.object(executor, '_execute_mysql') as mock_execute:
            mock_execute.return_value = (True, "执行成功", 10)

            with patch("app.services.sql_executor.decrypt_instance_password") as mock_decrypt:
                mock_decrypt.return_value = "plain_password"

                result = await executor.execute_for_approval(mock_approval, mock_instance)

                assert result == (True, "执行成功", 10)

    @pytest.mark.asyncio
    async def test_execute_for_approval_postgresql(self, executor, mock_approval, mock_instance):
        """测试执行PostgreSQL审批SQL"""
        mock_instance.db_type = "postgresql"

        with patch.object(executor, '_execute_postgresql') as mock_execute:
            mock_execute.return_value = (True, "执行成功", 10)

            with patch("app.services.sql_executor.decrypt_instance_password") as mock_decrypt:
                mock_decrypt.return_value = "plain_password"

                result = await executor.execute_for_approval(mock_approval, mock_instance)

                assert result == (True, "执行成功", 10)

    @pytest.mark.asyncio
    async def test_execute_for_approval_decrypt_failed(self, executor, mock_approval, mock_instance):
        """测试密码解密失败"""
        with patch("app.services.sql_executor.decrypt_instance_password") as mock_decrypt:
            mock_decrypt.side_effect = ValueError("解密失败")

            success, message, affected = await executor.execute_for_approval(mock_approval, mock_instance)

            assert success is False
            assert "密码解密失败" in message
            assert affected == 0

    @pytest.mark.asyncio
    async def test_execute_for_approval_empty_sql(self, executor, mock_approval, mock_instance):
        """测试空SQL内容"""
        mock_approval.sql_content = ""
        mock_approval.sql_file_path = None

        with patch("app.services.sql_executor.decrypt_instance_password") as mock_decrypt:
            mock_decrypt.return_value = "plain_password"

            success, message, affected = await executor.execute_for_approval(mock_approval, mock_instance)

            assert success is True
            assert "无有效SQL" in message
            assert affected == 0

    def test_is_query_statement_ddl(self, executor):
        """测试DDL非查询判断"""
        assert executor._is_query_statement("CREATE TABLE users (id INT)") is False
        assert executor._is_query_statement("ALTER TABLE users ADD COLUMN name VARCHAR(50)") is False
        assert executor._is_query_statement("DROP TABLE users") is False

    def test_check_execution_success(self, executor):
        """测试检查执行结果是否成功"""
        assert executor.check_execution_success("执行完成: 成功2条, 失败0条, 共影响10行") is True
        assert executor.check_execution_success("执行完成: 成功1条, 失败1条, 共影响5行") is False
        assert executor.check_execution_success("执行完成: 成功0条, 失败2条, 共影响0行") is False
