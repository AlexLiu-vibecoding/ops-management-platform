"""
系统配置 API 测试用例
"""
import pytest
from fastapi.testclient import TestClient


class TestSystemOverview:
    """系统概览测试"""
    
    def test_get_overview_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/system/overview")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    
    def test_get_overview_operator_forbidden(self, client, operator_token):
        """测试普通用户无权访问"""
        response = client.get(
            "/api/v1/system/overview",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "权限不足"
    
    def test_get_overview_success(self, client, super_admin_token):
        """测试超级管理员获取系统概览"""
        response = client.get(
            "/api/v1/system/overview",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "python_version" in data
        assert "database_type" in data
        assert "storage_type" in data


class TestDatabaseConfig:
    """数据库类型配置测试"""
    
    def test_get_database_config_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/system/database-config")
        assert response.status_code == 401
    
    def test_get_database_config_success(self, client, super_admin_token):
        """测试获取数据库配置"""
        response = client.get(
            "/api/v1/system/database-config",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3  # MySQL, PostgreSQL, Redis
        
        # 验证配置项
        db_types = [item["db_type"] for item in data["items"]]
        assert "mysql" in db_types
        assert "postgresql" in db_types
        assert "redis" in db_types
    
    def test_update_database_config_enable(self, client, super_admin_token):
        """测试启用数据库类型"""
        response = client.put(
            "/api/v1/system/database-config/mysql",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_update_database_config_disable(self, client, super_admin_token):
        """测试禁用数据库类型"""
        response = client.put(
            "/api/v1/system/database-config/redis",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_update_database_config_invalid_type(self, client, super_admin_token):
        """测试更新无效的数据库类型"""
        response = client.put(
            "/api/v1/system/database-config/invalid",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 400
    
    def test_update_database_config_forbidden(self, client, operator_token):
        """测试普通用户无权更新"""
        response = client.put(
            "/api/v1/system/database-config/mysql",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403


class TestStorageConfig:
    """存储配置测试"""
    
    def test_get_storage_config_success(self, client, super_admin_token):
        """测试获取存储配置"""
        response = client.get(
            "/api/v1/system/storage-config",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "storage_type" in data
        assert "retention_days" in data
        assert "size_threshold" in data
    
    def test_update_storage_config(self, client, super_admin_token):
        """测试更新存储配置"""
        response = client.put(
            "/api/v1/system/storage-config",
            json={
                "retention_days": 60,
                "size_threshold": 20000
            },
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_update_storage_config_invalid_retention(self, client, super_admin_token):
        """测试更新无效的保留天数"""
        response = client.put(
            "/api/v1/system/storage-config",
            json={"retention_days": 500},  # 超过最大值
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_test_storage_config_local(self, client, super_admin_token):
        """测试本地存储连接"""
        response = client.post(
            "/api/v1/system/storage-config/test",
            json={"storage_type": "local"},
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data


class TestSecurityConfig:
    """安全配置测试"""
    
    def test_get_security_config_success(self, client, super_admin_token):
        """测试获取安全配置"""
        response = client.get(
            "/api/v1/system/security-config",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jwt_configured" in data
        assert "aes_configured" in data
        assert "token_expire_hours" in data
    
    def test_get_security_config_forbidden(self, client, operator_token):
        """测试普通用户无权访问安全配置"""
        response = client.get(
            "/api/v1/system/security-config",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403
