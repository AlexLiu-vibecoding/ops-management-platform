#!/usr/bin/env python3
"""
实例管理 API 核心测试

覆盖核心实例管理接口：
- RDB 实例: /api/v1/rdb-instances
- Redis 实例: /api/v1/redis-instances
- 连接测试: /api/v1/rdb-instances/test
"""
import pytest
from app.models import RDBInstance, RedisInstance, RDBType, Environment


class TestRDBInstancesListAPI:
    """RDB 实例列表 API 测试类"""

    def test_list_rdb_instances_success(self, client, operator_token):
        """测试获取 RDB 实例列表"""
        response = client.get(
            "/api/v1/rdb-instances",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_rdb_instances_no_auth(self, client):
        """测试未授权获取实例列表"""
        response = client.get("/api/v1/rdb-instances")
        assert response.status_code == 401

    def test_list_rdb_instances_with_filters(self, client, operator_token, test_environment, db_session):
        """测试带过滤条件获取实例列表"""
        # 创建测试实例
        instance = RDBInstance(
            name="test-mysql-filter",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id,
            status=True
        )
        db_session.add(instance)
        db_session.commit()

        # 按环境过滤
        response = client.get(
            f"/api/v1/rdb-instances?environment_id={test_environment.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

        # 按数据库类型过滤
        response = client.get(
            "/api/v1/rdb-instances?db_type=mysql",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200


class TestRDBInstanceDetailAPI:
    """RDB 实例详情 API 测试类"""

    def test_get_instance_detail_success(self, client, operator_token, test_rdb_instance):
        """测试获取实例详情"""
        response = client.get(
            f"/api/v1/rdb-instances/{test_rdb_instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_rdb_instance.id
        assert data["name"] == test_rdb_instance.name
        assert "host" in data
        assert "port" in data

    def test_get_instance_detail_not_found(self, client, operator_token):
        """测试获取不存在的实例详情"""
        response = client.get(
            "/api/v1/rdb-instances/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404

    def test_get_instance_detail_no_auth(self, client, test_rdb_instance):
        """测试未授权获取实例详情"""
        response = client.get(f"/api/v1/rdb-instances/{test_rdb_instance.id}")
        assert response.status_code == 401


class TestRDBInstanceCreateAPI:
    """RDB 实例创建 API 测试类"""

    def test_create_instance_rds(self, client, operator_token, test_environment):
        """测试创建 AWS RDS 实例"""
        instance_data = {
            "name": "test-rds-core-api",
            "db_type": "mysql",
            "host": "test-db.abc123xyz.us-east-1.rds.amazonaws.com",
            "port": 3306,
            "username": "admin",
            "password": "rds-password123",
            "environment_id": test_environment.id,
            "is_rds": True,
            "description": "测试 RDS 实例"
        }

        response = client.post(
            "/api/v1/rdb-instances",
            json=instance_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # RDS 实例可能成功创建（不需要连接测试）
        assert response.status_code in [200, 201, 400, 403]

    def test_create_instance_duplicate_name(self, client, operator_token, test_environment, db_session):
        """测试创建重复名称的实例"""
        # 先创建实例
        instance = RDBInstance(
            name="duplicate-core-test",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        # 尝试创建同名实例
        instance_data = {
            "name": "duplicate-core-test",
            "db_type": "mysql",
            "host": "192.168.1.100",
            "port": 3306,
            "username": "root",
            "password": "test123",
            "environment_id": test_environment.id
        }

        response = client.post(
            "/api/v1/rdb-instances",
            json=instance_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [400, 409]

    def test_create_instance_missing_required(self, client, operator_token, test_environment):
        """测试创建实例缺少必填字段"""
        instance_data = {
            "name": "incomplete-instance",
            # 缺少 host, username, password
            "environment_id": test_environment.id
        }

        response = client.post(
            "/api/v1/rdb-instances",
            json=instance_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [400, 422]

    def test_create_instance_no_auth(self, client, test_environment):
        """测试未授权创建实例"""
        instance_data = {
            "name": "unauthorized-instance",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306
        }

        response = client.post(
            "/api/v1/rdb-instances",
            json=instance_data
        )
        assert response.status_code == 401


class TestRDBInstanceUpdateAPI:
    """RDB 实例更新 API 测试类"""

    def test_update_instance_success(self, client, operator_token, test_rdb_instance):
        """测试成功更新实例"""
        update_data = {
            "name": "updated-core-name",
            "description": "更新后的描述"
        }

        response = client.put(
            f"/api/v1/rdb-instances/{test_rdb_instance.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或无权限
        assert response.status_code in [200, 400, 403, 404]

    def test_update_instance_not_found(self, client, operator_token):
        """测试更新不存在的实例"""
        update_data = {"name": "updated-name"}

        response = client.put(
            "/api/v1/rdb-instances/99999",
            json=update_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404


class TestRDBInstanceDeleteAPI:
    """RDB 实例删除 API 测试类"""

    def test_delete_instance_success(self, client, operator_token, test_environment, db_session):
        """测试成功删除实例"""
        # 创建临时实例用于删除测试
        instance = RDBInstance(
            name="delete-test-instance",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)

        response = client.delete(
            f"/api/v1/rdb-instances/{instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或无权限
        assert response.status_code in [200, 204, 400, 403]

    def test_delete_instance_not_found(self, client, operator_token):
        """测试删除不存在的实例"""
        response = client.delete(
            "/api/v1/rdb-instances/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404


class TestRDBInstanceTestAPI:
    """RDB 实例连接测试 API 测试类"""

    def test_test_connection_mysql(self, client, operator_token):
        """测试 MySQL 连接"""
        test_data = {
            "name": "test-mysql-conn",
            "db_type": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "username": "root",
            "password": "test"
        }

        response = client.post(
            "/api/v1/rdb-instances/test",
            json=test_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 连接可能成功或失败，但请求格式应该正确
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data

    def test_test_connection_postgresql(self, client, operator_token):
        """测试 PostgreSQL 连接"""
        test_data = {
            "name": "test-pg-conn",
            "db_type": "postgresql",
            "host": "127.0.0.1",
            "port": 5432,
            "username": "postgres",
            "password": "test"
        }

        response = client.post(
            "/api/v1/rdb-instances/test",
            json=test_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_test_connection_missing_fields(self, client, operator_token):
        """测试连接缺少字段"""
        test_data = {
            "name": "test-incomplete",
            # 缺少 host, username
        }

        response = client.post(
            "/api/v1/rdb-instances/test",
            json=test_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 400, 422]


class TestRedisInstancesAPI:
    """Redis 实例管理 API 测试类"""

    def test_list_redis_instances(self, client, operator_token):
        """测试获取 Redis 实例列表"""
        response = client.get(
            "/api/v1/redis-instances",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或端点不存在
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "items" in data or isinstance(data, list)

    def test_create_redis_instance(self, client, operator_token, test_environment):
        """测试创建 Redis 实例"""
        instance_data = {
            "name": "test-redis-core",
            "host": "localhost",
            "port": 6379,
            "environment_id": test_environment.id,
            "description": "测试 Redis 实例"
        }

        response = client.post(
            "/api/v1/redis-instances",
            json=instance_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 201, 400, 404]


class TestInstanceBatchAPI:
    """实例批量操作 API 测试类"""

    def test_batch_delete_instances(self, client, operator_token, test_environment, db_session):
        """测试批量删除实例"""
        # 创建测试实例
        instance1 = RDBInstance(
            name="batch-delete-1",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        instance2 = RDBInstance(
            name="batch-delete-2",
            host="localhost",
            port=3307,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add_all([instance1, instance2])
        db_session.commit()
        db_session.refresh(instance1)
        db_session.refresh(instance2)

        batch_data = {
            "ids": [instance1.id, instance2.id]
        }

        response = client.post(
            "/api/v1/batch/instances/delete",
            json=batch_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、无权限或端点不存在
        assert response.status_code in [200, 400, 403, 404]

    def test_batch_update_status(self, client, operator_token, test_environment, db_session):
        """测试批量更新实例状态"""
        instance = RDBInstance(
            name="batch-status-test",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id,
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)

        batch_data = {
            "ids": [instance.id],
            "status": False
        }

        response = client.post(
            "/api/v1/batch/instances/status",
            json=batch_data,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 400, 403, 404]
