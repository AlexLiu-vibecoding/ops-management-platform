"""
通知插件系统测试
"""
import pytest
from app.plugins.notification.manager import NotificationPluginManager
from app.plugins.notification.base import NotificationMessage, NotificationStatus
from app.plugins.notification.dingtalk import DingTalkPlugin
from app.plugins.notification.wechat import WeChatPlugin


class TestNotificationPluginManager:
    """测试插件管理器"""
    
    def test_init(self):
        """测试初始化"""
        manager = NotificationPluginManager()
        assert manager is not None
        assert len(manager._plugins) == 0
    
    def test_register_plugin(self):
        """测试注册插件"""
        manager = NotificationPluginManager()
        result = manager.register_plugin(DingTalkPlugin)
        assert result is True
        assert len(manager._plugins) == 1
        assert manager.plugin_exists("dingtalk")
    
    def test_register_duplicate_plugin(self):
        """测试注册重复插件"""
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        result = manager.register_plugin(DingTalkPlugin)
        assert result is False
        assert len(manager._plugins) == 1
    
    def test_get_plugin(self):
        """测试获取插件"""
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        plugin = manager.get_plugin("dingtalk")
        assert plugin is not None
        assert plugin.plugin_name == "dingtalk"
        assert plugin.display_name == "钉钉"
    
    def test_get_nonexistent_plugin(self):
        """测试获取不存在的插件"""
        manager = NotificationPluginManager()
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None
    
    def test_list_plugins(self):
        """测试列出所有插件"""
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        manager.register_plugin(WeChatPlugin)
        
        plugins = manager.list_plugins()
        assert len(plugins) == 2
        
        plugin_types = [p["channel_type"] for p in plugins]
        assert "dingtalk" in plugin_types
        assert "wechat" in plugin_types
    
    def test_discover_plugins(self):
        """测试自动发现插件"""
        manager = NotificationPluginManager()
        count = manager.discover_plugins("app/plugins/notification")
        assert count >= 2  # 至少有钉钉和企业微信插件


class TestDingTalkPlugin:
    """测试钉钉插件"""
    
    def test_plugin_properties(self):
        """测试插件属性"""
        plugin = DingTalkPlugin()
        assert plugin.plugin_name == "dingtalk"
        assert plugin.plugin_version == "1.0.0"
        assert plugin.channel_type == "dingtalk"
        assert plugin.display_name == "钉钉"
        assert plugin.description is not None
        assert plugin.config_schema is not None
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        """测试验证配置 - 有效配置"""
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "auth_type": "none"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_webhook(self):
        """测试验证配置 - 无效webhook"""
        plugin = DingTalkPlugin()
        config = {
            "webhook": "invalid-url",
            "auth_type": "none"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_config_sign_missing_secret(self):
        """测试验证配置 - 加签验证缺少密钥"""
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "auth_type": "sign"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_config_keyword_missing_keywords(self):
        """测试验证配置 - 关键词验证缺少关键词"""
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "auth_type": "keyword"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        plugin = DingTalkPlugin()
        plugin_dict = plugin.to_dict()
        assert plugin_dict["plugin_name"] == "dingtalk"
        assert plugin_dict["channel_type"] == "dingtalk"
        assert plugin_dict["display_name"] == "钉钉"
        assert plugin_dict["config_schema"] is not None
    
    def test_config_schema_structure(self):
        """测试配置schema结构"""
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "webhook" in schema["properties"]
        assert "auth_type" in schema["properties"]


class TestWeChatPlugin:
    """测试企业微信插件"""
    
    def test_plugin_properties(self):
        """测试插件属性"""
        plugin = WeChatPlugin()
        assert plugin.plugin_name == "wechat"
        assert plugin.plugin_version == "1.0.0"
        assert plugin.channel_type == "wechat"
        assert plugin.display_name == "企业微信"
        assert plugin.description is not None
        assert plugin.config_schema is not None
    
    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        """测试验证配置 - 有效配置"""
        plugin = WeChatPlugin()
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_config_invalid_webhook(self):
        """测试验证配置 - 无效webhook"""
        plugin = WeChatPlugin()
        config = {
            "webhook": "invalid-url"
        }
        is_valid = await plugin.validate_config(config)
        assert is_valid is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        plugin = WeChatPlugin()
        plugin_dict = plugin.to_dict()
        assert plugin_dict["plugin_name"] == "wechat"
        assert plugin_dict["channel_type"] == "wechat"
        assert plugin_dict["display_name"] == "企业微信"
        assert plugin_dict["config_schema"] is not None


class TestNotificationMessage:
    """测试通知消息"""
    
    def test_message_creation(self):
        """测试消息创建"""
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True
        )
        assert message.title == "测试标题"
        assert message.content == "测试内容"
        assert message.markdown is True
        assert message.at_users is None
        assert message.extra is None
    
    def test_message_with_at_users(self):
        """测试带@用户的消息"""
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True,
            at_users=["13800138000"]
        )
        assert message.at_users == ["13800138000"]
    
    def test_message_to_dict(self):
        """测试转换为字典"""
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True,
            extra={"key": "value"}
        )
        message_dict = message.to_dict()
        assert message_dict["title"] == "测试标题"
        assert message_dict["content"] == "测试内容"
        assert message_dict["markdown"] is True
        assert message_dict["at_users"] == []
        assert message_dict["extra"] == {"key": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
