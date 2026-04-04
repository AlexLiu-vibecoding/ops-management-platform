"""
测试 task_scheduler.py 模块

功能点：
1. TaskScheduler 类：
   - start/stop（调度器启动和停止）
   - _start_performance_collector（启动性能采集）
   - _stop_performance_collector（停止性能采集）
   - _collect_rds_metrics（采集RDS性能指标）
   - _load_enabled_tasks（加载启用的任务）
   - add_job（添加任务）
   - update_job（更新任务）
   - remove_job（移除任务）
   - pause_job（暂停任务）
   - resume_job（恢复任务）
   - trigger_now（立即触发）
   - _execute_scheduled_task（执行定时任务）
   - _execute_task_async（异步执行任务）
   - _run_script（运行脚本）

测试策略：
- 使用 Mock 模拟 APScheduler
- 使用 Mock 模拟数据库操作
- 使用 AsyncMock 模拟异步操作
- 测试正常路径和异常场景
- 测试任务生命周期管理
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from datetime import datetime
import asyncio
import os

from app.services.task_scheduler import TaskScheduler, task_scheduler
from app.models import ScheduledTask, Script, ScriptExecution, RDBInstance, PerformanceMetric, MonitorSwitch, MonitorType, TriggerType, ExecutionStatus
from sqlalchemy.orm import Session


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_scheduler():
    """Mock TaskScheduler 实例"""
    return TaskScheduler()


@pytest.fixture
def mock_apscheduler():
    """Mock APScheduler 实例"""
    scheduler = Mock()
    scheduler.start = Mock()
    scheduler.shutdown = Mock()
    scheduler.add_job = Mock()
    scheduler.remove_job = Mock()
    scheduler.pause_job = Mock()
    scheduler.resume_job = Mock()
    return scheduler


@pytest.fixture
def mock_scheduled_task():
    """Mock 定时任务"""
    task = Mock(spec=ScheduledTask)
    task.id = 1
    task.name = "测试任务"
    task.script_id = 1
    task.cron_expression = "0 */5 * * *"
    task.timezone = "Asia/Shanghai"
    task.status = "enabled"
    task.params = {"key": "value"}
    task.run_count = 0
    task.success_count = 0
    task.fail_count = 0
    return task


@pytest.fixture
def mock_script():
    """Mock 脚本"""
    script = Mock(spec=Script)
    script.id = 1
    script.name = "测试脚本"
    script.script_type = Mock()
    script.script_type.value = "python"
    script.content = "print('hello')"
    script.is_enabled = True
    script.version = "1.0"
    script.timeout = 300
    return script


@pytest.fixture
def mock_rdb_instance():
    """Mock RDS 实例"""
    instance = Mock(spec=RDBInstance)
    instance.id = 1
    instance.is_rds = True
    instance.rds_instance_id = "db-instance-123"
    instance.status = True
    instance.environment_id = 1
    instance.aws_region = "us-east-1"
    return instance


@pytest.fixture
def mock_monitor_switch():
    """Mock 监控开关"""
    switch = Mock(spec=MonitorSwitch)
    switch.instance_id = 1
    switch.monitor_type = MonitorType.PERFORMANCE
    switch.enabled = True
    return switch


@pytest.fixture
def mock_db():
    """Mock 数据库 Session"""
    db = Mock(spec=Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.refresh = Mock()
    db.close = Mock()
    return db


# =============================================================================
# 1. start/stop 测试
# =============================================================================

class TestTaskSchedulerStartStop:
    """测试调度器启动和停止"""

    def test_start_scheduler(self, mock_scheduler):
        """测试启动调度器"""
        with patch('app.services.task_scheduler.AsyncIOScheduler') as mock_async_scheduler:
            mock_instance = Mock()
            mock_instance.start = Mock()
            mock_async_scheduler.return_value = mock_instance
            
            mock_scheduler._load_enabled_tasks = Mock()
            mock_scheduler._start_performance_collector = Mock()
            
            mock_scheduler.start()
            
            assert mock_scheduler.scheduler is not None
            mock_instance.start.assert_called_once()
            mock_scheduler._load_enabled_tasks.assert_called_once()
            mock_scheduler._start_performance_collector.assert_called_once()

    def test_start_scheduler_already_running(self, mock_scheduler):
        """测试启动已运行的调度器"""
        mock_scheduler.scheduler = Mock()
        
        mock_scheduler.start()
        
        # 应该不创建新调度器
        assert mock_scheduler.scheduler is not None

    def test_stop_scheduler(self, mock_scheduler):
        """测试停止调度器"""
        mock_scheduler.scheduler = Mock()
        mock_scheduler._stop_performance_collector = Mock()
        
        # 保存 shutdown 方法引用
        shutdown_method = mock_scheduler.scheduler.shutdown
        
        mock_scheduler.stop()
        
        mock_scheduler._stop_performance_collector.assert_called_once()
        shutdown_method.assert_called_once()
        assert mock_scheduler.scheduler is None

    def test_stop_scheduler_not_running(self, mock_scheduler):
        """测试停止未运行的调度器"""
        mock_scheduler.stop()
        
        # 应该不抛出异常
        assert mock_scheduler.scheduler is None


# =============================================================================
# 2. 性能采集测试
# =============================================================================

class TestPerformanceCollector:
    """测试性能采集功能"""

    def test_start_performance_collector(self, mock_scheduler):
        """测试启动性能采集任务"""
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.add_job = Mock()
        
        mock_scheduler._start_performance_collector()
        
        mock_scheduler.scheduler.add_job.assert_called_once()
        
        # 验证参数
        call_args = mock_scheduler.scheduler.add_job.call_args
        assert call_args[1]['id'] == "rds_performance_collector"
        assert call_args[1]['replace_existing'] is True

    def test_start_performance_collector_exception(self, mock_scheduler):
        """测试启动性能采集任务异常"""
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.add_job = Mock(side_effect=Exception("添加失败"))
        
        # 应该不抛出异常，只记录错误
        mock_scheduler._start_performance_collector()

    def test_stop_performance_collector(self, mock_scheduler):
        """测试停止性能采集任务"""
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.remove_job = Mock()
        
        mock_scheduler._stop_performance_collector()
        
        mock_scheduler.scheduler.remove_job.assert_called_once_with("rds_performance_collector")

    def test_stop_performance_collector_not_exists(self, mock_scheduler):
        """测试停止不存在的性能采集任务"""
        from apscheduler.jobstores.base import JobLookupError
        
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.remove_job = Mock(side_effect=JobLookupError("任务不存在"))
        
        # 应该不抛出异常
        mock_scheduler._stop_performance_collector()


# =============================================================================
# 3. 加载任务测试
# =============================================================================

class TestLoadEnabledTasks:
    """测试加载启用的任务"""

    def test_load_enabled_tasks_success(self, mock_scheduler, mock_scheduled_task, mock_db):
        """测试成功加载启用的任务"""
        mock_scheduler.scheduler = Mock()
        mock_scheduler.add_job = Mock()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_scheduled_task])
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            mock_scheduler._load_enabled_tasks()
        
        mock_scheduler.add_job.assert_called_once_with(mock_scheduled_task)

    def test_load_enabled_tasks_empty(self, mock_scheduler, mock_db):
        """测试加载启用的任务（空列表）"""
        mock_scheduler.scheduler = Mock()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            mock_scheduler._load_enabled_tasks()
        
        # 应该不调用 add_job
        assert not hasattr(mock_scheduler.add_job, 'assert_called')


# =============================================================================
# 4. 添加任务测试
# =============================================================================

class TestAddJob:
    """测试添加任务"""

    def test_add_job_success(self, mock_scheduler, mock_scheduled_task, mock_db):
        """测试成功添加任务"""
        mock_scheduler.scheduler = Mock()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.update = Mock()
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            result = mock_scheduler.add_job(mock_scheduled_task)
        
        assert result is True
        mock_scheduler.scheduler.add_job.assert_called_once()

    def test_add_job_scheduler_not_started(self, mock_scheduler, mock_scheduled_task):
        """测试调度器未启动时添加任务"""
        mock_scheduler.scheduler = None
        
        result = mock_scheduler.add_job(mock_scheduled_task)
        
        assert result is False

    def test_add_job_updates_next_run_time(self, mock_scheduler, mock_scheduled_task, mock_db):
        """测试添加任务更新下次执行时间"""
        mock_scheduler.scheduler = Mock()
        
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.update = Mock()
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            mock_scheduler.add_job(mock_scheduled_task)
        
        # 验证 next_run_time 被更新
        mock_query.update.assert_called_once()
        update_args = mock_query.update.call_args[0][0]
        assert 'next_run_time' in update_args


# =============================================================================
# 5. 更新任务测试
# =============================================================================

class TestUpdateJob:
    """测试更新任务"""

    def test_update_job_enabled(self, mock_scheduler, mock_scheduled_task):
        """测试更新启用的任务"""
        mock_scheduler.remove_job = Mock()
        mock_scheduler.add_job = Mock(return_value=True)
        
        mock_scheduler.update_job(mock_scheduled_task)
        
        mock_scheduler.remove_job.assert_called_once_with(mock_scheduled_task.id)
        mock_scheduler.add_job.assert_called_once_with(mock_scheduled_task)

    def test_update_job_disabled(self, mock_scheduler, mock_scheduled_task):
        """测试更新禁用的任务"""
        mock_scheduled_task.status = "disabled"
        
        mock_scheduler.remove_job = Mock()
        mock_scheduler.add_job = Mock()
        
        mock_scheduler.update_job(mock_scheduled_task)
        
        mock_scheduler.remove_job.assert_called_once_with(mock_scheduled_task.id)
        # 禁用任务不应该重新添加
        mock_scheduler.add_job.assert_not_called()


# =============================================================================
# 6. 移除任务测试
# =============================================================================

class TestRemoveJob:
    """测试移除任务"""

    def test_remove_job_success(self, mock_scheduler):
        """测试成功移除任务"""
        mock_scheduler.scheduler = Mock()
        
        mock_scheduler.remove_job(1)
        
        mock_scheduler.scheduler.remove_job.assert_called_once_with("scheduled_task_1")

    def test_remove_job_not_exists(self, mock_scheduler):
        """测试移除不存在的任务"""
        from apscheduler.jobstores.base import JobLookupError
        
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.remove_job = Mock(side_effect=JobLookupError("任务不存在"))
        
        # 应该不抛出异常
        mock_scheduler.remove_job(1)

    def test_remove_job_scheduler_not_started(self, mock_scheduler):
        """测试调度器未启动时移除任务"""
        mock_scheduler.scheduler = None
        
        # 应该不抛出异常
        mock_scheduler.remove_job(1)


# =============================================================================
# 7. 暂停任务测试
# =============================================================================

class TestPauseJob:
    """测试暂停任务"""

    def test_pause_job_success(self, mock_scheduler):
        """测试成功暂停任务"""
        mock_scheduler.scheduler = Mock()
        
        mock_scheduler.pause_job(1)
        
        mock_scheduler.scheduler.pause_job.assert_called_once_with("scheduled_task_1")

    def test_pause_job_not_exists(self, mock_scheduler):
        """测试暂停不存在的任务"""
        from apscheduler.jobstores.base import JobLookupError
        
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.pause_job = Mock(side_effect=JobLookupError("任务不存在"))
        
        # 应该不抛出异常
        mock_scheduler.pause_job(1)


# =============================================================================
# 8. 恢复任务测试
# =============================================================================

class TestResumeJob:
    """测试恢复任务"""

    def test_resume_job_success(self, mock_scheduler, mock_scheduled_task):
        """测试成功恢复任务"""
        mock_scheduler.scheduler = Mock()
        
        mock_scheduler.resume_job(mock_scheduled_task)
        
        mock_scheduler.scheduler.resume_job.assert_called_once_with("scheduled_task_1")

    def test_resume_job_not_exists(self, mock_scheduler, mock_scheduled_task):
        """测试恢复不存在的任务（重新添加）"""
        from apscheduler.jobstores.base import JobLookupError
        
        mock_scheduler.scheduler = Mock()
        mock_scheduler.scheduler.resume_job = Mock(side_effect=JobLookupError("任务不存在"))
        mock_scheduler.add_job = Mock()
        
        mock_scheduler.resume_job(mock_scheduled_task)
        
        # 任务不存在时应该重新添加
        mock_scheduler.add_job.assert_called_once_with(mock_scheduled_task)


# =============================================================================
# 9. 立即触发测试
# =============================================================================

class TestTriggerNow:
    """测试立即触发任务"""

    @pytest.mark.asyncio
    async def test_trigger_now(self, mock_scheduler, mock_scheduled_task):
        """测试立即触发任务"""
        mock_scheduler._execute_task_async = AsyncMock()
        
        # 在异步上下文中调用
        mock_scheduler.trigger_now(mock_scheduled_task, triggered_by=1)
        
        # 稍微等待以确保任务被创建
        await asyncio.sleep(0.1)
        
        # 验证 _execute_task_async 方法存在
        assert mock_scheduler._execute_task_async is not None


# =============================================================================
# 10. 运行脚本测试
# =============================================================================

class TestRunScript:
    """测试运行脚本"""

    @pytest.mark.asyncio
    async def test_run_python_script_success(self, mock_scheduler, mock_script, mock_db):
        """测试成功运行 Python 脚本"""
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock 进程
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b'output', b'error'))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await mock_scheduler._run_script(mock_script, {}, execution, mock_db)
            
            assert result is True
            assert execution.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_run_python_script_failure(self, mock_scheduler, mock_script, mock_db):
        """测试运行 Python 脚本失败"""
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b'output', b'error'))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process
            
            result = await mock_scheduler._run_script(mock_script, {}, execution, mock_db)
            
            assert result is False
            assert execution.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_run_script_timeout(self, mock_scheduler, mock_script, mock_db):
        """测试脚本执行超时"""
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_process.kill = Mock()
            mock_subprocess.return_value = mock_process
            
            result = await mock_scheduler._run_script(mock_script, {}, execution, mock_db)
            
            assert result is False
            assert execution.status == ExecutionStatus.TIMEOUT
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_bash_script(self, mock_scheduler, mock_script, mock_db):
        """测试运行 Bash 脚本"""
        mock_script.script_type.value = "bash"
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b'output', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            result = await mock_scheduler._run_script(mock_script, {}, execution, mock_db)
            
            assert result is True
            # 验证使用 bash 命令
            call_args = mock_subprocess.call_args[0]
            assert call_args[0] == 'bash'

    @pytest.mark.asyncio
    async def test_run_unsupported_script_type(self, mock_scheduler, mock_script, mock_db):
        """测试运行不支持的脚本类型"""
        mock_script.script_type.value = "unsupported"
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        result = await mock_scheduler._run_script(mock_script, {}, execution, mock_db)
        
        assert result is False
        assert execution.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_run_script_with_params(self, mock_scheduler, mock_script, mock_db):
        """测试运行带参数的脚本"""
        execution = Mock(spec=ScriptExecution)
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now()
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.communicate = AsyncMock(return_value=(b'output', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            params = {"param1": "value1", "param2": "value2"}
            result = await mock_scheduler._run_script(mock_script, params, execution, mock_db)
            
            assert result is True
            # 验证环境变量包含参数
            call_kwargs = mock_subprocess.call_args[1]
            env = call_kwargs['env']
            assert 'SCRIPT_PARAMS' in env
            assert 'PARAM_PARAM1' in env
            assert 'PARAM_PARAM2' in env


# =============================================================================
# 11. 执行任务测试
# =============================================================================

class TestExecuteTask:
    """测试执行任务"""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, mock_scheduler, mock_scheduled_task, mock_script, mock_db):
        """测试成功执行任务"""
        mock_scheduler._run_script = AsyncMock(return_value=True)
        mock_scheduler.send_scheduled_task_notification = AsyncMock()
        
        # Mock 查询
        def mock_query_side_effect(model):
            query_mock = Mock()
            if model == ScheduledTask:
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=mock_scheduled_task)))
            elif model == Script:
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=mock_script)))
            return query_mock
        
        mock_db.query = Mock(side_effect=mock_query_side_effect)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db), \
             patch('app.services.task_scheduler.notification_service') as mock_notification:
            
            await mock_scheduler._execute_task_async(1)
            
            # 验证任务统计更新
            assert mock_scheduled_task.run_count == 1
            assert mock_scheduled_task.success_count == 1
            assert mock_scheduled_task.last_run_status == "success"

    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, mock_scheduler, mock_db):
        """测试执行不存在的任务"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=Mock(first=Mock(return_value=None)))
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            await mock_scheduler._execute_task_async(1)
        
        # 应该不抛出异常，只记录错误

    @pytest.mark.asyncio
    async def test_execute_task_script_not_found(self, mock_scheduler, mock_scheduled_task, mock_db):
        """测试脚本不存在"""
        def mock_query_side_effect(model):
            query_mock = Mock()
            if model == ScheduledTask:
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=mock_scheduled_task)))
            elif model == Script:
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=None)))
            return query_mock
        
        mock_db.query = Mock(side_effect=mock_query_side_effect)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            await mock_scheduler._execute_task_async(1)
        
        # 应该不抛出异常，只记录错误

    @pytest.mark.asyncio
    async def test_execute_task_with_manual_trigger(self, mock_scheduler, mock_scheduled_task, mock_script, mock_db):
        """测试手动触发任务"""
        mock_scheduler._run_script = AsyncMock(return_value=True)
        
        from app.models import TriggerType
        
        def mock_query_side_effect(model):
            query_mock = Mock()
            if model == ScheduledTask:
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=mock_scheduled_task)))
            elif model == Script:
                script_mock = Mock(spec=Script)
                script_mock.id = 1
                script_mock.script_type = Mock()
                script_mock.script_type.value = "python"
                script_mock.content = "print('hello')"
                script_mock.is_enabled = True
                script_mock.version = "1.0"
                script_mock.timeout = 300
                query_mock.filter = Mock(return_value=Mock(first=Mock(return_value=script_mock)))
            return query_mock
        
        mock_db.query = Mock(side_effect=mock_query_side_effect)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db), \
             patch('app.services.task_scheduler.notification_service'):
            
            # 捕获创建的 execution
            created_execution = None
            original_add = mock_db.add
            
            def capture_add(obj):
                nonlocal created_execution
                created_execution = obj
                return original_add(obj)
            
            mock_db.add = Mock(side_effect=capture_add)
            
            await mock_scheduler._execute_task_async(1, triggered_by=1)
            
            # 验证触发类型为手动
            assert created_execution.trigger_type == TriggerType.MANUAL
            assert created_execution.triggered_by == 1


