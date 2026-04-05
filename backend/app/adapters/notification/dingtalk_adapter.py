"""
钉钉通知渠道适配器

实现钉钉机器人的消息发送功能。
"""
import hashlib
import hmac
import time
import urllib.parse
import base64
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.notification.base import NotificationAdapter, NotificationMessage, NotificationResult


class DingTalkAdapter(NotificationAdapter):
    """钉钉适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化钉钉适配器
        
        Args:
            config: 配置字典，包含:
                - webhook: webhook 地址
                - auth_type: 验证类型（none/keyword/sign）
                - secret: 密钥（sign 验证时需要）
                - keywords: 关键词列表（keyword 验证时需要）
        """
        self.webhook = config.get("webhook", "")
        self.auth_type = config.get("auth_type", "none")
        self.secret = config.get("secret")
        self.keywords = config.get("keywords", [])
    
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
    
    def _to_dingtalk_format(self, message: NotificationMessage) -> Dict[str, Any]:
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
            if self.auth_type == "keyword" and self.keywords:
                content = f"{' '.join(self.keywords)}\n\n{content}"
            return {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
    
    async def send(
        self,
        message: NotificationMessage,
        recipients: Optional[List[str]] = None
    ) -> NotificationResult:
        """发送消息"""
        import time
        start_time = time.time()
        
        try:
            # 构建完整 webhook URL
            full_webhook = self.webhook
            if self.auth_type == "sign" and self.secret:
                timestamp, sign = self._generate_sign(self.secret)
                separator = "&" if "?" in self.webhook else "?"
                full_webhook = f"{self.webhook}{separator}timestamp={timestamp}&sign={sign}"
            
            # 转换为钉钉格式
            dingtalk_msg = self._to_dingtalk_format(message)
            
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
                    success=True,
                    channel_type="dingtalk",
                    response_data=response_data,
                    latency_ms=round(latency, 2)
                )
            else:
                return NotificationResult(
                    success=False,
                    channel_type="dingtalk",
                    error_message=response_data.get("errmsg", "发送失败"),
                    response_data=response_data,
                    latency_ms=round(latency, 2)
                )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return NotificationResult(
                success=False,
                channel_type="dingtalk",
                error_message=str(e),
                latency_ms=round(latency, 2)
            )
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        webhook = config.get("webhook", "")
        if not webhook:
            return False
        
        auth_type = config.get("auth_type", "none")
        
        if auth_type == "sign":
            if not config.get("secret"):
                return False
        
        if auth_type == "keyword":
            if not config.get("keywords"):
                return False
        
        return True
    
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        return "dingtalk"
    
    async def test_connection(self, config: Dict[str, Any]) -> NotificationResult:
        """测试连接"""
        test_message = NotificationMessage(
            title="连接测试",
            content="这是一条测试消息，如果您看到此消息说明配置成功。",
            markdown=True
        )
        
        # 临时替换配置
        original_webhook = self.webhook
        original_auth_type = self.auth_type
        original_secret = self.secret
        original_keywords = self.keywords
        
        self.webhook = config.get("webhook", "")
        self.auth_type = config.get("auth_type", "none")
        self.secret = config.get("secret")
        self.keywords = config.get("keywords", [])
        
        try:
            result = await self.send(test_message)
            return result
        finally:
            # 恢复原始配置
            self.webhook = original_webhook
            self.auth_type = original_auth_type
            self.secret = original_secret
            self.keywords = original_keywords
