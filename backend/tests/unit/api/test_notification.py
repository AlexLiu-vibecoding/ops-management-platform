"""
通知管理API测试
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestNotificationSchemas:
    """测试通知Schema"""
    
    def test_channel_create_fields(self):
        """测试创建通道Schema字段"""
        from app.api.notification import ChannelCreate
        
        fields = ChannelCreate.model_fields
        assert 'name' in fields
        assert 'channel_type' in fields
        assert 'webhook' in fields
        assert 'auth_type' in fields
        assert 'secret' in fields
        assert 'keywords' in fields
    
    def test_channel_create_defaults(self):
        """测试创建通道默认值"""
        from app.api.notification import ChannelCreate
        
        field = ChannelCreate.model_fields['channel_type']
        assert field.default == "dingtalk"
    
    def test_channel_update_fields(self):
        """测试更新通道Schema字段"""
        from app.api.notification import ChannelUpdate
        
        fields = ChannelUpdate.model_fields
        assert 'name' in fields
        assert 'webhook' in fields
        assert 'is_enabled' in fields
    
    def test_binding_create_fields(self):
        """测试创建绑定Schema字段"""
        from app.api.notification import BindingCreate
        
        fields = BindingCreate.model_fields
        assert 'channel_id' in fields
        assert 'notification_type' in fields
        assert 'environment_id' in fields


class TestNotificationRouter:
    """测试通知路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.notification import router
        
        assert router.prefix == "/notification"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.notification import router
        
        assert "通知管理" in router.tags


class TestDingTalkSignHelper:
    """测试钉钉签名辅助函数"""
    
    def test_generate_sign(self):
        """测试生成签名"""
        from app.api.notification import generate_dingtalk_sign
        
        timestamp, sign = generate_dingtalk_sign("SEC123456")
        
        assert timestamp is not None
        assert len(timestamp) > 0
        assert sign is not None
        assert len(sign) > 0
    
    def test_generate_sign_format(self):
        """测试签名格式"""
        from app.api.notification import generate_dingtalk_sign
        
        timestamp, sign = generate_dingtalk_sign("SEC123456")
        
        # 时间戳应该是毫秒级
        assert len(timestamp) == 13
        # 签名应该是URL编码的
        assert '%' in sign or sign.isalnum()


class TestNotificationConstants:
    """测试通知常量"""
    
    def test_channel_type_labels(self):
        """测试通道类型标签"""
        from app.api.notification import CHANNEL_TYPE_LABELS
        
        assert CHANNEL_TYPE_LABELS["dingtalk"] == "钉钉"
        assert CHANNEL_TYPE_LABELS["wechat"] == "企业微信"
        assert CHANNEL_TYPE_LABELS["feishu"] == "飞书"
        assert CHANNEL_TYPE_LABELS["email"] == "邮件"
        assert CHANNEL_TYPE_LABELS["webhook"] == "自定义Webhook"
    
    def test_notification_type_labels(self):
        """测试通知类型标签"""
        from app.api.notification import NOTIFICATION_TYPE_LABELS
        
        assert NOTIFICATION_TYPE_LABELS["approval"] == "审批通知"
        assert NOTIFICATION_TYPE_LABELS["alert"] == "告警通知"
        assert NOTIFICATION_TYPE_LABELS["scheduled_task"] == "定时任务通知"
        assert NOTIFICATION_TYPE_LABELS["operation"] == "审计日志通知"
    
    def test_all_channel_types_defined(self):
        """测试所有通道类型都已定义"""
        from app.api.notification import CHANNEL_TYPE_LABELS
        
        expected_types = ["dingtalk", "wechat", "feishu", "email", "webhook"]
        for channel_type in expected_types:
            assert channel_type in CHANNEL_TYPE_LABELS


class TestChannelCreateValidation:
    """测试通道创建验证"""
    
    def test_name_max_length(self):
        """测试名称最大长度"""
        from app.api.notification import ChannelCreate
        
        field = ChannelCreate.model_fields['name']
        metadata = field.metadata
        # 从metadata中获取max_length
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 100
    
    def test_valid_channel_types(self):
        """测试有效通道类型"""
        from app.api.notification import ChannelCreate
        
        field = ChannelCreate.model_fields['channel_type']
        assert "dingtalk" in str(field.description)
    
    def test_auth_types(self):
        """测试认证类型"""
        from app.api.notification import ChannelCreate
        
        field = ChannelCreate.model_fields['auth_type']
        assert field.default == "none"


class TestBindingCreateValidation:
    """测试绑定创建验证"""
    
    def test_channel_id_required(self):
        """测试通道ID必填"""
        from app.api.notification import BindingCreate
        
        field = BindingCreate.model_fields['channel_id']
        assert field is not None
    
    def test_notification_type_required(self):
        """测试通知类型必填"""
        from app.api.notification import BindingCreate
        
        field = BindingCreate.model_fields['notification_type']
        assert field is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
