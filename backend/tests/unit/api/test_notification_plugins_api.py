"""
通知插件API完整测试
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestNotificationPluginsAPI:
    """测试通知插件API"""
    
    def test_list_plugins(self, client):
        """测试列出所有插件"""
        response = client.get("/api/v1/notification/plugins")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "total" in data
    
    def test_get_plugin_info(self, client):
        """测试获取插件信息"""
        response = client.get("/api/v1/notification/plugins/dingtalk")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["plugin_name"] == "dingtalk"
    
    def test_get_plugin_info_not_found(self, client):
        """测试获取不存在的插件"""
        response = client.get("/api/v1/notification/plugins/nonexistent")
        
        assert response.status_code == 404
    
    def test_get_plugin_schema(self, client):
        """测试获取插件Schema"""
        response = client.get("/api/v1/notification/plugins/dingtalk/schema")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "config_schema" in data["data"]
    
    def test_validate_plugin_config_valid(self, client):
        """测试验证有效配置"""
        response = client.post(
            "/api/v1/notification/plugins/validate",
            json={
                "channel_type": "dingtalk",
                "config": {
                    "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                    "auth_type": "none"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True
    
    def test_validate_plugin_config_invalid(self, client):
        """测试验证无效配置"""
        response = client.post(
            "/api/v1/notification/plugins/validate",
            json={
                "channel_type": "dingtalk",
                "config": {
                    "webhook": "invalid",
                    "auth_type": "none"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is False
    
    def test_validate_plugin_not_found(self, client):
        """测试验证不存在的插件"""
        response = client.post(
            "/api/v1/notification/plugins/validate",
            json={
                "channel_type": "nonexistent",
                "config": {}
            }
        )
        
        assert response.status_code == 404
    
    def test_send_notification(self, client):
        """测试发送通知"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.to_dict.return_value = {
            "status": "success",
            "message": "发送成功",
            "channel_type": "dingtalk"
        }
        
        with patch('app.api.notification_plugins.notification_plugin_manager.send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = mock_result
            response = client.post(
                "/api/v1/notification/plugins/send",
                json={
                    "channel_type": "dingtalk",
                    "config": {
                        "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                        "auth_type": "none"
                    },
                    "title": "测试通知",
                    "content": "测试内容",
                    "markdown": True,
                    "at_users": []
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
    
    def test_send_notification_plugin_not_found(self, client):
        """测试发送通知 - 插件不存在"""
        response = client.post(
            "/api/v1/notification/plugins/send",
            json={
                "channel_type": "nonexistent",
                "config": {},
                "title": "测试",
                "content": "内容"
            }
        )
        
        assert response.status_code == 404
    
    def test_reload_plugin(self, client):
        """测试重载插件"""
        with patch('app.api.notification_plugins.notification_plugin_manager.reload_plugin') as mock_reload:
            mock_reload.return_value = True
            response = client.post("/api/v1/notification/plugins/reload/dingtalk")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_reload_plugin_not_found(self, client):
        """测试重载不存在的插件"""
        response = client.post("/api/v1/notification/plugins/reload/nonexistent")
        
        assert response.status_code == 404
    
    def test_discover_plugins(self, client):
        """测试发现插件"""
        with patch('app.api.notification_plugins.notification_plugin_manager.discover_plugins') as mock_discover:
            mock_discover.return_value = 3
            response = client.get("/api/v1/notification/plugins/discover")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestNotificationPluginsManager:
    """测试插件管理器"""
    
    def test_init(self):
        """测试初始化"""
        from app.plugins.notification.manager import NotificationPluginManager
        manager = NotificationPluginManager()
        assert manager is not None
    
    def test_register_plugin(self):
        """测试注册插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        manager = NotificationPluginManager()
        result = manager.register_plugin(DingTalkPlugin)
        assert result is True
        assert manager.plugin_exists("dingtalk")
    
    def test_register_duplicate_plugin(self):
        """测试注册重复插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        result = manager.register_plugin(DingTalkPlugin)
        assert result is False
    
    def test_get_plugin(self):
        """测试获取插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        plugin = manager.get_plugin("dingtalk")
        assert plugin is not None
        assert plugin.plugin_name == "dingtalk"
    
    def test_get_nonexistent_plugin(self):
        """测试获取不存在的插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        
        manager = NotificationPluginManager()
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None
    
    def test_list_plugins(self):
        """测试列出插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.wechat import WeChatPlugin
        
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        manager.register_plugin(WeChatPlugin)
        
        plugins = manager.list_plugins()
        assert len(plugins) >= 2
        
        plugin_types = [p["channel_type"] for p in plugins]
        assert "dingtalk" in plugin_types
        assert "wechat" in plugin_types
    
    def test_discover_plugins(self):
        """测试自动发现插件"""
        from app.plugins.notification.manager import NotificationPluginManager
        
        manager = NotificationPluginManager()
        count = manager.discover_plugins("app/plugins/notification")
        assert count >= 2
    
    def test_plugin_exists(self):
        """测试插件存在检查"""
        from app.plugins.notification.manager import NotificationPluginManager
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        manager = NotificationPluginManager()
        manager.register_plugin(DingTalkPlugin)
        
        assert manager.plugin_exists("dingtalk") is True
        assert manager.plugin_exists("nonexistent") is False


class TestNotificationPluginsAsync:
    """测试通知插件异步功能"""
    
    @pytest.mark.asyncio
    async def test_validate_config(self):
        """测试异步验证配置"""
        from app.plugins.notification.manager import notification_plugin_manager
        
        result = await notification_plugin_manager.validate_config(
            "dingtalk",
            {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
                "auth_type": "none"
            }
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_invalid_config(self):
        """测试异步验证无效配置"""
        from app.plugins.notification.manager import notification_plugin_manager
        
        result = await notification_plugin_manager.validate_config(
            "dingtalk",
            {
                "webhook": "invalid",
                "auth_type": "none"
            }
        )
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试异步发送消息"""
        from app.plugins.notification.manager import notification_plugin_manager
        from app.plugins.notification.base import NotificationMessage
        
        message = NotificationMessage(
            title="测试",
            content="测试内容",
            markdown=True
        )
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.to_dict.return_value = {
            "status": "success",
            "message": "发送成功",
            "channel_type": "dingtalk"
        }
        
        with patch.object(
            notification_plugin_manager.get_plugin("dingtalk"),
            'send',
            new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = mock_result
            result = await notification_plugin_manager.send_message(
                "dingtalk",
                {"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"},
                message
            )
            assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
