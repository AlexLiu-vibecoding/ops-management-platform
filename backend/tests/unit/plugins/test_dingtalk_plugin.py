"""
钉钉通知插件测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import time


class TestDingTalkPluginProperties:
    """测试钉钉插件属性"""
    
    def test_plugin_name(self):
        """测试插件名称"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        assert plugin.plugin_name == "dingtalk"
    
    def test_plugin_version(self):
        """测试插件版本"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        assert plugin.plugin_version == "1.0.0"
    
    def test_channel_type(self):
        """测试通道类型"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        assert plugin.channel_type == "dingtalk"
    
    def test_display_name(self):
        """测试显示名称"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        assert plugin.display_name == "钉钉"
    
    def test_description(self):
        """测试描述"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        assert "钉钉" in plugin.description
        assert "Markdown" in plugin.description


class TestDingTalkConfigSchema:
    """测试配置Schema"""
    
    def test_config_schema_structure(self):
        """测试配置Schema结构"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "webhook" in schema["properties"]
        assert "auth_type" in schema["properties"]
    
    def test_webhook_property(self):
        """测试webhook属性"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        
        webhook = schema["properties"]["webhook"]
        assert webhook["type"] == "string"
        assert webhook["required"] is True
    
    def test_auth_type_property(self):
        """测试auth_type属性"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        
        auth_type = schema["properties"]["auth_type"]
        assert auth_type["enum"] == ["none", "keyword", "sign"]
    
    def test_secret_property(self):
        """测试secret属性"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        
        secret = schema["properties"]["secret"]
        assert secret["type"] == "string"
        assert secret["required"] is False
    
    def test_keywords_property(self):
        """测试keywords属性"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        schema = plugin.config_schema
        
        keywords = schema["properties"]["keywords"]
        assert keywords["type"] == "array"


class TestDingTalkValidateConfig:
    """测试配置验证"""
    
    @pytest.mark.asyncio
    async def test_valid_config_none_auth(self):
        """测试无验证配置"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
        }
        
        result = await plugin.validate_config(config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_valid_config_with_sign(self):
        """测试加签配置"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "sign",
            "secret": "SECxxx"
        }
        
        result = await plugin.validate_config(config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_valid_config_with_keywords(self):
        """测试关键词配置"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "keyword",
            "keywords": ["测试", "通知"]
        }
        
        result = await plugin.validate_config(config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_empty(self):
        """测试空webhook"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "",
            "auth_type": "none"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_webhook_wrong_prefix(self):
        """测试错误前缀"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "http://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_sign_missing_secret(self):
        """测试加签但缺少密钥"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "sign"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_keyword_missing_keywords(self):
        """测试关键词但缺少keywords字段"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "keyword"
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_keyword_empty_list(self):
        """测试关键词空列表"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "keyword",
            "keywords": []
        }
        
        result = await plugin.validate_config(config)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalid_keyword_wrong_type(self):
        """测试关键词类型错误"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "keyword",
            "keywords": "not a list"
        }
        
        result = await plugin.validate_config(config)
        assert result is False


class TestDingTalkSignGeneration:
    """测试签名生成"""
    
    def test_generate_sign(self):
        """测试签名生成"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        secret = "SEC123456"
        
        timestamp, sign = plugin._generate_sign(secret)
        
        assert timestamp is not None
        assert len(timestamp) > 0
        assert sign is not None
        assert len(sign) > 0
    
    def test_generate_sign_deterministic(self):
        """测试相同密钥产生不同时间戳"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        secret = "SEC123456"
        
        timestamp1, sign1 = plugin._generate_sign(secret)
        time.sleep(0.01)  # 等待一小段时间
        timestamp2, sign2 = plugin._generate_sign(secret)
        
        # 时间戳应该不同
        assert timestamp1 != timestamp2


class TestDingTalkToFormat:
    """测试消息格式转换"""
    
    def test_to_markdown_format(self):
        """测试Markdown格式"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=True
        )
        
        result = plugin._to_dingtalk_format(message, {})
        
        assert result["msgtype"] == "markdown"
        assert result["markdown"]["title"] == "测试标题"
        assert result["markdown"]["text"] == "测试内容"
    
    def test_to_text_format(self):
        """测试文本格式"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=False
        )
        
        result = plugin._to_dingtalk_format(message, {})
        
        assert result["msgtype"] == "text"
        assert result["text"]["content"] == "测试内容"
    
    def test_to_text_with_keywords(self):
        """测试带关键词的文本格式"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试标题",
            content="测试内容",
            markdown=False
        )
        config = {
            "auth_type": "keyword",
            "keywords": ["关键词1", "关键词2"]
        }
        
        result = plugin._to_dingtalk_format(message, config)
        
        assert "关键词1" in result["text"]["content"]
        assert "关键词2" in result["text"]["content"]
        assert "测试内容" in result["text"]["content"]


class TestDingTalkSend:
    """测试发送消息"""
    
    @pytest.mark.asyncio
    async def test_send_success(self):
        """测试发送成功"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
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
    async def test_send_with_sign(self):
        """测试带加签发送"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "sign",
            "secret": "SECxxx"
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
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errcode": 400, "errmsg": "error"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_exception(self):
        """测试发送异常"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        from app.plugins.notification.base import NotificationMessage, NotificationStatus
        
        plugin = DingTalkPlugin()
        message = NotificationMessage(
            title="测试",
            content="测试内容"
        )
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("Network error"))
            
            result = await plugin.send(config, message)
            
            assert result.status == NotificationStatus.FAILED
            assert "Network error" in result.message


class TestDingTalkTestConnection:
    """测试连接测试"""
    
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """测试连接成功"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
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
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        config = {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "auth_type": "none"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=Exception("Network error"))
            
            result = await plugin.test_connection(config)
            assert result is False


class TestDingTalkToDict:
    """测试转换为字典"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        from app.plugins.notification.dingtalk import DingTalkPlugin
        
        plugin = DingTalkPlugin()
        result = plugin.to_dict()
        
        assert result["plugin_name"] == "dingtalk"
        assert result["channel_type"] == "dingtalk"
        assert result["display_name"] == "钉钉"
        assert "description" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
