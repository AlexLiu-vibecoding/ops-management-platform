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


class TestKeyRotationStatistics:
    """密钥轮换统计测试"""

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
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return KeyRotationService(mock_db, operator_id=1)

    @pytest.fixture
    def mock_keys(self):
        """Mock 多个密钥"""
        key1 = Mock()
        key1.key_id = "v1"
        key1.key_value = "key1-value-12345678901234567890"
        key1.is_active = True
        
        key2 = Mock()
        key2.key_id = "v2"
        key2.key_value = "key2-value-12345678901234567890"
        key2.is_active = False
        
        return [key1, key2]

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        config = Mock()
        config.current_key_id = "v1"
        config.enabled = True
        config.schedule_type = "monthly"
        config.schedule_day = 1
        config.schedule_time = "02:00"
        config.auto_switch = False
        config.rotation_interval_days = 90
        return config

    def test_get_statistics_with_data(self, service, mock_db, mock_keys, mock_config):
        """测试获取统计数据 - 有数据"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=mock_keys):
            
            # Mock execute 返回表存在和统计数据
            mock_db.execute.return_value.scalar.return_value = 10
            
            result = service.get_statistics()
            
            assert "total" in result
            assert "by_version" in result
            assert "legacy_count" in result
            assert "needs_migration" in result
            assert "versions" in result

    def test_get_statistics_empty(self, service, mock_db, mock_keys, mock_config):
        """测试获取统计数据 - 无数据"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=[]):
            
            mock_db.execute.return_value.scalar.return_value = 0
            
            result = service.get_statistics()
            
            assert result["total"] == 0
            assert result["legacy_count"] == 0

    def test_get_statistics_table_not_exists(self, service, mock_db, mock_keys, mock_config):
        """测试获取统计数据 - 表不存在"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=mock_keys):
            
            # 第一次调用检查表存在性返回 False
            mock_db.execute.return_value.scalar.return_value = False
            
            result = service.get_statistics()
            
            assert result["total"] == 0


class TestKeyRotationMigration:
    """密钥轮换迁移测试"""

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
    def mock_key_v2(self):
        """Mock v2 密钥"""
        key = Mock()
        key.id = 2
        key.key_id = "v2"
        key.key_value = "v2-key-value-1234567890123456"
        key.is_active = False
        key.created_at = datetime.now()
        return key

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        config = Mock()
        config.current_key_id = "v1"
        config.enabled = True
        config.schedule_type = "monthly"
        config.schedule_day = 1
        config.schedule_time = "02:00"
        config.auto_switch = False
        config.rotation_interval_days = 90
        return config

    def test_get_next_key_for_migration_exists(self, service, mock_db, mock_key_v2):
        """测试获取下一个待迁移密钥 - 存在"""
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_key_v2]
        
        result = service.get_next_key_for_migration()
        
        assert result == mock_key_v2

    def test_get_next_key_for_migration_multiple(self, service, mock_db):
        """测试获取下一个待迁移密钥 - 多个密钥返回版本最高的"""
        key1 = Mock()
        key1.key_id = "v1"
        key2 = Mock()
        key2.key_id = "v2"
        key3 = Mock()
        key3.key_id = "v3"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [key1, key2, key3]
        
        result = service.get_next_key_for_migration()
        
        assert result == key3  # v3 是版本最高的

    def test_get_next_key_for_migration_none(self, service, mock_db):
        """测试获取下一个待迁移密钥 - 不存在"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = service.get_next_key_for_migration()
        
        assert result is None

    def test_preview_migration_no_key(self, service, mock_db, mock_config):
        """测试预览迁移 - 没有待迁移密钥"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=[]), \
             patch.object(service, 'get_next_key_for_migration', return_value=None):
            
            result = service.preview_migration()
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert "所有数据已迁移" in result[0]["description"]

    def test_preview_migration_with_key(self, service, mock_db, mock_key_v2, mock_config):
        """测试预览迁移 - 有待迁移密钥"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_all_keys', return_value=[mock_key_v2]), \
             patch.object(service, 'get_next_key_for_migration', return_value=mock_key_v2):
            
            # Mock execute 返回表存在和统计数据
            mock_db.execute.return_value.scalar.return_value = 5
            
            result = service.preview_migration()
            
            assert isinstance(result, list)

    def test_execute_migration_no_key(self, service, mock_db, mock_config):
        """测试执行迁移 - 没有待迁移密钥"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_next_key_for_migration', return_value=None):
            
            result = service.execute_migration()
            
            assert result["success"] == False
            assert "没有待迁移的密钥" in result["message"]
            assert result["total_migrated"] == 0

    def test_execute_migration_with_key(self, service, mock_db, mock_key_v2, mock_config):
        """测试执行迁移 - 有待迁移密钥"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_next_key_for_migration', return_value=mock_key_v2), \
             patch.object(service, 'get_active_key', return_value=Mock(key_id="v1")):
            
            # Mock execute: 表存在返回 True, 其他查询返回 0
            def mock_execute_side_effect(*args, **kwargs):
                result = Mock()
                if isinstance(args[0], str) and "EXISTS" in args[0]:
                    result.scalar.return_value = True
                else:
                    result.scalar.return_value = 0
                return result
            
            mock_db.execute.side_effect = mock_execute_side_effect
            
            result = service.execute_migration()
            
            assert "success" in result
            assert "total_migrated" in result
            assert "target_version" in result
            assert result["target_version"] == "v2"


