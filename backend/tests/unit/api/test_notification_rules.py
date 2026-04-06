"""
通知规则API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestSilenceRuleSchemas:
    """测试静默规则Schema"""
    
    def test_silence_rule_create_fields(self):
        """测试创建静默规则Schema字段"""
        from app.api.notification_rules import SilenceRuleCreate
        
        fields = SilenceRuleCreate.model_fields
        assert 'name' in fields
        assert 'description' in fields
        assert 'silence_type' in fields
        assert 'is_enabled' in fields
        assert 'start_time' in fields
        assert 'end_time' in fields
        assert 'weekdays' in fields
    
    def test_silence_rule_create_defaults(self):
        """测试创建静默规则默认值"""
        from app.api.notification_rules import SilenceRuleCreate
        
        field = SilenceRuleCreate.model_fields['silence_type']
        assert field.default == "once"
    
    def test_silence_rule_update_fields(self):
        """测试更新静默规则Schema字段"""
        from app.api.notification_rules import SilenceRuleUpdate
        
        fields = SilenceRuleUpdate.model_fields
        assert 'name' in fields
        assert 'description' in fields
        assert 'silence_type' in fields
        assert 'is_enabled' in fields


class TestSilenceRuleRouter:
    """测试静默规则路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.notification_rules import router
        
        assert router.prefix == "/notification"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.notification_rules import router
        
        assert "通知规则管理" in router.tags


class TestSilenceRuleConstants:
    """测试静默规则常量"""
    
    def test_silence_type_labels(self):
        """测试静默类型标签"""
        from app.api.notification_rules import SILENCE_TYPE_LABELS
        
        assert SILENCE_TYPE_LABELS["once"] == "一次性"
        assert SILENCE_TYPE_LABELS["daily"] == "每日"
        assert SILENCE_TYPE_LABELS["weekly"] == "每周"
    
    def test_weekday_names(self):
        """测试星期名称"""
        from app.api.notification_rules import WEEKDAY_NAMES
        
        assert WEEKDAY_NAMES[0] == "周一"
        assert WEEKDAY_NAMES[6] == "周日"
        assert len(WEEKDAY_NAMES) == 7


class TestFormatWeekdays:
    """测试格式化星期函数"""
    
    def test_format_weekdays_valid(self):
        """测试格式化有效星期"""
        from app.api.notification_rules import format_weekdays
        
        result = format_weekdays([0, 1, 2])
        assert "周一" in result
        assert "周二" in result
        assert "周三" in result
    
    def test_format_weekdays_empty(self):
        """测试格式化空列表"""
        from app.api.notification_rules import format_weekdays
        
        result = format_weekdays([])
        assert result == "-"
    
    def test_format_weekdays_none(self):
        """测试格式化None"""
        from app.api.notification_rules import format_weekdays
        
        result = format_weekdays(None)
        assert result == "-"
    
    def test_format_weekdays_single(self):
        """测试格式化单个星期"""
        from app.api.notification_rules import format_weekdays
        
        result = format_weekdays([3])
        assert result == "周四"
    
    def test_format_weekdays_out_of_range(self):
        """测试格式化超出范围"""
        from app.api.notification_rules import format_weekdays
        
        # 超出范围的会被过滤掉
        result = format_weekdays([0, 7, 8])
        assert "周一" in result
        assert "周日" not in result or len(result.split(",")) == 1


class TestSilenceRuleValidation:
    """测试静默规则验证"""
    
    def test_name_max_length(self):
        """测试名称最大长度"""
        from app.api.notification_rules import SilenceRuleCreate
        
        field = SilenceRuleCreate.model_fields['name']
        metadata = field.metadata
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 100
    
    def test_description_max_length(self):
        """测试描述最大长度"""
        from app.api.notification_rules import SilenceRuleCreate
        
        field = SilenceRuleCreate.model_fields['description']
        metadata = field.metadata
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 200
    
    def test_valid_silence_types(self):
        """测试有效静默类型"""
        from app.api.notification_rules import SilenceRuleCreate
        
        field = SilenceRuleCreate.model_fields['silence_type']
        assert "once/daily/weekly" in str(field.description)


class TestSilenceRuleCreate:
    """测试创建静默规则"""
    
    def test_create_once_rule(self):
        """测试创建一次性规则"""
        from app.api.notification_rules import SilenceRuleCreate
        
        rule = SilenceRuleCreate(
            name="测试规则",
            silence_type="once",
            start_time=datetime(2024, 1, 1, 0, 0),
            end_time=datetime(2024, 1, 2, 0, 0)
        )
        
        assert rule.name == "测试规则"
        assert rule.silence_type == "once"
        assert rule.start_time is not None
    
    def test_create_daily_rule(self):
        """测试创建每日规则"""
        from app.api.notification_rules import SilenceRuleCreate
        
        rule = SilenceRuleCreate(
            name="夜间静默",
            silence_type="daily",
            time_start="22:00",
            time_end="08:00"
        )
        
        assert rule.silence_type == "daily"
        assert rule.time_start == "22:00"
        assert rule.time_end == "08:00"
    
    def test_create_weekly_rule(self):
        """测试创建每周规则"""
        from app.api.notification_rules import SilenceRuleCreate
        
        rule = SilenceRuleCreate(
            name="周末静默",
            silence_type="weekly",
            time_start="00:00",
            time_end="23:59",
            weekdays=[5, 6]
        )
        
        assert rule.silence_type == "weekly"
        assert 5 in rule.weekdays
        assert 6 in rule.weekdays


class TestSilenceRuleToDict:
    """测试静默规则转字典"""
    
    def test_silence_rule_to_dict(self):
        """测试转换函数"""
        from app.api.notification_rules import silence_rule_to_dict, format_weekdays
        
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.channel_id = 1
        mock_rule.name = "测试规则"
        mock_rule.description = "测试描述"
        mock_rule.instance_type = "rdb"
        mock_rule.instance_id = 1
        mock_rule.metric_type = "cpu"
        mock_rule.silence_type = "once"
        mock_rule.start_time = datetime(2024, 1, 1)
        mock_rule.end_time = datetime(2024, 1, 2)
        mock_rule.time_start = None
        mock_rule.time_end = None
        mock_rule.weekdays = None
        mock_rule.is_enabled = True
        mock_rule.created_at = datetime(2024, 1, 1)
        mock_rule.updated_at = datetime(2024, 1, 1)
        
        result = silence_rule_to_dict(mock_rule)
        
        assert result["id"] == 1
        assert result["name"] == "测试规则"
        assert result["silence_type"] == "once"
        assert result["silence_type_label"] == "一次性"
        assert result["is_enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
