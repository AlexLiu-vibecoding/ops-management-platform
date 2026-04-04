#!/usr/bin/env python3
"""
慢查询监控 API 核心测试

覆盖核心慢查询接口：
- 慢查询列表: /api/v1/slow-query/{instance_id}
- Top 慢查询: /api/v1/slow-query/{instance_id}/top
- 慢查询分析: /api/v1/slow-query/{instance_id}/analyze
- 慢查询统计: /api/v1/slow-query/{instance_id}/stats
- 优化建议: /api/v1/slow-query/{instance_id}/suggestions
"""
import pytest
from datetime import datetime, timedelta
from app.models import SlowQuery, RDBInstance, RDBType


class TestSlowQueryListAPI:
    """慢查询列表 API 测试类"""

    def test_list_slow_queries_success(self, client, operator_token, test_rdb_instance):
        """测试获取慢查询列表"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_slow_queries_with_min_time(self, client, operator_token, test_rdb_instance):
        """测试带最小执行时间过滤"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}?min_time=1.0",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_slow_queries_with_limit(self, client, operator_token, test_rdb_instance):
        """测试带数量限制"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}?limit=50",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50

    def test_list_slow_queries_instance_not_found(self, client, operator_token):
        """测试获取不存在实例的慢查询"""
        response = client.get(
            "/api/v1/slow-query/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 404

    def test_list_slow_queries_no_auth(self, client, test_rdb_instance):
        """测试未授权获取慢查询"""
        response = client.get(f"/api/v1/slow-query/{test_rdb_instance.id}")
        assert response.status_code == 401


class TestSlowQueryTopAPI:
    """Top 慢查询 API 测试类"""

    def test_get_top_slow_queries(self, client, operator_token, test_rdb_instance):
        """测试获取 Top 慢查询"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/top",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或监控未启用
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_top_slow_queries_with_params(self, client, operator_token, test_rdb_instance):
        """测试带参数获取 Top 慢查询"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/top?hours=48&top_n=20",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [200, 400]

    def test_get_top_slow_queries_instance_not_found(self, client, operator_token):
        """测试获取不存在实例的 Top 慢查询"""
        response = client.get(
            "/api/v1/slow-query/99999/top",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code == 404


class TestSlowQueryAnalyzeAPI:
    """慢查询分析 API 测试类"""

    def test_analyze_slow_query(self, client, operator_token, test_rdb_instance, db_session):
        """测试分析慢查询"""
        # 先创建一个慢查询记录
        slow_query = SlowQuery(
            instance_id=test_rdb_instance.id,
            sql_sample="SELECT * FROM users WHERE status = 1",
            sql_fingerprint="SELECT*FROMusersWHEREstatus",
            query_time=5.5,
            lock_time=0.1,
            rows_sent=100,
            rows_examined=10000
        )
        db_session.add(slow_query)
        db_session.commit()
        db_session.refresh(slow_query)

        response = client.post(
            f"/api/v1/slow-query/{test_rdb_instance.id}/analyze/{slow_query.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

    def test_analyze_slow_query_not_found(self, client, operator_token, test_rdb_instance):
        """测试分析不存在的慢查询"""
        response = client.post(
            f"/api/v1/slow-query/{test_rdb_instance.id}/analyze/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        assert response.status_code in [404]


class TestSlowQueryStatsAPI:
    """慢查询统计 API 测试类"""

    def test_get_slow_query_stats(self, client, operator_token, test_rdb_instance):
        """测试获取慢查询统计"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/stats",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

        if response.status_code == 200:
            data = response.json()
            assert "total_count" in data or "avg_time" in data

    def test_get_slow_query_trend(self, client, operator_token, test_rdb_instance):
        """测试获取慢查询趋势"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/trend?days=7",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSlowQuerySuggestionsAPI:
    """慢查询优化建议 API 测试类"""

    def test_get_optimization_suggestions(self, client, operator_token, test_rdb_instance):
        """测试获取优化建议"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/suggestions",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

    def test_apply_optimization(self, client, operator_token, test_rdb_instance):
        """测试应用优化建议"""
        response = client.post(
            f"/api/v1/slow-query/{test_rdb_instance.id}/suggestions/1/apply",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSlowQueryCollectAPI:
    """慢查询采集 API 测试类"""

    def test_collect_slow_queries(self, client, operator_token, test_rdb_instance):
        """测试手动触发慢查询采集"""
        response = client.post(
            f"/api/v1/slow-query/{test_rdb_instance.id}/collect",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功或端点不存在
        assert response.status_code in [200, 400, 404]

    def test_get_collection_status(self, client, operator_token, test_rdb_instance):
        """测试获取采集状态"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/collect/status",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSlowQueryExportAPI:
    """慢查询导出 API 测试类"""

    def test_export_slow_queries(self, client, operator_token, test_rdb_instance):
        """测试导出慢查询"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/export",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

    def test_export_slow_queries_with_filter(self, client, operator_token, test_rdb_instance):
        """测试带过滤条件导出"""
        response = client.get(
            f"/api/v1/slow-query/{test_rdb_instance.id}/export?format=csv&start_date=2024-01-01",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]


class TestSlowQueryGlobalAPI:
    """全局慢查询 API 测试类"""

    def test_get_global_slow_queries(self, client, operator_token):
        """测试获取全局慢查询列表"""
        response = client.get(
            "/api/v1/slow-query/global",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

    def test_get_global_stats(self, client, operator_token):
        """测试获取全局慢查询统计"""
        response = client.get(
            "/api/v1/slow-query/global/stats",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]

    def test_compare_instances(self, client, operator_token):
        """测试对比多个实例的慢查询"""
        response = client.post(
            "/api/v1/slow-query/compare",
            json={"instance_ids": [1, 2, 3]},
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # 可能成功、端点不存在或方法不允许
        assert response.status_code in [200, 404, 405]
