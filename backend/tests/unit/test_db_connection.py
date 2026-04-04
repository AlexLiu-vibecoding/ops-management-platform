"""
测试数据库连接服务 - Database Connection Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call

# 提前导入用于 patch 的类
from app.services.db_connection import DatabaseConnectionManager, DatabaseConnectionError, DatabaseExecutionError, db_manager


# 重新定义导入函数以避免重复导入
def get_db_manager():
    # DatabaseConnectionManager already imported at top
    return DatabaseConnectionManager()  # 这是一个方法级别的 fixture，每次调用都创建新实例


class TestDatabaseConnectionErrorClass:
    """测试数据库连接异常"""


class TestDatabaseConnectionErrorClass:
    """测试数据库连接异常"""
    
    def test_connection_error(self):
        """测试连接异常"""
        error = DatabaseConnectionError("Connection failed")
        assert str(error) == "Connection failed"
    
    def test_execution_error(self):
        """测试执行异常"""
        error = DatabaseExecutionError("Query failed")
        assert str(error) == "Query failed"


class TestDatabaseConnectionManagerInit:
    """测试数据库连接管理器初始化"""
    
    @pytest.fixture
    def db_manager(self):
        """创建测试用的连接管理器"""
        return get_db_manager()
    
    def test_init(self, db_manager):
        """测试初始化"""
        assert db_manager._instance_cache == {}
        assert db_manager.POOL_MIN_CACHED == 1
        assert db_manager.POOL_MAX_CACHED == 5
        assert db_manager.POOL_MAX_CONNECTIONS == 10


class TestGetCredentials:
    """测试获取连接凭证"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.fixture
    def mock_instance(self):
        """创建模拟实例"""
        instance = MagicMock()
        instance.host = "localhost"
        instance.username = "root"
        instance.password_encrypted = "encrypted_password"
        instance.port = 3306
        return instance
    
    @patch('app.services.db_connection.decrypt_instance_password')
    def test_get_credentials_success(self, mock_decrypt, db_manager, mock_instance):
        """测试成功获取凭证"""
        mock_decrypt.return_value = "decrypted_password"
        
        host, username, password, port = db_manager._get_credentials(mock_instance)
        
        assert host == "localhost"
        assert username == "root"
        assert password == "decrypted_password"
        assert port == 3306
    
    @patch('app.services.db_connection.decrypt_instance_password')
    def test_get_credentials_decrypt_failure(self, mock_decrypt, db_manager, mock_instance):
        """测试解密失败"""
        mock_decrypt.side_effect = ValueError("Invalid password")
        
        with pytest.raises(Exception) as exc_info:
            db_manager._get_credentials(mock_instance)
        
        assert "密码解密失败" in str(exc_info.value)


class TestGetPoolKey:
    """测试获取连接池键"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.fixture
    def mock_instance(self):
        instance = MagicMock()
        instance.id = 123
        return instance
    
    def test_get_pool_key_with_database(self, db_manager, mock_instance):
        """测试带数据库名的键"""
        key = db_manager._get_pool_key(mock_instance, "test_db")
        assert key == (123, "test_db")
    
    def test_get_pool_key_without_database(self, db_manager, mock_instance):
        """测试不带数据库名的键"""
        key = db_manager._get_pool_key(mock_instance, None)
        assert key == (123, "default")


class TestMySQLConnection:
    """测试 MySQL 连接"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        # 清空连接池缓存
        DatabaseConnectionManager._mysql_pools = {}
        return DatabaseConnectionManager()
    
    @pytest.fixture
    def mock_mysql_instance(self):
        instance = MagicMock()
        instance.id = 1
        instance.host = "localhost"
        instance.username = "root"
        instance.password_encrypted = "encrypted"
        instance.port = 3306
        instance.db_type = "mysql"
        return instance
    
    @patch('app.services.db_connection.decrypt_instance_password')
    @patch('app.services.db_connection.pymysql.connect')
    def test_get_mysql_connection_no_pool(self, mock_connect, mock_decrypt, db_manager, mock_mysql_instance):
        """测试获取 MySQL 连接（不使用连接池）"""
        mock_decrypt.return_value = "password"
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = db_manager.get_mysql_connection(mock_mysql_instance, "test_db", use_pool=False)
        
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert call_args.kwargs['host'] == "localhost"
        assert call_args.kwargs['database'] == "test_db"
        assert conn == mock_conn
    
    @patch('app.services.db_connection.decrypt_instance_password')
    @patch('app.services.db_connection.PooledDB')
    def test_create_mysql_pool(self, mock_pool_class, mock_decrypt, db_manager, mock_mysql_instance):
        """测试创建 MySQL 连接池"""
        mock_decrypt.return_value = "password"
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        pool = db_manager._create_mysql_pool(mock_mysql_instance, "test_db")
        
        mock_pool_class.assert_called_once()
        call_args = mock_pool_class.call_args
        assert call_args.kwargs['host'] == "localhost"
        assert call_args.kwargs['database'] == "test_db"
        assert pool == mock_pool
    
    @patch('app.services.db_connection.decrypt_instance_password')
    @patch('app.services.db_connection.PooledDB')
    def test_create_mysql_pool_failure(self, mock_pool_class, mock_decrypt, db_manager, mock_mysql_instance):
        """测试创建连接池失败"""
        mock_decrypt.return_value = "password"
        mock_pool_class.side_effect = Exception("Pool creation failed")
        
        with pytest.raises(Exception) as exc_info:
            db_manager._create_mysql_pool(mock_mysql_instance, "test_db")
        
        assert "创建连接池失败" in str(exc_info.value)


