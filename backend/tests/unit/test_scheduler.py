"""
测试定时任务调度器 - Scheduler Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestApprovalScheduler:
    """测试审批定时调度器"""
    
    @pytest.fixture
    def scheduler(self):
        """创建测试用的调度器实例"""
        from app.services.scheduler import ApprovalScheduler
        return ApprovalScheduler()
    
    @pytest.fixture
    def mock_scheduler(self):
        """Mock APScheduler"""
        with patch('app.services.scheduler.AsyncIOScheduler') as mock:
            scheduler_instance = MagicMock()
            mock.return_value = scheduler_instance
            yield scheduler_instance
    
    def test_scheduler_init(self, scheduler):
        """测试调度器初始化"""
        assert scheduler.scheduler is None
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_scheduler_start(self, mock_scheduler_class, scheduler):
        """测试启动调度器"""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        
        assert scheduler.scheduler is not None
        mock_scheduler.start.assert_called_once()
        # 验证添加了5个定时任务
        assert mock_scheduler.add_job.call_count == 5
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_scheduler_start_already_running(self, mock_scheduler_class, scheduler):
        """测试启动已经在运行的调度器"""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        scheduler.start()  # 再次启动
        
        # 应该只启动一次
        mock_scheduler.start.assert_called_once()
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_scheduler_stop(self, mock_scheduler_class, scheduler):
        """测试停止调度器"""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        scheduler.stop()
        
        mock_scheduler.shutdown.assert_called_once()
        assert scheduler.scheduler is None
    
    def test_scheduler_stop_not_running(self, scheduler):
        """测试停止未运行的调度器"""
        # 不应该抛出异常
        scheduler.stop()
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_schedule_approval_execution(self, mock_scheduler_class, scheduler):
        """测试调度审批执行"""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        
        execute_time = datetime.now() + timedelta(hours=1)
        result = scheduler.schedule_approval_execution(123, execute_time)
        
        assert result is True
        mock_scheduler.add_job.assert_called()
        # 验证是DateTrigger
        call_args = mock_scheduler.add_job.call_args
        assert 'trigger' in call_args.kwargs
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_schedule_approval_execution_not_started(self, mock_scheduler_class, scheduler):
        """测试在未启动的调度器上调度"""
        execute_time = datetime.now() + timedelta(hours=1)
        result = scheduler.schedule_approval_execution(123, execute_time)
        
        assert result is False
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_cancel_scheduled_execution(self, mock_scheduler_class, scheduler):
        """测试取消定时执行"""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        scheduler.cancel_scheduled_execution(123)
        
        mock_scheduler.remove_job.assert_called_once_with("approval_execute_123")
    
    def test_cancel_scheduled_execution_not_running(self, scheduler):
        """测试在调度器未运行时取消"""
        # 不应该抛出异常
        scheduler.cancel_scheduled_execution(123)
    
    @patch('app.services.scheduler.AsyncIOScheduler')
    def test_cancel_scheduled_execution_job_not_found(self, mock_scheduler_class, scheduler):
        """测试取消不存在的任务"""
        mock_scheduler = MagicMock()
        mock_scheduler.remove_job.side_effect = Exception("Job not found")
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler.start()
        # 不应该抛出异常
        scheduler.cancel_scheduled_execution(999)


class TestCheckScheduledApprovals:
    """测试检查定时审批"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.ApprovalScheduler.execute_approval')
    async def test_check_scheduled_approvals_found(self, mock_execute, mock_session_class):
        """测试发现需要执行的审批"""
        from app.services.scheduler import approval_scheduler
        
        # Mock 数据库会话
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 审批记录
        mock_approval = MagicMock()
        mock_approval.id = 123
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = [mock_approval]
        
        await approval_scheduler.check_scheduled_approvals()
        
        mock_execute.assert_called_once_with(123, mock_db)
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.ApprovalScheduler.execute_approval')
    async def test_check_scheduled_approvals_empty(self, mock_execute, mock_session_class):
        """测试没有需要执行的审批"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        await approval_scheduler.check_scheduled_approvals()
        
        mock_execute.assert_not_called()
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_check_scheduled_approvals_exception(self, mock_session_class):
        """测试检查异常处理"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        mock_db.query.side_effect = Exception("Database error")
        
        # 不应该抛出异常
        await approval_scheduler.check_scheduled_approvals()
        mock_db.close.assert_called_once()


class TestExecuteApproval:
    """测试执行审批"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.sql_executor')
    @patch('app.services.scheduler.notification_service')
    async def test_execute_approval_success(
        self, mock_notification, mock_sql_executor, mock_session_class
    ):
        """测试成功执行审批"""
        from app.services.scheduler import approval_scheduler
        from app.models import ApprovalStatus
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 审批记录
        mock_approval = MagicMock()
        mock_approval.id = 123
        mock_approval.status = ApprovalStatus.APPROVED
        mock_approval.execute_time = None
        mock_approval.title = "Test Approval"
        mock_approval.change_type = "DDL"
        mock_approval.rdb_instance_id = 1
        mock_approval.redis_instance_id = None
        mock_approval.instance_id = None
        mock_approval.requester_id = 1
        mock_approval.instance = None
        mock_approval.environment_id = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_approval
        
        # Mock 实例
        mock_instance = MagicMock()
        mock_instance.id = 1
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_approval,  # 第一次查询审批
            mock_instance,  # 第二次查询实例
        ]
        
        # Mock SQL执行结果
        mock_sql_executor.execute_for_approval.return_value = (True, "Success", 1)
        mock_sql_executor.check_execution_success.return_value = True
        
        await approval_scheduler.execute_approval(123)
        
        assert mock_approval.status == ApprovalStatus.EXECUTED
        mock_db.commit.assert_called()
        mock_notification.send_approval_notification.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_execute_approval_not_found(self, mock_session_class):
        """测试执行不存在的审批"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # 不应该抛出异常
        await approval_scheduler.execute_approval(999)
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_execute_approval_already_executed(self, mock_session_class):
        """测试执行已执行的审批"""
        from app.services.scheduler import approval_scheduler
        from app.models import ApprovalStatus
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        mock_approval = MagicMock()
        mock_approval.id = 123
        mock_approval.status = ApprovalStatus.EXECUTED
        mock_approval.execute_time = datetime.now()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_approval
        
        await approval_scheduler.execute_approval(123)
        
        # 不应该再执行
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_execute_approval_not_approved(self, mock_session_class):
        """测试执行未通过的审批"""
        from app.services.scheduler import approval_scheduler
        from app.models import ApprovalStatus
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        mock_approval = MagicMock()
        mock_approval.id = 123
        mock_approval.status = ApprovalStatus.PENDING
        mock_approval.execute_time = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_approval
        
        await approval_scheduler.execute_approval(123)
        
        # 不应该执行
        mock_db.commit.assert_not_called()


