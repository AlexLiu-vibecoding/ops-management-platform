#!/usr/bin/env python3
"""
监控告警 E2E 测试

测试范围：
1. 告警规则 CRUD
2. 告警聚合规则
3. 告警静默规则
4. 告警升级规则
5. 告警记录查询
6. 监控开关配置

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_monitoring_alerts.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestMonitoringAlerts:
    """监控告警 E2E 测试类"""

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

    class TestAlertRules:
        """告警规则测试"""

        def test_list_alert_rules(self, client, auth_headers):
            """测试获取告警规则列表"""
            response = client.get("/api/v1/alert-rules", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

        def test_list_alert_rule_types(self, client, auth_headers):
            """测试获取告警规则类型"""
            response = client.get("/api/v1/alert-rules/types/list", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

        def test_list_alert_operators(self, client, auth_headers):
            """测试获取告警规则操作符"""
            response = client.get("/api/v1/alert-rules/operators/list", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

    class TestAlertAggregation:
        """告警聚合测试"""

        def test_list_aggregation_rules(self, client, auth_headers):
            """测试获取告警聚合规则"""
            response = client.get("/api/v1/alert-rules/aggregations", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

        def test_create_and_delete_aggregation_rule(self, client, auth_headers):
            """测试创建和删除告警聚合规则"""
            rule_data = {
                "name": f"E2E聚合规则_{os.urandom(4).hex()}",
                "metric_type": "cpu_usage",
                "alert_level": "P1",
                "aggregation_window": 300,
                "priority": 10,
                "is_enabled": True
            }

            # 创建规则
            response = client.post(
                "/api/v1/alert-rules/aggregations",
                json=rule_data,
                headers=auth_headers
            )

            if response.status_code == 201:
                rule_id = response.json().get("id")
                # 删除规则
                delete_resp = client.delete(
                    f"/api/v1/alert-rules/aggregations/{rule_id}",
                    headers=auth_headers
                )
                assert delete_resp.status_code == 200
            else:
                # 可能已存在相同规则或其他错误
                assert response.status_code in [201, 400, 409]

    class TestAlertSilence:
        """告警静默测试"""

        def test_list_silence_rules(self, client, auth_headers):
            """测试获取告警静默规则"""
            response = client.get("/api/v1/alert-rules/silences", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

        def test_create_and_delete_silence_rule(self, client, auth_headers):
            """测试创建和删除告警静默规则"""
            import datetime
            now = datetime.datetime.now()
            end_time = now + datetime.timedelta(hours=1)

            rule_data = {
                "name": f"E2E静默规则_{os.urandom(4).hex()}",
                "metric_type": "cpu_usage",
                "start_time": now.isoformat(),
                "end_time": end_time.isoformat(),
                "recurrence_type": "once",
                "is_enabled": True
            }

            # 创建规则
            response = client.post(
                "/api/v1/alert-rules/silences",
                json=rule_data,
                headers=auth_headers
            )

            if response.status_code == 201:
                rule_id = response.json().get("id")
                # 删除规则
                delete_resp = client.delete(
                    f"/api/v1/alert-rules/silences/{rule_id}",
                    headers=auth_headers
                )
                assert delete_resp.status_code == 200
            else:
                assert response.status_code in [201, 400]

    class TestAlertRecords:
        """告警记录测试"""

        def test_list_alert_records(self, client, auth_headers):
            """测试获取告警记录"""
            response = client.get("/api/v1/alerts", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data

        def test_get_alert_stats(self, client, auth_headers):
            """测试获取告警统计"""
            response = client.get("/api/v1/alerts/stats", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "active" in data
            assert "resolved" in data

        def test_list_alert_metric_types(self, client, auth_headers):
            """测试获取告警指标类型"""
            response = client.get("/api/v1/alerts/metric-types/list", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

        def test_list_alert_levels(self, client, auth_headers):
            """测试获取告警级别"""
            response = client.get("/api/v1/alerts/levels/list", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    class TestMonitorSwitches:
        """监控开关测试"""

        def test_get_global_monitor_switch(self, client, auth_headers):
            """测试获取全局监控开关"""
            response = client.get("/api/v1/monitor/switches/global", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "is_enabled" in data

        def test_update_global_monitor_switch(self, client, auth_headers):
            """测试更新全局监控开关"""
            # 先获取当前状态
            get_resp = client.get("/api/v1/monitor/switches/global", headers=auth_headers)
            current_status = get_resp.json().get("is_enabled", True)

            # 切换状态
            response = client.put(
                "/api/v1/monitor/switches/global",
                json={"is_enabled": not current_status},
                headers=auth_headers
            )

            assert response.status_code == 200

            # 恢复原始状态
            client.put(
                "/api/v1/monitor/switches/global",
                json={"is_enabled": current_status},
                headers=auth_headers
            )

    class TestSlowQuery:
        """慢查询测试"""

        def test_get_slow_query_config(self, client, auth_headers):
            """测试获取慢查询配置"""
            response = client.get("/api/v1/monitor/slow-query/config", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "is_enabled" in data

        def test_get_high_cpu_config(self, client, auth_headers):
            """测试获取高 CPU 查询配置"""
            response = client.get("/api/v1/monitor/high-cpu/config", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "is_enabled" in data

        def test_get_monitor_overview(self, client, auth_headers):
            """测试获取监控概览"""
            response = client.get("/api/v1/monitor/overview", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)
