"""
通知渠道适配器工厂

负责创建和管理通知渠道适配器实例。
遵循开闭原则：新增通知渠道只需注册，无需修改工厂代码。
"""
from typing import Dict, Any, Type
from app.adapters.notification.base import NotificationAdapter


class NotificationAdapterFactory:
    """通知渠道适配器工厂
    
    使用工厂模式创建适配器实例，支持动态注册新类型。
    """
    
    # 已注册的适配器类型
    _adapters: Dict[str, Type[NotificationAdapter]] = {}
    
    @classmethod
    def register(cls, channel_type: str, adapter_class: Type[NotificationAdapter]):
        """注册新适配器类型
        
        Args:
            channel_type: 通道类型标识（如 "dingtalk", "wechat"）
            adapter_class: 适配器类
        
        Example:
            NotificationAdapterFactory.register("slack", SlackAdapter)
        """
        if not issubclass(adapter_class, NotificationAdapter):
            raise TypeError(f"{adapter_class} 必须是 NotificationAdapter 的子类")
        cls._adapters[channel_type] = adapter_class
    
    @classmethod
    def create(cls, channel_type: str, config: Dict[str, Any]) -> NotificationAdapter:
        """创建适配器实例
        
        Args:
            channel_type: 通道类型标识
            config: 配置字典
        
        Returns:
            适配器实例
        
        Raises:
            ValueError: 不支持的通道类型
        
        Example:
            adapter = NotificationAdapterFactory.create("dingtalk", {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                "auth_type": "sign",
                "secret": "SECxxxx"
            })
        """
        adapter_class = cls._adapters.get(channel_type)
        if not adapter_class:
            raise ValueError(
                f"不支持的通知渠道类型: {channel_type}. "
                f"支持的类型: {list(cls._adapters.keys())}"
            )
        return adapter_class(config)
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取支持的通道类型列表
        
        Returns:
            支持的类型列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def is_supported(cls, channel_type: str) -> bool:
        """检查是否支持指定类型
        
        Args:
            channel_type: 通道类型标识
        
        Returns:
            是否支持
        """
        return channel_type in cls._adapters
