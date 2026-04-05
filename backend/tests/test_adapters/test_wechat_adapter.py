"""
企业微信通知适配器单元测试

使用 mock 测试企业微信适配器的核心功能，避免依赖真实的企业微信 API 调用。
"""
import pytest
from unittest.mock import Mock, patch
import asyncio

from app.adapters.notification.wechat_adapter import WeChatAdapter
from app.adapters.notification.base import NotificationMessage, NotificationResult


class TestWeChatAdapter:
    """企业微信适配器测试"""

    def test_init(self):
        """测试初始化"""
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)

        assert adapter.get_adapter_type() == "wechat"
        assert adapter.webhook == config["webhook"]

    @patch('httpx.AsyncClient.post')
    async def test_send_success(self, mock_post):
        """测试发送消息成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        result = await adapter.send(message)

        assert result.success is True
        assert result.channel_type == "wechat"

    @patch('httpx.AsyncClient.post')
    async def test_send_failure(self, mock_post):
        """测试发送消息失败"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 40035,
            "errmsg": "不支持的文本类型"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        result = await adapter.send(message)

        assert result.success is False
        assert "不支持的文本类型" in result.error_message

    @patch('httpx.AsyncClient.post')
    async def test_send_markdown(self, mock_post):
        """测试发送 Markdown 格式消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="**加粗** 和 *斜体*",
            markdown=True
        )

        result = await adapter.send(message)

        assert result.success is True

    @patch('httpx.AsyncClient.post')
    async def test_send_with_extra(self, mock_post):
        """测试发送带额外信息的消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            extra={
                "level": "warning",
                "source": "monitor"
            }
        )

        result = await adapter.send(message)

        assert result.success is True

    @patch('httpx.AsyncClient.post')
    async def test_send_to_mentioned_users(self, mock_post):
        """测试发送消息并提及用户"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            extra={
                "mentioned_list": ["user1", "user2"]
            }
        )

        result = await adapter.send(message)

        assert result.success is True

    @patch('httpx.AsyncClient.post')
    async def test_send_to_mentioned_mobiles(self, mock_post):
        """测试发送消息并提及手机号用户"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            extra={
                "mentioned_mobile_list": ["13800138000"]
            }
        )

        result = await adapter.send(message)

        assert result.success is True

    def test_validate_config_valid(self):
        """测试验证有效配置"""
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)

        assert adapter.validate_config(config) is True

    def test_validate_config_missing_webhook(self):
        """测试缺少 webhook 配置"""
        config = {}

        adapter = WeChatAdapter(config)

        assert adapter.validate_config(config) is False

    def test_validate_config_invalid_webhook(self):
        """测试无效的 webhook URL"""
        config = {
            "webhook": "invalid-url"
        }

        adapter = WeChatAdapter(config)

        assert adapter.validate_config(config) is False

    @patch('httpx.AsyncClient.post')
    async def test_connection(self, mock_post):
        """测试连接测试"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)

        result = await adapter.test_connection(config)

        assert result.success is True
        assert result.channel_type == "wechat"

    @patch('httpx.AsyncClient.post')
    async def test_connection_failure(self, mock_post):
        """测试连接失败"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)

        result = await adapter.test_connection(config)

        assert result.success is False

    @patch('httpx.AsyncClient.post')
    async def test_send_with_recipients(self, mock_post):
        """测试发送消息给指定接收者"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        recipients = ["user1", "user2"]
        result = await adapter.send(message, recipients=recipients)

        assert result.success is True

    def test_get_adapter_type(self):
        """测试获取适配器类型"""
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }

        adapter = WeChatAdapter(config)

        assert adapter.get_adapter_type() == "wechat"
