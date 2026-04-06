"""
监控配置API测试
"""
import pytest
from unittest.mock import MagicMock


class TestMonitorSchemas:
    """测试监控Schema"""
    
    def test_slow_query_config_fields(self):
        """测试慢查询配置Schema字段"""
        from app.api.monitor import SlowQueryConfig
        
        fields = SlowQueryConfig.model_fields
        assert 'enabled' in fields
        assert 'threshold' in fields
        assert 'collect_interval' in fields
        assert 'log_path' in fields
        assert 'analysis_tool' in fields
        assert 'auto_analyze' in fields
        assert 'retention_days' in fields
        assert 'top_n' in fields
    
    def test_slow_query_config_defaults(self):
        """测试慢查询配置默认值"""
        from app.api.monitor import SlowQueryConfig
        
        field = SlowQueryConfig.model_fields['enabled']
        assert field.default is True
        
        field = SlowQueryConfig.model_fields['threshold']
        assert field.default == 1.0
        
        field = SlowQueryConfig.model_fields['collect_interval']
        assert field.default == 300
    
    def test_high_cpu_sql_config_fields(self):
        """测试高CPU SQL配置Schema字段"""
        from app.api.monitor import HighCPUSQLConfig
        
        fields = HighCPUSQLConfig.model_fields
        assert 'enabled' in fields
        assert 'cpu_threshold' in fields
        assert 'memory_threshold' in fields
        assert 'collect_interval' in fields
        assert 'track_realtime' in fields
        assert 'auto_kill' in fields
    
    def test_alert_rule_config_fields(self):
        """测试告警规则配置Schema字段"""
        from app.api.monitor import AlertRuleConfig
        
        fields = AlertRuleConfig.model_fields
        assert 'rule_id' in fields
        assert 'name' in fields
        assert 'metric_type' in fields
        assert 'operator' in fields
        assert 'threshold' in fields
        assert 'severity' in fields
        assert 'enabled' in fields
    
    def test_monitor_overview_fields(self):
        """测试监控总览Schema字段"""
        from app.api.monitor import MonitorOverview
        
        fields = MonitorOverview.model_fields
        assert 'slow_query' in fields
        assert 'high_cpu_sql' in fields
        assert 'performance' in fields
        assert 'alert_stats' in fields


