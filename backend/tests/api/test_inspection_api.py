"""
巡检报告 API 测试

覆盖巡检报告接口：
- 巡检指标: /api/v1/inspection/metrics
- 巡检执行: /api/v1/inspection/run
- 巡检结果: /api/v1/inspection/results
- 巡检报告: /api/v1/inspection/reports
- 巡检模块: /api/v1/inspection/modules/list
- 定时巡检: /api/v1/scheduled-inspection
"""
import pytest


class TestInspectionAPI:
    """巡检报告 API 测试类"""

    def test_list_inspection_metrics(self, client, admin_headers):
        """测试获取巡检指标列表"""
        response = client.get("/api/v1/inspection/metrics", headers=admin_headers)
        assert response.status_code == 200

    def test_list_inspection_results(self, client, admin_headers):
        """测试获取巡检结果列表"""
        response = client.get("/api/v1/inspection/results", headers=admin_headers)
        assert response.status_code == 200

    def test_list_inspection_reports(self, client, admin_headers):
        """测试获取巡检报告列表"""
        response = client.get("/api/v1/inspection/reports", headers=admin_headers)
        assert response.status_code == 200

    def test_list_inspection_modules(self, client, admin_headers):
        """测试获取巡检模块列表"""
        response = client.get("/api/v1/inspection/modules/list", headers=admin_headers)
        assert response.status_code == 200

    def test_list_scheduled_inspections(self, client, admin_headers):
        """测试获取定时巡检列表"""
        response = client.get("/api/v1/scheduled-inspection", headers=admin_headers)
        assert response.status_code == 200

    def test_run_inspection(self, client, admin_headers):
        """测试执行巡检"""
        response = client.post("/api/v1/inspection/run", headers=admin_headers)
        assert response.status_code in [200, 201, 422]

    def test_create_inspection_metric(self, client, admin_headers):
        """测试创建巡检指标"""
        metric_data = {
            "name": "CPU 使用率检查",
            "module": "system",
            "check_type": "threshold",
            "description": "检查 CPU 使用率"
        }
        response = client.post(
            "/api/v1/inspection/metrics",
            json=metric_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201, 422]

    def test_create_scheduled_inspection(self, client, admin_headers):
        """测试创建定时巡检"""
        task_data = {
            "name": "每日巡检",
            "cron_expression": "0 3 * * *",
            "description": "每天凌晨3点执行巡检",
            "is_enabled": True
        }
        response = client.post(
            "/api/v1/scheduled-inspection",
            json=task_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201, 422]


class TestInspectionAPIErrorHandling:
    """巡检报告 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/inspection/metrics")
        assert response.status_code == 401

    def test_get_nonexistent_metric(self, client, admin_headers):
        """测试获取不存在的巡检指标"""
        response = client.get("/api/v1/inspection/metrics/99999", headers=admin_headers)
        assert response.status_code in [404, 405]
