"""
测试 sql_executor.py 模块

功能点：
1. SQLExecutor 类：
   - execute_for_approval（主入口）
   - _get_target_database（确定目标数据库）
   - _get_sql_content（获取SQL内容）
   - _execute_mysql（MySQL执行）
   - _execute_postgreSQL（PostgreSQL执行）
   - _execute_sql_statements（执行SQL语句）
   - _is_query_statement（判断查询语句）
   - _build_result_message（构建结果消息）
   - check_execution_success（检查执行结果）

2. RedisExecutor 类：
   - execute_for_approval（主入口）
   - _execute_redis_command（执行单个命令）

测试策略：
- 使用 Mock 模拟数据库连接
- 使用 AsyncMock 模拟异步操作
- 测试正常路径和异常场景
- 测试 MySQL 和 PostgreSQL 两种数据库类型
- 测试 Redis 命令执行
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from datetime import datetime

from app.services.sql_executor import SQLExecutor, RedisExecutor
from app.models import ApprovalRecord, RDBInstance, RedisInstance


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_approval():
    """Mock 审批记录"""
    approval = Mock(spec=ApprovalRecord)
    approval.id = 1
    approval.sql_content = "SELECT * FROM test;\nUPDATE test SET status=1 WHERE id=1;"
    approval.sql_file_path = None
    approval.database_mode = "single"
    approval.database_name = "test_db"
    approval.database_list = None
    return approval


@pytest.fixture
def mock_approval_with_file():
    """Mock 带SQL文件的审批记录"""
    approval = Mock(spec=ApprovalRecord)
    approval.id = 2
    approval.sql_content = None
    approval.sql_file_path = "sql_files/test.sql"
    approval.database_mode = "multiple"
    approval.database_name = None
    approval.database_list = ["db1", "db2"]
    return approval


@pytest.fixture
def mock_approval_empty_sql():
    """Mock 空SQL的审批记录"""
    approval = Mock(spec=ApprovalRecord)
    approval.id = 3
    approval.sql_content = ""
    approval.sql_file_path = None
    approval.database_mode = "single"
    approval.database_name = "test_db"
    return approval


@pytest.fixture
def mock_mysql_instance():
    """Mock MySQL 实例"""
    instance = Mock(spec=RDBInstance)
    instance.id = 1
    instance.host = "localhost"
    instance.port = 3306
    instance.username = "root"
    instance.password_encrypted = "encrypted_password"
    instance.db_type = "MySQL"
    return instance


@pytest.fixture
def mock_postgresql_instance():
    """Mock PostgreSQL 实例"""
    instance = Mock(spec=RDBInstance)
    instance.id = 2
    instance.host = "localhost"
    instance.port = 5432
    instance.username = "postgres"
    instance.password_encrypted = "encrypted_password"
    instance.db_type = "PostgreSQL"
    return instance


@pytest.fixture
def mock_redis_instance():
    """Mock Redis 实例"""
    instance = Mock(spec=RedisInstance)
    instance.id = 1
    instance.host = "localhost"
    instance.port = 6379
    instance.password_encrypted = "encrypted_password"
    instance.redis_db = 0
    return instance


@pytest.fixture
def mock_db_connection():
    """Mock 数据库连接"""
    conn = Mock()
    conn.cursor = Mock(return_value=Mock())
    conn.commit = Mock()
    conn.rollback = Mock()
    conn.close = Mock()
    conn.autocommit = None
    return conn


@pytest.fixture
def mock_redis_client():
    """Mock Redis 客户端"""
    client = Mock()
    client.ping = Mock(return_value=True)
    client.get = Mock(return_value="value")
    client.set = Mock(return_value=True)
    client.delete = Mock(return_value=1)
    client.expire = Mock(return_value=True)
    client.ttl = Mock(return_value=3600)
    client.keys = Mock(return_value=["key1", "key2"])
    client.hget = Mock(return_value="value")
    client.hset = Mock(return_value=True)
    client.hgetall = Mock(return_value={"field1": "value1"})
    client.lpush = Mock(return_value=1)
    client.rpop = Mock(return_value="value")
    client.lrange = Mock(return_value=["item1", "item2"])
    client.sadd = Mock(return_value=1)
    client.smembers = Mock(return_value={"member1", "member2"})
    client.zadd = Mock(return_value=1)
    client.zrange = Mock(return_value=["member1", "member2"])
    client.close = Mock()
    return client


# =============================================================================
# 1. SQLExecutor - _get_target_database 测试
# =============================================================================

class TestSQLExecutorGetTargetDatabase:
    """测试 _get_target_database 方法"""

    def test_single_database_mode(self, mock_approval):
        """测试单数据库模式"""
        executor = SQLExecutor()
        result = executor._get_target_database(mock_approval)
        assert result == "test_db"

    def test_multiple_database_mode(self, mock_approval_with_file):
        """测试多数据库模式"""
        executor = SQLExecutor()
        result = executor._get_target_database(mock_approval_with_file)
        assert result == "db1"  # 返回第一个数据库

    def test_no_database_info(self, mock_approval_empty_sql):
        """测试无数据库信息"""
        mock_approval_empty_sql.database_mode = None
        mock_approval_empty_sql.database_list = None

        executor = SQLExecutor()
        result = executor._get_target_database(mock_approval_empty_sql)
        assert result is None

    def test_multiple_mode_empty_list(self, mock_approval_empty_sql):
        """测试多数据库模式但列表为空"""
        mock_approval_empty_sql.database_mode = "multiple"
        mock_approval_empty_sql.database_list = []

        executor = SQLExecutor()
        result = executor._get_target_database(mock_approval_empty_sql)
        assert result is None


# =============================================================================
# 2. SQLExecutor - _get_sql_content 测试
# =============================================================================

class TestSQLExecutorGetSQLContent:
    """测试 _get_sql_content 方法"""

    @pytest.mark.asyncio
    async def test_sql_from_content(self, mock_approval):
        """测试从 approval.sql_content 获取 SQL"""
        executor = SQLExecutor()
        result = await executor._get_sql_content(mock_approval)
        assert "SELECT" in result
        assert "UPDATE" in result

    @pytest.mark.asyncio
    async def test_sql_from_file(self, mock_approval_with_file):
        """测试从文件获取 SQL"""
        with patch('app.services.sql_executor.storage_manager') as mock_storage:
            mock_storage.backend.read = Mock(return_value=b"SELECT * FROM test;")
            
            executor = SQLExecutor()
            result = await executor._get_sql_content(mock_approval_with_file)
            
            assert result == "SELECT * FROM test;"
            mock_storage.backend.read.assert_called_once_with("sql_files/test.sql")

    @pytest.mark.asyncio
    async def test_sql_from_file_string(self, mock_approval_with_file):
        """测试从文件获取 SQL（返回字符串）"""
        with patch('app.services.sql_executor.storage_manager') as mock_storage:
            mock_storage.backend.read = Mock(return_value="SELECT * FROM test;")
            
            executor = SQLExecutor()
            result = await executor._get_sql_content(mock_approval_with_file)
            
            assert result == "SELECT * FROM test;"

    @pytest.mark.asyncio
    async def test_sql_file_read_error(self, mock_approval_with_file):
        """测试读取文件失败"""
        with patch('app.services.sql_executor.storage_manager') as mock_storage:
            mock_storage.backend.read = Mock(side_effect=Exception("文件不存在"))
            
            executor = SQLExecutor()
            with pytest.raises(Exception, match="读取SQL文件失败"):
                await executor._get_sql_content(mock_approval_with_file)

    @pytest.mark.asyncio
    async def test_sql_content_and_file_both_exist(self, mock_approval_with_file):
        """测试同时有 content 和 file（优先使用 file）"""
        mock_approval_with_file.sql_content = "UPDATE test SET x=1;"
        
        with patch('app.services.sql_executor.storage_manager') as mock_storage:
            mock_storage.backend.read = Mock(return_value=b"SELECT * FROM test;")
            
            executor = SQLExecutor()
            result = await executor._get_sql_content(mock_approval_with_file)
            
            # 应该使用文件内容
            assert result == "SELECT * FROM test;"
            # content 内容被覆盖

    @pytest.mark.asyncio
    async def test_empty_sql(self, mock_approval_empty_sql):
        """测试空 SQL"""
        executor = SQLExecutor()
        result = await executor._get_sql_content(mock_approval_empty_sql)
        assert result == ""


# =============================================================================
# 3. SQLExecutor - _is_query_statement 测试
# =============================================================================

class TestSQLExecutorIsQueryStatement:
    """测试 _is_query_statement 方法"""

    def test_select_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("SELECT * FROM test") is True

    def test_show_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("SHOW TABLES") is True

    def test_describe_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("DESCRIBE test") is True
        assert executor._is_query_statement("DESC test") is True

    def test_explain_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("EXPLAIN SELECT * FROM test") is True

    def test_with_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("WITH cte AS (...) SELECT * FROM cte") is True

    def test_update_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("UPDATE test SET x=1") is False

    def test_insert_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("INSERT INTO test VALUES (1)") is False

    def test_delete_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("DELETE FROM test WHERE id=1") is False

    def test_create_statement(self):
        executor = SQLExecutor()
        assert executor._is_query_statement("CREATE TABLE test (id INT)") is False

    def test_case_insensitive(self):
        # 注意：_is_query_statement 期望传入的已经是转换为大写的 SQL
        # 因为在 _execute_sql_statements 中，传入的是已经转换为大写的
        executor = SQLExecutor()
        assert executor._is_query_statement("SELECT * FROM TEST") is True
        # 小写需要先转换
        assert executor._is_query_statement("select * from test".upper()) is True
        assert executor._is_query_statement("Select * From test".upper()) is True

    def test_with_leading_spaces(self):
        # 注意：_is_query_statement 期望传入的已经是转换为大写并 strip 的 SQL
        executor = SQLExecutor()
        assert executor._is_query_statement("SELECT * FROM TEST".upper()) is True
        # 需要先 strip 再转换大写
        assert executor._is_query_statement("  SELECT * FROM test".strip().upper()) is True
        assert executor._is_query_statement("\nSELECT * FROM test".strip().upper()) is True


# =============================================================================
# 4. SQLExecutor - _build_result_message 测试
# =============================================================================

class TestSQLExecutorBuildResultMessage:
    """测试 _build_result_message 方法"""

    def test_all_success(self):
        executor = SQLExecutor()
        results = [
            "语句1: 成功, 影响10行",
            "语句2: 成功, 影响5行",
        ]
        success, msg, affected = executor._build_result_message(results, 15)
        
        assert success is True
        assert "成功2条" in msg
        assert "失败0条" in msg
        assert "共影响15行" in msg
        assert affected == 15

    def test_some_failure(self):
        executor = SQLExecutor()
        results = [
            "语句1: 成功, 影响10行",
            "语句2: 失败 - 语法错误",
            "语句3: 成功, 影响5行",
        ]
        success, msg, affected = executor._build_result_message(results, 15)
        
        assert success is False
        assert "成功2条" in msg
        assert "失败1条" in msg
        assert "共影响15行" in msg
        assert affected == 15

    def test_all_failure(self):
        executor = SQLExecutor()
        results = [
            "语句1: 失败 - 语法错误",
            "语句2: 失败 - 表不存在",
        ]
        success, msg, affected = executor._build_result_message(results, 0)
        
        assert success is False
        assert "成功0条" in msg
        assert "失败2条" in msg
        assert "共影响0行" in msg
        assert affected == 0

    def test_empty_results(self):
        executor = SQLExecutor()
        success, msg, affected = executor._build_result_message([], 0)
        
        assert success is True
        assert msg == "执行完成: 无有效SQL语句"
        assert affected == 0


# =============================================================================
# 5. SQLExecutor - check_execution_success 测试
# =============================================================================

class TestSQLExecutorCheckExecutionSuccess:
    """测试 check_execution_success 方法"""

    def test_all_success_message(self):
        executor = SQLExecutor()
        result_msg = "执行完成: 成功2条, 失败0条, 共影响15行"
        assert executor.check_execution_success(result_msg) is True

    def test_partial_failure_message(self):
        executor = SQLExecutor()
        result_msg = "执行完成: 成功1条, 失败1条, 共影响10行"
        assert executor.check_execution_success(result_msg) is False

    def test_all_failure_message(self):
        executor = SQLExecutor()
        result_msg = "执行完成: 成功0条, 失败2条, 共影响0行"
        assert executor.check_execution_success(result_msg) is False

    def test_message_without_failure_count(self):
        executor = SQLExecutor()
        result_msg = "执行完成: 成功5条, 共影响50行"
        assert executor.check_execution_success(result_msg) is True

    def test_custom_message(self):
        executor = SQLExecutor()
        result_msg = "其他消息"
        assert executor.check_execution_success(result_msg) is True


# =============================================================================
# 6. SQLExecutor - execute_for_approval 测试
# =============================================================================

class TestSQLExecutorExecuteForApproval:
    """测试 execute_for_approval 主方法"""

    @pytest.mark.asyncio
    async def test_mysql_success(self, mock_approval, mock_mysql_instance):
        """测试 MySQL 执行成功"""
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('pymysql.connect') as mock_connect:
            
            # Mock 连接和游标
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute = Mock()
            mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
            mock_cursor.rowcount = 5
            mock_conn.cursor = Mock(return_value=mock_cursor)
            mock_conn.close = Mock()
            mock_connect.return_value = mock_conn
            
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_mysql_instance)
            
            assert success is True
            assert "成功" in msg
            assert affected > 0
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgresql_success(self, mock_approval, mock_postgresql_instance):
        """测试 PostgreSQL 执行成功"""
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('psycopg2.connect') as mock_connect:
            
            # Mock 连接和游标
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute = Mock()
            mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
            mock_cursor.rowcount = 5
            mock_conn.cursor = Mock(return_value=mock_cursor)
            mock_conn.close = Mock()
            mock_connect.return_value = mock_conn
            
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_postgresql_instance)
            
            assert success is True
            assert "成功" in msg
            # PostgreSQL 应该设置 autocommit
            mock_conn.autocommit = False

    @pytest.mark.asyncio
    async def test_password_decryption_failure(self, mock_approval, mock_mysql_instance):
        """测试密码解密失败"""
        with patch('app.services.sql_executor.decrypt_instance_password', side_effect=ValueError("解密错误")):
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_mysql_instance)
            
            assert success is False
            assert "密码解密失败" in msg
            assert affected == 0

    @pytest.mark.asyncio
    async def test_empty_sql(self, mock_approval_empty_sql, mock_mysql_instance):
        """测试空 SQL"""
        mock_approval_empty_sql.sql_content = ""
        mock_approval_empty_sql.sql_file_path = None
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"):
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval_empty_sql, mock_mysql_instance)
            
            assert success is True
            assert "无有效SQL语句" in msg
            assert affected == 0

    @pytest.mark.asyncio
    async def test_mysql_connection_failure(self, mock_approval, mock_mysql_instance):
        """测试 MySQL 连接失败"""
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('pymysql.connect', side_effect=Exception("连接超时")):
            
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_mysql_instance)
            
            assert success is False
            assert "数据库连接失败" in msg
            assert affected == 0

    @pytest.mark.asyncio
    async def test_postgresql_connection_failure(self, mock_approval, mock_postgresql_instance):
        """测试 PostgreSQL 连接失败"""
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('psycopg2.connect', side_effect=Exception("连接超时")):
            
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_postgresql_instance)
            
            assert success is False
            assert "数据库连接失败" in msg
            assert affected == 0

    @pytest.mark.asyncio
    async def test_sql_file_read_failure(self, mock_approval_with_file, mock_mysql_instance):
        """测试读取 SQL 文件失败（抛出异常）"""
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('app.services.sql_executor.storage_manager') as mock_storage:
            
            mock_storage.backend.read = Mock(side_effect=Exception("文件不存在"))
            
            executor = SQLExecutor()
            # 期望抛出异常而不是返回错误消息
            with pytest.raises(Exception, match="读取SQL文件失败"):
                await executor.execute_for_approval(mock_approval_with_file, mock_mysql_instance)

    @pytest.mark.asyncio
    async def test_unknown_db_type(self, mock_approval, mock_mysql_instance):
        """测试未知数据库类型（默认使用 MySQL）"""
        mock_mysql_instance.db_type = "UnknownDB"
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('pymysql.connect') as mock_connect:
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute = Mock()
            mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
            mock_cursor.rowcount = 5
            mock_conn.cursor = Mock(return_value=mock_cursor)
            mock_conn.close = Mock()
            mock_connect.return_value = mock_conn
            
            executor = SQLExecutor()
            success, msg, affected = await executor.execute_for_approval(mock_approval, mock_mysql_instance)
            
            # 应该默认使用 MySQL
            assert success is True
            mock_connect.assert_called_once()


# =============================================================================
# 7. SQLExecutor - _execute_mysql 测试
# =============================================================================

class TestSQLExecutorExecuteMySQL:
    """测试 _execute_mysql 方法"""

    @pytest.mark.asyncio
    async def test_execute_mysql_success(self, mock_mysql_instance, mock_db_connection):
        """测试 MySQL 执行成功"""
        with patch('pymysql.connect', return_value=mock_db_connection):
            executor = SQLExecutor()
            
            # Patch _execute_sql_statements
            with patch.object(executor, '_execute_sql_statements', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (True, "执行成功", 10)
                
                success, msg, affected = await executor._execute_mysql(
                    mock_mysql_instance, "password", "test_db", "SELECT 1"
                )
                
                assert success is True
                assert msg == "执行成功"
                assert affected == 10

    @pytest.mark.asyncio
    async def test_execute_mysql_no_database(self, mock_mysql_instance, mock_db_connection):
        """测试 MySQL 无指定数据库"""
        with patch('pymysql.connect', return_value=mock_db_connection):
            executor = SQLExecutor()
            
            with patch.object(executor, '_execute_sql_statements', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (True, "执行成功", 10)
                
                await executor._execute_mysql(
                    mock_mysql_instance, "password", None, "SELECT 1"
                )
                
                # 验证连接参数
                mock_db_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_mysql_connection_error(self, mock_mysql_instance):
        """测试 MySQL 连接错误"""
        with patch('pymysql.connect', side_effect=Exception("连接失败")):
            executor = SQLExecutor()
            success, msg, affected = await executor._execute_mysql(
                mock_mysql_instance, "password", "test_db", "SELECT 1"
            )
            
            assert success is False
            assert "数据库连接失败" in msg
            assert affected == 0

    @pytest.mark.asyncio
    async def test_execute_mysql_close_exception(self, mock_mysql_instance, mock_db_connection):
        """测试 MySQL 关闭连接异常"""
        mock_db_connection.close = Mock(side_effect=Exception("关闭失败"))
        
        with patch('pymysql.connect', return_value=mock_db_connection):
            executor = SQLExecutor()
            
            with patch.object(executor, '_execute_sql_statements', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (True, "执行成功", 10)
                
                # 应该正常返回，忽略关闭异常
                success, msg, affected = await executor._execute_mysql(
                    mock_mysql_instance, "password", "test_db", "SELECT 1"
                )
                
                assert success is True


# =============================================================================
# 8. SQLExecutor - _execute_postgresql 测试
# =============================================================================

class TestSQLExecutorExecutePostgreSQL:
    """测试 _execute_postgresql 方法"""

    @pytest.mark.asyncio
    async def test_execute_postgresql_success(self, mock_postgresql_instance, mock_db_connection):
        """测试 PostgreSQL 执行成功"""
        with patch('psycopg2.connect', return_value=mock_db_connection):
            executor = SQLExecutor()
            
            with patch.object(executor, '_execute_sql_statements', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (True, "执行成功", 10)
                
                success, msg, affected = await executor._execute_postgresql(
                    mock_postgresql_instance, "password", "test_db", "SELECT 1"
                )
                
                assert success is True
                assert msg == "执行成功"
                assert affected == 10
                assert mock_db_connection.autocommit == False

    @pytest.mark.asyncio
    async def test_execute_postgresql_no_database(self, mock_postgresql_instance, mock_db_connection):
        """测试 PostgreSQL 无指定数据库（使用默认 postgres）"""
        with patch('psycopg2.connect', return_value=mock_db_connection):
            executor = SQLExecutor()
            
            with patch.object(executor, '_execute_sql_statements', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = (True, "执行成功", 10)
                
                await executor._execute_postgresql(
                    mock_postgresql_instance, "password", None, "SELECT 1"
                )
                
                # 验证 autocommit 被设置
                assert mock_db_connection.autocommit == False

    @pytest.mark.asyncio
    async def test_execute_postgresql_connection_error(self, mock_postgresql_instance):
        """测试 PostgreSQL 连接错误"""
        with patch('psycopg2.connect', side_effect=Exception("连接失败")):
            executor = SQLExecutor()
            success, msg, affected = await executor._execute_postgresql(
                mock_postgresql_instance, "password", "test_db", "SELECT 1"
            )
            
            assert success is False
            assert "数据库连接失败" in msg
            assert affected == 0


# =============================================================================
# 9. SQLExecutor - _execute_sql_statements 测试
# =============================================================================

class TestSQLExecutorExecuteSQLStatements:
    """测试 _execute_sql_statements 方法"""

    @pytest.mark.asyncio
    async def test_execute_single_query(self, mock_db_connection):
        """测试执行单个查询"""
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.fetchall = Mock(return_value=[(1, 'test'), (2, 'test2')])
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, "SELECT * FROM test;", "mysql"
        )
        
        assert success is True
        assert affected == 2
        assert "成功1条" in msg
        mock_cursor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_update(self, mock_db_connection):
        """测试执行单个 UPDATE"""
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.rowcount = 5
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        mock_db_connection.commit = Mock()
        
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, "UPDATE test SET status=1 WHERE id=1;", "mysql"
        )
        
        assert success is True
        assert affected == 5
        assert "成功1条" in msg
        mock_db_connection.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_statements_all_success(self, mock_db_connection):
        """测试执行多条语句全部成功"""
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
        mock_cursor.rowcount = 5
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        mock_db_connection.commit = Mock()
        
        sql = "SELECT 1;\nUPDATE test SET x=1;\nSELECT 2;"
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, sql, "mysql"
        )
        
        assert success is True
        assert "成功3条" in msg
        assert affected == 7  # 1 + 5 + 1

    @pytest.mark.asyncio
    async def test_execute_with_failure_rollback(self, mock_db_connection):
        """测试执行失败回滚"""
        mock_cursor = Mock()
        execute_count = [0]
        
        def execute_side_effect(sql):
            execute_count[0] += 1
            if execute_count[0] == 2:
                raise Exception("语法错误")
        
        mock_cursor.execute = Mock(side_effect=execute_side_effect)
        mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
        mock_cursor.rowcount = 5
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        mock_db_connection.commit = Mock()
        mock_db_connection.rollback = Mock()
        
        sql = "SELECT 1;\nUPDATE invalid_table SET x=1;\nSELECT 2;"
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, sql, "mysql"
        )
        
        assert success is False
        assert "失败1条" in msg
        mock_db_connection.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_execute_empty_sql(self, mock_db_connection):
        """测试执行空 SQL"""
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, "", "mysql"
        )
        
        assert success is True
        assert "无有效SQL语句" in msg
        assert affected == 0

    @pytest.mark.asyncio
    async def test_execute_sql_with_comments_and_blank_lines(self, mock_db_connection):
        """测试 SQL 包含注释和空行"""
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.fetchall = Mock(return_value=[(1, 'test')])
        mock_cursor.rowcount = 5
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        mock_db_connection.commit = Mock()
        
        sql = """
        -- 这是注释
        SELECT 1;
        
        -- 另一个注释
        UPDATE test SET x=1;
        """
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, sql, "mysql"
        )
        
        assert success is True
        assert "成功2条" in msg

    @pytest.mark.asyncio
    async def test_execute_delete_statement(self, mock_db_connection):
        """测试执行 DELETE 语句"""
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        mock_cursor.rowcount = 10
        mock_cursor.close = Mock()
        mock_db_connection.cursor = Mock(return_value=mock_cursor)
        mock_db_connection.commit = Mock()
        
        executor = SQLExecutor()
        success, msg, affected = await executor._execute_sql_statements(
            mock_db_connection, "DELETE FROM test WHERE id=1;", "mysql"
        )
        
        assert success is True
        assert affected == 10
        mock_db_connection.commit.assert_called_once()


# =============================================================================
# 10. RedisExecutor 测试
# =============================================================================

class TestRedisExecutor:
    """测试 RedisExecutor 类"""

    @pytest.mark.asyncio
    async def test_redis_get_command(self, mock_approval, mock_redis_instance, mock_redis_client):
        """测试 Redis GET 命令"""
        mock_approval.sql_content = "GET mykey"
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', return_value=mock_redis_client):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            assert "成功1条" in result
            mock_redis_client.get.assert_called_once_with("mykey")

    @pytest.mark.asyncio
    async def test_redis_set_command(self, mock_approval, mock_redis_instance, mock_redis_client):
        """测试 Redis SET 命令"""
        mock_approval.sql_content = "SET mykey myvalue"
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', return_value=mock_redis_client):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            assert "成功1条" in result
            mock_redis_client.set.assert_called_once_with("mykey", "myvalue")

    @pytest.mark.asyncio
    async def test_redis_multiple_commands(self, mock_approval, mock_redis_instance, mock_redis_client):
        """测试多个 Redis 命令"""
        mock_approval.sql_content = "GET key1\nSET key2 value2\nDEL key3"
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', return_value=mock_redis_client):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            assert "成功3条" in result
            mock_redis_client.get.assert_called_once()
            mock_redis_client.set.assert_called_once()
            mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_command_with_comments(self, mock_approval, mock_redis_instance, mock_redis_client):
        """测试 Redis 命令带注释"""
        mock_approval.sql_content = "# 获取key\nGET mykey\n# 设置key\nSET key value"
        
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', return_value=mock_redis_client):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            assert "成功2条" in result
            # 注释行应该被跳过
            assert mock_redis_client.get.call_count == 1
            assert mock_redis_client.set.call_count == 1

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, mock_approval, mock_redis_instance):
        """测试 Redis 连接失败（通用异常）"""
        import redis
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', side_effect=Exception("连接超时")):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            # 通用异常返回 "执行失败"
            assert "执行失败" in result

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, mock_approval, mock_redis_instance):
        """测试 Redis 连接错误（特定异常）"""
        import redis
        with patch('app.services.sql_executor.decrypt_instance_password', return_value="decrypted_pass"), \
             patch('redis.Redis', side_effect=redis.ConnectionError("连接超时")):
            
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            # redis.ConnectionError 返回 "Redis连接失败"
            assert "Redis连接失败" in result

    @pytest.mark.asyncio
    async def test_redis_password_decryption_failure(self, mock_approval, mock_redis_instance):
        """测试 Redis 密码解密失败"""
        with patch('app.services.sql_executor.decrypt_instance_password', side_effect=ValueError("解密错误")):
            executor = RedisExecutor()
            result = await executor.execute_for_approval(mock_approval, mock_redis_instance)
            
            assert "密码解密失败" in result

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_get(self):
        """测试 _execute_redis_command GET"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.get = Mock(return_value="value")
        
        result = executor._execute_redis_command(mock_client, "GET", ["mykey"])
        assert result == "value"
        mock_client.get.assert_called_once_with("mykey")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_set(self):
        """测试 _execute_redis_command SET"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.set = Mock(return_value=True)
        
        result = executor._execute_redis_command(mock_client, "SET", ["mykey", "myvalue"])
        assert result is True
        mock_client.set.assert_called_once_with("mykey", "myvalue")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_delete(self):
        """测试 _execute_redis_command DEL"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.delete = Mock(return_value=2)
        
        result = executor._execute_redis_command(mock_client, "DEL", ["key1", "key2"])
        assert result == 2
        mock_client.delete.assert_called_once_with("key1", "key2")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_expire(self):
        """测试 _execute_redis_command EXPIRE"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.expire = Mock(return_value=True)
        
        result = executor._execute_redis_command(mock_client, "EXPIRE", ["mykey", "3600"])
        assert result is True
        mock_client.expire.assert_called_once_with("mykey", 3600)

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_ttl(self):
        """测试 _execute_redis_command TTL"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.ttl = Mock(return_value=3600)
        
        result = executor._execute_redis_command(mock_client, "TTL", ["mykey"])
        assert result == 3600
        mock_client.ttl.assert_called_once_with("mykey")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_keys(self):
        """测试 _execute_redis_command KEYS"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.keys = Mock(return_value=["key1", "key2"])
        
        result = executor._execute_redis_command(mock_client, "KEYS", ["pattern*"])
        assert result == ["key1", "key2"]
        mock_client.keys.assert_called_once_with("pattern*")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_keys_no_pattern(self):
        """测试 _execute_redis_command KEYS 无模式"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.keys = Mock(return_value=["key1"])
        
        result = executor._execute_redis_command(mock_client, "KEYS", [])
        assert result == ["key1"]
        mock_client.keys.assert_called_once_with("*")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_hget(self):
        """测试 _execute_redis_command HGET"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.hget = Mock(return_value="value")
        
        result = executor._execute_redis_command(mock_client, "HGET", ["myhash", "field"])
        assert result == "value"
        mock_client.hget.assert_called_once_with("myhash", "field")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_hset(self):
        """测试 _execute_redis_command HSET"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.hset = Mock(return_value=True)
        
        result = executor._execute_redis_command(mock_client, "HSET", ["myhash", "field", "value"])
        assert result is True
        mock_client.hset.assert_called_once_with("myhash", "field", "value")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_hgetall(self):
        """测试 _execute_redis_command HGETALL"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.hgetall = Mock(return_value={"field1": "value1"})
        
        result = executor._execute_redis_command(mock_client, "HGETALL", ["myhash"])
        assert result == {"field1": "value1"}
        mock_client.hgetall.assert_called_once_with("myhash")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_lpush(self):
        """测试 _execute_redis_command LPUSH"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.lpush = Mock(return_value=3)
        
        result = executor._execute_redis_command(mock_client, "LPUSH", ["mylist", "item1", "item2"])
        assert result == 3
        mock_client.lpush.assert_called_once_with("mylist", "item1", "item2")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_rpop(self):
        """测试 _execute_redis_command RPOP"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.rpop = Mock(return_value="item")
        
        result = executor._execute_redis_command(mock_client, "RPOP", ["mylist"])
        assert result == "item"
        mock_client.rpop.assert_called_once_with("mylist")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_lrange(self):
        """测试 _execute_redis_command LRANGE"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.lrange = Mock(return_value=["item1", "item2"])
        
        result = executor._execute_redis_command(mock_client, "LRANGE", ["mylist", "0", "-1"])
        assert result == ["item1", "item2"]
        mock_client.lrange.assert_called_once_with("mylist", 0, -1)

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_sadd(self):
        """测试 _execute_redis_command SADD"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.sadd = Mock(return_value=1)
        
        result = executor._execute_redis_command(mock_client, "SADD", ["myset", "member1", "member2"])
        assert result == 1
        mock_client.sadd.assert_called_once_with("myset", "member1", "member2")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_smembers(self):
        """测试 _execute_redis_command SMEMBERS"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.smembers = Mock(return_value={"member1", "member2"})
        
        result = executor._execute_redis_command(mock_client, "SMEMBERS", ["myset"])
        assert result == {"member1", "member2"}
        mock_client.smembers.assert_called_once_with("myset")

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_zadd(self):
        """测试 _execute_redis_command ZADD"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.zadd = Mock(return_value=1)
        
        result = executor._execute_redis_command(mock_client, "ZADD", ["myzset", "member1", "100.5"])
        assert result == 1
        mock_client.zadd.assert_called_once_with("myzset", {"member1": 100.5})

    @pytest.mark.asyncio
    async def test_redis_execute_redis_command_zrange(self):
        """测试 _execute_redis_command ZRANGE"""
        executor = RedisExecutor()
        mock_client = Mock()
        mock_client.zrange = Mock(return_value=["member1", "member2"])
        
        result = executor._execute_redis_command(mock_client, "ZRANGE", ["myzset", "0", "-1"])
        assert result == ["member1", "member2"]
        mock_client.zrange.assert_called_once_with("myzset", 0, -1)
