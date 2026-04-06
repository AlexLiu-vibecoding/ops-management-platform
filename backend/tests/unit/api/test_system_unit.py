"""
系统配置API测试
"""
import pytest
from unittest.mock import MagicMock


class TestSystemSchemas:
    """测试系统配置Schema"""
    
    def test_database_type_config_fields(self):
        """测试数据库类型配置Schema字段"""
        from app.api.system import DatabaseTypeConfig
        
        fields = DatabaseTypeConfig.model_fields
        assert 'db_type' in fields
        assert 'display_name' in fields
        assert 'default_port' in fields
        assert 'enabled' in fields
        assert 'icon' in fields
        assert 'description' in fields
    
    def test_database_config_update_fields(self):
        """测试数据库配置更新Schema字段"""
        from app.api.system import DatabaseConfigUpdate
        
        fields = DatabaseConfigUpdate.model_fields
        assert 'enabled' in fields
    
    def test_database_config_response_fields(self):
        """测试数据库配置响应Schema字段"""
        from app.api.system import DatabaseConfigResponse
        
        fields = DatabaseConfigResponse.model_fields
        assert 'items' in fields


class TestSystemRouter:
    """测试系统配置路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.system import router
        
        assert router.prefix == "/system"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.system import router
        
        assert "系统配置" in router.tags


class TestDatabaseTypeConfig:
    """测试数据库类型配置"""
    
    def test_create_mysql_config(self):
        """测试创建MySQL配置"""
        from app.api.system import DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="mysql",
            display_name="MySQL",
            default_port=3306,
            enabled=True,
            icon="mysql",
            description="MySQL 数据库实例"
        )
        
        assert config.db_type == "mysql"
        assert config.default_port == 3306
        assert config.enabled is True
    
    def test_create_postgresql_config(self):
        """测试创建PostgreSQL配置"""
        from app.api.system import DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="postgresql",
            display_name="PostgreSQL",
            default_port=5432,
            enabled=True,
            icon="postgresql",
            description="PostgreSQL 数据库实例"
        )
        
        assert config.db_type == "postgresql"
        assert config.default_port == 5432
    
    def test_create_redis_config(self):
        """测试创建Redis配置"""
        from app.api.system import DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="redis",
            display_name="Redis",
            default_port=6379,
            enabled=True,
            icon="redis",
            description="Redis 缓存实例"
        )
        
        assert config.db_type == "redis"
        assert config.default_port == 6379
    
    def test_config_defaults(self):
        """测试配置默认值"""
        from app.api.system import DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="test",
            display_name="Test",
            default_port=3306
        )
        
        assert config.enabled is True
        assert config.icon == ""
        assert config.description == ""


class TestDatabaseConfigUpdate:
    """测试数据库配置更新"""
    
    def test_enable_db_type(self):
        """测试启用数据库类型"""
        from app.api.system import DatabaseConfigUpdate
        
        update = DatabaseConfigUpdate(enabled=True)
        assert update.enabled is True
    
    def test_disable_db_type(self):
        """测试禁用数据库类型"""
        from app.api.system import DatabaseConfigUpdate
        
        update = DatabaseConfigUpdate(enabled=False)
        assert update.enabled is False


class TestDatabaseConfigResponse:
    """测试数据库配置响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.system import DatabaseConfigResponse, DatabaseTypeConfig
        
        configs = [
            DatabaseTypeConfig(
                db_type="mysql",
                display_name="MySQL",
                default_port=3306
            ),
            DatabaseTypeConfig(
                db_type="postgresql",
                display_name="PostgreSQL",
                default_port=5432
            )
        ]
        
        response = DatabaseConfigResponse(items=configs)
        assert len(response.items) == 2


class TestDefaultDbConfigs:
    """测试默认数据库配置"""
    
    def test_default_configs_exist(self):
        """测试默认配置存在"""
        from app.api.system import DEFAULT_DB_CONFIGS
        
        assert len(DEFAULT_DB_CONFIGS) == 3
    
    def test_mysql_default_config(self):
        """测试MySQL默认配置"""
        from app.api.system import DEFAULT_DB_CONFIGS
        
        mysql = next(c for c in DEFAULT_DB_CONFIGS if c["db_type"] == "mysql")
        assert mysql["display_name"] == "MySQL"
        assert mysql["default_port"] == 3306
        assert mysql["enabled"] is True
    
    def test_postgresql_default_config(self):
        """测试PostgreSQL默认配置"""
        from app.api.system import DEFAULT_DB_CONFIGS
        
        pg = next(c for c in DEFAULT_DB_CONFIGS if c["db_type"] == "postgresql")
        assert pg["display_name"] == "PostgreSQL"
        assert pg["default_port"] == 5432
    
    def test_redis_default_config(self):
        """测试Redis默认配置"""
        from app.api.system import DEFAULT_DB_CONFIGS
        
        redis = next(c for c in DEFAULT_DB_CONFIGS if c["db_type"] == "redis")
        assert redis["display_name"] == "Redis"
        assert redis["default_port"] == 6379


class TestSystemModels:
    """测试系统模型"""
    
    def test_global_config_model(self):
        """测试全局配置模型"""
        from app.models import GlobalConfig
        
        # 检查模型存在
        assert GlobalConfig is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