class TestPostgreSQLConnection:
    """测试 PostgreSQL 连接"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        # 清空连接池缓存
        DatabaseConnectionManager._pg_pools = {}
        return DatabaseConnectionManager()
    
    @pytest.fixture
    def mock_pg_instance(self):
        instance = MagicMock()
        instance.id = 1
        instance.host = "localhost"
        instance.username = "postgres"
        instance.password_encrypted = "encrypted"
        instance.port = 5432
        instance.db_type = "postgresql"
        return instance
    
    @patch('app.services.db_connection.decrypt_instance_password')
    @patch('app.services.db_connection.psycopg2.connect')
    def test_get_postgresql_connection_no_pool(self, mock_connect, mock_decrypt, db_manager, mock_pg_instance):
        """测试获取 PostgreSQL 连接（不使用连接池）"""
        mock_decrypt.return_value = "password"
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = db_manager.get_postgresql_connection(mock_pg_instance, "test_db", use_pool=False)
        
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert call_args.kwargs['host'] == "localhost"
        assert call_args.kwargs['database'] == "test_db"
        assert conn == mock_conn
    
    @patch('app.services.db_connection.decrypt_instance_password')
    @patch('app.services.db_connection.psycopg2.pool.ThreadedConnectionPool')
    def test_create_pg_pool(self, mock_pool_class, mock_decrypt, db_manager, mock_pg_instance):
        """测试创建 PostgreSQL 连接池"""
        mock_decrypt.return_value = "password"
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        pool = db_manager._create_pg_pool(mock_pg_instance, "test_db")
        
        mock_pool_class.assert_called_once()
        call_args = mock_pool_class.call_args
        assert call_args.kwargs['host'] == "localhost"
        assert call_args.kwargs['database'] == "test_db"
        assert pool == mock_pool
    
    @patch('app.services.db_connection.decrypt_instance_password')
    def test_release_postgresql_connection(self, mock_decrypt, db_manager, mock_pg_instance):
        """测试释放 PostgreSQL 连接"""
        mock_decrypt.return_value = "password"
        
        # 先创建连接池
        with patch('app.services.db_connection.psycopg2.pool.ThreadedConnectionPool') as mock_pool_class:
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            pool = db_manager._create_pg_pool(mock_pg_instance, "test_db")
            db_manager._pg_pools[(1, "test_db")] = pool
            
            mock_conn = MagicMock()
            db_manager.release_postgresql_connection(mock_pg_instance, mock_conn, "test_db")
            
            mock_pool.putconn.assert_called_once_with(mock_conn)


class TestGetConnection:
    """测试通用获取连接方法"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @patch.object(DatabaseConnectionManager, 'get_mysql_connection')
    def test_get_connection_mysql(self, mock_get_mysql, db_manager):
        """测试获取 MySQL 连接"""
        instance = MagicMock()
        instance.db_type = "mysql"
        mock_conn = MagicMock()
        mock_get_mysql.return_value = mock_conn
        
        conn = db_manager.get_connection(instance, "test_db")
        
        mock_get_mysql.assert_called_once_with(instance, "test_db", True)
        assert conn == mock_conn
    
    @patch.object(DatabaseConnectionManager, 'get_postgresql_connection')
    def test_get_connection_postgresql(self, mock_get_pg, db_manager):
        """测试获取 PostgreSQL 连接"""
        instance = MagicMock()
        instance.db_type = "postgresql"
        mock_conn = MagicMock()
        mock_get_pg.return_value = mock_conn
        
        conn = db_manager.get_connection(instance, "test_db")
        
        mock_get_pg.assert_called_once_with(instance, "test_db", True)
        assert conn == mock_conn
    
    @patch.object(DatabaseConnectionManager, 'get_mysql_connection')
    def test_get_connection_default_mysql(self, mock_get_mysql, db_manager):
        """测试默认使用 MySQL"""
        instance = MagicMock()
        instance.db_type = None
        mock_get_mysql.return_value = MagicMock()
        
        db_manager.get_connection(instance, "test_db")
        
        mock_get_mysql.assert_called_once()


