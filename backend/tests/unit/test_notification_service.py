"""
通知服务测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from app.services.notification import NotificationService
from app.models import NotificationLog


class TestNotificationService:
    """通知服务测试类"""

    def test_render_template_approval(self, db_session):
        """测试审批通知模板渲染"""
        title, content = NotificationService.render_template(
            db_session,
            notification_type="approval",
            title="测试变更",
            requester_name="测试用户",
            instance_name="测试实例",
            change_type="DDL",
            risk_level="low"
        )

        assert "变更审批通知" in title
        assert "测试变更" in content
        assert "测试用户" in content
        assert "测试实例" in content

    def test_render_template_alert(self, db_session):
        """测试告警通知模板渲染"""
        title, content = NotificationService.render_template(
            db_session,
            notification_type="alert",
            alert_title="CPU告警",
            alert_level="high",
            instance_name="生产实例",
            metric_name="cpu_usage",
            current_value="85%",
            threshold="80%"
        )

        assert "告警通知" in title
        assert "CPU告警" in title
        assert "85%" in content
        assert "high" in content

    def test_render_template_scheduled_task(self, db_session):
        """测试定时任务通知模板渲染"""
        title, content = NotificationService.render_template(
            db_session,
            notification_type="scheduled_task",
            task_name="每日备份",
            script_name="backup.sh",
            status="成功",
            duration="10.5秒",
            exit_code=0
        )

        assert "定时任务" in title
        assert "每日备份" in title
        assert "backup.sh" in content

    def test_render_template_with_missing_vars(self, db_session):
        """测试模板渲染时缺少变量"""
        title, content = NotificationService.render_template(
            db_session,
            notification_type="approval",
            title="测试"  # 只提供部分变量
        )

        assert title is not None
        assert content is not None

    def test_create_notification_log(self, db_session):
        """测试创建通知日志"""
        log = NotificationService.create_notification_log(
            db=db_session,
            notification_type="approval",
            title="测试通知",
            content="测试内容",
            channel_id=1,
            channel_name="钉钉通道",
            status="pending"
        )

        assert log.id is not None
        assert log.notification_type == "approval"
        assert log.title == "测试通知"
        assert log.status == "pending"

    def test_update_notification_log(self, db_session):
        """测试更新通知日志"""
        # 先创建日志
        log = NotificationService.create_notification_log(
            db=db_session,
            notification_type="approval",
            title="测试通知",
            status="pending"
        )

        # 更新日志
        NotificationService.update_notification_log(
            db=db_session,
            log=log,
            status="success",
            response_code=200,
            response_data={"errcode": 0}
        )

        assert log.status == "success"
        assert log.response_code == 200
        assert log.sent_at is not None

    def test_generate_approval_token(self):
        """测试生成审批令牌"""
        token = NotificationService.generate_approval_token(
            approval_id=123,
            action="approve",
            expires_hours=24
        )

        assert token is not None
        assert len(token) > 0

    def test_verify_approval_token_valid(self):
        """测试验证有效的审批令牌"""
        # 生成令牌
        token = NotificationService.generate_approval_token(
            approval_id=123,
            action="approve",
            expires_hours=24
        )

        # 验证令牌
        result = NotificationService.verify_approval_token(token)

        assert result is not None
        assert result["approval_id"] == 123
        assert result["action"] == "approve"

    def test_verify_approval_token_expired(self):
        """测试验证过期的审批令牌"""
        # 生成已过期的令牌
        token = NotificationService.generate_approval_token(
            approval_id=123,
            action="approve",
            expires_hours=-1  # 已经过期
        )

        # 验证令牌
        result = NotificationService.verify_approval_token(token)

        assert result is None

    def test_verify_approval_token_invalid(self):
        """测试验证无效的审批令牌"""
        result = NotificationService.verify_approval_token("invalid_token")

        assert result is None

    def test_build_approval_url(self):
        """测试构建审批链接"""
        url = NotificationService.build_approval_url(
            approval_id=123,
            action="approve"
        )

        assert "approvals/dingtalk-action" in url
        assert "token=" in url

    def test_decrypt_secret_valid(self):
        """测试解密有效的密钥"""
        from app.utils.auth import aes_cipher

        # 加密一个密钥
        original = "test_secret_key"
        encrypted = aes_cipher.encrypt(original)

        # 解密
        decrypted = NotificationService.decrypt_secret(encrypted)

        assert decrypted == original

    def test_decrypt_secret_empty(self):
        """测试解密空密钥"""
        result = NotificationService.decrypt_secret("")

        assert result == ""

    def test_decrypt_secret_invalid(self):
        """测试解密无效的密钥"""
        result = NotificationService.decrypt_secret("invalid_encrypted_data")

        assert result == ""

    def test_generate_dingtalk_sign(self):
        """测试生成钉钉加签"""
        timestamp, sign = NotificationService.generate_dingtalk_sign("test_secret")

        assert timestamp is not None
        assert sign is not None
        assert len(timestamp) > 0
        assert len(sign) > 0

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_success(self):
        """测试发送钉钉消息成功"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message={"msgtype": "text", "text": {"content": "测试消息"}},
                auth_type="none"
            )

            assert result["success"] is True
            assert result["response_code"] == 200

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_with_sign(self):
        """测试发送钉钉消息使用加签"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message={"msgtype": "text", "text": {"content": "测试消息"}},
                auth_type="sign",
                secret="test_secret"
            )

            # 检查URL中是否包含签名参数
            call_args = mock_post.call_args
            assert "timestamp=" in str(call_args)
            assert "sign=" in str(call_args)

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_with_keyword(self):
        """测试发送钉钉消息使用关键词"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            message = {"msgtype": "text", "text": {"content": "测试消息"}}
            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message=message,
                auth_type="keyword",
                keywords=["关键字"]
            )

            # 检查消息中是否添加了关键词
            assert "关键字" in message["text"]["content"]

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_failed(self):
        """测试发送钉钉消息失败"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 400001, "errmsg": "参数错误"}
            mock_post.return_value = mock_response

            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message={"msgtype": "text", "text": {"content": "测试消息"}},
                auth_type="none"
            )

            assert result["success"] is False
            assert "参数错误" in result["error_message"]

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_http_error(self):
        """测试发送钉钉消息HTTP错误"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message={"msgtype": "text", "text": {"content": "测试消息"}},
                auth_type="none"
            )

            assert result["success"] is False
            assert result["response_code"] == 500

    @pytest.mark.asyncio
    async def test_send_dingtalk_message_exception(self):
        """测试发送钉钉消息异常"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = Exception("网络错误")

            result = await NotificationService.send_dingtalk_message(
                webhook="https://oapi.dingtalk.com/robot/send",
                message={"msgtype": "text", "text": {"content": "测试消息"}},
                auth_type="none"
            )

            assert result["success"] is False
            assert "网络错误" in result["error_message"]
