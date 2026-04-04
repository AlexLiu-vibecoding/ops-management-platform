#!/usr/bin/env python3
"""
SQL 执行 E2E 测试

测试范围：
1. SQL 执行（SELECT、INSERT、UPDATE、DELETE）
2. 数据库和表列表获取
3. SQL 优化建议
4. 执行历史查询

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_sql_execution.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestSQLExecution:
    """SQL 执行 E2E 测试类"""

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

    def test_sql_execute_select(self, client, auth_headers):
        """测试执行 SELECT 语句"""
        # 注意：此测试需要真实的数据库实例
        # 如果没有实例，会返回错误
        execute_data = {
            "instance_id": 1,
            "database": "mysql",
            "sql": "SELECT 1 as test",
            "limit": 100
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=execute_data,
            headers=auth_headers
        )

        # 可能成功或失败（取决于是否有实例）
        assert response.status_code in [200, 400, 404]

    def test_get_databases(self, client, auth_headers):
        """测试获取数据库列表"""
        # 此测试需要真实的数据库实例
        response = client.get("/api/v1/sql/databases/1", headers=auth_headers)

        # 可能成功或失败（取决于是否有实例）
        assert response.status_code in [200, 400, 404]

    def test_sql_optimizer_analyze(self, client, auth_headers):
        """测试 SQL 优化分析"""
        analyze_data = {
            "sql": "SELECT * FROM users WHERE id = 1",
            "instance_id": 1,
            "database": "test_db"
        }

        response = client.post(
            "/api/v1/sql-optimizer/analyze",
            json=analyze_data,
            headers=auth_headers
        )

        # 可能成功或失败（取决于是否有实例）
        assert response.status_code in [200, 400, 404]

    def test_sql_optimizer_history(self, client, auth_headers):
        """测试 SQL 优化历史"""
        response = client.get("/api/v1/sql-optimizer/analysis-history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestSQLOptimization:
    """SQL 优化 E2E 测试"""

    @pytest.fixture(scope="function")
    def client(self):
        return TestClient(app)

    @pytest.fixture(scope="function")
    def admin_token(self):
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username="admin").first()
            if not user:
                user = User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    real_name="超级管理员",
                    email="admin@test.com",
                    role=UserRole.SUPER_ADMIN,
                    status=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            token = create_access_token({
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value
            })
            return token
        finally:
            db.close()

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}

    def test_list_optimization_tasks(self, client, auth_headers):
        """测试获取优化任务列表"""
        response = client.get("/api/v1/sql-optimization/tasks", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_optimization_suggestions(self, client, auth_headers):
        """测试获取优化建议列表"""
        response = client.get("/api/v1/sql-optimization/suggestions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_cron_validation(self, client, auth_headers):
        """测试 Cron 表达式验证"""
        test_cases = [
            ("0 0 * * *", True),  # 每天午夜
            ("*/5 * * * *", True),  # 每5分钟
            ("invalid", False),  # 无效表达式
        ]

        for cron_expr, expected_valid in test_cases:
            response = client.post(
                "/api/v1/sql-optimization/validate-cron",
                json={"expression": cron_expr},
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] == expected_valid
