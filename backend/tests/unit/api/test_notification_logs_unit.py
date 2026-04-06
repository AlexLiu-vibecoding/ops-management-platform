"""
通知历史记录API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestNotificationLogSchemas:
    """测试通知日志Schema"""
    
    def test_notification_log_response_fields(self):
        """测试通知日志响应Schema字段"""
        from app.api.notification_logs import NotificationLogResponse
        
        fields = NotificationLogResponse.model_fields
        assert 'id' in fields
        assert 'notification_type' in fields
        assert 'sub_type' in fields
        assert 'channel_id' in fields
        assert 'channel_name' in fields
        assert 'title' in fields
        assert 'content' in fields
        assert 'status' in fields
        assert 'error_message' in fields
        assert 'sent_at' in fields
        assert 'created_at' in fields
    
    def test_notification_log_response_defaults(self):
        """测试通知日志响应默认值"""
        from app.api.notification_logs import NotificationLogResponse
        
        # sub_type 默认值
        assert NotificationLogResponse.model_fields['sub_type'].default is None
        # content 默认值
        assert NotificationLogResponse.model_fields['content'].default is None


class TestNotificationLogRouter:
    """测试路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.notification_logs import router
        
        assert router.prefix == "/notification-logs"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.notification_logs import router
        
        assert "通知历史" in router.tags


class TestNotificationLogResponse:
    """测试通知日志响应"""
    
    def test_create_response(self):
        """测试创建响应"""
        from app.api.notification_logs import NotificationLogResponse
        
        now = datetime.now()
        response = NotificationLogResponse(
            id=1,
            notification_type="approval",
            sub_type="success",
            channel_id=1,
            channel_name="钉钉",
            title="审批通知",
            content="变更已审批通过",
            status="success",
            created_at=now
        )
        
        assert response.id == 1
        assert response.notification_type == "approval"
        assert response.status == "success"
    
    def test_response_with_error(self):
        """测试带错误的响应"""
        from app.api.notification_logs import NotificationLogResponse
        
        now = datetime.now()
        response = NotificationLogResponse(
            id=2,
            notification_type="alert",
            title="告警通知",
            status="failed",
            error_message="Webhook调用失败",
            response_code=500,
            created_at=now
        )
        
        assert response.error_message == "Webhook调用失败"
        assert response.response_code == 500


class TestPaginationData:
    """测试分页数据"""
    
    def test_pagination_fields(self):
        """测试分页字段"""
        from app.api.notification_logs import PaginationData
        
        fields = PaginationData.model_fields
        assert 'items' in fields
        assert 'total' in fields
        assert 'page' in fields
        assert 'page_size' in fields
    
    def test_create_pagination(self):
        """测试创建分页数据"""
        from app.api.notification_logs import PaginationData
        
        pagination = PaginationData(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=1,
            page_size=20
        )
        
        assert len(pagination.items) == 2
        assert pagination.total == 100
        assert pagination.page == 1
        assert pagination.page_size == 20


class TestNotificationLogListResponse:
    """测试通知日志列表响应"""
    
    def test_response_fields(self):
        """测试响应字段"""
        from app.api.notification_logs import NotificationLogListResponse
        
        fields = NotificationLogListResponse.model_fields
        assert 'code' in fields
        assert 'message' in fields
        assert 'data' in fields


class TestNotificationStats:
    """测试通知统计"""
    
    def test_stats_fields(self):
        """测试统计字段"""
        from app.api.notification_logs import NotificationStats
        
        fields = NotificationStats.model_fields
        assert 'total' in fields
        assert 'success' in fields
        assert 'failed' in fields
        assert 'pending' in fields
        assert 'by_type' in fields
        assert 'by_channel' in fields
    
    def test_create_stats(self):
        """测试创建统计"""
        from app.api.notification_logs import NotificationStats
        
        stats = NotificationStats(
            total=100,
            success=80,
            failed=15,
            pending=5,
            by_type={"approval": 50, "alert": 50},
            by_channel={"dingtalk": 60, "email": 40}
        )
        
        assert stats.total == 100
        assert stats.success == 80
        assert stats.by_type["approval"] == 50


class TestBaseResponse:
    """测试基础响应"""
    
    def test_base_response_defaults(self):
        """测试基础响应默认值"""
        from app.api.notification_logs import BaseResponse
        
        response = BaseResponse()
        assert response.code == 0
        assert response.message == "success"
    
    def test_base_response_custom(self):
        """测试基础响应自定义"""
        from app.api.notification_logs import BaseResponse
        
        response = BaseResponse(code=400, message="error")
        assert response.code == 400
        assert response.message == "error"


class TestNotificationLogDetailResponse:
    """测试通知日志详情响应"""
    
    def test_response_fields(self):
        """测试响应字段"""
        from app.api.notification_logs import NotificationLogDetailResponse
        
        fields = NotificationLogDetailResponse.model_fields
        assert 'code' in fields
        assert 'message' in fields
        assert 'data' in fields
    
    def test_response_with_data(self):
        """测试带数据的响应"""
        from app.api.notification_logs import NotificationLogDetailResponse, NotificationLogResponse
        
        now = datetime.now()
        data = NotificationLogResponse(
            id=1,
            notification_type="approval",
            title="测试",
            status="success",
            created_at=now
        )
        
        response = NotificationLogDetailResponse(data=data)
        assert response.data is not None
        assert response.data.id == 1


class TestNotificationLogModels:
    """测试通知日志模型"""
    
    def test_notification_log_model(self):
        """测试NotificationLog模型"""
        from app.models import NotificationLog
        
        assert NotificationLog is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
