"""
调度器服务测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from app.services.scheduler import ApprovalScheduler


class TestApprovalScheduler:
    """审批调度器测试"""

    @pytest.fixture
    def scheduler(self):
        """创建调度器实例"""
        with patch('app.services.scheduler.AsyncIOScheduler'):
            return ApprovalScheduler()

    def test_init(self):
        """测试初始化"""
        scheduler = ApprovalScheduler()
        assert scheduler.scheduler is None

    def test_start_success(self, scheduler):
        """测试启动成功"""
        mock_scheduler_instance = Mock()
        with patch('app.services.scheduler.AsyncIOScheduler') as mock_scheduler_class:
            mock_scheduler_class.return_value = mock_scheduler_instance

            scheduler.start()

            assert scheduler.scheduler == mock_scheduler_instance
            mock_scheduler_instance.add_job.assert_called()
            mock_scheduler_instance.start.assert_called_once()

    def test_start_already_running(self, scheduler):
        """测试重复启动"""
        scheduler.scheduler = Mock()

        scheduler.start()

        # 应该打印警告，不应该重新创建调度器
        assert len(scheduler.scheduler.add_job.mock_calls) == 0

    def test_stop(self, scheduler):
        """测试停止调度器"""
        mock_scheduler_instance = Mock()
        scheduler.scheduler = mock_scheduler_instance

        scheduler.stop()

        mock_scheduler_instance.shutdown.assert_called_once()
        assert scheduler.scheduler is None

    def test_stop_no_scheduler(self, scheduler):
        """测试停止未启动的调度器"""
        scheduler.scheduler = None

        scheduler.stop()

        # 不应该报错
        assert scheduler.scheduler is None

    def test_schedule_approval_execution_success(self, scheduler):
        """测试调度审批执行成功"""
        scheduler.scheduler = Mock()

        execute_time = datetime.now() + timedelta(hours=1)
        result = scheduler.schedule_approval_execution(123, execute_time)

        assert result is True
        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert call_args[0][0] == scheduler.execute_approval
        assert call_args[1]['args'] == [123]

    def test_schedule_approval_execution_no_scheduler(self, scheduler):
        """测试调度器未启动时调度审批执行"""
        scheduler.scheduler = None

        result = scheduler.schedule_approval_execution(123, datetime.now())

        assert result is False

    def test_cancel_scheduled_execution(self, scheduler):
        """测试取消调度执行"""
        scheduler.scheduler = Mock()

        scheduler.cancel_scheduled_execution(123)

        scheduler.scheduler.remove_job.assert_called_once_with(
            "approval_execute_123"
        )

    def test_cancel_scheduled_execution_no_scheduler(self, scheduler):
        """测试取消调度执行（调度器未启动）"""
        scheduler.scheduler = None

        # 不应该报错
        scheduler.cancel_scheduled_execution(123)

    def test_cancel_scheduled_execution_job_not_exists(self, scheduler):
        """测试取消不存在的调度任务"""
        scheduler.scheduler = Mock()
        scheduler.scheduler.remove_job.side_effect = Exception("Job not found")

        # 不应该报错
        scheduler.cancel_scheduled_execution(123)

    @pytest.mark.asyncio
    async def test_check_scheduled_approvals(self, scheduler):
        """测试检查定时审批"""
        mock_db = Mock()
        mock_approval = Mock()
        mock_approval.id = 1
        mock_approval.title = "Test Approval"

        with patch('app.services.scheduler.SessionLocal') as mock_session_class:
            mock_session_class.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = [
                mock_approval
            ]

            with patch.object(scheduler, 'execute_approval') as mock_execute:
                mock_execute.return_value = AsyncMock()

                await scheduler.check_scheduled_approvals()

                mock_db.query.assert_called_once()
                mock_execute.assert_called_once_with(1, mock_db)

    @pytest.mark.asyncio
    async def test_check_scheduled_approvals_exception(self, scheduler):
        """测试检查定时审批（异常情况）"""
        with patch('app.services.scheduler.SessionLocal') as mock_session_class:
            mock_db = Mock()
            mock_db.query.side_effect = Exception("Database error")
            mock_session_class.return_value = mock_db

            # 不应该报错
            await scheduler.check_scheduled_approvals()

            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_approval_not_found(self, scheduler):
        """测试执行不存在的审批"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # 不应该报错
        await scheduler.execute_approval(999, mock_db)

        mock_db.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_approval_wrong_status(self, scheduler):
        """测试执行状态错误的审批"""
        mock_approval = Mock()
        mock_approval.status = "pending"
        mock_approval.execute_time = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_approval
        mock_db = Mock()
        mock_db.query.return_value = mock_query

        # 不应该报错
        await scheduler.execute_approval(1, mock_db)

        mock_db.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_approval_already_executed(self, scheduler):
        """测试执行已执行的审批"""
        mock_approval = Mock()
        mock_approval.status = "approved"
        mock_approval.execute_time = datetime.now()

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_approval
        mock_db = Mock()
        mock_db.query.return_value = mock_query

        # 不应该报错
        await scheduler.execute_approval(1, mock_db)

        mock_db.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_approval_success_rdb(self, scheduler):
        """测试执行审批成功（RDB实例）"""
        mock_approval = Mock()
        mock_approval.status = "approved"
        mock_approval.execute_time = None
        mock_approval.rdb_instance_id = 1
        mock_approval.redis_instance_id = None
        mock_approval.instance_id = None
        mock_approval.title = "Test Approval"

        mock_instance = Mock()
        mock_instance.host = "localhost"
        mock_instance.port = 5432
        mock_instance.db_type = "postgresql"

        mock_query = Mock()
        # 模拟两次查询：一次查审批，一次查实例
        mock_query.filter.return_value.first.side_effect = [mock_approval, mock_instance]
        mock_db = Mock()
        mock_db.query.return_value = mock_query

        with patch('app.services.scheduler.sql_executor') as mock_executor:
            mock_executor.execute_sql = AsyncMock(return_value={"success": True})

            # 不应该报错
            await scheduler.execute_approval(1, mock_db)

            mock_db.query.assert_called()
