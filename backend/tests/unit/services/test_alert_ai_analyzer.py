"""
告警 AI 分析服务测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.alert_ai_analyzer import (
    AlertAIAnalyzer,
    analyze_alert,
    build_content_with_analysis
)
from app.models import AlertRecord, RDBInstance, RedisInstance, SlowQuery


class TestAlertAIAnalyzer:
    """告警 AI 分析器测试"""

    def test_is_enabled_default(self):
        """测试默认状态"""
        assert AlertAIAnalyzer.is_enabled() is True

    def test_set_enabled(self):
        """测试设置启用状态"""
        AlertAIAnalyzer.set_enabled(False)
        assert AlertAIAnalyzer.is_enabled() is False

        AlertAIAnalyzer.set_enabled(True)
        assert AlertAIAnalyzer.is_enabled() is True

    @pytest.fixture
    def mock_alert(self):
        """创建模拟告警"""
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.alert_title = "慢查询告警"
        alert.alert_level = "warning"
        alert.metric_type = "slow_query"
        alert.alert_content = "检测到慢查询"
        alert.rdb_instance_id = 1
        alert.redis_instance_id = None
        alert.created_at = datetime.now()
        return alert

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.mark.asyncio
    async def test_analyze_alert_disabled(self, mock_db, mock_alert):
        """测试 AI 分析被禁用"""
        AlertAIAnalyzer.set_enabled(False)

        result = await AlertAIAnalyzer.analyze_alert(mock_db, mock_alert)

        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_alert_success(self, mock_db, mock_alert):
        """测试 AI 分析成功"""
        AlertAIAnalyzer.set_enabled(True)

        # 模拟调用 AI
        mock_model = Mock()
        mock_model.name = "test-model"

        with patch('app.services.ai_model_service.call_with_scene') as mock_call:
            mock_call.return_value = ("AI 分析结果", mock_model)

            result = await AlertAIAnalyzer.analyze_alert(mock_db, mock_alert)

            assert result is not None
            assert "AI 分析结果" in result
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_alert_runtime_error(self, mock_db, mock_alert):
        """测试 AI 分析配置错误"""
        AlertAIAnalyzer.set_enabled(True)

        with patch('app.services.ai_model_service.call_with_scene',
                   side_effect=RuntimeError("配置错误")):
            result = await AlertAIAnalyzer.analyze_alert(mock_db, mock_alert)

            # 配置错误应该返回 None，不抛出异常
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_alert_general_error(self, mock_db, mock_alert):
        """测试 AI 分析一般错误"""
        AlertAIAnalyzer.set_enabled(True)

        with patch('app.services.ai_model_service.call_with_scene',
                   side_effect=Exception("未知错误")):
            result = await AlertAIAnalyzer.analyze_alert(mock_db, mock_alert)

            # 一般错误应该返回 None，不抛出异常
            assert result is None

    def test_collect_alert_context_rdb_instance(self, mock_db, mock_alert):
        """测试收集 RDB 实例上下文"""
        # 模拟实例
        mock_instance = Mock(spec=RDBInstance)
        mock_instance.id = 1
        mock_instance.name = "test-db"
        mock_instance.db_type = "postgresql"
        mock_instance.host = "localhost"
        mock_instance.port = 5432
        mock_environment = Mock()
        mock_environment.name = "production"
        mock_instance.environment = mock_environment

        mock_db.query.return_value.filter.return_value.first.return_value = mock_instance

        context = AlertAIAnalyzer._collect_alert_context(mock_db, mock_alert)

        assert context["instance"] is not None
        assert context["instance"]["name"] == "test-db"
        assert context["instance"]["type"] == "rdb"

    def test_collect_alert_context_redis_instance(self, mock_db):
        """测试收集 Redis 实例上下文"""
        # 创建 Redis 告警
        mock_alert = Mock(spec=AlertRecord)
        mock_alert.redis_instance_id = 1
        mock_alert.rdb_instance_id = None
        mock_alert.metric_type = "memory"
        mock_alert.alert_title = "内存告警"
        mock_alert.alert_level = "warning"
        mock_alert.alert_content = "内存使用率高"
        mock_alert.created_at = datetime.now()

        # 模拟 Redis 实例
        mock_instance = Mock(spec=RedisInstance)
        mock_instance.id = 1
        mock_instance.name = "test-redis"
        mock_instance.host = "localhost"
        mock_instance.port = 6379
        mock_environment = Mock()
        mock_environment.name = "production"
        mock_instance.environment = mock_environment

        mock_db.query.return_value.filter.return_value.first.return_value = mock_instance

        context = AlertAIAnalyzer._collect_alert_context(mock_db, mock_alert)

        assert context["instance"] is not None
        assert context["instance"]["name"] == "test-redis"
        assert context["instance"]["type"] == "redis"

    def test_collect_alert_context_slow_query(self, mock_db, mock_alert):
        """测试收集慢查询上下文"""
        # 模拟慢查询
        mock_slow_query = Mock(spec=SlowQuery)
        mock_slow_query.sql_sample = "SELECT * FROM users WHERE id = ?"
        mock_slow_query.query_time = 1500
        mock_slow_query.rows_examined = 10000
        mock_slow_query.rows_sent = 10

        # 模拟查询链
        mock_query = Mock()
        mock_query.order_by.return_value.limit.return_value.all.return_value = [
            mock_slow_query
        ]
        mock_db.query.return_value.filter.return_value = mock_query

        context = AlertAIAnalyzer._collect_alert_context(mock_db, mock_alert)

        assert len(context["recent_slow_queries"]) > 0
        assert context["recent_slow_queries"][0]["execution_time"] == 1500

    def test_collect_alert_context_no_instance(self, mock_db, mock_alert):
        """测试没有实例的上下文"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        context = AlertAIAnalyzer._collect_alert_context(mock_db, mock_alert)

        assert context["instance"] is None

    def test_build_analysis_prompt(self, mock_alert):
        """测试构建分析提示词"""
        context = {
            "instance": {
                "name": "test-db",
                "type": "rdb",
                "db_type": "postgresql",
                "environment": "production"
            },
            "recent_slow_queries": [
                {
                    "execution_time": 1500,
                    "rows_examined": 10000,
                    "sql": "SELECT * FROM users"
                }
            ],
            "recent_alerts": []
        }

        prompt = AlertAIAnalyzer._build_analysis_prompt(mock_alert, context)

        assert "慢查询告警" in prompt
        assert "test-db" in prompt
        assert "1500" in prompt
        assert "根因分析" in prompt
        assert "处理建议" in prompt

    def test_format_analysis(self):
        """测试格式化分析结果"""
        analysis = """
        根因分析

        慢查询


        处理建议

        1. 优化索引


        风险提示

        暂无
        """

        result = AlertAIAnalyzer._format_analysis(analysis)

        # 应该移除空行
        assert "\n\n\n" not in result
        assert "根因分析" in result
        assert "处理建议" in result

    def test_build_notification_content_with_analysis(self):
        """测试构建包含分析的通知内容"""
        original = "告警内容：慢查询"
        analysis = "根因分析：缺少索引\n处理建议：添加索引"

        result = AlertAIAnalyzer.build_notification_content_with_analysis(
            original, analysis
        )

        assert original in result
        assert "AI 分析" in result
        assert analysis in result
        assert "---" in result

    def test_build_notification_content_without_analysis(self):
        """测试构建不包含分析的通知内容"""
        original = "告警内容：慢查询"

        result = AlertAIAnalyzer.build_notification_content_with_analysis(
            original, None
        )

        assert result == original
        assert "AI 分析" not in result


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)

    @pytest.fixture
    def mock_alert(self):
        alert = Mock(spec=AlertRecord)
        alert.id = 1
        alert.alert_title = "测试告警"
        alert.alert_level = "info"
        alert.metric_type = "test"
        alert.alert_content = "测试内容"
        alert.rdb_instance_id = 1
        alert.redis_instance_id = None
        alert.created_at = datetime.now()
        return alert

    @pytest.mark.asyncio
    async def test_analyze_alert_function(self, mock_db, mock_alert):
        """测试便捷函数 analyze_alert"""
        with patch.object(AlertAIAnalyzer, 'analyze_alert',
                         return_value="分析结果") as mock_analyze:
            result = await analyze_alert(mock_db, mock_alert)

            assert result == "分析结果"
            mock_analyze.assert_called_once_with(mock_db, mock_alert)

    def test_build_content_with_analysis_function(self):
        """测试便捷函数 build_content_with_analysis"""
        original = "原始内容"
        analysis = "分析内容"

        result = build_content_with_analysis(original, analysis)

        assert "原始内容" in result
        assert "AI 分析" in result
        assert "分析内容" in result
