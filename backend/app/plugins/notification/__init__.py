"""
通知插件模块

提供插件化的通知通道管理能力。
"""
from app.plugins.notification.base import (
    NotificationPlugin,
    NotificationMessage,
    NotificationResult,
    NotificationStatus
)
from app.plugins.notification.manager import NotificationPluginManager, notification_plugin_manager

__all__ = [
    "NotificationPlugin",
    "NotificationMessage",
    "NotificationResult",
    "NotificationStatus",
    "NotificationPluginManager",
    "notification_plugin_manager"
]