class TestMonitorRouter:
    """测试监控路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.monitor import router
        
        assert router.prefix == "/monitor"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.monitor import router
        
        assert "监控配置" in router.tags


class TestSlowQueryConfig:
    """测试慢查询配置"""
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        from app.api.monitor import SlowQueryConfig
        
        config = SlowQueryConfig()
        
        assert config.enabled is True
        assert config.threshold == 1.0
        assert config.collect_interval == 300
        assert config.analysis_tool == "built-in"
        assert config.auto_analyze is True
    
    def test_create_custom_config(self):
        """测试创建自定义配置"""
        from app.api.monitor import SlowQueryConfig
        
        config = SlowQueryConfig(
            enabled=False,
            threshold=5.0,
            log_path="/var/log/slow.log",
            top_n=20
        )
        
        assert config.enabled is False
        assert config.threshold == 5.0
        assert config.log_path == "/var/log/slow.log"
        assert config.top_n == 20


class TestHighCPUConfig:
    """测试高CPU SQL配置"""
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        from app.api.monitor import HighCPUSQLConfig
        
        config = HighCPUSQLConfig()
        
        assert config.enabled is True
        assert config.cpu_threshold == 80.0
        assert config.memory_threshold == 80.0
        assert config.auto_kill is False
    
    def test_create_with_auto_kill(self):
        """测试创建启用自动Kill的配置"""
        from app.api.monitor import HighCPUSQLConfig
        
        config = HighCPUSQLConfig(
            auto_kill=True,
            auto_kill_threshold=95.0,
            max_kill_time=600
        )
        
        assert config.auto_kill is True
        assert config.auto_kill_threshold == 95.0
        assert config.max_kill_time == 600


class TestAlertRuleConfig:
    """测试告警规则配置"""
    
    def test_create_alert_rule(self):
        """测试创建告警规则"""
        from app.api.monitor import AlertRuleConfig
        
        rule = AlertRuleConfig(
            rule_id="cpu_high",
            name="CPU使用率过高",
            metric_type="cpu",
            operator=">",
            threshold=80.0,
            severity="warning"
        )
        
        assert rule.rule_id == "cpu_high"
        assert rule.metric_type == "cpu"
        assert rule.operator == ">"
        assert rule.threshold == 80.0
    
    def test_alert_rule_with_channels(self):
        """测试创建带通知通道的告警规则"""
        from app.api.monitor import AlertRuleConfig
        
        rule = AlertRuleConfig(
            rule_id="memory_high",
            name="内存使用率过高",
            metric_type="memory",
            operator=">=",
            threshold=90.0,
            notify_channels=[1, 2, 3]
        )
        
        assert len(rule.notify_channels) == 3
    
    def test_alert_rule_severity_levels(self):
        """测试告警级别"""
        from app.api.monitor import AlertRuleConfig
        
        # Info级别
        rule = AlertRuleConfig(
            rule_id="test",
            name="Test",
            metric_type="cpu",
            threshold=50,
            severity="info"
        )
        assert rule.severity == "info"
        
        # Critical级别
        rule.severity = "critical"
        assert rule.severity == "critical"


class TestMonitorOverview:
    """测试监控总览"""
    
    def test_create_overview(self):
        """测试创建总览"""
        from app.api.monitor import MonitorOverview
        
        overview = MonitorOverview(
            slow_query={"enabled": True, "count": 10},
            high_cpu_sql={"enabled": False, "count": 0},
            performance={"enabled": True},
            alert_stats={"total": 5, "critical": 1}
        )
        
        assert overview.slow_query["enabled"] is True
        assert overview.alert_stats["critical"] == 1


class TestMonitorModels:
    """测试监控模型"""
    
    def test_monitor_type_values(self):
        """测试监控类型枚举"""
        from app.models import MonitorType
        
        # 检查是否有监控类型
        assert hasattr(MonitorType, 'CPU') or hasattr(MonitorType, 'SLOW_QUERY') or hasattr(MonitorType, 'MEMORY')


class TestMonitorConfigValidation:
    """测试监控配置验证"""
    
    def test_slow_query_threshold_range(self):
        """测试慢查询阈值范围"""
        from app.api.monitor import SlowQueryConfig
        
        field = SlowQueryConfig.model_fields['threshold']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 0.1
        assert le == 3600
    
    def test_slow_query_retention_days_range(self):
        """测试数据保留天数范围"""
        from app.api.monitor import SlowQueryConfig
        
        field = SlowQueryConfig.model_fields['retention_days']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 1
        assert le == 365
    
    def test_high_cpu_threshold_range(self):
        """测试CPU阈值范围"""
        from app.api.monitor import HighCPUSQLConfig
        
        field = HighCPUSQLConfig.model_fields['cpu_threshold']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 0
        assert le == 100
    
    def test_high_cpu_collect_interval_range(self):
        """测试采集间隔范围"""
        from app.api.monitor import HighCPUSQLConfig
        
        field = HighCPUSQLConfig.model_fields['collect_interval']
        metadata = field.metadata
        ge = next((m.ge for m in metadata if hasattr(m, 'ge')), None)
        le = next((m.le for m in metadata if hasattr(m, 'le')), None)
        assert ge == 1
        assert le == 60


class TestAlertRuleEdgeCases:
    """测试告警规则边界情况"""
    
    def test_alert_rule_all_operators(self):
        """测试所有操作符"""
        from app.api.monitor import AlertRuleConfig
        
        for op in [">", "<", ">=", "<=", "=="]:
            rule = AlertRuleConfig(
                rule_id="test",
                name="Test",
                metric_type="cpu",
                operator=op,
                threshold=80
            )
            assert rule.operator == op
    
    def test_alert_rule_all_severities(self):
        """测试所有严重级别"""
        from app.api.monitor import AlertRuleConfig
        
        for severity in ["info", "warning", "critical"]:
            rule = AlertRuleConfig(
                rule_id="test",
                name="Test",
                metric_type="cpu",
                threshold=80,
                severity=severity
            )
            assert rule.severity == severity
    
    def test_alert_rule_all_metric_types(self):
        """测试所有指标类型"""
        from app.api.monitor import AlertRuleConfig
        
        for metric in ["cpu", "memory", "disk", "connections", "qps", "slow_query"]:
            rule = AlertRuleConfig(
                rule_id="test",
                name="Test",
                metric_type=metric,
                threshold=80
            )
            assert rule.metric_type == metric


class TestMonitorSwitchesModel:
    """测试监控开关模型"""
    
    def test_monitor_switch_model_exists(self):
        """测试MonitorSwitch模型存在"""
        from app.models import MonitorSwitch
        
        assert MonitorSwitch is not None
    
    def test_slow_query_model_exists(self):
        """测试SlowQuery模型存在"""
        from app.models import SlowQuery
        
        assert SlowQuery is not None
    
    def test_performance_metric_model_exists(self):
        """测试PerformanceMetric模型存在"""
        from app.models import PerformanceMetric
        
        assert PerformanceMetric is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
