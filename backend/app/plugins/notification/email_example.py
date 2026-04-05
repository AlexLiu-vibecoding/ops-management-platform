"""
邮件通知插件示例

展示如何创建一个新的通知插件。
"""
from typing import Any, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.plugins.notification.base import (
    NotificationPlugin,
    NotificationMessage,
    NotificationResult,
    NotificationStatus
)


class EmailPlugin(NotificationPlugin):
    """邮件通知插件（示例）"""
    
    @property
    def plugin_name(self) -> str:
        return "email"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def channel_type(self) -> str:
        return "email"
    
    @property
    def display_name(self) -> str:
        return "邮件"
    
    @property
    def description(self) -> str:
        return "邮件通知，支持SMTP协议"
    
    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "title": "邮件配置",
            "properties": {
                "smtp_host": {
                    "type": "string",
                    "title": "SMTP服务器地址",
                    "required": True,
                    "placeholder": "smtp.example.com"
                },
                "smtp_port": {
                    "type": "integer",
                    "title": "SMTP端口",
                    "required": True,
                    "default": 587
                },
                "smtp_user": {
                    "type": "string",
                    "title": "SMTP用户名",
                    "required": True
                },
                "smtp_password": {
                    "type": "string",
                    "title": "SMTP密码",
                    "required": True
                },
                "sender_email": {
                    "type": "string",
                    "title": "发件人邮箱",
                    "required": True,
                    "placeholder": "noreply@example.com"
                }
            },
            "required": ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "sender_email"]
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        required_fields = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "sender_email"]
        for field in required_fields:
            if not config.get(field):
                return False
        
        if not isinstance(config.get("smtp_port"), int):
            return False
        
        return True
    
    async def send(
        self,
        config: Dict[str, Any],
        message: NotificationMessage
    ) -> NotificationResult:
        """发送邮件"""
        import time
        start_time = time.time()
        
        try:
            smtp_host = config["smtp_host"]
            smtp_port = config["smtp_port"]
            smtp_user = config["smtp_user"]
            smtp_password = config["smtp_password"]
            sender_email = config["sender_email"]
            
            # 获取收件人（从extra中获取，或使用默认）
            recipients = message.extra.get("recipients", []) if message.extra else []
            if not recipients:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    channel_type=self.channel_type,
                    message="缺少收件人地址"
                )
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = message.title
            
            # 邮件正文
            if message.markdown:
                # 简单的Markdown转HTML（实际应用中应该使用专门的库）
                body = message.content.replace("\n", "<br>")
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(message.content, 'plain'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, recipients, msg.as_string())
            
            latency = (time.time() - start_time) * 1000
            
            return NotificationResult(
                status=NotificationStatus.SUCCESS,
                channel_type=self.channel_type,
                message="邮件发送成功",
                latency_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return NotificationResult(
                status=NotificationStatus.FAILED,
                channel_type=self.channel_type,
                message=str(e),
                latency_ms=round(latency, 2)
            )
    
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """测试连接"""
        try:
            smtp_host = config["smtp_host"]
            smtp_port = config["smtp_port"]
            smtp_user = config["smtp_user"]
            smtp_password = config["smtp_password"]
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                return True
        except Exception:
            return False
