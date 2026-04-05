"""
通知渠道适配器包

提供统一的通知渠道发送接口，支持钉钉/企业微信/飞书/邮件/Webhook 等多种渠道。

使用示例:
    from app.adapters.notification.factory import NotificationAdapterFactory
    from app.adapters.notification.base import NotificationMessage
    
    # 创建适配器
    adapter = NotificationAdapterFactory.create("dingtalk", config={"webhook": "...", ...})
    
    # 发送消息
    message = NotificationMessage(title="告警", content="CPU 使用率过高", markdown=True)
    result = await adapter.send(message)
"""

from app.adapters.notification.base import NotificationAdapter, NotificationMessage, NotificationResult
from app.adapters.notification.factory import NotificationAdapterFactory

__all__ = ["NotificationAdapter", "NotificationMessage", "NotificationResult", "NotificationAdapterFactory"]