class TestKeyRotationSwitch:
    """密钥版本切换测试"""

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
    def mock_key_v1(self):
        """Mock v1 密钥"""
        key = Mock()
        key.id = 1
        key.key_id = "v1"
        key.key_value = "v1-key-value-1234567890123456"
        key.is_active = True
        return key

    @pytest.fixture
    def mock_key_v2(self):
        """Mock v2 密钥"""
        key = Mock()
        key.id = 2
        key.key_id = "v2"
        key.key_value = "v2-key-value-1234567890123456"
        key.is_active = False
        return key

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        config = Mock()
        config.current_key_id = "v1"
        config.enabled = True
        config.schedule_type = "monthly"
        config.schedule_day = 1
        config.schedule_time = "02:00"
        config.auto_switch = False
        config.rotation_interval_days = 90
        return config

    def test_switch_version_not_exists(self, service, mock_db, mock_config):
        """测试切换版本 - 目标版本不存在"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_key_by_id', return_value=None):
            
            result = service.switch_version("v999")
            
            assert result == False

    def test_switch_version_same_version(self, service, mock_db, mock_key_v1, mock_config):
        """测试切换版本 - 切换到相同版本"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_key_by_id', return_value=mock_key_v1), \
             patch.object(service, 'get_active_key', return_value=mock_key_v1):
            
            result = service.switch_version("v1")
            
            assert result == True

    def test_switch_version_different_version(self, service, mock_db, mock_key_v1, mock_key_v2, mock_config):
        """测试切换版本 - 切换到不同版本"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_key_by_id', return_value=mock_key_v2), \
             patch.object(service, 'get_active_key', return_value=mock_key_v1), \
             patch.object(service, 'execute_migration', return_value={"success": True, "total_migrated": 0, "total_failed": 0}):
            
            # Mock execute: 表存在返回 False (跳过迁移)
            def mock_execute_side_effect(*args, **kwargs):
                result = Mock()
                result.scalar.return_value = False
                return result
            
            mock_db.execute.side_effect = mock_execute_side_effect
            
            result = service.switch_version("v2")
            
            assert result == True


class TestKeyRotationFullRotation:
    """一键轮换测试"""

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
    def mock_new_key(self):
        """Mock 新密钥"""
        key = Mock()
        key.id = 2
        key.key_id = "v2"
        key.key_value = "v2-key-value-1234567890123456"
        key.is_active = False
        return key

    @pytest.fixture
    def mock_config(self):
        """Mock 配置"""
        config = Mock()
        config.current_key_id = "v1"
        config.enabled = True
        config.schedule_type = "monthly"
        config.schedule_day = 1
        config.schedule_time = "02:00"
        config.auto_switch = True  # 启用自动切换
        config.rotation_interval_days = 90
        return config

    @patch('app.services.key_rotation_service.settings')
    def test_full_rotation_auto_switch_enabled(self, mock_settings, service, mock_db, mock_new_key, mock_config):
        """测试一键轮换 - 自动切换启用"""
        mock_settings.security.AES_KEY = "test-key"
        
        with patch.object(service, 'get_all_keys', return_value=[]), \
             patch.object(service, 'get_or_create_initial_key', return_value=Mock(key_id="v1")), \
             patch.object(service, 'generate_new_key', return_value=mock_new_key), \
             patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'execute_migration', return_value={"success": True, "total_migrated": 0, "total_failed": 0}), \
             patch.object(service, 'switch_version', return_value=True):
            
            result = service.full_rotation()
            
            assert "new_key_version" in result
            assert result["new_key_version"] == "v2"
            assert "migration_result" in result
            assert result["auto_switched"] == True

    @patch('app.services.key_rotation_service.settings')
    def test_full_rotation_auto_switch_disabled(self, mock_settings, service, mock_db, mock_new_key, mock_config):
        """测试一键轮换 - 自动切换禁用"""
        mock_settings.security.AES_KEY = "test-key"
        mock_config.auto_switch = False
        
        with patch.object(service, 'get_all_keys', return_value=[]), \
             patch.object(service, 'get_or_create_initial_key', return_value=Mock(key_id="v1")), \
             patch.object(service, 'generate_new_key', return_value=mock_new_key), \
             patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'execute_migration', return_value={"success": True, "total_migrated": 0, "total_failed": 0}):
            
            result = service.full_rotation()
            
            assert result["auto_switched"] == False


class TestKeyRotationSchedule:
    """密钥轮换调度测试"""

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
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return KeyRotationService(mock_db, operator_id=1)

    @pytest.fixture
    def mock_config_weekly(self):
        """Mock 每周轮换配置"""
        config = Mock()
        config.schedule_type = "weekly"
        config.schedule_day = 3  # 周三
        config.schedule_time = "02:00"
        return config

    @pytest.fixture
    def mock_config_monthly(self):
        """Mock 每月轮换配置"""
        config = Mock()
        config.schedule_type = "monthly"
        config.schedule_day = 15
        config.schedule_time = "02:00"
        return config

    @pytest.fixture
    def mock_config_quarterly(self):
        """Mock 每季度轮换配置"""
        config = Mock()
        config.schedule_type = "quarterly"
        config.schedule_day = 1
        config.schedule_time = "02:00"
        return config

    def test_calculate_next_rotation_weekly(self, service, mock_config_weekly):
        """测试计算下次轮换时间 - 每周"""
        with patch.object(service, 'get_config', return_value=mock_config_weekly):
            result = service.calculate_next_rotation()
            
            assert isinstance(result, datetime)
            # 验证是未来时间
            assert result > datetime.now()

    def test_calculate_next_rotation_monthly(self, service, mock_config_monthly):
        """测试计算下次轮换时间 - 每月"""
        with patch.object(service, 'get_config', return_value=mock_config_monthly):
            result = service.calculate_next_rotation()
            
            assert isinstance(result, datetime)
            assert result > datetime.now()

    def test_calculate_next_rotation_quarterly(self, service, mock_config_quarterly):
        """测试计算下次轮换时间 - 每季度"""
        with patch.object(service, 'get_config', return_value=mock_config_quarterly):
            result = service.calculate_next_rotation()
            
            assert isinstance(result, datetime)
            assert result > datetime.now()


class TestAESCipherAdvanced:
    """AES 加密高级测试 - 简化版"""

    def test_encrypt_basic(self):
        """测试基本加密功能"""
        from app.services.key_rotation_service import AESCipher
        
        cipher = AESCipher("test-key-12345678901234567890")
        original = "sensitive-data"
        
        # 加密
        encrypted = cipher.encrypt(original)
        
        # 验证加密后不等于原文
        assert encrypted != original
        # 验证包含版本前缀
        assert encrypted.startswith("v")

    def test_encrypt_different_values(self):
        """测试每次加密产生不同结果（IV随机）"""
        from app.services.key_rotation_service import AESCipher
        
        cipher = AESCipher("test-key-12345678901234567890")
        original = "same-data"
        
        encrypted1 = cipher.encrypt(original)
        encrypted2 = cipher.encrypt(original)
        
        # 由于 IV 随机，每次加密结果不同
        assert encrypted1 != encrypted2
