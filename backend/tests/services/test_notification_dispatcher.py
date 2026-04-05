"""
通知分发器单元测试

使用 mock 测试通知分发器的核心功能，避免依赖真实的通知渠道。
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.notification_dispatcher import NotificationDispatcher
from app.adapters.notification.base import NotificationMessage, NotificationResult
from app.models.notification_new import NotificationChannel


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.add.return_value = None
    db.commit.return_value = None
    return db


@pytest.fixture
def mock_dingtalk_channel():
    """创建模拟的钉钉通道"""
    channel = Mock()
    channel.id = 1
    channel.name = "测试钉钉通道"
    channel.channel_type = "dingtalk"
    channel.enabled = True
    channel.config = {
        "webhook": "https://oapi.dingtalk.com/robot/send",
        "auth_type": "keyword",
        "keywords": ["告警"]
    }
    return channel


@pytest.fixture
def mock_wechat_channel():
    """创建模拟的企业微信通道"""
    channel = Mock()
    channel.id = 2
    channel.name = "测试企业微信通道"
    channel.channel_type = "wechat"
    channel.enabled = True
    channel.config = {
        "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    }
    return channel


@pytest.fixture
def mock_message():
    """创建模拟的通知消息"""
    return NotificationMessage(
        title="测试告警",
        content="这是一个测试告警消息",
        markdown=True,
        extra={"level": "warning"}
    )


@pytest.fixture
def dispatcher():
    """创建通知分发器实例"""
    return NotificationDispatcher()


class TestNotificationDispatcher:
    """通知分发器测试"""

    def test_init(self, dispatcher):
        """测试初始化"""
        assert dispatcher is not None

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_to_channel_success(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_message):
        """测试成功发送到单个通道"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        result = await dispatcher.send_to_channel(
            mock_db_session,
            mock_dingtalk_channel.id,
            mock_message
        )

        assert result.success is True
        assert result.channel_id == mock_dingtalk_channel.id
        assert mock_adapter.send.called

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_to_channel_failure(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_message):
        """测试发送到单个通道失败"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=False,
            channel_type="dingtalk",
            error_message="发送失败"
        ))
        mock_factory_create.return_value = mock_adapter

        result = await dispatcher.send_to_channel(
            mock_db_session,
            mock_dingtalk_channel.id,
            mock_message
        )

        assert result.success is False
        assert result.error_message == "发送失败"

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_to_multiple_channels(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_wechat_channel, mock_message):
        """测试发送到多个通道"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        results = await dispatcher.send_to_multiple_channels(
            mock_db_session,
            [mock_dingtalk_channel.id, mock_wechat_channel.id],
            mock_message
        )

        assert len(results) == 2
        assert all(r.success for r in results)

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_to_multiple_channels_partial_failure(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_wechat_channel, mock_message):
        """测试发送到多个通道，部分失败"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(side_effect=[
            NotificationResult(success=True, channel_type="dingtalk"),
            NotificationResult(success=False, channel_type="wechat", error_message="失败")
        ])
        mock_factory_create.return_value = mock_adapter

        results = await dispatcher.send_to_multiple_channels(
            mock_db_session,
            [mock_dingtalk_channel.id, mock_wechat_channel.id],
            mock_message
        )

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_with_retry(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_message):
        """测试发送失败后重试"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(side_effect=[
            NotificationResult(success=False, channel_type="dingtalk", error_message="失败"),
            NotificationResult(success=True, channel_type="dingtalk")
        ])
        mock_factory_create.return_value = mock_adapter

        result = await dispatcher.send_with_retry(
            mock_db_session,
            mock_dingtalk_channel.id,
            mock_message,
            max_retries=2
        )

        assert result.success is True
        assert mock_adapter.send.call_count == 2

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_with_retry_exhausted(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_message):
        """测试重试次数耗尽"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=False,
            channel_type="dingtalk",
            error_message="失败"
        ))
        mock_factory_create.return_value = mock_adapter

        result = await dispatcher.send_with_retry(
            mock_db_session,
            mock_dingtalk_channel.id,
            mock_message,
            max_retries=2
        )

        assert result.success is False
        assert mock_adapter.send.call_count == 3  # 初始1次 + 2次重试

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_broadcast_message(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_wechat_channel, mock_message):
        """测试广播消息"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        # 模拟数据库查询返回通道
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_dingtalk_channel,
            mock_wechat_channel
        ]

        result = await dispatcher.broadcast_message(
            mock_db_session,
            mock_message
        )

        assert "total" in result
        assert "success_count" in result
        assert "failure_count" in result
        assert result["total"] == 2
        assert result["success_count"] == 2

    async def test_send_scheduled_message(self, dispatcher, mock_db_session, mock_message):
        """测试发送定时消息"""
        scheduled_time = datetime.now()

        result = await dispatcher.send_scheduled_message(
            mock_db_session,
            mock_dingtalk_channel,
            mock_message,
            scheduled_time
        )

        # 定时消息的实现可能不同，这里只测试调用不报错
        assert "scheduled" in result or "success" in result

    def test_create_message_from_template(self, dispatcher):
        """测试从模板创建消息"""
        template = "告警：{level} - {message}"
        variables = {"level": "warning", "message": "CPU使用率过高"}

        message = dispatcher.create_message_from_template(
            template,
            variables
        )

        assert "warning" in message.content
        assert "CPU使用率过高" in message.content

    def test_create_message_from_template_missing_variable(self, dispatcher):
        """测试模板缺少变量"""
        template = "告警：{level} - {message}"
        variables = {"level": "warning"}  # 缺少 message

        message = dispatcher.create_message_from_template(
            template,
            variables
        )

        # 应该处理缺失的变量
        assert message.content is not None

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_test_channel_connection(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel):
        """测试通道连接测试"""
        mock_adapter = Mock()
        mock_adapter.test_connection = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        result = await dispatcher.test_channel_connection(
            mock_db_session,
            mock_dingtalk_channel.id
        )

        assert result.success is True

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_with_recipients(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel, mock_message):
        """测试发送给指定接收者"""
        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        recipients = ["user1", "user2"]
        result = await dispatcher.send_to_channel(
            mock_db_session,
            mock_dingtalk_channel.id,
            mock_message,
            recipients=recipients
        )

        assert result.success is True

    def test_validate_message(self, dispatcher, mock_message):
        """测试验证消息"""
        assert dispatcher._validate_message(mock_message) is True

    def test_validate_message_invalid(self, dispatcher):
        """测试验证无效消息"""
        invalid_message = NotificationMessage(
            title="",  # 空标题
            content=""  # 空内容
        )

        assert dispatcher._validate_message(invalid_message) is False

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_get_delivery_status(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel):
        """测试获取投递状态"""
        # 模拟数据库查询返回发送记录
        mock_record = Mock()
        mock_record.status = "success"
        mock_record.sent_at = datetime.now()
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_record]

        status = await dispatcher.get_delivery_status(
            mock_db_session,
            mock_dingtalk_channel.id
        )

        assert "total" in status
        assert "success" in status
        assert status["success"] == 1

    @patch('app.adapters.notification.factory.NotificationAdapterFactory.create')
    async def test_send_batch_messages(self, mock_factory_create, dispatcher, mock_db_session, mock_dingtalk_channel):
        """测试批量发送消息"""
        messages = [
            NotificationMessage(title="消息1", content="内容1"),
            NotificationMessage(title="消息2", content="内容2"),
            NotificationMessage(title="消息3", content="内容3")
        ]

        mock_adapter = Mock()
        mock_adapter.send = AsyncMock(return_value=NotificationResult(
            success=True,
            channel_type="dingtalk"
        ))
        mock_factory_create.return_value = mock_adapter

        results = await dispatcher.send_batch_messages(
            mock_db_session,
            mock_dingtalk_channel.id,
            messages
        )

        assert len(results) == 3
        assert all(r.success for r in results)
