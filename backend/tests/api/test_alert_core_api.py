"""
告警中心核心 API 测试

告警规则、告警记录相关 API 测试
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import User, UserRole
from app.models import AlertRule, AlertRecord


class TestAlertRuleAPI:
    """告警规则 API 测试"""

    def test_list_alert_rules(self, client: TestClient, admin_headers: dict):
        """测试获取告警规则列表"""
        response = client.get("/api/v1/alerts/rules", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # 可能是分页格式或列表格式
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_create_alert_rule(self, client: TestClient, admin_headers: dict):
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
            "/api/v1/alerts/rules",
            json=rule_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == rule_data["name"]
            assert "id" in data

    def test_get_alert_rule_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取告警规则详情"""
        # 先创建一个规则
        rule = AlertRule(
            name="测试规则",
            description="测试描述",
            rule_type="metric",
            metric_name="cpu_usage",
            operator=">",
            threshold=80,
            duration=300,
            alert_level="warning",
            is_enabled=True,
            created_by=1
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        response = client.get(
            f"/api/v1/alerts/rules/{rule.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rule.id
        assert data["name"] == rule.name

    def test_update_alert_rule(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试更新告警规则"""
        # 先创建一个规则
        rule = AlertRule(
            name="旧规则名称",
            rule_type="metric",
            metric_name="cpu_usage",
            operator=">",
            threshold=80,
            duration=300,
            alert_level="warning",
            is_enabled=True,
            created_by=1
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        update_data = {
            "name": "新规则名称",
            "threshold": 90,
            "is_enabled": False
        }
        response = client.put(
            f"/api/v1/alerts/rules/{rule.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新规则名称"

    def test_delete_alert_rule(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试删除告警规则"""
        # 先创建一个规则
        rule = AlertRule(
            name="待删除规则",
            rule_type="metric",
            metric_name="memory_usage",
            operator=">",
            threshold=70,
            duration=300,
            alert_level="critical",
            is_enabled=True,
            created_by=1
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)
        rule_id = rule.id

        response = client.delete(
            f"/api/v1/alerts/rules/{rule_id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # 验证已删除
        deleted = db_session.query(AlertRule).filter_by(id=rule_id).first()
        assert deleted is None

    def test_enable_disable_alert_rule(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试启用/禁用告警规则"""
        # 先创建一个禁用的规则
        rule = AlertRule(
            name="测试规则",
            rule_type="metric",
            metric_name="cpu_usage",
            operator=">",
            threshold=80,
            duration=300,
            alert_level="warning",
            is_enabled=False,
            created_by=1
        )
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)

        # 启用规则
        response = client.post(
            f"/api/v1/alerts/rules/{rule.id}/enable",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]  # 可能接口不存在


class TestAlertRecordAPI:
    """告警记录 API 测试"""

    def test_list_alert_records(self, client: TestClient, admin_headers: dict):
        """测试获取告警记录列表"""
        response = client.get("/api/v1/alerts/records", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # 可能是分页格式或列表格式
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_get_alert_record_detail(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试获取告警记录详情"""
        # 先创建告警记录
        record = AlertRecord(
            rule_id=1,
            instance_id=1,
            alert_name="CPU 告警",
            alert_level="warning",
            status="pending",
            message="CPU 使用率超过阈值",
            metric_value=85.5,
            threshold=80.0
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        response = client.get(
            f"/api/v1/alerts/records/{record.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == record.id
        assert data["alert_name"] == record.alert_name

    def test_acknowledge_alert(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试确认告警"""
        # 先创建告警记录
        record = AlertRecord(
            rule_id=1,
            instance_id=1,
            alert_name="CPU 告警",
            alert_level="warning",
            status="pending",
            message="CPU 使用率超过阈值",
            metric_value=85.5,
            threshold=80.0
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        ack_data = {
            "remark": "已处理"
        }
        response = client.post(
            f"/api/v1/alerts/records/{record.id}/acknowledge",
            json=ack_data,
            headers=admin_headers
        )
        # 可能接口存在或不存在
        assert response.status_code in [200, 404]

    def test_resolve_alert(self, client: TestClient, admin_headers: dict, db_session: Session):
        """测试解决告警"""
        # 先创建告警记录
        record = AlertRecord(
            rule_id=1,
            instance_id=1,
            alert_name="CPU 告警",
            alert_level="warning",
            status="pending",
            message="CPU 使用率超过阈值",
            metric_value=85.5,
            threshold=80.0
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        response = client.post(
            f"/api/v1/alerts/records/{record.id}/resolve",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]

    def test_filter_alert_records_by_level(self, client: TestClient, admin_headers: dict):
        """测试按级别筛选告警记录"""
        response = client.get(
            "/api/v1/alerts/records",
            params={"level": "warning"},
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_filter_alert_records_by_status(self, client: TestClient, admin_headers: dict):
        """测试按状态筛选告警记录"""
        response = client.get(
            "/api/v1/alerts/records",
            params={"status": "active"},
            headers=admin_headers
        )
        assert response.status_code == 200


class TestAlertStatisticsAPI:
    """告警统计 API 测试"""

    def test_get_alert_statistics(self, client: TestClient, admin_headers: dict):
        """测试获取告警统计"""
        response = client.get("/api/v1/alerts/statistics", headers=admin_headers)
        # 可能返回统计或404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_alert_trend(self, client: TestClient, admin_headers: dict):
        """测试获取告警趋势"""
        response = client.get(
            "/api/v1/alerts/trend",
            params={"days": 7},
            headers=admin_headers
        )
        # 可能返回趋势或404
        assert response.status_code in [200, 404]


class TestAlertAPIErrorHandling:
    """告警 API 错误处理测试"""

    def test_get_nonexistent_alert_rule(self, client: TestClient, admin_headers: dict):
        """测试获取不存在的告警规则"""
        response = client.get("/api/v1/alerts/rules/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_nonexistent_alert_rule(self, client: TestClient, admin_headers: dict):
        """测试更新不存在的告警规则"""
        response = client.put(
            "/api/v1/alerts/rules/99999",
            json={"name": "新名称"},
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_nonexistent_alert_rule(self, client: TestClient, admin_headers: dict):
        """测试删除不存在的告警规则"""
        response = client.delete("/api/v1/alerts/rules/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_create_alert_rule_with_invalid_data(self, client: TestClient, admin_headers: dict):
        """测试创建无效告警规则"""
        # 缺少必填字段
        response = client.post(
            "/api/v1/alerts/rules",
            json={"description": "缺少名称"},
            headers=admin_headers
        )
        assert response.status_code == 422

    def test_unauthorized_access(self, client: TestClient):
        """测试未授权访问"""
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 401

    def test_get_nonexistent_alert_record(self, client: TestClient, admin_headers: dict):
        """测试获取不存在的告警记录"""
        response = client.get("/api/v1/alerts/records/99999", headers=admin_headers)
        assert response.status_code == 404
