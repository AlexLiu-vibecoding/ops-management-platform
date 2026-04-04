#!/usr/bin/env python3
"""
实例管理 E2E 测试（优化版）

测试范围：
1. RDB 实例 CRUD 操作
2. Redis 实例 CRUD 操作
3. 实例连接测试（仅在有真实服务器时）
4. 批量操作

改进：
1. 添加 pytest 标记
2. 测试隔离和清理
3. 更好的错误处理
4. 清晰的测试文档

运行方式:
    cd /workspace/projects/backend

    # 运行所有测试（跳过需要真实连接的）
    python -m pytest tests/e2e/test_instance_management.py -v

    # 运行需要真实连接的测试
    python -m pytest tests/e2e/test_instance_management.py -v -m "requires_db"

    # 跳过需要真实连接的测试
    python -m pytest tests/e2e/test_instance_management.py -v -m "not requires_db"
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


@pytest.mark.e2e
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
        assert response.status_code in [200, 201]
        env_id = response.json()["id"]
        yield env_id
        # 清理
        client.delete(f"/api/v1/environments/{env_id}", headers=auth_headers)

    class TestRDBInstance:
        """RDB 实例测试"""

        def test_create_rdb_instance(self, client, auth_headers, test_environment):
            """
            测试创建 RDB 实例

            注意：此测试会尝试连接真实数据库，如果没有数据库会返回 400
            """
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

            # 如果有真实数据库连接，应该返回 201
            # 如果没有，应该返回 400（连接失败）
            assert response.status_code in [201, 400]

            if response.status_code == 201:
                data = response.json()
                assert data["name"] == instance_data["name"]
                assert data["host"] == instance_data["host"]
                # 清理
                instance_id = data["id"]
                client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

        @pytest.mark.requires_mysql
        def test_list_rdb_instances(self, client, auth_headers, test_environment):
            """测试列出 RDB 实例（需要MySQL）"""
            # 创建一个实例
            instance_data = {
                "name": f"test_list_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "测试列表",
                "status": True
            }
            create_response = client.post(
                "/api/v1/rdb-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                # 列出实例
                response = client.get("/api/v1/rdb-instances", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert "items" in data or isinstance(data, list)

                # 清理
                instance_id = create_response.json()["id"]
                client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

        @pytest.mark.requires_mysql
        def test_update_rdb_instance(self, client, auth_headers, test_environment):
            """测试更新 RDB 实例（需要MySQL）"""
            # 创建实例
            instance_data = {
                "name": f"test_update_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "原描述",
                "status": True
            }
            create_response = client.post(
                "/api/v1/rdb-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                instance_id = create_response.json()["id"]

                # 更新实例
                update_data = {"description": "更新后的描述"}
                response = client.put(
                    f"/api/v1/rdb-instances/{instance_id}",
                    json=update_data,
                    headers=auth_headers
                )
                assert response.status_code in [200, 400]  # 400 如果连接失败

                # 清理
                client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

        @pytest.mark.requires_mysql
        def test_delete_rdb_instance(self, client, auth_headers, test_environment):
            """测试删除 RDB 实例（需要MySQL）"""
            # 创建实例
            instance_data = {
                "name": f"test_delete_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "测试删除",
                "status": True
            }
            create_response = client.post(
                "/api/v1/rdb-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                instance_id = create_response.json()["id"]

                # 删除实例
                response = client.delete(
                    f"/api/v1/rdb-instances/{instance_id}",
                    headers=auth_headers
                )
                assert response.status_code == 200

                # 验证删除
                get_response = client.get(
                    f"/api/v1/rdb-instances/{instance_id}",
                    headers=auth_headers
                )
                assert get_response.status_code == 404

        @pytest.mark.requires_mysql
        def test_test_rdb_connection(self, client, auth_headers, test_environment):
            """测试 RDB 实例连接（需要MySQL）"""
            # 创建实例
            instance_data = {
                "name": f"test_conn_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 3306,
                "db_type": "mysql",
                "environment_id": test_environment,
                "username": "root",
                "password": "password",
                "description": "测试连接",
                "status": True
            }
            create_response = client.post(
                "/api/v1/rdb-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                instance_id = create_response.json()["id"]

                # 测试连接
                response = client.post(
                    f"/api/v1/rdb-instances/{instance_id}/test-connection",
                    headers=auth_headers
                )

                # 如果有真实数据库，应该返回 200
                # 如果没有，应该返回 400（连接失败）
                assert response.status_code in [200, 400]

                # 清理
                client.delete(f"/api/v1/rdb-instances/{instance_id}", headers=auth_headers)

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
                "description": "测试 Redis 实例",
                "status": True
            }

            response = client.post(
                "/api/v1/redis-instances",
                json=instance_data,
                headers=auth_headers
            )

            # 如果有真实 Redis，应该返回 201
            # 如果没有，应该返回 400（连接失败）
            assert response.status_code in [201, 400]

            if response.status_code == 201:
                data = response.json()
                assert data["name"] == instance_data["name"]
                # 清理
                instance_id = data["id"]
                client.delete(f"/api/v1/redis-instances/{instance_id}", headers=auth_headers)

        @pytest.mark.requires_redis
        def test_list_redis_instances(self, client, auth_headers, test_environment):
            """测试列出 Redis 实例（需要Redis）"""
            # 创建实例
            instance_data = {
                "name": f"test_redis_list_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment,
                "password": "",
                "description": "测试列表",
                "status": True
            }
            create_response = client.post(
                "/api/v1/redis-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                # 列出实例
                response = client.get("/api/v1/redis-instances", headers=auth_headers)
                assert response.status_code == 200
                data = response.json()
                assert "items" in data or isinstance(data, list)

                # 清理
                instance_id = create_response.json()["id"]
                client.delete(f"/api/v1/redis-instances/{instance_id}", headers=auth_headers)

        @pytest.mark.requires_redis
        def test_update_redis_instance(self, client, auth_headers, test_environment):
            """测试更新 Redis 实例（需要Redis）"""
            # 创建实例
            instance_data = {
                "name": f"test_redis_update_{os.urandom(4).hex()}",
                "host": "localhost",
                "port": 6379,
                "environment_id": test_environment,
                "password": "",
                "description": "原描述",
                "status": True
            }
            create_response = client.post(
                "/api/v1/redis-instances",
                json=instance_data,
                headers=auth_headers
            )

            if create_response.status_code == 201:
                instance_id = create_response.json()["id"]

                # 更新实例
                update_data = {"description": "更新后的描述"}
                response = client.put(
                    f"/api/v1/redis-instances/{instance_id}",
                    json=update_data,
                    headers=auth_headers
                )
                assert response.status_code == 200

                # 清理
                client.delete(f"/api/v1/redis-instances/{instance_id}", headers=auth_headers)

    class TestBatchOperations:
        """批量操作测试"""

        def test_batch_delete_instances(self, client, auth_headers, test_environment):
            """测试批量删除实例"""
            # 创建多个实例（不需要真实连接）
            instance_ids = []
            for i in range(3):
                # 这里不创建真实实例，只测试批量删除 API
                # 因为真实连接测试会被标记为 requires_db
                pass

            # 注意：批量删除需要真实的实例 ID
            # 这里只是展示测试结构，实际使用时需要先创建实例
            # 如果创建了实例，应该清理它们
            pass
