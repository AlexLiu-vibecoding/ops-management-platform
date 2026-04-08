"""
JWT 轮换服务测试
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.jwt_rotation_service import JWTRotationService
from app.models.key_rotation import JWTRotationKey, JWTRotationConfig, KeyRotationLog


class TestJWTRotationService:
    """JWT 轮换服务测试"""

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
        db.delete = Mock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return JWTRotationService(mock_db, operator_id=1)

    @pytest.fixture
    def mock_config(self):
        """Mock JWT 配置"""
        config = Mock(spec=JWTRotationConfig)
        config.id = 1
        config.enabled = True
        config.current_key_id = "v1"
        config.last_rotation_at = datetime.now()
        return config

    @pytest.fixture
    def mock_jwt_key(self):
        """Mock JWT 密钥"""
        key = Mock(spec=JWTRotationKey)
        key.id = 1
        key.key_id = "v1"
        key.key_value = "test-jwt-secret-key-12345678901234567890"
        key.is_active = True
        key.created_at = datetime.now()
        key.created_by = 1
        key.to_dict = Mock(return_value={
            "id": 1,
            "key_id": "v1",
            "key_value_preview": "test***7890",
            "is_active": True,
            "created_at": datetime.now().isoformat()
        })
        return key

    # ==================== 配置测试 ====================

    def test_get_config_existing(self, service, mock_db, mock_config):
        """测试获取已存在的配置"""
        mock_db.query.return_value.first.return_value = mock_config
        
        result = service.get_config()
        
        assert result == mock_config

    def test_get_config_create_default(self, service, mock_db):
        """测试创建默认配置"""
        mock_db.query.return_value.first.return_value = None
        
        result = service.get_config()
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    # ==================== 密钥查询测试 ====================

    def test_get_all_keys(self, service, mock_db, mock_jwt_key):
        """测试获取所有密钥"""
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_jwt_key]
        
        result = service.get_all_keys()
        
        assert result == [mock_jwt_key]

    def test_get_key_by_id(self, service, mock_db, mock_jwt_key):
        """测试根据版本号获取密钥"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_jwt_key
        
        result = service.get_key_by_id("v1")
        
        assert result == mock_jwt_key

    def test_get_active_key(self, service, mock_db, mock_config, mock_jwt_key):
        """测试获取当前活跃密钥"""
        with patch.object(service, 'get_config', return_value=mock_config), \
             patch.object(service, 'get_key_by_id', return_value=mock_jwt_key):
            result = service.get_active_key()
        
        assert result == mock_jwt_key

    def test_get_current_version(self, service, mock_db, mock_config):
        """测试获取当前版本号"""
        mock_db.query.return_value.first.return_value = mock_config
        
        result = service.get_current_version()
        
        assert result == "v1"

    # ==================== 密钥生成测试 ====================

    def test_generate_key_value(self, service):
        """测试生成密钥值"""
        result = service._generate_key_value()
        
        # secrets.token_urlsafe(64) 生成约 86 字符的 base64 字符串
        assert len(result) > 60
        assert isinstance(result, str)

    def test_get_next_key_id_empty(self, service, mock_db):
        """测试没有密钥时返回 v1"""
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        result = service._get_next_key_id()
        
        assert result == "v1"

    def test_get_next_key_id_single(self, service, mock_db, mock_jwt_key):
        """测试单个密钥时返回 v2"""
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_jwt_key]
        
        result = service._get_next_key_id()
        
        assert result == "v2"

    def test_generate_key(self, service, mock_db, mock_jwt_key):
        """测试生成新密钥"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        result = service.generate_key()
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_generate_key_existing(self, service, mock_db, mock_jwt_key):
        """测试生成已存在的密钥版本"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_jwt_key
        
        with pytest.raises(ValueError, match="密钥版本 v1 已存在"):
            service.generate_key("v1")

    def test_generate_key_with_id(self, service, mock_db):
        """测试指定版本号生成密钥"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        result = service.generate_key("v5")
        
        # 验证添加了2个对象（密钥和日志）
        assert mock_db.add.call_count == 2

    # ==================== 密钥切换测试 ====================

    def test_switch_version(self, service, mock_db, mock_config, mock_jwt_key):
        """测试切换密钥版本"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_jwt_key
        mock_db.query.return_value.first.return_value = mock_config
        
        result = service.switch_version("v1")
        
        assert result == True
        mock_db.commit.assert_called()

    def test_switch_version_not_found(self, service, mock_db, mock_config):
        """测试切换不存在的版本"""
        with patch.object(service, 'get_key_by_id', return_value=None), \
             patch.object(service, 'get_config', return_value=mock_config):
            result = service.switch_version("v999")
        
        assert result == False

    # ==================== 状态查询测试 ====================

    @patch('app.services.jwt_rotation_service.settings')
    def test_get_status(self, mock_settings, service, mock_db, mock_config, mock_jwt_key):
        """测试获取轮换状态"""
        mock_settings.SECRET_KEY = "test-secret"
        mock_db.query.return_value.first.return_value = mock_config
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_jwt_key]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        result = service.get_status()
        
        assert "enabled" in result
        assert "current_version" in result
        assert "total_keys" in result
        assert "keys" in result
        assert "history" in result

    # ==================== 一键轮换测试 ====================

    def test_full_rotation(self, service, mock_db, mock_config):
        """测试一键轮换"""
        mock_db.query.return_value.first.return_value = mock_config
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        result = service.full_rotation()
        
        assert result["success"] == True
        assert "new_version" in result
        assert "key_preview" in result

    # ==================== 删除密钥测试 ====================

    def test_delete_key(self, service, mock_db, mock_config, mock_jwt_key):
        """测试删除密钥"""
        # 使用 v3 来删除，这样不会与 mock_jwt_key (v1) 冲突
        with patch.object(service, 'get_current_version', return_value="v2"), \
             patch.object(service, 'get_key_by_id', return_value=mock_jwt_key):
            result = service.delete_key("v3")
        
        assert result == True
        # 会调用 add(log) 和 delete(key)，然后 commit
        assert mock_db.add.called
        mock_db.delete.assert_called_with(mock_jwt_key)
        mock_db.commit.assert_called()

    def test_delete_key_current_active(self, service, mock_db, mock_config):
        """测试不能删除当前活跃密钥"""
        mock_db.query.return_value.first.return_value = mock_config
        
        with pytest.raises(ValueError, match="不能删除当前活跃的密钥版本"):
            service.delete_key("v1")

    def test_delete_key_not_found(self, service, mock_db, mock_config):
        """测试删除不存在的密钥"""
        mock_db.query.return_value.first.return_value = mock_config
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = service.delete_key("v999")
        
        assert result == False
