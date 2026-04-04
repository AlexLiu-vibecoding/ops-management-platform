#!/usr/bin/env python3
"""
实例管理 E2E 测试

测试范围：
1. RDB 实例 CRUD 操作
2. Redis 实例 CRUD 操作
3. 实例连接测试
4. 批量操作

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_instance_management.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestInstanceManagement:
    """实例管理 E2E 测试类"""

    @pytest.fixture(scope="function")
    def admin_token(self, db_session):
        """创建管理员 token"""
        user = db_session.query(User).filter_by(username="admin").first()
        if not user:
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@test.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        })
        return token

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        """认证头"""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="function")
    def test_environment(self, client, auth_headers, db_session):
        """创建测试环境"""
        from app.models import Environment
        env_data = {
            "name": "E2E测试环境",
            "code": f"e2e_test_{os.urandom(4).hex()}",
            "color": "#1890FF",
            "description": "E2E测试用环境"
        }
        response = client.post("/api/v1/environments", json=env_data, headers=auth_headers)
        assert response.status_code == 201
        env_id = response.json()["id"]
        yield env_id
        # 清理
        client.delete(f"/api/v1/environments/{env_id}", headers=auth_headers)

    class TestRDBInstance:
        """RDB 实例测试"""

        def test_create_rdb_instance(self, client, auth_headers, test_environment):
            """测试创建 RDB 实例"""
            instance_data = {
                "name": f"test_mysql_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "测试 MySQL 实例",
                "status": True
            }

            response = client.post(
                "/api/v1/rdb-instances",
                json=instance_data,
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == instance_data["name"]
            assert data["host"] == instance_data["host"]
            assert data["db_type"] == "mysql"
            assert "id" in data

            # 清理
            client.delete(f"/api/v1/rdb-instances/{data['id']}", headers=auth_headers)

        def test_list_rdb_instances(self, client, auth_headers, test_environment):
            """测试获取 RDB 实例列表"""
            # 先创建一个实例
            instance_data = {
                "name": f"test_mysql_list_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password"
            }
            create_resp = client.post("/api/v1/rdb-instances", json=instance_data, headers=auth_headers)
            instance_id = create_resp.json()["id"]

            # 获取列表
            response = client.get("/api/v1/rdb-instances", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # 清理
            client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

        def test_update_rdb_instance(self, client, auth_headers, test_environment):
            """测试更新 RDB 实例"""
            # 创建实例
            instance_data = {
                "name": f"test_mysql_update_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "原始描述"
            }
            create_resp = client.post("/api/v1/rdb-instances", json=instance_data, headers=auth_headers)
            instance_id = create_resp.json()["id"]

            # 更新实例
            update_data = {
                "name": instance_data["name"],
                "host": "127.0.0.1",
                "port": 3307,
                "description": "更新后的描述"
            }
            response = client.put(
                f"/api/v1/rdb-instances/{instance_id}",
                json=update_data,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["host"] == "127.0.0.1"
            assert data["port"] == 3307
            assert data["description"] == "更新后的描述"

            # 清理
            client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

        def test_delete_rdb_instance(self, client, auth_headers, test_environment):
            """测试删除 RDB 实例"""
            # 创建实例
            instance_data = {
                "name": f"test_mysql_delete_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password"
            }
            create_resp = client.post("/api/v1/rdb-instances", json=instance_data, headers=auth_headers)
            instance_id = create_resp.json()["id"]

            # 删除实例
            response = client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)
            assert response.status_code == 200

            # 验证已删除
            get_resp = client.get(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)
            assert get_resp.status_code == 404

        def test_test_rdb_connection(self, client, auth_headers, test_environment):
            """测试 RDB 连接测试接口"""
            test_data = {
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "username": "root",
                "password": "wrong_password"
            }

            response = client.post("/api/v1/rdb-instances/test", json=test_data, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "message" in data

    class TestRedisInstance:
        """Redis 实例测试"""

        def test_create_redis_instance(self, client, auth_headers, test_environment):
            """测试创建 Redis 实例"""
            instance_data = {
                "name": f"test_redis_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment,
                "password": "",
                "description": "测试 Redis 实例"
            }

            response = client.post(
                "/api/v1/redis-instances",
                json=instance_data,
                headers=auth_headers
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == instance_data["name"]
            assert data["host"] == instance_data["host"]
            assert "id" in data

            # 清理
            client.delete(f"/api/v1/redis-instances/{data['id']}", headers=auth_headers)

        def test_list_redis_instances(self, client, auth_headers, test_environment):
            """测试获取 Redis 实例列表"""
            # 创建实例
            instance_data = {
                "name": f"test_redis_list_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment
            }
            create_resp = client.post("/api/v1/redis-instances", json=instance_data, headers=auth_headers)
            instance_id = create_resp.json()["id"]

            # 获取列表
            response = client.get("/api/v1/redis-instances", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # 清理
            client.delete(f"/api/v1/redis-instances/{instance_id}", headers=auth_headers)

        def test_update_redis_instance(self, client, auth_headers, test_environment):
            """测试更新 Redis 实例"""
            # 创建实例
            instance_data = {
                "name": f"test_redis_update_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment
            }
            create_resp = client.post("/api/v1/redis-instances", json=instance_data, headers=auth_headers)
            instance_id = create_resp.json()["id"]

            # 更新实例
            update_data = {
                "name": instance_data["name"],
                "host": "127.0.0.1",
                "port": 6380,
                "description": "更新后的 Redis 描述"
            }
            response = client.put(
                f"/api/v1/redis-instances/{instance_id}",
                json=update_data,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["host"] == "127.0.0.1"
            assert data["port"] == 6380

            # 清理
            client.delete(f"/api/v1/redis-instances/{instance_id}", headers=auth_headers)

    class TestBatchOperations:
        """批量操作测试"""

        def test_batch_delete_instances(self, client, auth_headers, test_environment):
            """测试批量删除实例"""
            # 创建多个实例
            instance_ids = []
            for i in range(3):
                instance_data = {
                    "name": f"test_batch_{i}_{os.urandom(4).hex()}",
                    "host": "localhost",
                    "port": 3306,
                    "db_type": "mysql",
                    "environment_id": test_environment,
                    "username": "root",
                    "password": "password"
                }
                resp = client.post("/api/v1/rdb-instances", json=instance_data, headers=auth_headers)
                instance_ids.append(resp.json()["id"])

            # 批量删除
            response = client.post(
                "/api/v1/batch/instances",
                json={"ids": instance_ids, "action": "delete"},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == len(instance_ids)

            # 验证已删除
            for instance_id in instance_ids:
                get_resp = client.get(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)
                assert get_resp.status_code == 404