class TestConnectionContextManager:
    """测试连接上下文管理器"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @patch.object(DatabaseConnectionManager, 'get_connection')
    def test_connection_context_manager_mysql(self, mock_get_connection, db_manager):
        """测试 MySQL 连接上下文"""
        instance = MagicMock()
        instance.db_type = "mysql"
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        with db_manager.connection(instance, "test_db") as conn:
            assert conn == mock_conn
        
        mock_conn.close.assert_called_once()
    
    @patch.object(DatabaseConnectionManager, 'get_connection')
    @patch.object(DatabaseConnectionManager, 'release_postgresql_connection')
    def test_connection_context_manager_postgresql(self, mock_release, mock_get_connection, db_manager):
        """测试 PostgreSQL 连接上下文"""
        instance = MagicMock()
        instance.db_type = "postgresql"
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        with db_manager.connection(instance, "test_db", use_pool=True) as conn:
            assert conn == mock_conn
        
        mock_release.assert_called_once_with(instance, mock_conn, "test_db")
    
    @patch.object(DatabaseConnectionManager, 'get_connection')
    def test_connection_context_manager_exception(self, mock_get_connection, db_manager):
        """测试连接上下文异常处理"""
        instance = MagicMock()
        instance.db_type = "mysql"
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        try:
            with db_manager.connection(instance, "test_db") as conn:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # 即使发生异常，连接也应该被关闭
        mock_conn.close.assert_called_once()


class TestTestConnection:
    """测试连接测试"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_test_connection_mysql_success(self, mock_connection, db_manager):
        """测试 MySQL 连接成功"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("8.0.0",)
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.test_connection(instance)
        
        assert result['success'] is True
        assert result['message'] == '连接成功'
        assert result['version'] == "8.0.0"
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_test_connection_postgresql_success(self, mock_connection, db_manager):
        """测试 PostgreSQL 连接成功"""
        instance = MagicMock()
        instance.db_type = "postgresql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("PostgreSQL 14.0",)
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.test_connection(instance)
        
        assert result['success'] is True
        assert 'PostgreSQL' in result['version']
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_test_connection_failure(self, mock_connection, db_manager):
        """测试连接失败"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(side_effect=Exception("Connection refused"))
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.test_connection(instance)
        
        assert result['success'] is False
        assert '连接失败' in result['message']


