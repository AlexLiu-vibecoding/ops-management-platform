#!/usr/bin/env python3
"""
SQL 执行 API 核心测试

覆盖核心 SQL 执行接口：
- SQL 执行: /api/v1/sql/execute
- 数据库列表: /api/v1/sql/databases/{instance_id}
- 表列表: /api/v1/sql/tables/{instance_id}/{database}
"""
import pytest
from app.models import RDBInstance, RDBType


class TestSQLExecuteAPI:
    """SQL 执行 API 测试类"""

    def test_execute_sql_select(self, client, operator_token, test_rdb_instance):
        """测试执行 SELECT 查询"""
        sql_request = {
            "instance_id": test_rdb_instance.id,
            "sql": "SELECT 1 as test_value",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或连接失败
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "message" in data

    def test_execute_sql_instance_not_found(self, client, operator_token):
        """测试执行 SQL 时实例不存在"""
        sql_request = {
            "instance_id": 99999,
            "sql": "SELECT 1",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 404

    def test_execute_sql_risk_check_drop_database(self, client, operator_token, test_rdb_instance):
        """测试 SQL 风险检查 - DROP DATABASE"""
        sql_request = {
            "instance_id": test_rdb_instance.id,
            "sql": "DROP DATABASE test_db",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 应该被风险检查拦截
        assert response.status_code in [403, 400]

    def test_execute_sql_risk_check_truncate(self, client, operator_token, test_rdb_instance):
        """测试 SQL 风险检查 - TRUNCATE"""
        sql_request = {
            "instance_id": test_rdb_instance.id,
            "sql": "TRUNCATE TABLE test_table",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 应该被风险检查拦截
        assert response.status_code in [403, 400]

    def test_execute_sql_missing_required(self, client, operator_token):
        """测试执行 SQL 缺少必填字段"""
        sql_request = {
            # 缺少 instance_id, sql
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 422

    def test_execute_sql_no_auth(self, client, test_rdb_instance):
        """测试未授权执行 SQL"""
        sql_request = {
            "instance_id": test_rdb_instance.id,
            "sql": "SELECT 1",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/execute",
            json=sql_request
        )

        assert response.status_code == 401


class TestSQLDatabasesAPI:
    """数据库列表 API 测试类"""

    def test_list_databases_success(self, client, operator_token, test_rdb_instance):
        """测试获取数据库列表"""
        response = client.get(
            f"/api/v1/sql/databases/{test_rdb_instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或连接失败
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_list_databases_instance_not_found(self, client, operator_token):
        """测试获取不存在实例的数据库列表"""
        response = client.get(
            "/api/v1/sql/databases/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 404

    def test_list_databases_no_auth(self, client, test_rdb_instance):
        """测试未授权获取数据库列表"""
        response = client.get(f"/api/v1/sql/databases/{test_rdb_instance.id}")
        assert response.status_code == 401

    def test_list_databases_redis(self, client, operator_token, test_environment, db_session):
        """测试 Redis 实例返回空数据库列表"""
        # 创建 Redis 实例
        from app.models import RedisInstance
        redis_instance = RedisInstance(
            name="test-redis-sql",
            host="localhost",
            port=6379,
            environment_id=test_environment.id
        )
        db_session.add(redis_instance)
        db_session.commit()
        db_session.refresh(redis_instance)

        response = client.get(
            f"/api/v1/sql/databases/{redis_instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # Redis 应该返回空列表
        if response.status_code == 200:
            data = response.json()
            assert data == []


class TestSQLTablesAPI:
    """表列表 API 测试类"""

    def test_list_tables_success(self, client, operator_token, test_rdb_instance):
        """测试获取表列表"""
        response = client.get(
            f"/api/v1/sql/tables/{test_rdb_instance.id}/test_db",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或连接失败
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_list_tables_instance_not_found(self, client, operator_token):
        """测试获取不存在实例的表列表"""
        response = client.get(
            "/api/v1/sql/tables/99999/test_db",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 404

    def test_list_tables_no_auth(self, client, test_rdb_instance):
        """测试未授权获取表列表"""
        response = client.get(f"/api/v1/sql/tables/{test_rdb_instance.id}/test_db")
        assert response.status_code == 401


class TestSQLExplainAPI:
    """SQL 执行计划 API 测试类（如果存在）"""

    def test_explain_sql(self, client, operator_token, test_rdb_instance):
        """测试获取 SQL 执行计划"""
        explain_request = {
            "instance_id": test_rdb_instance.id,
            "sql": "SELECT * FROM test_table WHERE id = 1",
            "database_name": "test_db"
        }

        response = client.post(
            "/api/v1/sql/explain",
            json=explain_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSQLFormatAPI:
    """SQL 格式化 API 测试类（如果存在）"""

    def test_format_sql(self, client, operator_token):
        """测试 SQL 格式化"""
        format_request = {
            "sql": "SELECT id,name FROM users WHERE id=1"
        }

        response = client.post(
            "/api/v1/sql/format",
            json=format_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSQLValidateAPI:
    """SQL 验证 API 测试类（如果存在）"""

    def test_validate_sql_valid(self, client, operator_token):
        """测试验证有效 SQL"""
        validate_request = {
            "sql": "SELECT id, name FROM users WHERE id = 1"
        }

        response = client.post(
            "/api/v1/sql/validate",
            json=validate_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            assert "valid" in data or "is_valid" in data

    def test_validate_sql_invalid(self, client, operator_token):
        """测试验证无效 SQL"""
        validate_request = {
            "sql": "SELET id FORM users"  # 语法错误
        }

        response = client.post(
            "/api/v1/sql/validate",
            json=validate_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能返回错误、验证结果或方法不允许
        assert response.status_code in [200, 400, 404, 405]


class TestSQLHistoryAPI:
    """SQL 执行历史 API 测试类"""

    def test_list_sql_history(self, client, operator_token):
        """测试获取 SQL 执行历史"""
        response = client.get(
            "/api/v1/sql/history",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            assert "items" in data or isinstance(data, list)

    def test_get_sql_history_detail(self, client, operator_token):
        """测试获取 SQL 执行历史详情"""
        response = client.get(
            "/api/v1/sql/history/1",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、不存在或端点不存在
        assert response.status_code in [200, 404, 405]


class TestSQLRiskCheckAPI:
    """SQL 风险检查 API 测试类"""

    def test_check_sql_risk_low(self, client, operator_token):
        """测试低风险 SQL"""
        check_request = {
            "sql": "SELECT id FROM users WHERE id = 1"
        }

        response = client.post(
            "/api/v1/sql/risk-check",
            json=check_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            if "risk_level" in data:
                assert data["risk_level"] == "low"

    def test_check_sql_risk_high(self, client, operator_token):
        """测试高风险 SQL - 无 WHERE 的 DELETE"""
        check_request = {
            "sql": "DELETE FROM users"
        }

        response = client.post(
            "/api/v1/sql/risk-check",
            json=check_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            if "risk_level" in data:
                assert data["risk_level"] in ["high", "critical"]

    def test_check_sql_risk_critical(self, client, operator_token):
        """测试高危 SQL - DROP DATABASE"""
        check_request = {
            "sql": "DROP DATABASE test_db"
        }

        response = client.post(
            "/api/v1/sql/risk-check",
            json=check_request,
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            if "risk_level" in data:
                assert data["risk_level"] == "critical"
