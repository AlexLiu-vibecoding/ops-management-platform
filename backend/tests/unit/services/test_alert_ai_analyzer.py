#!/usr/bin/env python3
"""
告警AI分析器单元测试

测试范围：
1. AI分析器启用/禁用
2. 告警分析流程
3. 上下文数据收集
4. 分析提示词构建
5. 分析结果格式化
6. 通知内容构建
7. 异常处理

运行方式:
    cd /workspace/projects/backend

    # 运行所有告警AI分析器测试
    python -m pytest tests/unit/services/test_alert_ai_analyzer.py -v

    # 运行特定测试
    python -m pytest tests/unit/services/test_alert_ai_analyzer.py::TestAlertAIAnalyzer -v
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import (
    User, UserRole, AlertRecord, RDBInstance, RedisInstance,
    Environment, SlowQuery, LockWait, ReplicationStatus
)
from app.services.alert_ai_analyzer import AlertAIAnalyzer, analyze_alert, build_content_with_analysis


@pytest.fixture(scope="function")
def test_environment(db_session):
    """创建测试环境"""
    env = Environment(
        name="生产环境",
        code="production",
        color="#FF4D4F",
        require_approval=True
    )
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    yield env
    # 清理
    db_session.delete(env)
    db_session.commit()


@pytest.fixture(scope="function")
def test_rdb_instance(db_session, test_environment):
    """创建测试RDB实例"""
    instance = RDBInstance(
        name="测试MySQL实例",
        host="127.0.0.1",
        port=3306,
        username="root",
        password_encrypted="encrypted_password",
        db_type="mysql",
        environment_id=test_environment.id,
        status=True
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    yield instance
    # 清理
    db_session.delete(instance)
    db_session.commit()


@pytest.fixture(scope="function")
def test_redis_instance(db_session, test_environment):
    """创建测试Redis实例"""
    instance = RedisInstance(
        name="测试Redis实例",
        host="127.0.0.1",
        port=6379,
        password_encrypted="encrypted_password",
        environment_id=test_environment.id,
        status=True
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    yield instance
    # 清理
    db_session.delete(instance)
    db_session.commit()


@pytest.fixture(scope="function")
def test_alert(db_session, test_rdb_instance):
    """创建测试告警记录"""
    alert = AlertRecord(
        alert_title="慢查询告警",
        alert_level="high",
        metric_type="slow_query",
        alert_content="查询执行时间超过10秒",
        rdb_instance_id=test_rdb_instance.id,
        status="active"
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    yield alert
    # 清理
    db_session.delete(alert)
    db_session.commit()


@pytest.fixture(scope="function")
def test_slow_query(db_session, test_rdb_instance):
    """创建测试慢查询记录"""
    slow_query = SlowQuery(
        instance_id=test_rdb_instance.id,
        db_name="test_db",
        sql_sample="SELECT * FROM large_table WHERE id > 1000",
        query_time=15.5,
        rows_examined=10000,
        rows_sent=100,
        last_seen=datetime.now()
    )
    db_session.add(slow_query)
    db_session.commit()
    db_session.refresh(slow_query)
    yield slow_query
    # 清理
    db_session.delete(slow_query)
    db_session.commit()


@pytest.fixture(scope="function")
def test_lock_wait(db_session, test_rdb_instance):
    """创建测试锁等待记录"""
    lock = LockWait(
        instance_id=test_rdb_instance.id,
        waiting_sql="UPDATE users SET status=1 WHERE id=100",
        blocking_sql="UPDATE users SET status=0 WHERE id=100",
        wait_time=5.2,
        created_at=datetime.now()
    )
    db_session.add(lock)
    db_session.commit()
    db_session.refresh(lock)
    yield lock
    # 清理
    db_session.delete(lock)
    db_session.commit()


@pytest.fixture(scope="function")
def test_replication_status(db_session, test_rdb_instance):
    """创建测试复制状态记录"""
    repl = ReplicationStatus(
        instance_id=test_rdb_instance.id,
        seconds_behind_master=30,
        slave_io_running=True,
        slave_sql_running=False,
        check_time=datetime.now()
    )
    db_session.add(repl)
    db_session.commit()
    db_session.refresh(repl)
    yield repl
    # 清理
    db_session.delete(repl)
    db_session.commit()


@pytest.mark.unit
class TestAlertAIAnalyzer:
    """告警AI分析器测试"""

    def test_is_enabled_default(self):
        """测试默认启用状态"""
        assert AlertAIAnalyzer.is_enabled() is True

    def test_set_enabled(self):
        """测试设置启用状态"""
        AlertAIAnalyzer.set_enabled(False)
        assert AlertAIAnalyzer.is_enabled() is False
        # 恢复默认状态
        AlertAIAnalyzer.set_enabled(True)

    @pytest.mark.asyncio
    async def test_analyze_alert_when_disabled(self, db_session, test_alert):
        """测试禁用时分析告警"""
        AlertAIAnalyzer.set_enabled(False)
        result = await AlertAIAnalyzer.analyze_alert(db_session, test_alert)
        assert result is None
        # 恢复默认状态
        AlertAIAnalyzer.set_enabled(True)

    @pytest.mark.asyncio
    async def test_analyze_alert_success_with_mock_ai(self, db_session, test_alert):
        """测试成功分析告警（使用mock AI）"""
        # Mock AI模型服务
        mock_model = Mock()
        mock_model.name = "test-model"

        with patch('app.services.alert_ai_analyzer.call_with_scene') as mock_call:
            mock_call.return_value = ("**根因分析**\nSQL查询性能问题\n\n**处理建议**\n1. 添加索引\n2. 优化查询", mock_model)

            result = await AlertAIAnalyzer.analyze_alert(db_session, test_alert)
            assert result is not None
            assert "根因分析" in result
            assert "处理建议" in result

    @pytest.mark.asyncio
    async def test_analyze_alert_runtime_error(self, db_session, test_alert):
        """测试AI配置错误时的处理"""
        with patch('app.services.alert_ai_analyzer.call_with_scene') as mock_call:
            mock_call.side_effect = RuntimeError("配置错误")

            result = await AlertAIAnalyzer.analyze_alert(db_session, test_alert)
            # 配置错误应该返回None，不影响告警发送
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_alert_general_error(self, db_session, test_alert):
        """测试其他异常时的处理"""
        with patch('app.services.alert_ai_analyzer.call_with_scene') as mock_call:
            mock_call.side_effect = Exception("未知错误")

            result = await AlertAIAnalyzer.analyze_alert(db_session, test_alert)
            # 异常应该被捕获并返回None
            assert result is None

    def test_collect_alert_context_rdb_instance(self, db_session, test_alert, test_rdb_instance):
        """测试收集RDB实例上下文"""
        context = AlertAIAnalyzer._collect_alert_context(db_session, test_alert)
        assert context["instance"] is not None
        assert context["instance"]["name"] == test_rdb_instance.name
        assert context["instance"]["type"] == "rdb"
        assert context["instance"]["host"] == test_rdb_instance.host
        assert context["instance"]["port"] == test_rdb_instance.port

    def test_collect_alert_context_redis_instance(self, db_session, test_environment, test_redis_instance):
        """测试收集Redis实例上下文"""
        alert = AlertRecord(
            alert_title="Redis内存告警",
            alert_level="high",
            metric_type="memory",
            alert_content="内存使用率超过90%",
            redis_instance_id=test_redis_instance.id,
            status="active"
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        assert context["instance"] is not None
        assert context["instance"]["name"] == test_redis_instance.name
        assert context["instance"]["type"] == "redis"

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_collect_alert_context_slow_query(self, db_session, test_alert, test_slow_query):
        """测试收集慢查询上下文"""
        context = AlertAIAnalyzer._collect_alert_context(db_session, test_alert)
        assert "recent_slow_queries" in context
        assert len(context["recent_slow_queries"]) >= 1
        assert context["recent_slow_queries"][0]["sql"] == test_slow_query.sql_sample
        assert context["recent_slow_queries"][0]["execution_time"] == test_slow_query.query_time

    def test_collect_alert_context_lock_info(self, db_session, test_rdb_instance):
        """测试收集锁等待上下文"""
        alert = AlertRecord(
            alert_title="锁等待告警",
            alert_level="high",
            metric_type="lock",
            alert_content="检测到长时间锁等待",
            rdb_instance_id=test_rdb_instance.id,
            status="active"
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        assert "lock_info" in context
        assert context["lock_info"] is not None
        assert context["lock_info"]["wait_time"] == test_lock_wait.wait_time

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_collect_alert_context_replication_info(self, db_session, test_rdb_instance):
        """测试收集复制状态上下文"""
        alert = AlertRecord(
            alert_title="主从复制延迟告警",
            alert_level="high",
            metric_type="repl",
            alert_content="主从复制延迟超过30秒",
            rdb_instance_id=test_rdb_instance.id,
            status="active"
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        assert "replication_info" in context
        assert context["replication_info"] is not None
        assert context["replication_info"]["seconds_behind"] == test_replication_status.seconds_behind_master

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_collect_alert_context_recent_alerts(self, db_session, test_alert, test_rdb_instance):
        """测试收集历史告警"""
        # 创建几个历史告警
        for i in range(3):
            old_alert = AlertRecord(
                alert_title=f"历史告警{i}",
                alert_level="medium",
                metric_type="slow_query",
                alert_content=f"历史告警{i}",
                rdb_instance_id=test_rdb_instance.id,
                created_at=datetime.now() - timedelta(hours=i),
                status="active"
            )
            db_session.add(old_alert)
        db_session.commit()

        context = AlertAIAnalyzer._collect_alert_context(db_session, test_alert)
        assert "recent_alerts" in context
        # 应该包含历史告警
        assert len(context["recent_alerts"]) >= 3

        # 清理
        for i in range(3):
            # 这里需要根据实际情况删除
            pass

    def test_build_analysis_prompt_basic(self, db_session, test_alert, test_rdb_instance):
        """测试构建基础分析提示词"""
        context = AlertAIAnalyzer._collect_alert_context(db_session, test_alert)
        prompt = AlertAIAnalyzer._build_analysis_prompt(test_alert, context)

        assert "告警信息" in prompt
        assert test_alert.alert_title in prompt
        assert test_alert.alert_level in prompt
        assert "实例信息" in prompt
        assert test_rdb_instance.name in prompt

    def test_build_analysis_prompt_with_slow_query(self, db_session, test_alert, test_slow_query):
        """测试构建包含慢查询的分析提示词"""
        context = AlertAIAnalyzer._collect_alert_context(db_session, test_alert)
        prompt = AlertAIAnalyzer._build_analysis_prompt(test_alert, context)

        assert "最近慢查询" in prompt
        assert test_slow_query.sql_sample in prompt

    def test_build_analysis_prompt_with_lock(self, db_session, test_rdb_instance, test_lock_wait):
        """测试构建包含锁等待的分析提示词"""
        alert = AlertRecord(
            alert_title="锁等待告警",
            alert_level="high",
            metric_type="lock",
            alert_content="检测到长时间锁等待",
            rdb_instance_id=test_rdb_instance.id,
            status="active"
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        prompt = AlertAIAnalyzer._build_analysis_prompt(alert, context)

        assert "锁等待信息" in prompt
        assert test_lock_wait.waiting_sql in prompt
        assert test_lock_wait.blocking_sql in prompt

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_build_analysis_prompt_with_replication(self, db_session, test_rdb_instance, test_replication_status):
        """测试构建包含复制状态的分析提示词"""
        alert = AlertRecord(
            alert_title="主从复制延迟告警",
            alert_level="high",
            metric_type="repl",
            alert_content="主从复制延迟超过30秒",
            rdb_instance_id=test_rdb_instance.id,
            status="active"
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        prompt = AlertAIAnalyzer._build_analysis_prompt(alert, context)

        assert "复制状态" in prompt
        assert str(test_replication_status.seconds_behind_master) in prompt

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_format_analysis(self):
        """测试格式化分析结果"""
        raw_analysis = """
        **根因分析**


        SQL查询性能问题


        **处理建议**


        1. 添加索引


        2. 优化查询

        """
        formatted = AlertAIAnalyzer._format_analysis(raw_analysis)
        # 应该去除多余的空行
        assert formatted == "**根因分析**\nSQL查询性能问题\n\n**处理建议**\n1. 添加索引\n2. 优化查询"

    def test_build_notification_content_with_analysis(self):
        """测试构建包含分析的完整通知内容"""
        original = "原始告警内容"
        analysis = "**根因分析**\nSQL性能问题\n\n**处理建议**\n1. 优化查询"
        result = AlertAIAnalyzer.build_notification_content_with_analysis(original, analysis)

        assert original in result
        assert "🤖 **AI 分析**" in result
        assert analysis in result

    def test_build_notification_content_without_analysis(self):
        """测试没有分析结果时的通知内容"""
        original = "原始告警内容"
        result = AlertAIAnalyzer.build_notification_content_with_analysis(original, None)
        # 应该返回原始内容
        assert result == original

    def test_build_notification_content_with_empty_analysis(self):
        """测试空分析结果时的通知内容"""
        original = "原始告警内容"
        result = AlertAIAnalyzer.build_notification_content_with_analysis(original, "")
        # 空字符串应该视为没有分析结果
        assert result == original

    @pytest.mark.asyncio
    async def test_convenience_function_analyze_alert(self, db_session, test_alert):
        """测试便捷函数analyze_alert"""
        with patch('app.services.alert_ai_analyzer.call_with_scene') as mock_call:
            mock_model = Mock()
            mock_model.name = "test-model"
            mock_call.return_value = ("分析结果", mock_model)

            result = await analyze_alert(db_session, test_alert)
            assert result == "分析结果"

    def test_convenience_function_build_content_with_analysis(self):
        """测试便捷函数build_content_with_analysis"""
        original = "原始内容"
        analysis = "分析结果"
        result = build_content_with_analysis(original, analysis)

        assert "原始内容" in result
        assert "分析结果" in result
        assert "AI 分析" in result

    def test_collect_alert_context_error_handling(self, db_session):
        """测试上下文收集的异常处理"""
        # 创建一个没有实例关联的告警
        alert = AlertRecord(
            alert_title="孤立告警",
            alert_level="medium",
            metric_type="test",
            alert_content="测试",
            status="active"
        )
        db_session.add(alert)
        db_session.commit()

        # 应该不会抛出异常
        context = AlertAIAnalyzer._collect_alert_context(db_session, alert)
        assert context is not None
        assert context["instance"] is None

        # 清理
        db_session.delete(alert)
        db_session.commit()

    def test_build_analysis_prompt_with_empty_context(self, db_session, test_alert):
        """测试空上下文时的提示词构建"""
        context = {
            "instance": None,
            "recent_slow_queries": [],
            "recent_performance": [],
            "recent_alerts": [],
            "lock_info": None,
            "replication_info": None
        }
        prompt = AlertAIAnalyzer._build_analysis_prompt(test_alert, context)

        # 即使上下文为空，也应该构建完整的提示词
        assert "告警信息" in prompt
        assert test_alert.alert_title in prompt
        assert "实例信息" in prompt
        assert "请分析以下告警" in prompt

    def test_format_analysis_with_trailing_spaces(self):
        """测试去除分析结果中的尾部空格"""
        raw_analysis = "  **根因分析**  \n  SQL问题  \n  "
        formatted = AlertAIAnalyzer._format_analysis(raw_analysis)
        assert formatted == "**根因分析**\nSQL问题"