class TestExecuteQuery:
    """测试执行查询"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_query_select(self, mock_connection, db_manager):
        """测试执行 SELECT 查询"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 2
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "test1"), (2, "test2")]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.execute_query(instance, "SELECT * FROM users")
        
        assert result['success'] is True
        assert result['affected_rows'] == 2
        assert len(result['data']) == 2
        assert result['data'][0] == {'id': 1, 'name': 'test1'}
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_query_insert(self, mock_connection, db_manager):
        """测试执行 INSERT 查询"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.description = None
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.execute_query(instance, "INSERT INTO users VALUES (1)", fetch=False)
        
        assert result['success'] is True
        assert result['affected_rows'] == 1
        mock_conn.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_query_with_params(self, mock_connection, db_manager):
        """测试带参数的查询"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_cursor.description = None
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        await db_manager.execute_query(instance, "SELECT * FROM users WHERE id = %s", params=(1,))
        
        mock_cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_query_failure(self, mock_connection, db_manager):
        """测试查询失败"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Syntax error")
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        result = await db_manager.execute_query(instance, "INVALID SQL")
        
        assert result['success'] is False
        assert 'Syntax error' in result['message']


class TestExecuteScript:
    """测试执行脚本"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_script_success(self, mock_connection, db_manager):
        """测试成功执行脚本"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        script = "INSERT INTO t1 VALUES (1); INSERT INTO t2 VALUES (2);"
        result = await db_manager.execute_script(instance, script)
        
        assert result['success'] is True
        assert len(result['results']) == 2
        assert result['total_affected'] == 2
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_script_with_error_continue(self, mock_connection, db_manager):
        """测试执行脚本遇到错误继续"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # 第一条成功，第二条失败
        mock_cursor.execute.side_effect = [None, Exception("Error")]
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        script = "INSERT INTO t1 VALUES (1); INVALID; INSERT INTO t2 VALUES (2);"
        result = await db_manager.execute_script(instance, script, stop_on_error=False)
        
        assert result['success'] is False  # 有失败
        assert len(result['results']) == 2  # 两条语句
        assert result['results'][0]['success'] is True
        assert result['results'][1]['success'] is False
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_execute_script_with_error_stop(self, mock_connection, db_manager):
        """测试执行脚本遇到错误停止"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Error")
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        script = "INVALID; INSERT INTO t2 VALUES (2);"
        result = await db_manager.execute_script(instance, script, stop_on_error=True)
        
        assert result['success'] is False
        assert len(result['results']) == 1  # 只执行了一条就停止了


class TestGetDatabases:
    """测试获取数据库列表"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_get_databases_mysql(self, mock_connection, db_manager):
        """测试获取 MySQL 数据库列表"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("mysql",), ("test_db",), ("information_schema",)]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        databases = await db_manager.get_databases(instance)
        
        assert databases == ["mysql", "test_db", "information_schema"]
        mock_cursor.execute.assert_called_with("SHOW DATABASES")
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_get_databases_postgresql(self, mock_connection, db_manager):
        """测试获取 PostgreSQL 数据库列表"""
        instance = MagicMock()
        instance.db_type = "postgresql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("postgres",), ("test_db",)]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        databases = await db_manager.get_databases(instance)
        
        assert databases == ["postgres", "test_db"]


class TestGetTables:
    """测试获取表列表"""
    
    @pytest.fixture
    def db_manager(self):
        # DatabaseConnectionManager already imported at top
        return DatabaseConnectionManager()
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_get_tables_mysql(self, mock_connection, db_manager):
        """测试获取 MySQL 表列表"""
        instance = MagicMock()
        instance.db_type = "mysql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("users", "BASE TABLE"), ("orders", "BASE TABLE")]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        tables = await db_manager.get_tables(instance, "test_db")
        
        assert len(tables) == 2
        assert tables[0] == {'name': 'users', 'type': 'BASE TABLE'}
    
    @pytest.mark.asyncio
    @patch.object(DatabaseConnectionManager, 'connection')
    async def test_get_tables_postgresql(self, mock_connection, db_manager):
        """测试获取 PostgreSQL 表列表"""
        instance = MagicMock()
        instance.db_type = "postgresql"
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("users", "BASE TABLE")]
        mock_conn.cursor.return_value = mock_cursor
        
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_conn)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_connection.return_value = mock_context
        
        tables = await db_manager.get_tables(instance, "test_db")
        
        assert len(tables) == 1


class TestGlobalInstance:
    """测试全局实例"""
    
    def test_db_manager_global_instance(self):
        """测试全局 db_manager 实例"""
        from app.services.db_connection import db_manager
        # DatabaseConnectionManager already imported at top
        
        assert isinstance(db_manager, DatabaseConnectionManager)
