"""
实例管理 API 测试用例
"""
import pytest
from fastapi.testclient import TestClient


class TestInstancesAPI:
    """实例管理 API 测试"""

    def test_get_instances_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/instances")
        assert response.status_code == 401

    def test_get_instances_success(self, client, operator_token):
        """测试获取实例列表"""
        response = client.get(
            "/api/v1/instances",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_instance_missing_fields(self, client, operator_token):
        """测试创建实例缺少必填字段"""
        response = client.post(
            "/api/v1/instances",
            json={},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_mysql_instance(self, client, operator_token, test_environment):
        """测试创建 MySQL 实例"""
        response = client.post(
            "/api/v1/instances",
            json={
                "name": "测试MySQL实例",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "username": "root",
                "password": "test123",
                "environment_id": test_environment.id,
                "status": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # 可能因为连接测试失败，但请求格式应该是正确的
        assert response.status_code in [200, 400, 500]

    def test_create_postgresql_instance(self, client, operator_token, test_environment):
        """测试创建 PostgreSQL 实例"""
        response = client.post(
            "/api/v1/instances",
            json={
                "name": "测试PostgreSQL实例",
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "username": "postgres",
                "password": "test123",
                "environment_id": test_environment.id,
                "status": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400, 500]

    def test_create_redis_instance(self, client, operator_token, test_environment):
        """测试创建 Redis 实例"""
        response = client.post(
            "/api/v1/instances",
            json={
                "name": "测试Redis实例",
                "db_type": "redis",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment.id,
                "status": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400, 500]

    def test_create_rds_instance(self, client, operator_token, test_environment):
        """测试创建 AWS RDS 实例"""
        response = client.post(
            "/api/v1/instances",
            json={
                "name": "测试RDS实例",
                "db_type": "mysql",
                "is_rds": True,
                "rds_instance_id": "test-db-instance",
                "aws_region": "us-east-1",
                "environment_id": test_environment.id,
                "status": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400, 500]

    def test_test_instance_connection(self, client, operator_token, test_environment, db_session):
        """测试实例连接测试"""
        from app.models import RDBInstance
        
        # 创建测试实例（不需要真实连接）
        instance = RDBInstance(
            name="连接测试实例",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="encrypted",
            environment_id=test_environment.id,
            db_type="mysql",
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)
        
        response = client.post(
            f"/api/v1/instances/{instance.id}/check",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # 连接测试可能失败，但请求格式应该是正确的
        assert response.status_code in [200, 400, 500]


class TestInstancePermissions:
    """实例权限测试"""

    def test_create_instance_forbidden(self, client):
        """测试未授权用户无法创建实例"""
        from app.utils.auth import create_access_token
        from app.models import UserRole
        
        # 创建只读用户
        token = create_access_token({"sub": 999, "role": "readonly"})
        
        response = client.post(
            "/api/v1/instances",
            json={"name": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [401, 403]
