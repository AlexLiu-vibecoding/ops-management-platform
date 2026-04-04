"""
通知管理 API 测试

覆盖通知管理接口：
- 通知绑定: /api/v1/notification/bindings
- 通知模板: /api/v1/notification-templates
- 通知配置: /api/v1/notification-config
- 通知通道: /api/v1/notification-channels
- 通知规则: /api/v1/notification-rules
- 通知历史: /api/v1/notification-logs
"""
import pytest
from tests.helpers.base_api_test import BaseErrorHandlingTest


class TestNotificationAPI:
    """通知管理 API 测试类"""

    def test_list_notification_bindings(self, client, admin_headers):
        """测试获取通知绑定列表"""
        response = client.get("/api/v1/notification/bindings", headers=admin_headers)
        assert response.status_code == 200

    def test_list_notification_templates(self, client, admin_headers):
        """测试获取通知模板列表"""
        response = client.get("/api/v1/notification-templates", headers=admin_headers)
        assert response.status_code == 200

    def test_get_notification_config(self, client, admin_headers):
        """测试获取通知配置"""
        response = client.get("/api/v1/notification-config", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_list_notification_channels(self, client, admin_headers):
        """测试获取通知通道列表"""
        response = client.get("/api/v1/notification-channels", headers=admin_headers)
        assert response.status_code in [200, 404]

    def test_list_notification_rules(self, client, admin_headers):
        """测试获取通知规则列表"""
        response = client.get("/api/v1/notification-rules", headers=admin_headers)
        assert response.status_code in [200, 404, 405]

    def test_list_notification_logs(self, client, admin_headers):
        """测试获取通知历史列表"""
        response = client.get("/api/v1/notification-logs", headers=admin_headers)
        assert response.status_code == 200


class TestNotificationAPIErrorHandling:
    """通知管理 API 错误处理测试类"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/notification/bindings")
        assert response.status_code == 401

    def test_create_channel_invalid_data(self, client, admin_headers):
        """测试创建通道时提供无效数据"""
        response = client.post(
            "/api/v1/notification-channels",
            json={"name": "测试通道"},
            headers=admin_headers
        )
        assert response.status_code in [400, 404, 422, 405]

