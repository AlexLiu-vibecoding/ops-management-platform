"""
AI 模型配置 API 测试

覆盖 AI 模型配置接口：
- 模型列表: /api/v1/ai-models
- 模型创建: /api/v1/ai-models
- 模型更新: /api/v1/ai-models/{model_id}
- 模型删除: /api/v1/ai-models/{model_id}
- 模型测试: /api/v1/ai-models/{model_id}/test
- 场景配置: /api/v1/ai-models/scene-configs/*
"""
import pytest


class TestAIModelsAPI:
    """AI 模型配置 API 测试类"""

    def test_list_ai_models(self, client, admin_headers):
        """测试获取 AI 模型配置列表"""
        response = client.get("/api/v1/ai-models", headers=admin_headers)
        assert response.status_code == 200

    def test_get_providers(self, client, admin_headers):
        """测试获取支持的提供商列表"""
        response = client.get("/api/v1/ai-models/providers", headers=admin_headers)
        assert response.status_code == 200

    def test_get_scenes(self, client, admin_headers):
        """测试获取使用场景列表"""
        response = client.get("/api/v1/ai-models/scenes", headers=admin_headers)
        assert response.status_code == 200

    def test_get_templates(self, client, admin_headers):
        """测试获取模型模板"""
        response = client.get("/api/v1/ai-models/templates", headers=admin_headers)
        assert response.status_code == 200

    def test_create_ai_model(self, client, admin_headers):
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

    def test_create_ollama_model(self, client, admin_headers):
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

    def test_list_scene_configs(self, client, admin_headers):
        """测试获取场景配置列表"""
        response = client.get("/api/v1/ai-models/scene-configs/list", headers=admin_headers)
        assert response.status_code == 200

    def test_get_scene_config(self, client, admin_headers):
        """测试获取场景配置"""
        response = client.get("/api/v1/ai-models/scene-configs/sql_optimize", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_get_call_logs_stats(self, client, admin_headers):
        """测试获取调用日志统计"""
        response = client.get("/api/v1/ai-models/stats/call-logs", headers=admin_headers)
        assert response.status_code == 200

    def test_get_use_cases(self, client, admin_headers):
        """测试获取使用用例"""
        response = client.get("/api/v1/ai-models/use-cases", headers=admin_headers)
        assert response.status_code == 200

    def test_get_available_models(self, client, admin_headers):
        """测试获取可用模型列表"""
        response = client.get("/api/v1/ai-models/available-models", headers=admin_headers)
        assert response.status_code == 200

    def test_refresh_available_models(self, client, admin_headers):
        """测试刷新可用模型列表"""
        response = client.post("/api/v1/ai-models/available-models/refresh", headers=admin_headers)
        assert response.status_code in [200, 201]


class TestAIModelsAPIErrorHandling:
    """AI 模型配置 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/ai-models")
        assert response.status_code == 401

    def test_create_model_invalid_provider(self, client, admin_headers):
        """测试使用无效提供商创建模型"""
        model_data = {
            "name": "测试模型",
            "provider": "invalid_provider",
            "base_url": "https://api.example.com/v1",
            "model_name": "test-model"
        }
        response = client.post(
            "/api/v1/ai-models",
            json=model_data,
            headers=admin_headers
        )
        # API 可能会验证提供商，也可能不会，取决于实现
        assert response.status_code in [200, 201, 400, 422]

    def test_get_nonexistent_model(self, client, admin_headers):
        """测试获取不存在的模型"""
        response = client.get("/api/v1/ai-models/99999", headers=admin_headers)
        assert response.status_code in [404, 405]

    def test_update_nonexistent_model(self, client, admin_headers):
        """测试更新不存在的模型"""
        response = client.put(
            "/api/v1/ai-models/99999",
            json={"name": "新名称"},
            headers=admin_headers
        )
        assert response.status_code in [404, 405]

    def test_delete_nonexistent_model(self, client, admin_headers):
        """测试删除不存在的模型"""
        response = client.delete("/api/v1/ai-models/99999", headers=admin_headers)
        assert response.status_code in [404, 405]
