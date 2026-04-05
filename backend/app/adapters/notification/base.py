"""
通知渠道适配器基类

定义统一的通知渠道接口，所有通知渠道适配器必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class NotificationMessage:
    """统一消息格式
    
    所有通知渠道都使用此格式，适配器负责转换为各自的格式。
    """
    title: str
    content: str
    markdown: bool = True
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "markdown": self.markdown,
            "extra": self.extra or {}
        }


@dataclass
class NotificationResult:
    """通知发送结果
    
    统一的返回格式，包含发送状态和详细信息。
    """
    success: bool
    channel_type: str
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "channel_type": self.channel_type,
            "error_message": self.error_message,
            "response_data": self.response_data,
            "latency_ms": self.latency_ms
        }


class NotificationAdapter(ABC):
    """通知渠道适配器基类
    
    所有通知渠道适配器必须实现此接口，确保统一的发送方式。
    """
    
    @abstractmethod
    async def send(
        self,
        message: NotificationMessage,
        recipients: Optional[List[str]] = None
    ) -> NotificationResult:
        """发送消息
        
        Args:
            message: 统一的消息格式
            recipients: 接收者列表（部分渠道需要，如邮件）
        
        Returns:
            发送结果
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置
        
        Args:
            config: 配置字典
        
        Returns:
            配置是否有效
        """
        pass
    
    @abstractmethod
    def get_adapter_type(self) -> str:
        """获取适配器类型
        
        Returns:
            适配器类型标识，如 "dingtalk", "wechat", "email"
        """
        pass
    
    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> NotificationResult:
        """测试连接
        
        Args:
            config: 配置字典
        
        Returns:
            测试结果
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            适配器信息字典
        """
        return {
            "type": self.get_adapter_type(),
            "config_valid": True
        }
