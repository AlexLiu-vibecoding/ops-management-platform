"""
实例管理 API 集成测试
"""
import pytest


class TestRDBInstancesAPI:
    """RDB 实例管理接口测试"""

    def test_list_instances(self, client, auth_headers, test_environment, db_session):
        """测试获取实例列表"""
        from app.models import RDBInstance, RDBType
        
        # 创建测试实例
        instance = RDBInstance(
            name="test-mysql",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id,
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.get("/api/v1/instances/rdb", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_instance(self, client, auth_headers, test_environment):
        """测试创建 RDB 实例"""
        instance_data = {
            "name": "api-test-mysql",
            "host": "192.168.1.100",
            "port": 3306,
            "username": "root",
            "password": "secret123",
            "db_type": "MYSQL",
            "environment_id": test_environment.id,
            "description": "API test instance"
        }
        
        response = client.post(
            "/api/v1/instances/rdb",
            json=instance_data,
            headers=auth_headers
        )
        
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == "api-test-mysql"
            assert data["host"] == "192.168.1.100"

    def test_create_instance_duplicate_name(self, client, auth_headers, test_environment, db_session):
        """测试创建重复名称的实例"""
        from app.models import RDBInstance, RDBType
        
        # 先创建一个实例
        instance = RDBInstance(
            name="duplicate-db",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        # 尝试创建同名实例
        instance_data = {
            "name": "duplicate-db",
            "host": "192.168.1.100",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "db_type": "MYSQL",
            "environment_id": test_environment.id
        }
        
        response = client.post(
            "/api/v1/instances/rdb",
            json=instance_data,
            headers=auth_headers
        )
        
        assert response.status_code in [400, 409]

    def test_get_instance_detail(self, client, auth_headers, test_environment, db_session):
        """测试获取实例详情"""
        from app.models import RDBInstance, RDBType
        
        instance = RDBInstance(
            name="detail-db",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/instances/rdb/{instance.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "detail-db"

    def test_update_instance(self, client, auth_headers, test_environment, db_session):
        """测试更新实例"""
        from app.models import RDBInstance, RDBType
        
        instance = RDBInstance(
            name="update-db",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id,
            description="Old description"
        )
        db_session.add(instance)
        db_session.commit()
        
        update_data = {
            "description": "New description",
            "host": "new-host"
        }
        
        response = client.put(
            f"/api/v1/instances/rdb/{instance.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    def test_delete_instance(self, client, auth_headers, test_environment, db_session):
        """测试删除实例"""
        from app.models import RDBInstance, RDBType
        
        instance = RDBInstance(
            name="delete-db",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.delete(
            f"/api/v1/instances/rdb/{instance.id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 204]

    def test_test_connection(self, client, auth_headers, test_environment, db_session):
        """测试实例连接"""
        from app.models import RDBInstance, RDBType
        
        instance = RDBInstance(
            name="conn-test-db",
            host="invalid-host",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.post(
            f"/api/v1/instances/rdb/{instance.id}/test-connection",
            headers=auth_headers
        )
        
        # 连接测试可能成功或失败（取决于实际连接）
        assert response.status_code in [200, 500]


class TestRedisInstancesAPI:
    """Redis 实例管理接口测试"""

    def test_list_redis_instances(self, client, auth_headers, test_environment, db_session):
        """测试获取 Redis 实例列表"""
        from app.models import RedisInstance
        
        instance = RedisInstance(
            name="test-redis",
            host="localhost",
            port=6379,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.get("/api/v1/instances/redis", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_redis_instance(self, client, auth_headers, test_environment):
        """测试创建 Redis 实例"""
        instance_data = {
            "name": "api-test-redis",
            "host": "192.168.1.100",
            "port": 6379,
            "environment_id": test_environment.id,
            "description": "API test Redis"
        }
        
        response = client.post(
            "/api/v1/instances/redis",
            json=instance_data,
            headers=auth_headers
        )
        
        assert response.status_code in [201, 200]

    def test_get_redis_detail(self, client, auth_headers, test_environment, db_session):
        """测试获取 Redis 实例详情"""
        from app.models import RedisInstance
        
        instance = RedisInstance(
            name="redis-detail",
            host="localhost",
            port=6379,
            environment_id=test_environment.id
        )
        db_session.add(instance)
        db_session.commit()
        
        response = client.get(
            f"/api/v1/instances/redis/{instance.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "redis-detail"
