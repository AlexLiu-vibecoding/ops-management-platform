"""
钉钉通知插件

实现钉钉机器人的消息发送功能。
"""
import hashlib
import hmac
import time
import urllib.parse
import base64
from typing import Any, Dict, List, Optional
import httpx

from app.plugins.notification.base import (
    NotificationPlugin,
    NotificationMessage,
    NotificationResult,
    NotificationStatus
)


class DingTalkPlugin(NotificationPlugin):
    """钉钉通知插件"""
    
    @property
    def plugin_name(self) -> str:
        return "dingtalk"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def channel_type(self) -> str:
        return "dingtalk"
    
    @property
    def display_name(self) -> str:
        return "钉钉"
    
    @property
    def description(self) -> str:
        return "钉钉机器人通知，支持文本和Markdown格式，支持关键词和加签验证"
    
    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "title": "钉钉配置",
            "properties": {
                "webhook": {
                    "type": "string",
                    "title": "Webhook地址",
                    "description": "钉钉机器人的Webhook地址",
                    "required": True,
                    "placeholder": "https://oapi.dingtalk.com/robot/send?access_token=xxx"
                },
                "auth_type": {
                    "type": "string",
                    "title": "验证类型",
                    "description": "选择验证方式",
                    "enum": ["none", "keyword", "sign"],
                    "enumNames": ["无验证", "关键词", "加签"],
                    "default": "none",
                    "required": True
                },
                "secret": {
                    "type": "string",
                    "title": "加签密钥",
                    "description": "使用加签验证时需要配置",
                    "required": False,
                    "condition": {
                        "field": "auth_type",
                        "operator": "==",
                        "value": "sign"
                    }
                },
                "keywords": {
                    "type": "array",
                    "title": "关键词",
                    "description": "使用关键词验证时需要配置",
                    "items": {
                        "type": "string"
                    },
                    "required": False,
                    "condition": {
                        "field": "auth_type",
                        "operator": "==",
                        "value": "keyword"
                    }
                }
            },
            "required": ["webhook", "auth_type"]
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        webhook = config.get("webhook", "")
        if not webhook or not webhook.startswith("https://oapi.dingtalk.com/"):
            return False
        
        auth_type = config.get("auth_type", "none")
        
        if auth_type == "sign":
            if not config.get("secret"):
                return False
        
        if auth_type == "keyword":
            keywords = config.get("keywords", [])
            if not keywords or not isinstance(keywords, list):
                return False
        
        return True
    
    def _generate_sign(self, secret: str) -> tuple[str, str]:
        """生成钉钉加签
        
        Returns:
            (timestamp, sign)
        """
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    def _to_dingtalk_format(self, message: NotificationMessage, config: Dict[str, Any]) -> Dict[str, Any]:
        """转换为钉钉消息格式"""
        if message.markdown:
            # Markdown 格式
            return {
                "msgtype": "markdown",
                "markdown": {
                    "title": message.title,
                    "text": message.content
                }
            }
        else:
            # 文本格式
            content = message.content
            # 如果需要关键词验证
            if config.get("auth_type") == "keyword" and config.get("keywords"):
                content = f"{' '.join(config['keywords'])}\n\n{content}"
            return {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
    
    async def send(
        self,
        config: Dict[str, Any],
        message: NotificationMessage
    ) -> NotificationResult:
        """发送消息"""
        start_time = time.time()
        
        try:
            webhook = config["webhook"]
            auth_type = config.get("auth_type", "none")
            secret = config.get("secret")
            keywords = config.get("keywords", [])
            
            # 构建完整 webhook URL
            full_webhook = webhook
            if auth_type == "sign" and secret:
                timestamp, sign = self._generate_sign(secret)
                separator = "&" if "?" in webhook else "?"
                full_webhook = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
            
            # 转换为钉钉格式
            dingtalk_msg = self._to_dingtalk_format(message, config)
            
            # 发送消息
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    full_webhook,
                    json=dingtalk_msg
                )
            
            latency = (time.time() - start_time) * 1000
            
            # 解析响应
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("errcode") == 0:
                return NotificationResult(
                    status=NotificationStatus.SUCCESS,
                    channel_type=self.channel_type,
                    message="发送成功",
                    response_data=response_data,
                    latency_ms=round(latency, 2)
                )
            else:
                return NotificationResult(
                    status=NotificationStatus.FAILED,
                    channel_type=self.channel_type,
                    message=response_data.get("errmsg", "发送失败"),
                    response_data=response_data,
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
        test_message = NotificationMessage(
            title="连接测试",
            content="这是一条测试消息，如果您看到此消息说明配置成功。",
            markdown=True
        )
        
        result = await self.send(config, test_message)
        return result.success
