"""
数据库连接管理服务测试
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.db_connection import (
    DatabaseConnectionManager,
    DatabaseConnectionError,
    DatabaseExecutionError
)


class TestDatabaseConnectionError:
    """测试连接错误类"""
    
    def test_error_creation(self):
        """测试错误创建"""
        error = DatabaseConnectionError("连接失败")
        assert str(error) == "连接失败"
    
    def test_error_with_cause(self):
        """测试带原因的异常"""
        cause = ValueError("原始错误")
        try:
            raise ValueError("原始错误")
        except ValueError as e:
            error = DatabaseConnectionError("连接失败")
            error.__cause__ = e
        assert error.__cause__ is not None


class TestDatabaseExecutionError:
    """测试执行错误类"""
    
    def test_error_creation(self):
        """测试错误创建"""
        error = DatabaseExecutionError("执行失败")
        assert str(error) == "执行失败"


class TestDatabaseConnectionManagerConstants:
    """测试连接管理器常量"""
    
    def test_pool_constants(self):
        """测试连接池常量"""
        assert DatabaseConnectionManager.POOL_MIN_CACHED == 1
        assert DatabaseConnectionManager.POOL_MAX_CACHED == 5
        assert DatabaseConnectionManager.POOL_MAX_SHARED == 3
        assert DatabaseConnectionManager.POOL_MAX_CONNECTIONS == 10
        assert DatabaseConnectionManager.POOL_BLOCKING is True
    
    def test_timeout_constant(self):
        """测试超时常量"""
        assert DatabaseConnectionManager.CONNECT_TIMEOUT == 10


class TestDatabaseConnectionManagerCredentials:
    """测试凭证获取"""
    
    def test_get_pool_key(self):
        """测试连接池键生成"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.id = 123
        
        # 带数据库名
        key1 = manager._get_pool_key(mock_instance, "mydb")
        assert key1 == (123, "mydb")
        
        # 不带数据库名
        key2 = manager._get_pool_key(mock_instance, None)
        assert key2 == (123, "default")
    
    def test_get_credentials_success(self):
        """测试获取凭证成功"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.host = "localhost"
        mock_instance.username = "root"
        mock_instance.password_encrypted = "encrypted_password"
        mock_instance.port = 3306
        
        with patch('app.services.db_connection.decrypt_instance_password') as mock_decrypt:
            mock_decrypt.return_value = "plain_password"
            
            host, username, password, port = manager._get_credentials(mock_instance)
            
            assert host == "localhost"
            assert username == "root"
            assert password == "plain_password"
            assert port == 3306
    
    def test_get_credentials_decrypt_failure(self):
        """测试凭证解密失败"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.password_encrypted = "invalid"
        
        with patch('app.services.db_connection.decrypt_instance_password') as mock_decrypt:
            mock_decrypt.side_effect = ValueError("解密失败")
            
            with pytest.raises(DatabaseConnectionError) as exc_info:
                manager._get_credentials(mock_instance)
            
            assert "密码解密失败" in str(exc_info.value)


class TestDatabaseConnectionManagerInstance:
    """测试连接管理器实例"""
    
    def test_instance_creation(self):
        """测试实例创建"""
        manager = DatabaseConnectionManager()
        
        assert hasattr(manager, '_instance_cache')
        assert hasattr(manager, '_mysql_pools')
        assert hasattr(manager, '_pg_pools')


class TestDatabaseConnectionHelperFunctions:
    """测试辅助函数"""
    
    def test_instance_cache_initialization(self):
        """测试实例缓存初始化"""
        manager = DatabaseConnectionManager()
        assert manager._instance_cache == {}


class TestDatabaseConnectionMock:
    """使用Mock测试连接功能"""
    
    def test_mysql_pool_key_generation(self):
        """测试MySQL连接池键生成"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.id = 1
        
        key = manager._get_pool_key(mock_instance, "testdb")
        assert key[0] == 1
        assert key[1] == "testdb"
    
    def test_postgresql_pool_key_generation(self):
        """测试PostgreSQL连接池键生成"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.id = 2
        
        key = manager._get_pool_key(mock_instance, "postgres")
        assert key[0] == 2
        assert key[1] == "postgres"


class TestDatabaseConnectionManagerAsyncMethods:
    """测试异步方法Mock"""
    
    @pytest.mark.asyncio
    async def test_test_connection_returns_dict(self):
        """测试连接测试返回字典"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.db_type = "mysql"
        mock_instance.id = 1
        mock_instance.host = "localhost"
        mock_instance.username = "root"
        mock_instance.password_encrypted = "xxx"
        mock_instance.port = 3306
        
        with patch.object(manager, 'connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=Exception("连接失败"))
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_context
            
            result = await manager.test_connection(mock_instance)
            
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'message' in result
    
    @pytest.mark.asyncio
    async def test_execute_query_returns_dict(self):
        """测试查询执行返回字典"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.db_type = "mysql"
        
        with patch.object(manager, 'connection') as mock_conn:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=Exception("查询失败"))
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value = mock_context
            
            result = await manager.execute_query(mock_instance, "SELECT 1")
            
            assert isinstance(result, dict)
            assert result['success'] is False


class TestDatabaseConnectionPoolBehavior:
    """测试连接池行为"""
    
    def test_mysql_pools_initial_empty(self):
        """测试MySQL连接池初始为空"""
        manager = DatabaseConnectionManager()
        assert manager._mysql_pools == {}
    
    def test_pg_pools_initial_empty(self):
        """测试PostgreSQL连接池初始为空"""
        manager = DatabaseConnectionManager()
        assert manager._pg_pools == {}


class TestDatabaseNameHandling:
    """测试数据库名处理"""
    
    def test_none_database_uses_default(self):
        """测试None数据库使用默认"""
        manager = DatabaseConnectionManager()
        
        mock_instance = MagicMock()
        mock_instance.id = 1
        
        key = manager._get_pool_key(mock_instance, None)
        assert key[1] == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
