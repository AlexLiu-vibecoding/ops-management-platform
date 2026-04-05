"""
企业微信通知插件

实现企业微信机器人的消息发送功能。
"""
import time
from typing import Any, Dict
import httpx

from app.plugins.notification.base import (
    NotificationPlugin,
    NotificationMessage,
    NotificationResult,
    NotificationStatus
)


class WeChatPlugin(NotificationPlugin):
    """企业微信通知插件"""
    
    @property
    def plugin_name(self) -> str:
        return "wechat"
    
    @property
    def plugin_version(self) -> str:
        return "1.0.0"
    
    @property
    def channel_type(self) -> str:
        return "wechat"
    
    @property
    def display_name(self) -> str:
        return "企业微信"
    
    @property
    def description(self) -> str:
        return "企业微信机器人通知，支持文本和Markdown格式"
    
    @property
    def config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "title": "企业微信配置",
            "properties": {
                "webhook": {
                    "type": "string",
                    "title": "Webhook地址",
                    "description": "企业微信机器人的Webhook地址",
                    "required": True,
                    "placeholder": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
                }
            },
            "required": ["webhook"]
        }
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        webhook = config.get("webhook", "")
        if not webhook or not webhook.startswith("https://qyapi.weixin.qq.com/"):
            return False
        return True
    
    def _to_wechat_format(self, message: NotificationMessage) -> Dict[str, Any]:
        """转换为企业微信消息格式"""
        if message.markdown:
            # Markdown 格式
            return {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"{message.title}\n\n{message.content}"
                }
            }
        else:
            # 文本格式
            return {
                "msgtype": "text",
                "text": {
                    "content": f"{message.title}\n\n{message.content}"
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
            
            # 转换为企业微信格式
            wechat_msg = self._to_wechat_format(message)
            
            # 发送消息
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook,
                    json=wechat_msg
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
