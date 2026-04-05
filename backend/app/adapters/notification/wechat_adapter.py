"""
企业微信通知渠道适配器

实现企业微信机器人的消息发送功能。
"""
import time
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.notification.base import NotificationAdapter, NotificationMessage, NotificationResult


class WeChatAdapter(NotificationAdapter):
    """企业微信适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化企业微信适配器
        
        Args:
            config: 配置字典，包含:
                - webhook: webhook 地址
        """
        self.webhook = config.get("webhook", "")
    
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
        message: NotificationMessage,
        recipients: Optional[List[str]] = None
    ) -> NotificationResult:
        """发送消息"""
        start_time = time.time()
        
        try:
            # 转换为企业微信格式
            wechat_msg = self._to_wechat_format(message)
            
            # 发送消息
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.webhook,
                    json=wechat_msg
                )
            
            latency = (time.time() - start_time) * 1000
            
            # 解析响应
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("errcode") == 0:
                return NotificationResult(
                    success=True,
                    channel_type="wechat",
                    response_data=response_data,
                    latency_ms=round(latency, 2)
                )
            else:
                return NotificationResult(
                    success=False,
                    channel_type="wechat",
                    error_message=response_data.get("errmsg", "发送失败"),
                    response_data=response_data,
                    latency_ms=round(latency, 2)
                )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return NotificationResult(
                success=False,
                channel_type="wechat",
                error_message=str(e),
                latency_ms=round(latency, 2)
            )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        webhook = config.get("webhook", "")
        if not webhook:
            return False
        return True
    
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        return "wechat"
    
    async def test_connection(self, config: Dict[str, Any]) -> NotificationResult:
        """测试连接"""
        test_message = NotificationMessage(
            title="连接测试",
            content="这是一条测试消息，如果您看到此消息说明配置成功。",
            markdown=True
        )
        
        # 临时替换配置
        original_webhook = self.webhook
        self.webhook = config.get("webhook", "")
        
        try:
            result = await self.send(test_message)
            return result
        finally:
            # 恢复原始配置
            self.webhook = original_webhook
