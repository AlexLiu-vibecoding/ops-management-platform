"""
密钥轮换服务测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.services.key_rotation_service import KeyRotationService
from app.models.key_rotation import KeyRotationKey, KeyRotationConfig, KeyRotationLog


class TestKeyRotationService:
    """密钥轮换服务测试"""

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
        db.refresh = Mock()
        db.execute = Mock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return KeyRotationService(mock_db, operator_id=1)

    @pytest.fixture
    def mock_key(self):
        """Mock 密钥"""
        key = Mock(spec=KeyRotationKey)
        key.id = 1
        key.key_id = "v1"
        key.key_value = "test-key-value-12345678901234"
        key.is_active = True
        key.created_at = datetime.now()
        return key

    # ==================== 初始化测试 ====================

    def test_get_or_create_initial_key_existing(self, service, mock_db, mock_key):
        """测试获取已存在的初始密钥"""
        mock_db.query.return_value.first.return_value = mock_key
        
        result = service.get_or_create_initial_key()
        
        assert result == mock_key
        mock_db.add.assert_not_called()

    @patch('app.services.key_rotation_service.settings')
    def test_get_or_create_initial_key_new(self, mock_settings, service, mock_db, mock_key):
        """测试创建新的初始密钥"""
        mock_db.query.return_value.first.return_value = None
        mock_settings.security.AES_KEY = "test-initial-key"
        
        result = service.get_or_create_initial_key()
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch('app.services.key_rotation_service.settings')
    def test_get_or_create_initial_key_no_env(self, mock_settings, service, mock_db, mock_key):
        """测试没有环境变量时使用默认值"""
        mock_db.query.return_value.first.return_value = None
        mock_settings.security.AES_KEY = None
        
        result = service.get_or_create_initial_key()
        
        mock_db.add.assert_called_once()
        # 验证使用了默认密钥
        call_args = mock_db.add.call_args[0][0]
        assert call_args.key_id == "v1"
        assert "dev-aes-key" in call_args.key_value

    # ==================== 版本管理测试 ====================

    def test_get_next_key_version_empty(self, service, mock_db):
        """测试没有密钥时返回 v1"""
        mock_db.query.return_value.all.return_value = []
        
        result = service.get_next_key_version()
        
        assert result == "v1"

    def test_get_next_key_version_single(self, service, mock_db, mock_key):
        """测试单个密钥时返回 v2"""
        mock_db.query.return_value.all.return_value = [mock_key]
        
        result = service.get_next_key_version()
        
        assert result == "v2"

    def test_get_next_key_version_multiple(self, service, mock_db):
        """测试多个密钥时返回下一个版本"""
        key1 = Mock(spec=KeyRotationKey)
        key1.key_id = "v1"
        key2 = Mock(spec=KeyRotationKey)
        key2.key_id = "v2"
        key3 = Mock(spec=KeyRotationKey)
        key3.key_id = "v3"
        
        mock_db.query.return_value.all.return_value = [key1, key2, key3]
        
        result = service.get_next_key_version()
        
        assert result == "v4"

    def test_get_next_key_version_irregular(self, service, mock_db):
        """测试不规则版本号"""
        key1 = Mock(spec=KeyRotationKey)
        key1.key_id = "v1"
        key2 = Mock(spec=KeyRotationKey)
        key2.key_id = "v10"  # 不规则
        
        mock_db.query.return_value.all.return_value = [key1, key2]
        
        result = service.get_next_key_version()
        
        assert result == "v11"

    # ==================== 密钥查询测试 ====================

    def test_get_active_key(self, service, mock_db, mock_key):
        """测试获取激活的密钥"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_key
        
        result = service.get_active_key()
        
        assert result == mock_key

    def test_get_key_by_id(self, service, mock_db, mock_key):
        """测试根据版本号获取密钥"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_key
        
        result = service.get_key_by_id("v1")
        
        assert result == mock_key

    def test_get_all_keys(self, service, mock_db, mock_key):
        """测试获取所有密钥"""
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_key]
        
        result = service.get_all_keys()
        
        assert result == [mock_key]

    # ==================== 密钥生成测试 ====================

    def test_generate_new_key(self, service, mock_db):
        """测试生成新密钥"""
        mock_db.query.return_value.all.return_value = []
        
        result = service.generate_new_key()
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        # 验证新密钥的版本号
        call_args = mock_db.add.call_args[0][0]
        assert call_args.key_id == "v1"
        assert call_args.is_active == False
        assert len(call_args.key_value) == 32

    def test_generate_new_key_multiple_versions(self, service, mock_db):
        """测试生成多个版本密钥"""
        key1 = Mock(spec=KeyRotationKey)
        key1.key_id = "v1"
        key2 = Mock(spec=KeyRotationKey)
        key2.key_id = "v2"
        
        mock_db.query.return_value.all.return_value = [key1, key2]
        
        result = service.generate_new_key()
        
        call_args = mock_db.add.call_args[0][0]
        assert call_args.key_id == "v3"

    # ==================== 配置管理测试 ====================

    def test_get_config_existing(self, service, mock_db):
        """测试获取已存在的配置"""
        mock_config = Mock(spec=KeyRotationConfig)
        mock_config.enabled = True
        mock_config.schedule_type = "monthly"
        mock_config.current_key_id = "v1"
        
        mock_db.query.return_value.first.return_value = mock_config
        
        result = service.get_config()
        
        assert result == mock_config

    def test_get_config_create_default(self, service, mock_db):
        """测试创建默认配置"""
        mock_db.query.return_value.first.return_value = None
        # 让 query().filter() 也返回 None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = service.get_config()
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_update_config(self, service, mock_db):
        """测试更新配置"""
        mock_config = Mock(spec=KeyRotationConfig)
        mock_config.enabled = False
        mock_config.schedule_type = "monthly"
        mock_config.schedule_day = 1
        mock_config.schedule_time = "02:00"
        mock_config.auto_switch = False
        
        mock_db.query.return_value.first.return_value = mock_config
        
        result = service.update_config(
            enabled=True,
            schedule_type="weekly",
            schedule_day=3,
            schedule_time="03:00",
            auto_switch=True
        )
        
        assert mock_config.enabled == True
        assert mock_config.schedule_type == "weekly"
        assert mock_config.schedule_day == 3
        assert mock_config.schedule_time == "03:00"
        assert mock_config.auto_switch == True
        mock_db.commit.assert_called()

    # ==================== 状态和概览测试 ====================

    def test_get_status(self, service, mock_db, mock_key):
        """测试获取密钥轮换状态"""
        mock_config = Mock(spec=KeyRotationConfig)
        mock_config.current_key_id = "v1"
        
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=[mock_key]), \
             patch.object(service, 'get_statistics', return_value={"total": 0, "needs_migration": 0}), \
             patch.object(service, 'get_key_by_id', return_value=mock_key):
            result = service.get_status()
        
        assert "current_version" in result
        assert "can_rotate" in result
        assert "migration_needed" in result
        assert "total_versions" in result
        assert "current_key_preview" in result
        assert "has_pending_key" in result

    def test_get_overview(self, service, mock_db, mock_key):
        """测试获取密钥轮换概览"""
        mock_config = Mock(spec=KeyRotationConfig)
        mock_config.current_key_id = "v1"
        
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=[mock_key]), \
             patch.object(service, 'get_statistics', return_value={"total": 10}):
            result = service.get_overview()
        
        assert "current_version" in result
        assert "total_keys" in result
        assert "total_records" in result

    # ==================== 日志测试 ====================

    def test_add_log(self, service, mock_db):
        """测试添加轮换日志"""
        result = service.add_log(
            action="generate",
            status="success",
            from_version="v1",
            to_version="v2",
            total_records=10,
            migrated_records=10,
            failed_records=0
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_history(self, service, mock_db):
        """测试获取历史记录"""
        mock_log = Mock(spec=KeyRotationLog)
        mock_log.id = 1
        mock_log.action = "switch"
        
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_log]
        
        result = service.get_history(limit=10, offset=0)
        
        assert result == [mock_log]

    def test_count_history(self, service, mock_db):
        """测试统计历史记录数"""
        mock_db.query.return_value.count.return_value = 5
        
        result = service.count_history()
        
        assert result == 5