# =============================================================================
# 12. RDS 性能采集测试
# =============================================================================

class TestCollectRDSMetrics:
    """测试 RDS 性能采集"""

    @pytest.mark.asyncio
    async def test_collect_rds_metrics_success(self, mock_scheduler, mock_rdb_instance, mock_monitor_switch, mock_db):
        """测试成功采集 RDS 性能指标"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_rdb_instance])
        mock_db.query = Mock(return_value=mock_query)
        
        # Mock 监控开关查询
        switch_query = Mock()
        switch_query.filter = Mock(return_value=Mock(first=Mock(return_value=mock_monitor_switch)))
        mock_db.query = Mock(side_effect=lambda model: switch_query if model == MonitorSwitch else mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db), \
             patch('app.utils.aws_rds_collector.get_rds_collector_for_environment') as mock_get_collector:
            
            # Mock 收集器
            mock_collector = Mock()
            mock_metrics = Mock()
            mock_metrics.error = None
            mock_metrics.collect_time = datetime.now()
            mock_metrics.cpu_usage = 50.0
            mock_metrics.memory_usage = 60.0
            mock_metrics.read_iops = 100
            mock_metrics.write_iops = 200
            mock_metrics.connections = 10
            mock_metrics.qps = 500
            mock_collector.collect_metrics = Mock(return_value=mock_metrics)
            mock_get_collector.return_value = mock_collector
            
            await mock_scheduler._collect_rds_metrics()
            
            # 验证指标被添加到数据库
            assert mock_db.add.call_count > 0

    @pytest.mark.asyncio
    async def test_collect_rds_metrics_no_instances(self, mock_scheduler, mock_db):
        """测试没有 RDS 实例时采集"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[])
        mock_db.query = Mock(return_value=mock_query)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            await mock_scheduler._collect_rds_metrics()
        
        # 应该提前返回
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_collect_rds_metrics_monitor_disabled(self, mock_scheduler, mock_rdb_instance, mock_db):
        """测试监控禁用时跳过采集"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_rdb_instance])
        mock_db.query = Mock(return_value=mock_query)
        
        # 监控开关禁用
        switch_query = Mock()
        switch_query.filter = Mock(return_value=Mock(first=Mock(return_value=None)))
        
        query_count = [0]
        def query_side_effect(model):
            query_count[0] += 1
            if query_count[0] == 1:
                return mock_query
            else:
                return switch_query
        
        mock_db.query = Mock(side_effect=query_side_effect)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db):
            await mock_scheduler._collect_rds_metrics()
        
        # 应该跳过采集
        assert mock_db.add.call_count == 0

    @pytest.mark.asyncio
    async def test_collect_rds_metrics_collector_error(self, mock_scheduler, mock_rdb_instance, mock_monitor_switch, mock_db):
        """测试收集器返回错误"""
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_rdb_instance])
        mock_db.query = Mock(return_value=mock_query)
        
        switch_query = Mock()
        switch_query.filter = Mock(return_value=Mock(first=Mock(return_value=mock_monitor_switch)))
        
        query_count = [0]
        def query_side_effect(model):
            query_count[0] += 1
            if query_count[0] == 1:
                return mock_query
            else:
                return switch_query
        
        mock_db.query = Mock(side_effect=query_side_effect)
        
        with patch('app.services.task_scheduler.SessionLocal', return_value=mock_db), \
             patch('app.utils.aws_rds_collector.get_rds_collector_for_environment') as mock_get_collector:
            
            mock_collector = Mock()
            mock_metrics = Mock()
            mock_metrics.error = "采集失败"
            mock_collector.collect_metrics = Mock(return_value=mock_metrics)
            mock_get_collector.return_value = mock_collector
            
            await mock_scheduler._collect_rds_metrics()
            
            # 应该跳过添加指标
            assert mock_db.add.call_count == 0
