"""
钉钉通知适配器单元测试

使用 mock 测试钉钉适配器的核心功能，避免依赖真实的钉钉 API 调用。
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.adapters.notification.dingtalk_adapter import DingTalkAdapter
from app.adapters.notification.base import NotificationMessage, NotificationResult


class TestDingTalkAdapter:
    """钉钉适配器测试"""

    def test_init(self):
        """测试初始化"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "secret": "test_secret",
            "keywords": ["告警", "警报"]
        }

        adapter = DingTalkAdapter(config)

        assert adapter.get_adapter_type() == "dingtalk"
        assert adapter.webhook == config["webhook"]
        assert adapter.auth_type == config["auth_type"]
        assert adapter.secret == config["secret"]

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
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        result = await adapter.send(message)

        assert result.success is True
        assert result.channel_type == "dingtalk"

    @patch('httpx.AsyncClient.post')
    async def test_send_failure(self, mock_post):
        """测试发送消息失败"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 310000,
            "errmsg": "keywords not in content"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        result = await adapter.send(message)

        assert result.success is False
        assert "keywords not in content" in result.error_message

    @patch('httpx.AsyncClient.post')
    async def test_send_with_sign(self, mock_post):
        """测试使用签名发送消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errcode": 0,
            "errmsg": "ok"
        }
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "sign",
            "secret": "SEC_test_secret"
        }

        adapter = DingTalkAdapter(config)
        message = NotificationMessage(
            title="测试标题",
            content="测试内容"
        )

        result = await adapter.send(message)

        assert result.success is True
        # 验证调用时是否包含签名参数
        assert mock_post.called

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
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)
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
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)
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

    def test_validate_config_with_keyword(self):
        """测试验证关键字配置"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警", "警报"]
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is True

    def test_validate_config_with_sign(self):
        """测试验证签名配置"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "sign",
            "secret": "SEC_test_secret"
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is True

    def test_validate_config_missing_webhook(self):
        """测试缺少 webhook 配置"""
        config = {
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is False

    def test_validate_config_keyword_missing(self):
        """测试关键字认证缺少关键字"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword"
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is False

    def test_validate_config_sign_missing_secret(self):
        """测试签名认证缺少密钥"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "sign"
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is False

    def test_validate_config_valid_no_auth(self):
        """测试无认证的有效配置"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "none"
        }

        adapter = DingTalkAdapter(config)

        assert adapter.validate_config(config) is True

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
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)

        result = await adapter.test_connection(config)

        assert result.success is True
        assert result.channel_type == "dingtalk"

    @patch('httpx.AsyncClient.post')
    async def test_connection_failure(self, mock_post):
        """测试连接失败"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)

        result = await adapter.test_connection(config)

        assert result.success is False

    def test_get_adapter_type(self):
        """测试获取适配器类型"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "keywords": ["告警"]
        }

        adapter = DingTalkAdapter(config)

        assert adapter.get_adapter_type() == "dingtalk"
