"""
告警聚合服务测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.alert_aggregation import (
    AlertAggregationService,
    AlertSilenceService,
    AlertEscalationService
)
from app.models import (
    AlertRecord, AlertAggregationRule, AlertAggregation,
    AlertSilenceRule, AlertEscalationRule
)


class TestAlertAggregationService:
    """告警聚合服务测试类"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def mock_alert(self):
        """创建模拟告警"""
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.metric_type = "cpu_usage"
        alert.alert_level = "P1"
        alert.rdb_instance_id = 1
        alert.redis_instance_id = None
        alert.created_at = datetime.now()
        return alert

    @pytest.fixture
    def mock_rule(self):
        """创建模拟聚合规则"""
        rule = Mock(spec=AlertAggregationRule)
        rule.id = 1
        rule.metric_type = "cpu_usage"
        rule.alert_level = "P1"
        rule.rdb_instance_id = 1
        rule.redis_instance_id = None
        rule.aggregation_window = 300
        rule.priority = 10
        rule.is_enabled = True
        return rule

    # ==================== 告警聚合测试 ====================

    def test_should_aggregate_alert_match(self, mock_db, mock_alert, mock_rule):
        """测试告警匹配聚合规则"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_rule]

        result = AlertAggregationService.should_aggregate_alert(mock_db, mock_alert)

        assert result is not None
        assert result.id == 1

    def test_should_aggregate_alert_no_match(self, mock_db, mock_alert):
        """测试告警不匹配聚合规则"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = AlertAggregationService.should_aggregate_alert(mock_db, mock_alert)

        assert result is None

    def test_should_aggregate_alert_metric_type_mismatch(self, mock_db, mock_alert):
        """测试指标类型不匹配"""
        rule = Mock(spec=AlertAggregationRule)
        rule.metric_type = "memory_usage"  # 不同的指标类型
        rule.alert_level = "P1"
        rule.rdb_instance_id = 1
        rule.is_enabled = True

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]

        result = AlertAggregationService.should_aggregate_alert(mock_db, mock_alert)

        assert result is None

    def test_should_aggregate_alert_level_mismatch(self, mock_db, mock_alert):
        """测试告警级别不匹配"""
        rule = Mock(spec=AlertAggregationRule)
        rule.metric_type = "cpu_usage"
        rule.alert_level = "P2"  # 不同的告警级别
        rule.rdb_instance_id = 1
        rule.is_enabled = True

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]

        result = AlertAggregationService.should_aggregate_alert(mock_db, mock_alert)

        assert result is None

    def test_should_aggregate_alert_instance_mismatch(self, mock_db, mock_alert):
        """测试实例不匹配"""
        rule = Mock(spec=AlertAggregationRule)
        rule.metric_type = "cpu_usage"
        rule.alert_level = "P1"
        rule.rdb_instance_id = 999  # 不同的实例
        rule.redis_instance_id = None
        rule.is_enabled = True

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]

        result = AlertAggregationService.should_aggregate_alert(mock_db, mock_alert)

        assert result is None


class TestAlertSilenceService:
    """告警静默服务测试类"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def mock_alert(self):
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.metric_type = "cpu_usage"
        alert.alert_level = "P1"
        alert.rdb_instance_id = 1
        return alert

    def test_check_silence_no_rules(self, mock_db, mock_alert):
        """测试无静默规则"""
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = AlertSilenceService.check_silence(mock_db, mock_alert)

        assert result is False

    def test_check_silence_metric_type_match(self, mock_db, mock_alert):
        """测试指标类型匹配静默"""
        rule = Mock(spec=AlertSilenceRule)
        rule.metric_type = "cpu_usage"
        rule.alert_level = None
        rule.rdb_instance_id = None
        rule.redis_instance_id = None
        rule.is_enabled = True
        rule.start_time = None
        rule.end_time = None
        rule.recurrence_type = "once"

        mock_db.query.return_value.filter.return_value.all.return_value = [rule]

        result = AlertSilenceService.check_silence(mock_db, mock_alert)

        assert result is True

    def test_check_silence_level_not_match(self, mock_db, mock_alert):
        """测试告警级别不匹配"""
        rule = Mock(spec=AlertSilenceRule)
        rule.metric_type = "cpu_usage"
        rule.alert_level = "P2"  # 不匹配
        rule.rdb_instance_id = None
        rule.is_enabled = True
        rule.start_time = None
        rule.end_time = None

        mock_db.query.return_value.filter.return_value.all.return_value = [rule]

        result = AlertSilenceService.check_silence(mock_db, mock_alert)

        assert result is False


class TestAlertSilenceTimeWindow:
    """告警静默时间窗口测试类"""

    def test_is_in_time_window_no_restrictions(self):
        """测试无时间限制"""
        rule = Mock(spec=AlertSilenceRule)
        rule.start_time = None
        rule.end_time = None
        rule.recurrence_type = "once"

        now = datetime.now()
        result = AlertSilenceService._is_in_time_window(now, rule)

        assert result is True

    def test_is_in_time_window_within_range(self):
        """测试在时间范围内"""
        rule = Mock(spec=AlertSilenceRule)
        rule.start_time = datetime.now() - timedelta(hours=1)
        rule.end_time = datetime.now() + timedelta(hours=1)
        rule.recurrence_type = "once"

        now = datetime.now()
        result = AlertSilenceService._is_in_time_window(now, rule)

        assert result is True

    def test_is_in_time_window_outside_range(self):
        """测试在时间范围外"""
        rule = Mock(spec=AlertSilenceRule)
        rule.start_time = datetime.now() + timedelta(hours=1)
        rule.end_time = datetime.now() + timedelta(hours=2)
        rule.recurrence_type = "once"

        now = datetime.now()
        result = AlertSilenceService._is_in_time_window(now, rule)

        assert result is False


class TestAlertEscalationService:
    """告警升级服务测试类"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def mock_alert(self):
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.status = "pending"
        alert.created_at = datetime.now() - timedelta(hours=2)
        return alert

    def test_check_escalation_no_rules(self, mock_db, mock_alert):
        """测试无升级规则"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # 不应抛出异常
        AlertEscalationService.check_escalation(mock_db, mock_alert)

    def test_check_escalation_already_resolved(self, mock_db, mock_alert):
        """测试已解决的告警不升级"""
        mock_alert.status = "resolved"

        # 不应抛出异常，函数在检查到状态非pending时直接返回
        AlertEscalationService.check_escalation(mock_db, mock_alert)