class TestCleanupExpiredFiles:
    """测试清理过期文件"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.get_storage_settings')
    @patch('app.services.scheduler.storage_manager')
    async def test_cleanup_expired_files_success(
        self, mock_storage, mock_settings, mock_session_class
    ):
        """测试成功清理过期文件"""
        from app.services.scheduler import approval_scheduler
        from app.models import ApprovalStatus
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 设置
        mock_settings.return_value.FILE_RETENTION_DAYS = 30
        
        # Mock 过期审批
        mock_approval = MagicMock()
        mock_approval.id = 1
        mock_approval.sql_file_path = "path/to/file.sql"
        mock_approval.rollback_file_path = "path/to/rollback.sql"
        
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = [mock_approval]
        
        # Mock 存储操作
        mock_storage.delete_sql_file.return_value = True
        mock_storage.cleanup_expired_files.return_value = 0
        
        await approval_scheduler.cleanup_expired_files()
        
        mock_storage.delete_sql_file.assert_any_call("path/to/file.sql")
        mock_storage.delete_sql_file.assert_any_call("path/to/rollback.sql")
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.get_storage_settings')
    async def test_cleanup_expired_files_exception(self, mock_settings, mock_session_class):
        """测试清理异常处理"""
        from app.services.scheduler import approval_scheduler
        
        mock_settings.return_value.FILE_RETENTION_DAYS = 30
        mock_session_class.side_effect = Exception("Database error")
        
        # 不应该抛出异常
        await approval_scheduler.cleanup_expired_files()


class TestCleanupExpiredSlowLogFiles:
    """测试清理过期慢日志文件"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.os.path.exists')
    @patch('app.services.scheduler.os.remove')
    async def test_cleanup_slow_log_files_success(self, mock_remove, mock_exists, mock_session_class):
        """测试成功清理慢日志文件"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 过期文件
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.file_path = "/path/to/slow.log"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_file]
        mock_exists.return_value = True
        
        await approval_scheduler.cleanup_expired_slow_log_files()
        
        mock_remove.assert_called_once_with("/path/to/slow.log")
        mock_db.delete.assert_called_once_with(mock_file)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_cleanup_slow_log_files_empty(self, mock_session_class):
        """测试没有过期文件"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        await approval_scheduler.cleanup_expired_slow_log_files()
        
        mock_db.commit.assert_not_called()


class TestCleanupExpiredAnalysisHistory:
    """测试清理过期分析历史"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    async def test_cleanup_analysis_history_success(self, mock_session_class):
        """测试成功清理分析历史"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 过期历史
        mock_history = MagicMock()
        mock_history.id = 1
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_history]
        
        await approval_scheduler.cleanup_expired_analysis_history()
        
        mock_db.delete.assert_called_once_with(mock_history)
        mock_db.commit.assert_called_once()


class TestRefreshAIModels:
    """测试刷新 AI 模型列表"""
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.httpx.AsyncClient')
    async def test_refresh_doubao_models(self, mock_client_class, mock_session_class):
        """测试刷新豆包模型列表"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 配置
        mock_config = MagicMock()
        mock_config.provider = "doubao"
        mock_config.is_enabled = True
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_config]
        mock_db.query.return_value.filter.return_value.first.return_value = None  # 模型不存在，需要创建
        
        await approval_scheduler.refresh_ai_available_models()
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.scheduler.SessionLocal')
    @patch('app.services.scheduler.httpx.AsyncClient')
    async def test_refresh_openai_compatible_models(self, mock_client_class, mock_session_class):
        """测试刷新 OpenAI 兼容模型列表"""
        from app.services.scheduler import approval_scheduler
        
        mock_db = MagicMock()
        mock_session_class.return_value = mock_db
        
        # Mock 配置
        mock_config = MagicMock()
        mock_config.provider = "openai"
        mock_config.is_enabled = True
        mock_config.base_url = "https://api.openai.com/v1"
        mock_config.api_key_encrypted = None
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_config]
        
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4", "name": "GPT-4"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        await approval_scheduler.refresh_ai_available_models()
        
        mock_client.get.assert_called_once()


class TestGlobalScheduler:
    """测试全局调度器实例"""
    
    def test_global_instance_exists(self):
        """测试全局实例存在"""
        from app.services.scheduler import approval_scheduler
        from app.services.scheduler import ApprovalScheduler
        
        assert isinstance(approval_scheduler, ApprovalScheduler)
