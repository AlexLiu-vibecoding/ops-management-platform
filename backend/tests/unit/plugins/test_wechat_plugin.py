"""
企业微信通知插件测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import time


class TestWeChatPluginProperties:
    """测试企业微信插件属性"""
    
    def test_plugin_name(self):
        """测试插件名称"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        assert plugin.plugin_name == "wechat"
    
    def test_plugin_version(self):
        """测试插件版本"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        assert plugin.plugin_version == "1.0.0"
    
    def test_channel_type(self):
        """测试通道类型"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        assert plugin.channel_type == "wechat"
    
    def test_display_name(self):
        """测试显示名称"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        assert plugin.display_name == "企业微信"
    
    def test_description(self):
        """测试描述"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        assert "企业微信" in plugin.description


class TestWeChatConfigSchema:
    """测试配置Schema"""
    
    def test_config_schema_structure(self):
        """测试配置Schema结构"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        schema = plugin.config_schema
        
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "webhook" in schema["properties"]
    
    def test_webhook_property(self):
        """测试webhook属性"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        schema = plugin.config_schema
        
        webhook = schema["properties"]["webhook"]
        assert webhook["type"] == "string"
        assert webhook["required"] is True
    
    def test_required_fields(self):
        """测试必填字段"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        schema = plugin.config_schema
        
        assert "webhook" in schema["required"]


class TestWeChatValidateConfig:
    """测试配置验证"""
    
    @pytest.mark.asyncio
    async def test_valid_config(self):
        """测试有效配置"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        result = await plugin.validate_config(config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_empty(self):
        """测试空webhook"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": ""
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_wrong_domain(self):
        """测试错误域名"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_http(self):
        """测试HTTP协议"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": "http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_missing_webhook(self):
        """测试缺少webhook"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {}
        
        result = await plugin.validate_config(config)
        assert result is False


class TestWeChatToFormat:
    """测试消息格式转换"""
    
    def test_to_markdown_format(self):
        """测试Markdown格式"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True
        )
        
        result = plugin._to_wechat_format(message)
        
        assert result["msgtype"] == "markdown"
        assert "测试标题" in result["markdown"]["content"]
        assert "测试内容" in result["markdown"]["content"]
    
    def test_to_text_format(self):
        """测试文本格式"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=False
        )
        
        result = plugin._to_wechat_format(message)
        
        assert result["msgtype"] == "text"
        assert "测试标题" in result["text"]["content"]
        assert "测试内容" in result["text"]["content"]
    
    def test_markdown_with_newlines(self):
        """测试Markdown格式包含换行"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="标题",
            content="内容",
            markdown=True
        )
        
        result = plugin._to_wechat_format(message)
        content = result["markdown"]["content"]
        
        assert "\n\n" in content


class TestWeChatSend:
    """测试发送消息"""
    
    @pytest.mark.asyncio
    async def test_send_success(self):
        """测试发送成功"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.SUCCESS
            assert result.success is True
            assert result.latency_ms >= 0
    
    @pytest.mark.asyncio
    async def test_send_markdown(self):
        """测试发送Markdown"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试",
            content="**粗体** 内容",
            markdown=True
        )
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_send_api_error(self):
        """测试API错误"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 400, "errmsg": "error"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_http_error(self):
        """测试HTTP错误"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errcode": 500, "errmsg": "internal error"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_exception(self):
        """测试发送异常"""
        from app.plugins.notification.wechat import WeChatPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = WeChatPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("Network error"))
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.FAILED
            assert "Network error" in result.message


class TestWeChatTestConnection:
    """测试连接测试"""
    
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """测试连接成功"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.test_connection(config)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """测试连接失败"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        config = {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("Network error"))
            
            result = await plugin.test_connection(config)
            assert result is False


class TestWeChatToDict:
    """测试转换为字典"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        from app.plugins.notification.wechat import WeChatPlugin
        
        plugin = WeChatPlugin()
        result = plugin.to_dict()
        
        assert result["plugin_name"] == "wechat"
        assert result["channel_type"] == "wechat"
        assert result["display_name"] == "企业微信"
        assert "description" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
