"""
审计日志和监控 API 测试用例
"""
import pytest
from datetime import datetime, timedelta


class TestAuditAPI:
    """审计日志 API 测试"""

    def test_get_audit_logs_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/audit/logs")
        assert response.status_code == 401

    def test_get_audit_logs_success(self, client, operator_token):
        """测试获取审计日志列表"""
        response = client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_get_audit_logs_with_filters(self, client, operator_token):
        """测试带过滤条件获取审计日志"""
        response = client.get(
            "/api/v1/audit/logs",
            params={
                "operation_type": "login",
                "page": 1,
                "limit": 20
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_audit_operation_types(self, client, operator_token):
        """测试获取操作类型列表"""
        response = client.get(
            "/api/v1/audit/operation-types",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSlowQueryAPI:
    """慢查询监控 API 测试"""

    def test_get_slow_queries_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/slow-query/1")
        assert response.status_code == 401

    def test_get_slow_queries_instance_not_found(self, client, operator_token):
        """测试实例不存在"""
        response = client.get(
            "/api/v1/slow-query/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404

    def test_get_slow_queries_success(self, client, operator_token, test_environment, db_session):
        """测试获取慢查询列表"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="慢查询测试实例",
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
        
        response = client.get(
            f"/api/v1/slow-query/{instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # 可能因为没有数据返回空列表
        assert response.status_code in [200, 400]

    def test_get_slow_query_statistics(self, client, operator_token, test_environment, db_session):
        """测试获取慢查询统计"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="统计测试实例",
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
        
        response = client.get(
            f"/api/v1/slow-query/{instance.id}/statistics",
            params={"hours": 24},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400]


class TestPerformanceAPI:
    """性能监控 API 测试"""

    def test_get_performance_history_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/performance/1/history")
        assert response.status_code == 401

    def test_get_performance_history_success(self, client, operator_token, test_environment, db_session):
        """测试获取性能历史数据"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="性能测试实例",
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
        
        response = client.get(
            f"/api/v1/performance/{instance.id}/history",
            params={"hours": 1},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400]

    def test_get_performance_statistics(self, client, operator_token, test_environment, db_session):
        """测试获取性能统计数据"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="性能统计实例",
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
        
        response = client.get(
            f"/api/v1/performance/{instance.id}/statistics",
            params={"hours": 24},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400]


class TestDashboardAPI:
    """仪表盘 API 测试"""

    def test_get_dashboard_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    def test_get_dashboard_success(self, client, operator_token):
        """测试获取仪表盘数据"""
        response = client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # 验证返回数据结构
        assert "instance_count" in data
        assert "pending_approval_count" in data


class TestSQLAPI:
    """SQL 操作 API 测试"""

    def test_get_databases_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/sql/databases/1")
        assert response.status_code == 401

    def test_get_databases_instance_not_found(self, client, operator_token):
        """测试实例不存在"""
        response = client.get(
            "/api/v1/sql/databases/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404

    def test_get_tables_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/sql/tables/1/test_db")
        assert response.status_code == 401
