"""
通知插件基类

定义通知插件的标准接口，所有通知插件必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class NotificationStatus(Enum):
    """通知状态"""
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class NotificationMessage:
    """统一消息格式
    
    所有通知插件都使用此格式，插件负责转换为各自的格式。
    """
    title: str
    content: str
    markdown: bool = True
    at_users: Optional[List[str]] = None
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "markdown": self.markdown,
            "at_users": self.at_users or [],
            "extra": self.extra or {}
        }


@dataclass
class NotificationResult:
    """通知发送结果
    
    统一的返回格式，包含发送状态和详细信息。
    """
    status: NotificationStatus
    channel_type: str
    message: str = ""
    response_data: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "channel_type": self.channel_type,
            "message": self.message,
            "response_data": self.response_data,
            "latency_ms": self.latency_ms
        }
    
    @property
    def success(self) -> bool:
        """是否成功"""
        return self.status == NotificationStatus.SUCCESS


class NotificationPlugin(ABC):
    """通知插件基类
    
    所有通知插件必须实现此接口，确保统一的调用方式。
    """
    
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """插件名称（用于日志和调试）"""
        pass
    
    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def channel_type(self) -> str:
        """通道类型标识（用于唯一标识插件）"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """显示名称（用于前端展示）"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @property
    @abstractmethod
    def config_schema(self) -> Dict[str, Any]:
        """配置schema，用于前端渲染配置表单
        
        Returns:
            JSON Schema格式的配置定义
        """
        pass
    
    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置是否有效
        
        Args:
            config: 配置字典
        
        Returns:
            配置是否有效
        """
        pass
    
    @abstractmethod
    async def send(
        self,
        config: Dict[str, Any],
        message: NotificationMessage
    ) -> NotificationResult:
        """发送消息
        
        Args:
            config: 配置字典
            message: 消息内容
        
        Returns:
            发送结果
        """
        pass
    
    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """测试连接
        
        Args:
            config: 配置字典
        
        Returns:
            连接是否成功
        """
        pass
    
    @property
    def supports_batch(self) -> bool:
        """是否支持批量发送
        
        Returns:
            是否支持批量发送
        """
        return False
    
    async def send_batch(
        self,
        config: Dict[str, Any],
        messages: List[NotificationMessage]
    ) -> List[NotificationResult]:
        """批量发送消息
        
        如果支持批量发送，插件可以覆盖此方法以提高性能。
        默认实现是逐个发送。
        
        Args:
            config: 配置字典
            messages: 消息列表
        
        Returns:
            发送结果列表
        
        Raises:
            NotImplementedError: 如果不支持批量发送
        """
        if not self.supports_batch:
            raise NotImplementedError("Batch sending is not supported by this plugin")
        
        results = []
        for message in messages:
            result = await self.send(config, message)
            results.append(result)
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            插件信息字典
        """
        return {
            "plugin_name": self.plugin_name,
            "version": self.plugin_version,
            "channel_type": self.channel_type,
            "display_name": self.display_name,
            "description": self.description,
            "config_schema": self.config_schema,
            "supports_batch": self.supports_batch
        }
