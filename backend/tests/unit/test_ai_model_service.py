"""
AI模型服务测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.ai_model_service import (
    decrypt_api_key,
    get_scene_model,
    get_all_scene_models,
    get_available_model,
    get_all_available_models,
    call_with_scene,
    call_with_fallback
)
from app.models.ai_model import AIModelConfig, AISceneConfig, AICallLog


class TestDecryptApiKey:
    """API密钥解密测试"""

    def test_decrypt_empty_key(self):
        """测试解密空密钥"""
        result = decrypt_api_key("")
        assert result == ""

    def test_decrypt_valid_key(self):
        """测试解密密钥"""
        # 由于 aes_cipher 使用默认密钥，我们测试调用流程
        with patch('app.services.ai_model_service.aes_cipher') as mock_cipher:
            mock_cipher.decrypt.return_value = "decrypted_key"
            result = decrypt_api_key("encrypted_key")
            assert result == "decrypted_key"


class TestGetSceneModel:
    """获取场景模型测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock()

    def test_get_scene_model_found(self, mock_db):
        """测试获取场景模型成功"""
        # 创建模拟的场景配置
        mock_scene_config = Mock()
        mock_scene_config.model_config_id = 1

        # 创建模拟的模型配置
        mock_model = Mock()
        mock_model.id = 1
        mock_model.name = "Test Model"
        mock_model.is_enabled = True

        # 配置查询链
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [mock_scene_config, mock_model]
        mock_db.query.return_value = mock_query

        result = get_scene_model(mock_db, "sql_optimize")

        assert result is not None
        assert result.id == 1

    def test_get_scene_model_not_found(self, mock_db):
        """测试场景配置不存在"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        result = get_scene_model(mock_db, "non_existent_scene")

        assert result is None

    def test_get_scene_model_disabled(self, mock_db):
        """测试场景模型被禁用"""
        mock_scene_config = Mock()
        mock_scene_config.model_config_id = 1

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [mock_scene_config, None]
        mock_db.query.return_value = mock_query

        result = get_scene_model(mock_db, "sql_optimize")

        assert result is None


class TestGetAllSceneModels:
    """获取所有场景模型测试"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    def test_get_all_scene_models_found(self, mock_db):
        """测试获取场景所有模型"""
        mock_model = Mock()
        mock_model.id = 1
        mock_model.name = "Test Model"

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [
            Mock(model_config_id=1),
            mock_model
        ]
        mock_db.query.return_value = mock_query

        result = get_all_scene_models(mock_db, "sql_optimize")

        assert len(result) == 1
        assert result[0].id == 1

    def test_get_all_scene_models_not_found(self, mock_db):
        """测试获取场景模型为空"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        result = get_all_scene_models(mock_db, "non_existent")

        assert len(result) == 0


class TestCompatibleAPI:
    """兼容旧API测试"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    def test_get_available_model(self, mock_db):
        """测试兼容API：获取可用模型"""
        mock_model = Mock()
        mock_model.id = 1

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [
            Mock(model_config_id=1),
            mock_model
        ]
        mock_db.query.return_value = mock_query

        result = get_available_model(mock_db, "sql_optimize")

        assert result is not None
        assert result.id == 1

    def test_get_all_available_models(self, mock_db):
        """测试兼容API：获取所有可用模型"""
        mock_model = Mock()
        mock_model.id = 1

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = [
            Mock(model_config_id=1),
            mock_model
        ]
        mock_db.query.return_value = mock_query

        result = get_all_available_models(mock_db, "sql_optimize")

        assert len(result) == 1

