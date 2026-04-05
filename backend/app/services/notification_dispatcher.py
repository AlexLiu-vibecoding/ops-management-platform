"""
通知分发器服务

统一管理通知发送，支持多通道批量发送和结果汇总。
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from app.models.notification_new import NotificationChannel
from app.adapters.notification.factory import NotificationAdapterFactory
from app.adapters.notification.base import NotificationMessage, NotificationResult


logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """通知分发器
    
    提供统一的通知发送接口，支持多通道、多接收者发送。
    """
    
    def __init__(self, db: Session):
        """
        初始化通知分发器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def send_to_channel(
        self,
        channel_id: int,
        message: NotificationMessage,
        recipients: Optional[List[str]] = None
    ) -> NotificationResult:
        """发送到指定通道
        
        Args:
            channel_id: 通道ID
            message: 消息内容
            recipients: 接收者列表（部分渠道需要）
        
        Returns:
            发送结果
        """
        # 获取通道配置
        channel = self.db.query(NotificationChannel).filter(
            NotificationChannel.id == channel_id
        ).first()
        
        if not channel:
            return NotificationResult(
                success=False,
                channel_type="unknown",
                error_message=f"Channel not found: {channel_id}"
            )
        
        if not channel.is_enabled:
            return NotificationResult(
                success=False,
                channel_type=channel.channel_type,
                error_message="Channel is disabled"
            )
        
        # 创建适配器
        adapter = NotificationAdapterFactory.create(
            channel.channel_type,
            channel.config
        )
        
        # 验证配置
        if not adapter.validate_config(channel.config):
            return NotificationResult(
                success=False,
                channel_type=channel.channel_type,
                error_message="Invalid channel configuration"
            )
        
        # 发送消息
        try:
            result = await adapter.send(message, recipients)
            result.channel_id = channel_id  # 补充通道ID
            return result
        except Exception as e:
            logger.error(f"Failed to send message to channel {channel_id}: {str(e)}")
            return NotificationResult(
                success=False,
                channel_type=channel.channel_type,
                error_message=f"Send failed: {str(e)}"
            )
    
    async def send_to_channels(
        self,
        channel_ids: List[int],
        message: NotificationMessage,
        recipients: Optional[List[str]] = None
    ) -> List[NotificationResult]:
        """批量发送到多个通道
        
        Args:
            channel_ids: 通道ID列表
            message: 消息内容
            recipients: 接收者列表
        
        Returns:
            发送结果列表
        """
        results = []
        for channel_id in channel_ids:
            result = await self.send_to_channel(channel_id, message, recipients)
            results.append(result)
        return results
    
    async def test_channel(self, channel_id: int) -> NotificationResult:
        """测试通道连接
        
        Args:
            channel_id: 通道ID
        
        Returns:
            测试结果
        """
        # 获取通道配置
        channel = self.db.query(NotificationChannel).filter(
            NotificationChannel.id == channel_id
        ).first()
        
        if not channel:
            return NotificationResult(
                success=False,
                channel_type="unknown",
                error_message=f"Channel not found: {channel_id}"
            )
        
        # 创建适配器
        adapter = NotificationAdapterFactory.create(
            channel.channel_type,
            channel.config
        )
        
        # 测试连接
        try:
            result = await adapter.test_connection(channel.config)
            result.channel_id = channel_id
            return result
        except Exception as e:
            logger.error(f"Failed to test channel {channel_id}: {str(e)}")
            return NotificationResult(
                success=False,
                channel_type=channel.channel_type,
                error_message=f"Test failed: {str(e)}"
            )
    
    def get_supported_channel_types(self) -> List[str]:
        """获取支持的通道类型列表
        
        Returns:
            支持的类型列表
        """
        return NotificationAdapterFactory.get_supported_types()
