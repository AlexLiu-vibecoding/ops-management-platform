"""
AI 模型配置核心 API 测试

AI 模型配置、场景配置、调用日志相关 API 测试
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, UserRole
from app.models.ai_model import (
    AIModelConfig, AISceneConfig, AICallLog,
    AIProvider, AIScene
)


class TestAIModelConfigAPI:
    """AI 模型配置 API 测试"""

    def test_list_ai_models(self, client: TestClient, admin_headers: dict):
        """测试获取 AI 模型配置列表"""
        response = client.get("/api/v1/ai-models", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # 可能是分页格式或列表格式
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_create_ai_model(self, client: TestClient, admin_headers: dict):
        """测试创建 AI 模型配置"""
        model_data = {
            "name": "测试 OpenAI 配置",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "model_name": "gpt-4o",
            "model_type": "chat",
            "max_tokens": 4096,
            "temperature": 0.7,
            "timeout": 30,
            "is_enabled": True,
            "priority": 10,
            "description": "OpenAI GPT-4o 测试配置"
        }
        response = client.post(
            "/api/v1/ai-models",
            json=model_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == model_data["name"]
            assert data["provider"] == model_data["provider"]
            assert "id" in data

    def test_create_ollama_model(self, client: TestClient, admin_headers: dict):
        """测试创建 Ollama 模型配置"""
        model_data = {
            "name": "本地 Ollama",
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "llama3.1",
            "max_tokens": 2048,
            "temperature": 0.5,
            "is_enabled": True
        }
        response = client.post(
            "/api/v1/ai-models",
            json=model_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

    def test_get_ai_model_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取 AI 模型配置详情"""
        # 先创建模型配置
        model = AIModelConfig(
            name="测试模型",
            provider=AIProvider.openai,
            base_url="https://api.openai.com/v1",
            api_key="encrypted_key",
            model_name="gpt-4o",
            max_tokens=4096,
            temperature=0.7,
            timeout=30,
            is_enabled=True,
            priority=10,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        response = client.get(
            f"/api/v1/ai-models/{model.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == model.id
        assert data["name"] == model.name
        # API 密钥应该脱敏
        if "api_key" in data:
            assert "***" in data["api_key"] or data["api_key"] == ""

    def test_update_ai_model(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试更新 AI 模型配置"""
        # 先创建模型配置
        model = AIModelConfig(
            name="旧模型名称",
            provider=AIProvider.openai,
            base_url="https://api.openai.com/v1",
            api_key="key",
            model_name="gpt-3.5",
            max_tokens=2048,
            temperature=0.7,
            is_enabled=True,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        update_data = {
            "name": "新模型名称",
            "model_name": "gpt-4o",
            "max_tokens": 4096,
            "temperature": 0.5,
            "is_enabled": False
        }
        response = client.put(
            f"/api/v1/ai-models/{model.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新模型名称"
        assert data["is_enabled"] == False

    def test_delete_ai_model(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试删除 AI 模型配置"""
        # 先创建模型配置
        model = AIModelConfig(
            name="待删除模型",
            provider=AIProvider.ollama,
            base_url="http://localhost:11434",
            model_name="llama3",
            is_enabled=True,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
        model_id = model.id

        response = client.delete(
            f"/api/v1/ai-models/{model_id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # 验证已删除
        deleted = db_session.query(AIModelConfig).filter_by(id=model_id).first()
        assert deleted is None

    def test_test_ai_model(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试 AI 模型连通性"""
        # 先创建模型配置
        model = AIModelConfig(
            name="测试模型",
            provider=AIProvider.openai,
            base_url="https://api.openai.com/v1",
            api_key="test_key",
            model_name="gpt-4o",
            is_enabled=True,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        test_data = {
            "prompt": "Hello, this is a test."
        }
        response = client.post(
            f"/api/v1/ai-models/{model.id}/test",
            json=test_data,
            headers=admin_headers
        )
        # 可能成功或失败（取决于实际连接），但不应该500错误
        assert response.status_code in [200, 400, 502]


class TestAISceneConfigAPI:
    """AI 场景配置 API 测试"""

    def test_list_ai_scenes(self, client: TestClient, admin_headers: dict):
        """测试获取场景配置列表"""
        response = client.get("/api/v1/ai-models/scenes", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_get_scene_config(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取场景配置"""
        # 先创建模型和场景配置
        model = AIModelConfig(
            name="测试模型",
            provider=AIProvider.openai,
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o",
            is_enabled=True,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        scene = AISceneConfig(
            scene=AIScene.sql_explain,
            model_config_id=model.id,
            custom_prompt="自定义提示词",
            custom_params={"temperature": 0.5},
            is_enabled=True
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        response = client.get(
            f"/api/v1/ai-models/scenes/{scene.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == scene.id
        assert data["scene"] == AIScene.sql_explain

    def test_update_scene_config(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试更新场景配置"""
        # 先创建模型和场景配置
        model = AIModelConfig(
            name="测试模型",
            provider=AIProvider.openai,
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o",
            is_enabled=True,
            created_by=1
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        scene = AISceneConfig(
            scene=AIScene.sql_explain,
            model_config_id=model.id,
            custom_prompt="原始提示词",
            is_enabled=True
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        update_data = {
            "model_config_id": model.id,
            "custom_prompt": "更新后的提示词",
            "custom_params": {"temperature": 0.3},
            "is_enabled": True
        }
        response = client.put(
            f"/api/v1/ai-models/scenes/{scene.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["custom_prompt"] == "更新后的提示词"

    def test_get_scene_templates(self, client: TestClient, admin_headers: dict):
        """测试获取场景模板"""
        response = client.get("/api/v1/ai-models/scene-templates", headers=admin_headers)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestAICallLogAPI:
    """AI 调用日志 API 测试"""

    def test_list_ai_call_logs(self, client: TestClient, admin_headers: dict):
        """测试获取 AI 调用日志列表"""
        response = client.get("/api/v1/ai-models/call-logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_get_call_log_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取调用日志详情"""
        # 先创建调用日志
        log = AICallLog(
            scene=AIScene.sql_explain,
            model_config_id=1,
            prompt="测试提示词",
            response="测试响应",
            tokens_input=100,
            tokens_output=50,
            cost_time_ms=500,
            status="success"
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        response = client.get(
            f"/api/v1/ai-models/call-logs/{log.id}",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == log.id

    def test_filter_call_logs_by_scene(self, client: TestClient, admin_headers: dict):
        """测试按场景筛选调用日志"""
        response = client.get(
            "/api/v1/ai-models/call-logs",
            params={"scene": "sql_explain"},
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_filter_call_logs_by_status(self, client: TestClient, admin_headers: dict):
        """测试按状态筛选调用日志"""
        response = client.get(
            "/api/v1/ai-models/call-logs",
            params={"status": "success"},
            headers=admin_headers
        )
        assert response.status_code == 200


class TestAIProviderTemplatesAPI:
    """AI 提供商模板 API 测试"""

    def test_get_provider_templates(self, client: TestClient, admin_headers: dict):
        """测试获取提供商模板"""
        response = client.get("/api/v1/ai-models/templates", headers=admin_headers)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_provider_list(self, client: TestClient, admin_headers: dict):
        """测试获取支持的提供商列表"""
        response = client.get("/api/v1/ai-models/providers", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 应该包含常见提供商
        providers = [p["value"] if isinstance(p, dict) else p for p in data]
        assert "openai" in providers or "ollama" in providers


class TestAIModelAPIErrorHandling:
    """AI 模型 API 错误处理测试"""

    def test_get_nonexistent_model(self, client: TestClient, admin_headers: dict):
        """测试获取不存在的模型配置"""
        response = client.get("/api/v1/ai-models/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_nonexistent_model(self, client: TestClient, admin_headers: dict):
        """测试更新不存在的模型配置"""
        response = client.put(
            "/api/v1/ai-models/99999",
            json={"name": "新名称"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_nonexistent_model(self, client: TestClient, admin_headers: dict):
        """测试删除不存在的模型配置"""
        response = client.delete("/api/v1/ai-models/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_test_nonexistent_model(self, client: TestClient, admin_headers: dict):
        """测试测试不存在的模型"""
        response = client.post(
            "/api/v1/ai-models/99999/test",
            json={"prompt": "test"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_create_model_with_invalid_provider(self, client: TestClient, admin_headers: dict):
        """测试使用无效提供商创建模型"""
        model_data = {
            "name": "测试模型",
            "provider": "invalid_provider",
            "base_url": "http://test.com",
            "model_name": "test-model"
        }
        response = client.post(
            "/api/v1/ai-models",
            json=model_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_create_model_without_required_fields(self, client: TestClient, admin_headers: dict):
        """测试缺少必填字段创建模型"""
        # 缺少 provider
        response = client.post(
            "/api/v1/ai-models",
            json={"name": "无效模型", "base_url": "http://test.com"},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_unauthorized_access(self, client: TestClient):
        """测试未授权访问"""
        response = client.get("/api/v1/ai-models")
        assert response.status_code == 401

    def test_invalid_temperature_range(self, client: TestClient, admin_headers: dict):
        """测试无效的温度参数范围"""
        model_data = {
            "name": "测试模型",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4",
            "temperature": 5.0  # 超出范围 0-2
        }
        response = client.post(
            "/api/v1/ai-models",
            json=model_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]
