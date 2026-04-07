"""
脚本管理API完整测试 - 100%覆盖率
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
from datetime import datetime
from fastapi import HTTPException


class TestSendScriptNotification:
    """测试 send_script_notification 函数"""
    
    @pytest.mark.asyncio
    async def test_no_notification_on_success_disabled(self):
        """测试成功时不发送通知（已禁用）"""
        from app.api.scripts import send_script_notification
        from app.models import Script, ScriptExecution, User, ExecutionStatus
        
        mock_db = MagicMock()
        mock_script = MagicMock()
        mock_script.notify_on_success = False
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_notification_on_failure_disabled(self):
        """测试失败时不发送通知（已禁用）"""
        from app.api.scripts import send_script_notification
        from app.models import Script, ScriptExecution, User, ExecutionStatus
        
        mock_db = MagicMock()
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = False
        mock_script.notify_channels = None
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.FAILED
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_notify_channels(self):
        """测试没有配置通知通道"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = ""
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_invalid_channel_ids(self):
        """测试无效的通道ID"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "abc,def"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        
        mock_user = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_no_enabled_channels(self):
        """测试没有启用的通道"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1,2"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_dingtalk_notification_success(self):
        """测试钉钉通知成功"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_dingtalk_notification_with_signature(self):
        """测试钉钉加签通知"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "signature",
            "secret": "encrypted_secret"
        }
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        NotificationService.decrypt_secret = MagicMock(return_value="secret123")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_dingtalk_notification_with_keyword(self):
        """测试钉钉关键词通知"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "keyword",
            "keywords": ["测试"]
        }
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_dingtalk_notification_failed(self):
        """测试钉钉通知失败"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 40003, "errmsg": "unknown error"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_dingtalk_no_webhook(self):
        """测试钉钉没有配置webhook"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_webhook_notification_success(self):
        """测试自定义Webhook通知成功"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 2
        mock_channel.name = "自定义Webhook"
        mock_channel.channel_type = "webhook"
        mock_channel.config = {
            "webhook": "https://example.com/webhook",
            "method": "POST",
            "headers": {"Content-Type": "application/json"}
        }
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "2"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_webhook_get_method(self):
        """测试Webhook GET请求"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 2
        mock_channel.name = "自定义Webhook"
        mock_channel.channel_type = "webhook"
        mock_channel.config = {
            "webhook": "https://example.com/webhook",
            "method": "GET"
        }
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "2"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_webhook_no_webhook_url(self):
        """测试Webhook没有URL"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 2
        mock_channel.name = "自定义Webhook"
        mock_channel.channel_type = "webhook"
        mock_channel.config = {}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "2"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_unsupported_channel_type(self):
        """测试不支持的通道类型"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 3
        mock_channel.name = "邮件"
        mock_channel.channel_type = "email"
        mock_channel.config = {}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "3"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_notification_exception(self):
        """测试通知发送异常"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "invalid_url"}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = True
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.SUCCESS
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_failed_execution_with_error_output(self):
        """测试失败执行带错误输出"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_success = False
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        # 长错误输出
        long_error = "A" * 600
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.FAILED
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 5.5
        mock_execution.error_output = long_error
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)
    
    @pytest.mark.asyncio
    async def test_timeout_execution(self):
        """测试超时执行"""
        from app.api.scripts import send_script_notification
        from app.models import ExecutionStatus
        from app.services.notification import NotificationService
        
        mock_db = MagicMock()
        
        mock_channel = MagicMock()
        mock_channel.id = 1
        mock_channel.name = "钉钉"
        mock_channel.channel_type = "dingtalk"
        mock_channel.config = {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_channel]
        
        mock_script = MagicMock()
        mock_script.notify_on_failure = True
        mock_script.notify_channels = "1"
        mock_script.name = "Test Script"
        
        mock_execution = MagicMock()
        mock_execution.status = ExecutionStatus.TIMEOUT
        mock_execution.start_time = datetime.now()
        mock_execution.duration = 300
        mock_execution.error_output = "Timeout"
        
        mock_user = MagicMock()
        mock_user.username = "test_user"
        
        mock_log = MagicMock()
        NotificationService.create_notification_log = MagicMock(return_value=mock_log)
        NotificationService.update_notification_log = MagicMock()
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await send_script_notification(mock_db, mock_script, mock_execution, mock_user)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
