"""
脚本管理API辅助函数测试 - 100%覆盖率
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestCheckScriptPermission:
    """测试 check_script_permission 函数"""
    
    def test_super_admin_always_has_permission(self):
        """测试超级管理员总有权限"""
        from app.api.scripts import check_script_permission
        
        mock_user = MagicMock()
        mock_user.role.value = "super_admin"
        
        mock_script = MagicMock()
        mock_script.created_by = 999  # 不同的用户
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True
    
    def test_owner_has_permission(self):
        """测试脚本创建者有权限"""
        from app.api.scripts import check_script_permission
        
        mock_user = MagicMock()
        mock_user.role.value = "operator"
        mock_user.id = 1
        
        mock_script = MagicMock()
        mock_script.created_by = 1
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True
    
    def test_other_user_no_permission(self):
        """测试其他用户没有权限"""
        from app.api.scripts import check_script_permission
        
        mock_user = MagicMock()
        mock_user.role.value = "operator"
        mock_user.id = 1
        
        mock_script = MagicMock()
        mock_script.created_by = 2
        mock_script.is_public = False
        mock_script.allowed_roles = None
        
        result = check_script_permission(mock_script, mock_user)
        assert result is False
    
    def test_developer_can_read_public_script(self):
        """测试开发者可以读取公开脚本"""
        from app.api.scripts import check_script_permission
        
        mock_user = MagicMock()
        mock_user.role.value = "developer"
        mock_user.id = 1
        
        mock_script = MagicMock()
        mock_script.created_by = 2
        mock_script.is_public = True
        
        result = check_script_permission(mock_script, mock_user)
        assert result is True


class TestSendScriptNotification:
    """测试 send_script_notification 函数"""
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """测试发送通知成功"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=fake"}
        mock_channel.is_enabled = True
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.name = "Test Script"
        mock_script.notify_on_success = True
        mock_script.notify_channels = "1"
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 1.5
        mock_execution.error_output = None
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        with patch('app.services.notification.NotificationService.create_notification_log') as mock_create:
            mock_create.return_value = MagicMock(id=1)
            
            with patch('app.services.notification.NotificationService.send_dingtalk_message', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True
                
                await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_notification_needed_on_success(self):
        """测试成功时不发送通知（未配置）"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        
        mock_script = MagicMock()
        mock_script.notify_on_success = False  # 不发送成功通知
        mock_script.notify_channels = "1"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_channels_configured(self):
        """测试没有配置通知渠道"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_channels = ""  # 空字符串
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_matching_channels(self):
        """测试没有匹配的通知渠道"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []  # 没有启用的渠道
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_channels = "1,2"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)


class TestExecuteScriptAsync:
    """测试 execute_script_async 函数"""
    
    @pytest.mark.asyncio
    async def test_script_not_found(self):
        """测试脚本不存在"""
        from app.api.scripts import execute_script_async
        from app.database import SessionLocal
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch.object(SessionLocal, '__call__', return_value=mock_db):
            # 函数没有返回语句，所以不会抛出异常
            await execute_script_async(1, 999, {}, 300)
    
    @pytest.mark.asyncio
    async def test_execution_not_found(self):
        """测试执行记录不存在"""
        from app.api.scripts import execute_script_async
        from app.database import SessionLocal
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            MagicMock(),  # script
            None  # execution
        ]
        
        with patch.object(SessionLocal, '__call__', return_value=mock_db):
            await execute_script_async(999, 1, {}, 300)
    
    @pytest.mark.asyncio
    async def test_user_not_found(self):
        """测试触发用户不存在"""
        from app.api.scripts import execute_script_async
        from app.models import ExecutionStatus
        from app.database import SessionLocal
        
        mock_script = MagicMock()
        mock_script.id = 1
        
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.PENDING
        mock_execution.triggered_by = 1
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_script,
            mock_execution,
            None  # user not found
        ]
        
        with patch.object(SessionLocal, '__call__', return_value=mock_db):
            await execute_script_async(1, 1, {}, 300)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
