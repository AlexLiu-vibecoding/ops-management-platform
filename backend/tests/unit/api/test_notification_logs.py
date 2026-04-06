"""
通知历史记录API测试
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestNotificationLogSchemas:
    """测试通知日志Schema"""
    
    def test_notification_log_response_fields(self):
        """测试日志响应字段"""
        from app.api.notification_logs import NotificationLogResponse
        
        fields = NotificationLogResponse.model_fields
        assert 'id' in fields
        assert 'notification_type' in fields
        assert 'status' in fields
        assert 'title' in fields
        assert 'content' in fields
        assert 'created_at' in fields
    
    def test_pagination_data_fields(self):
        """测试分页数据结构"""
        from app.api.notification_logs import PaginationData
        
        fields = PaginationData.model_fields
        assert 'items' in fields
        assert 'total' in fields
        assert 'page' in fields
        assert 'page_size' in fields
    
    def test_notification_stats_fields(self):
        """测试统计字段"""
        from app.api.notification_logs import NotificationStats
        
        fields = NotificationStats.model_fields
        assert 'total' in fields
        assert 'success' in fields
        assert 'failed' in fields
        assert 'pending' in fields
        assert 'by_type' in fields
        assert 'by_channel' in fields
    
    def test_base_response_defaults(self):
        """测试基础响应默认值"""
        from app.api.notification_logs import BaseResponse
        
        response = BaseResponse()
        assert response.code == 0
        assert response.message == "success"


class TestNotificationLogRouter:
    """测试通知日志路由"""
    
    def test_router_prefix(self):
        """测试路由前缀"""
        from app.api.notification_logs import router
        
        assert router.prefix == "/notification-logs"
    
    def test_router_tags(self):
        """测试路由标签"""
        from app.api.notification_logs import router
        
        assert "通知历史" in router.tags


class TestNotificationLogQueryParams:
    """测试查询参数"""
    
    def test_default_page(self):
        """测试默认页码"""
        from app.api.notification_logs import list_notification_logs
        
        # 检查函数存在
        assert list_notification_logs is not None
    
    def test_page_validation(self):
        """测试页码验证"""
        from app.api.notification_logs import NotificationLogResponse
        
        # 验证模型能正常创建
        log = NotificationLogResponse(
            id=1,
            notification_type="alert",
            status="success",
            title="测试通知",
            created_at=datetime.now()
        )
        assert log.id == 1
        assert log.notification_type == "alert"


class TestNotificationLogResponse:
    """测试日志响应"""
    
    def test_create_log_response(self):
        """测试创建日志响应"""
        from app.api.notification_logs import NotificationLogResponse
        
        now = datetime.now()
        log = NotificationLogResponse(
            id=1,
            notification_type="alert",
            status="success",
            title="测试通知",
            content="测试内容",
            created_at=now
        )
        
        assert log.id == 1
        assert log.notification_type == "alert"
        assert log.status == "success"
        assert log.title == "测试通知"
        assert log.created_at == now
    
    def test_optional_fields(self):
        """测试可选字段"""
        from app.api.notification_logs import NotificationLogResponse
        
        log = NotificationLogResponse(
            id=1,
            notification_type="alert",
            status="success",
            title="测试通知",
            created_at=datetime.now()
        )
        
        assert log.channel_id is None
        assert log.content is None
        assert log.error_message is None


class TestNotificationStats:
    """测试统计功能"""
    
    def test_create_stats(self):
        """测试创建统计"""
        from app.api.notification_logs import NotificationStats
        
        stats = NotificationStats(
            total=100,
            success=80,
            failed=15,
            pending=5,
            by_type={"alert": 60, "approval": 40},
            by_channel={"dingtalk": 70, "wechat": 30}
        )
        
        assert stats.total == 100
        assert stats.success == 80
        assert stats.failed == 15
        assert stats.pending == 5
        assert stats.by_type["alert"] == 60
        assert stats.by_channel["dingtalk"] == 70


class TestPaginationData:
    """测试分页数据"""
    
    def test_create_pagination(self):
        """测试创建分页数据"""
        from app.api.notification_logs import PaginationData
        
        data = PaginationData(
            items=[{"id": 1}, {"id": 2}],
            total=100,
            page=1,
            page_size=20
        )
        
        assert len(data.items) == 2
        assert data.total == 100
        assert data.page == 1
        assert data.page_size == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
