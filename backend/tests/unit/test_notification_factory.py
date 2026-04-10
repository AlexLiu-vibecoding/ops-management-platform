"""
通知渠道适配器工厂单元测试

测试通知适配器工厂的创建和注册功能。
"""
import pytest
from app.adapters.notification.factory import NotificationAdapterFactory
from app.adapters.notification.dingtalk_adapter import DingTalkAdapter
from app.adapters.notification.wechat_adapter import WeChatAdapter
from app.adapters.notification.base import NotificationMessage

# 导入注册模块以确保内置适配器被注册
from app.adapters.notification import registry


class TestNotificationAdapterFactory:
    """通知适配器工厂测试"""
    
    def test_create_dingtalk_adapter(self):
        """测试创建钉钉适配器"""
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send",
            "auth_type": "keyword",
            "secret": "test",
            "keywords": ["告警"]
        }
        
        adapter = NotificationAdapterFactory.create("dingtalk", config)
        
        assert isinstance(adapter, DingTalkAdapter)
        assert adapter.get_adapter_type() == "dingtalk"
    
    def test_create_wechat_adapter(self):
        """测试创建企业微信适配器"""
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        }
        
        adapter = NotificationAdapterFactory.create("wechat", config)
        
        assert isinstance(adapter, WeChatAdapter)
        assert adapter.get_adapter_type() == "wechat"
    
    def test_create_unsupported_adapter(self):
        """测试创建不支持的适配器"""
        with pytest.raises(ValueError, match="不支持的通知渠道类型"):
            NotificationAdapterFactory.create("slack", {})
    
    def test_register_custom_adapter(self):
        """测试注册自定义适配器"""
        from app.adapters.notification.base import NotificationAdapter, NotificationResult
        
        # 创建自定义适配器
        class CustomAdapter(NotificationAdapter):
            def __init__(self, config):
                self.config = config
            
            def get_adapter_type(self):
                return "custom"
            
            async def send(self, message, recipients=None):
                return NotificationResult(
                    success=True,
                    channel_type="custom"
                )
            
            def validate_config(self, config):
                return True
            
            async def test_connection(self, config):
                return NotificationResult(
                    success=True,
                    channel_type="custom"
                )
        
        # 注册
        NotificationAdapterFactory.register("custom", CustomAdapter)
        
        # 创建
        adapter = NotificationAdapterFactory.create("custom", {"test": True})
        
        assert isinstance(adapter, CustomAdapter)
        assert adapter.get_adapter_type() == "custom"
    
    def test_get_supported_types(self):
        """测试获取支持的类型列表"""
        types = NotificationAdapterFactory.get_supported_types()
        
        assert isinstance(types, list)
        assert "dingtalk" in types
        assert "wechat" in types
    
    def test_notification_message_creation(self):
        """测试通知消息创建"""
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True,
            extra={"level": "warning"}
        )
        
        assert message.title == "测试标题"
        assert message.content == "测试内容"
        assert message.markdown is True
        assert message.extra["level"] == "warning"
