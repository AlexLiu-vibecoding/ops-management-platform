"""
系统配置 API 测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestDatabaseConfigAPI:
    """数据库配置 API 测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = Mock()
        db.query.return_value = db
        db.filter.return_value = db
        db.first.return_value = None
        db.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def mock_user(self):
        """Mock 超级管理员用户"""
        user = Mock()
        user.id = 1
        user.username = "admin"
        user.role = "super_admin"
        user.is_super_admin = True
        return user

    # ==================== Schema 测试 ====================

    def test_database_type_config_schema(self):
        """测试数据库类型配置 Schema"""
        from app.api.system import DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="mysql",
            display_name="MySQL",
            default_port=3306,
            enabled=True,
            icon="mysql",
            description="MySQL 数据库"
        )
        
        assert config.db_type == "mysql"
        assert config.default_port == 3306
        assert config.enabled == True

    def test_database_config_update_schema(self):
        """测试数据库配置更新 Schema"""
        from app.api.system import DatabaseConfigUpdate
        
        update = DatabaseConfigUpdate(enabled=False)
        
        assert update.enabled == False

    def test_database_config_response_schema(self):
        """测试数据库配置响应 Schema"""
        from app.api.system import DatabaseConfigResponse, DatabaseTypeConfig
        
        config = DatabaseTypeConfig(
            db_type="mysql",
            display_name="MySQL",
            default_port=3306
        )
        
        response = DatabaseConfigResponse(items=[config])
        
        assert len(response.items) == 1

    # ==================== 默认配置测试 ====================

    def test_default_db_configs(self):
        """测试默认数据库配置"""
        from app.api.system import DEFAULT_DB_CONFIGS
        
        assert len(DEFAULT_DB_CONFIGS) == 3
        
        db_types = [c["db_type"] for c in DEFAULT_DB_CONFIGS]
        assert "mysql" in db_types
        assert "postgresql" in db_types
        assert "redis" in db_types

    # ==================== 路由测试 ====================

    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.system import router
        
        assert router.prefix == "/system"

    def test_router_tags(self):
        """测试路由标签"""
        from app.api.system import router
        
        assert "系统配置" in router.tags


class TestStorageConfigAPI:
    """存储配置 API 测试"""

    def test_storage_config_response_schema(self):
        """测试存储配置响应 Schema"""
        from app.api.system import StorageConfigResponse
        
        config = StorageConfigResponse(
            storage_type="local",
            retention_days=30,
            size_threshold=10485760,
            local_path="/data/storage"
        )
        
        assert config.storage_type == "local"
        assert config.retention_days == 30

    def test_storage_config_update_schema(self):
        """测试存储配置更新 Schema"""
        from app.api.system import StorageConfigUpdate
        
        update = StorageConfigUpdate(
            storage_type="s3",
            retention_days=60,
            s3_bucket="my-bucket",
            s3_region="us-east-1"
        )
        
        assert update.storage_type == "s3"
        assert update.s3_bucket == "my-bucket"

    def test_storage_test_response_schema(self):
        """测试存储测试响应 Schema"""
        from app.api.system import StorageTestResponse
        
        response = StorageTestResponse(success=True, message="连接成功")
        
        assert response.success == True
        assert "成功" in response.message


class TestSystemOverviewAPI:
    """系统概览 API 测试"""

    def test_scheduler_info_schema(self):
        """测试调度器信息 Schema"""
        from app.api.system import SchedulerInfo
        
        info = SchedulerInfo(
            name="approval_scheduler",
            description="审批调度器",
            running=True
        )
        
        assert info.name == "approval_scheduler"
        assert info.running == True

    def test_system_overview_schema(self):
        """测试系统概览 Schema"""
        from app.api.system import SystemOverview, SchedulerInfo
        
        scheduler = SchedulerInfo(
            name="approval_scheduler",
            description="审批调度器",
            running=True
        )
        
        overview = SystemOverview(
            version="1.0.0",
            python_version="3.12.0",
            database_type="postgresql",
            storage_type="local",
            redis_enabled=True,
            scheduler_running=True,
            schedulers=[scheduler]
        )
        
        assert overview.version == "1.0.0"
        assert overview.scheduler_running == True
        assert len(overview.schedulers) == 1
