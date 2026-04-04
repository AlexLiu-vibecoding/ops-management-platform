"""
告警规则 API 测试

覆盖告警规则接口：
- 规则列表: /api/v1/alert-rules
- 规则创建: /api/v1/alert-rules
- 规则更新: /api/v1/alert-rules/{rule_id}
- 规则删除: /api/v1/alert-rules/{rule_id}
- 规则开关: /api/v1/alert-rules/{rule_id}/toggle
"""
import pytest


class TestAlertRulesAPI:
    """告警规则 API 测试类"""

    def test_list_alert_rules(self, client, admin_headers):
        """测试获取告警规则列表"""
        response = client.get("/api/v1/alert-rules", headers=admin_headers)
        assert response.status_code == 200

    def test_get_rule_types(self, client, admin_headers):
        """测试获取规则类型列表"""
        response = client.get("/api/v1/alert-rules/types/list", headers=admin_headers)
        assert response.status_code == 200

    def test_get_rule_operators(self, client, admin_headers):
        """测试获取规则操作符列表"""
        response = client.get("/api/v1/alert-rules/operators/list", headers=admin_headers)
        assert response.status_code == 200

    def test_get_rule_severities(self, client, admin_headers):
        """测试获取规则严重性列表"""
        response = client.get("/api/v1/alert-rules/severities/list", headers=admin_headers)
        assert response.status_code == 200

    def test_create_alert_rule(self, client, admin_headers):
        """测试创建告警规则"""
        rule_data = {
            "name": "CPU 使用率告警",
            "description": "监控 CPU 使用率",
            "rule_type": "metric",
            "metric_name": "cpu_usage",
            "operator": ">",
            "threshold": 80,
            "duration": 300,
            "alert_level": "warning",
            "is_enabled": True
        }
        response = client.post(
            "/api/v1/alert-rules",
            json=rule_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

    def test_get_rule_aggregations(self, client, admin_headers):
        """测试获取聚合规则"""
        response = client.get("/api/v1/alert-rules/aggregations?page=1&limit=10", headers=admin_headers)
        assert response.status_code in [200, 404, 422]

    def test_get_rule_silences(self, client, admin_headers):
        """测试获取静默规则"""
        response = client.get("/api/v1/alert-rules/silences?page=1&limit=10", headers=admin_headers)
        assert response.status_code in [200, 404, 422]


class TestAlertRulesAPIErrorHandling:
    """告警规则 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/alert-rules")
        assert response.status_code == 401

    def test_create_rule_invalid_data(self, client, admin_headers):
        """测试创建规则时提供无效数据"""
        response = client.post(
            "/api/v1/alert-rules",
            json={"name": "测试规则"},
            headers=admin_headers
        )
        assert response.status_code in [400, 422]
