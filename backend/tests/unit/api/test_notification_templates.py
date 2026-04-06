"""
通知模板API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestNotificationTemplateSchemas:
    """测试通知模板Schema"""
    
    def test_template_create_fields(self):
        """测试创建模板Schema字段"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        fields = NotificationTemplateCreate.model_fields
        assert 'name' in fields
        assert 'notification_type' in fields
        assert 'title_template' in fields
        assert 'content_template' in fields
        assert 'is_enabled' in fields
        assert 'is_default' in fields
    
    def test_template_create_defaults(self):
        """测试创建模板默认值"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        is_enabled = NotificationTemplateCreate.model_fields['is_enabled']
        assert is_enabled.default is True
        
        is_default = NotificationTemplateCreate.model_fields['is_default']
        assert is_default.default is False
    
    def test_template_update_fields(self):
        """测试更新模板Schema字段"""
        from app.api.notification_templates import NotificationTemplateUpdate
        
        fields = NotificationTemplateUpdate.model_fields
        assert 'name' in fields
        assert 'notification_type' in fields
        assert 'title_template' in fields
        assert 'content_template' in fields
    
    def test_template_response_fields(self):
        """测试模板响应Schema字段"""
        from app.api.notification_templates import NotificationTemplateResponse
        
        fields = NotificationTemplateResponse.model_fields
        assert 'id' in fields
        assert 'name' in fields
        assert 'notification_type' in fields
        assert 'title_template' in fields
        assert 'content_template' in fields
        assert 'created_at' in fields


class TestNotificationTemplateRouter:
    """测试通知模板路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.notification_templates import router
        
        assert router.prefix == "/notification-templates"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.notification_templates import router
        
        assert "通知模板" in router.tags


class TestNotificationTemplateValidation:
    """测试模板验证"""
    
    def test_name_min_length(self):
        """测试名称最小长度"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        field = NotificationTemplateCreate.model_fields['name']
        metadata = field.metadata
        min_len = next((m.min_length for m in metadata if hasattr(m, 'min_length')), None)
        assert min_len == 1
    
    def test_name_max_length(self):
        """测试名称最大长度"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        field = NotificationTemplateCreate.model_fields['name']
        metadata = field.metadata
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 100
    
    def test_description_max_length(self):
        """测试描述最大长度"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        field = NotificationTemplateCreate.model_fields['description']
        metadata = field.metadata
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 200
    
    def test_title_template_max_length(self):
        """测试标题模板最大长度"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        field = NotificationTemplateCreate.model_fields['title_template']
        metadata = field.metadata
        max_len = next((m.max_length for m in metadata if hasattr(m, 'max_length')), None)
        assert max_len == 200


class TestNotificationTemplateCreate:
    """测试创建模板"""
    
    def test_create_approval_template(self):
        """测试创建审批模板"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        template = NotificationTemplateCreate(
            name="审批通过通知",
            notification_type="approval",
            title_template="审批结果通知",
            content_template="**{{applicant}}** 的申请已通过"
        )
        
        assert template.name == "审批通过通知"
        assert template.notification_type == "approval"
        assert template.is_enabled is True
        assert template.is_default is False
    
    def test_create_alert_template(self):
        """测试创建告警模板"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        template = NotificationTemplateCreate(
            name="CPU告警通知",
            notification_type="alert",
            sub_type="cpu_high",
            title_template="实例 {{instance_name}} CPU告警",
            content_template="CPU使用率: {{cpu_usage}}%"
        )
        
        assert template.notification_type == "alert"
        assert template.sub_type == "cpu_high"
    
    def test_create_with_variables(self):
        """测试创建带变量的模板"""
        from app.api.notification_templates import NotificationTemplateCreate
        
        template = NotificationTemplateCreate(
            name="变量模板",
            notification_type="alert",
            title_template="{{title}}",
            content_template="{{content}}",
            variables=[
                {"name": "title", "type": "string", "description": "标题"},
                {"name": "content", "type": "string", "description": "内容"}
            ]
        )
        
        assert len(template.variables) == 2
        assert template.variables[0]["name"] == "title"


class TestNotificationTemplateResponse:
    """测试模板响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.notification_templates import NotificationTemplateResponse
        from datetime import datetime
        
        now = datetime.now()
        response = NotificationTemplateResponse(
            id=1,
            name="测试模板",
            notification_type="alert",
            title_template="测试",
            content_template="测试内容",
            description=None,
            sub_type=None,
            variables=None,
            is_enabled=True,
            is_default=False,
            created_at=now,
            updated_at=now
        )
        
        assert response.id == 1
        assert response.name == "测试模板"
        assert response.is_enabled is True


class TestPaginationData:
    """测试分页数据"""
    
    def test_pagination_fields(self):
        """测试分页字段"""
        from app.api.notification_templates import PaginationData
        
        fields = PaginationData.model_fields
        assert 'items' in fields
        assert 'total' in fields
        assert 'page' in fields
        assert 'page_size' in fields
    
    def test_create_pagination(self):
        """测试创建分页"""
        from app.api.notification_templates import PaginationData
        
        data = PaginationData(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=1,
            page_size=20
        )
        
        assert len(data.items) == 2
        assert data.total == 100


class TestBaseResponse:
    """测试基础响应"""
    
    def test_default_values(self):
        """测试默认值"""
        from app.api.notification_templates import BaseResponse
        
        response = BaseResponse()
        assert response.code == 0
        assert response.message == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
