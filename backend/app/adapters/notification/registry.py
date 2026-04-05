"""
注册内置通知渠道适配器

自动注册所有内置的通知渠道适配器类型。
"""
from app.adapters.notification.factory import NotificationAdapterFactory
from app.adapters.notification.dingtalk_adapter import DingTalkAdapter
from app.adapters.notification.wechat_adapter import WeChatAdapter


def register_builtin_adapters():
    """注册所有内置通知渠道适配器"""
    NotificationAdapterFactory.register("dingtalk", DingTalkAdapter)
    NotificationAdapterFactory.register("wechat", WeChatAdapter)


# 模块导入时自动注册
register_builtin_adapters()
