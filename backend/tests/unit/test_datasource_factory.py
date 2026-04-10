"""
数据源适配器工厂单元测试

测试适配器工厂的创建和注册功能。
"""
import pytest
from app.adapters.datasource.factory import DataSourceAdapterFactory
from app.adapters.datasource.mysql_adapter import MySQLAdapter
from app.adapters.datasource.postgresql_adapter import PostgreSQLAdapter
from app.adapters.datasource.redis_adapter import RedisAdapter

# 导入注册模块以确保内置适配器被注册
from app.adapters.datasource import registry


class TestDataSourceAdapterFactory:
    """数据源适配器工厂测试"""
    
    def test_create_mysql_adapter(self):
        """测试创建 MySQL 适配器"""
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test"
        }
        
        adapter = DataSourceAdapterFactory.create("mysql", config)
        
        assert isinstance(adapter, MySQLAdapter)
        assert adapter.get_adapter_type() == "mysql"
    
    def test_create_postgresql_adapter(self):
        """测试创建 PostgreSQL 适配器"""
        config = {
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password",
            "database": "test"
        }
        
        adapter = DataSourceAdapterFactory.create("postgresql", config)
        
        assert isinstance(adapter, PostgreSQLAdapter)
        assert adapter.get_adapter_type() == "postgresql"
    
    def test_create_redis_adapter(self):
        """测试创建 Redis 适配器"""
        config = {
            "host": "localhost",
            "port": 6379,
            "password": "password",
            "db": 0
        }
        
        adapter = DataSourceAdapterFactory.create("redis", config)
        
        assert isinstance(adapter, RedisAdapter)
        assert adapter.get_adapter_type() == "redis"
    
    def test_create_unsupported_adapter(self):
        """测试创建不支持的适配器"""
        with pytest.raises(ValueError, match="不支持的数据源类型"):
            DataSourceAdapterFactory.create("mongodb", {})
    
    def test_register_custom_adapter(self):
        """测试注册自定义适配器"""
        from app.adapters.datasource.base import DataSourceAdapter
        
        # 创建自定义适配器
        class CustomAdapter(DataSourceAdapter):
            def __init__(self, config):
                self.config = config
                self._connected = False
            
            def get_adapter_type(self):
                return "custom"
            
            def connect(self):
                self._connected = True
                return True
            
            def disconnect(self):
                self._connected = False
                return True
            
            def is_connected(self):
                return self._connected
            
            def test_connection(self):
                return {"status": "ok"}
            
            def execute_query(self, query, params=None):
                return []
            
            def get_metrics(self):
                return {}
        
        # 注册
        DataSourceAdapterFactory.register("custom", CustomAdapter)
        
        # 创建
        adapter = DataSourceAdapterFactory.create("custom", {"test": True})
        
        assert isinstance(adapter, CustomAdapter)
        assert adapter.get_adapter_type() == "custom"
    
    def test_get_supported_types(self):
        """测试获取支持的类型列表"""
        types = DataSourceAdapterFactory.get_supported_types()
        
        assert isinstance(types, list)
        assert "mysql" in types
        assert "postgresql" in types
        assert "redis" in types
