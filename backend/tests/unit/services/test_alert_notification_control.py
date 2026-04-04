"""
告警通知管控服务测试
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, time

from app.services.alert_notification_control import AlertSilenceService
from app.models import AlertRecord, AlertSilenceRule, AlertRateLimitRule


class TestAlertSilenceService:
    """告警静默服务测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def mock_alert(self):
        """创建模拟告警"""
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.metric_type = "cpu_high"
        alert.alert_level = "warning"
        alert.rdb_instance_id = 1
        alert.redis_instance_id = None
        alert.alert_title = "CPU使用率过高"
        return alert

    def test_check_silence_no_rules(self, mock_db, mock_alert):
        """测试检查静默（无规则）"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = AlertSilenceService.check_silence(mock_db, mock_alert)

        assert result is False

    def test_check_silence_metric_type_mismatch(self, mock_db, mock_alert):
        """测试检查静默（指标类型不匹配）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.metric_type = "memory_high"  # 不匹配
        mock_rule.alert_level = None
        mock_rule.rdb_instance_id = None
        mock_rule.redis_instance_id = None
        mock_rule.silence_type = "always"

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_rule
        ]

        with patch.object(AlertSilenceService, '_is_in_time_window', return_value=True):
            result = AlertSilenceService.check_silence(mock_db, mock_alert)

            # 指标类型不匹配，不应该静默
            assert result is False

    def test_check_silence_alert_level_mismatch(self, mock_db, mock_alert):
        """测试检查静默（告警级别不匹配）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.metric_type = "cpu_high"
        mock_rule.alert_level = "critical"  # 不匹配
        mock_rule.rdb_instance_id = None
        mock_rule.redis_instance_id = None
        mock_rule.silence_type = "always"

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_rule
        ]

        with patch.object(AlertSilenceService, '_is_in_time_window', return_value=True):
            result = AlertSilenceService.check_silence(mock_db, mock_alert)

            # 告警级别不匹配，不应该静默
            assert result is False

    def test_check_silence_instance_mismatch(self, mock_db, mock_alert):
        """测试检查静默（实例不匹配）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.metric_type = "cpu_high"
        mock_rule.alert_level = "warning"
        mock_rule.rdb_instance_id = 999  # 不匹配
        mock_rule.redis_instance_id = None
        mock_rule.silence_type = "always"

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_rule
        ]

        with patch.object(AlertSilenceService, '_is_in_time_window', return_value=True):
            result = AlertSilenceService.check_silence(mock_db, mock_alert)

            # 实例不匹配，不应该静默
            assert result is False

    def test_check_silence_match(self, mock_db, mock_alert):
        """测试检查静默（匹配）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.metric_type = "cpu_high"
        mock_rule.alert_level = "warning"
        mock_rule.rdb_instance_id = 1
        mock_rule.redis_instance_id = None
        mock_rule.silence_type = "always"
        mock_rule.name = "维护窗口"

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_rule
        ]

        with patch.object(AlertSilenceService, '_is_in_time_window', return_value=True):
            result = AlertSilenceService.check_silence(mock_db, mock_alert)

            # 应该静默
            assert result is True

    def test_check_silence_not_in_time_window(self, mock_db, mock_alert):
        """测试检查静默（不在时间窗口）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.metric_type = "cpu_high"
        mock_rule.alert_level = "warning"
        mock_rule.rdb_instance_id = 1
        mock_rule.redis_instance_id = None
        mock_rule.silence_type = "always"

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_rule
        ]

        with patch.object(AlertSilenceService, '_is_in_time_window', return_value=False):
            result = AlertSilenceService.check_silence(mock_db, mock_alert)

            # 不在时间窗口，不应该静默
            assert result is False

    def test_is_in_time_window_always(self):
        """测试时间窗口判断（一次性）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "once"
        mock_rule.start_date = None
        mock_rule.end_date = None

        result = AlertSilenceService._is_in_time_window(datetime.now(), mock_rule)

        assert result is True

    def test_is_in_time_window_once_future(self):
        """测试时间窗口判断（一次性，未来）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "once"
        mock_rule.start_date = datetime.now() + timedelta(days=1)

        result = AlertSilenceService._is_in_time_window(datetime.now(), mock_rule)

        assert result is False

    def test_is_in_time_window_once_past(self):
        """测试时间窗口判断（一次性，过去）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "once"
        mock_rule.start_date = datetime.now() - timedelta(days=1)
        mock_rule.end_date = datetime.now() - timedelta(hours=1)

        result = AlertSilenceService._is_in_time_window(datetime.now(), mock_rule)

        assert result is False

    def test_is_in_time_window_once_in_range(self):
        """测试时间窗口判断（一次性，在范围内）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "once"
        mock_rule.start_date = datetime.now() - timedelta(hours=1)
        mock_rule.end_date = datetime.now() + timedelta(hours=1)

        result = AlertSilenceService._is_in_time_window(datetime.now(), mock_rule)

        assert result is True

    def test_is_in_time_window_daily(self):
        """测试时间窗口判断（每日）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "daily"
        mock_rule.time_start = "09:00"  # 字符串格式
        mock_rule.time_end = "18:00"

        # 当前时间 12:00
        now = datetime.now().replace(hour=12, minute=0)
        result = AlertSilenceService._is_in_time_window(now, mock_rule)

        assert result is True

    def test_is_in_time_window_daily_outside(self):
        """测试时间窗口判断（每日，窗口外）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "daily"
        mock_rule.time_start = "09:00"
        mock_rule.time_end = "18:00"

        # 当前时间 20:00
        now = datetime.now().replace(hour=20, minute=0)
        result = AlertSilenceService._is_in_time_window(now, mock_rule)

        assert result is False

    def test_is_in_time_window_daily_cross_day(self):
        """测试时间窗口判断（每日，跨天）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "daily"
        mock_rule.time_start = "22:00"
        mock_rule.time_end = "06:00"

        # 当前时间 23:00
        now = datetime.now().replace(hour=23, minute=0)
        result = AlertSilenceService._is_in_time_window(now, mock_rule)

        assert result is True

    def test_is_in_time_window_weekly(self):
        """测试时间窗口判断（每周）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "weekly"
        mock_rule.weekdays = [0, 6]  # 周一和周日（注意：0=周一，6=周日）
        mock_rule.time_start = "09:00"
        mock_rule.time_end = "18:00"

        # 周一 12:00
        now = datetime.now().replace(hour=12, minute=0)
        if now.weekday() != 0:  # 如果不是周一，就设置为周一
            now = now + timedelta(days=(0 - now.weekday()))

        result = AlertSilenceService._is_in_time_window(now, mock_rule)

        assert result is True

    def test_is_in_time_window_weekly_wrong_day(self):
        """测试时间窗口判断（每周，错误的星期）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "weekly"
        mock_rule.weekdays = [0, 6]  # 只允许周一和周日
        mock_rule.time_start = "09:00"
        mock_rule.time_end = "18:00"

        # 周三 12:00
        now = datetime.now().replace(hour=12, minute=0)
        if now.weekday() != 2:  # 如果不是周三，就设置为周三
            now = now + timedelta(days=(2 - now.weekday()))

        result = AlertSilenceService._is_in_time_window(now, mock_rule)

        assert result is False

    def test_is_in_time_window_exception(self):
        """测试时间窗口判断（异常）"""
        mock_rule = Mock(spec=AlertSilenceRule)
        mock_rule.silence_type = "invalid"

        result = AlertSilenceService._is_in_time_window(datetime.now(), mock_rule)

        # 异常情况下应该返回 False
        assert result is False
