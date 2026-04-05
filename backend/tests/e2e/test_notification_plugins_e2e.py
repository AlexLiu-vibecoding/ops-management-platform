#!/usr/bin/env python3
"""
通知插件系统 E2E 测试

测试场景：
1. 用户登录获取token
2. 获取可用插件列表
3. 使用插件验证配置
4. 创建通知通道（使用不同插件）
5. 设置默认通道
6. 发送测试消息
7. 查看通知日志
8. 删除通道

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_notification_plugins_e2e.py -v -s
"""

import pytest
import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, UserRole, NotificationChannel
from app.utils.auth import hash_password, create_access_token


class TestNotificationPluginsE2E:
    """通知插件系统端到端测试"""

    @pytest.fixture(scope="function")
    def client(self, db_session):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    @pytest.fixture(scope="function")
    def admin_token(self, db_session):
        """创建管理员用户的认证令牌"""
        from app.models import User, UserRole
        from app.utils.auth import hash_password, create_access_token

        # 检查是否已存在 admin 用户
        user = db_session.query(User).filter_by(username="admin").first()
        if not user:
            # 创建 admin 用户
            user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@test.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

        # 创建访问令牌
        token = create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value
        })
        return token

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        """创建认证请求头"""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="function")
    def cleanup_channels(self, db_session):
        """清理测试创建的通道"""
        from app.models.notification_new import NotificationChannel

        # 删除所有E2E测试创建的通道
        test_channels = db_session.query(NotificationChannel).filter(
            NotificationChannel.name.like("E2E-Plugin-%")
        ).all()

        channel_ids = [c.id for c in test_channels]

        for channel in test_channels:
            db_session.delete(channel)

        db_session.commit()
        yield channel_ids

    def test_01_user_login(self, client, auth_headers):
        """E2E-01: 验证认证token有效"""
        # 使用登录接口验证token
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_02_get_plugins_list(self, client, auth_headers):
        """E2E-02: 获取可用插件列表"""
        response = client.get(
            "/api/v1/notification/plugins",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) > 0

        # 验证插件数据格式
        for plugin in data["data"]:
            assert "plugin_name" in plugin
            assert "version" in plugin
            assert "channel_type" in plugin
            assert "display_name" in plugin
            assert "config_schema" in plugin

        # 验证必需的插件存在
        plugin_types = [p["channel_type"] for p in data["data"]]
        assert "dingtalk" in plugin_types
        assert "wechat" in plugin_types

    def test_03_validate_dingtalk_config(self, client, auth_headers):
        """E2E-03: 验证钉钉插件配置"""
        # 有效配置
        valid_config = {
            "channel_type": "dingtalk",
            "config": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test123",
                "auth_type": "keyword",
                "keywords": ["test"]
            }
        }

        response = client.post(
            "/api/v1/notification/plugins/validate",
            json=valid_config,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["valid"] is True

        # 无效配置（缺少webhook）
        invalid_config = {
            "channel_type": "dingtalk",
            "config": {
                "auth_type": "keyword",
                "keywords": ["test"]
            }
        }

        response = client.post(
            "/api/v1/notification/plugins/validate",
            json=invalid_config,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # 配置无效时，valid应该为false
        assert data["data"]["valid"] is False

    def test_04_validate_wechat_config(self, client, auth_headers):
        """E2E-04: 验证企业微信插件配置"""
        valid_config = {
            "channel_type": "wechat",
            "config": {
                "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test123"
            }
        }

        response = client.post(
            "/api/v1/notification/plugins/validate",
            json=valid_config,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_05_create_dingtalk_channel(self, client, auth_headers, cleanup_channels):
        """E2E-05: 创建钉钉通知通道"""
        channel_data = {
            "name": f"E2E-Plugin-DingTalk-{datetime.now().strftime('%H%M%S')}",
            "channel_type": "dingtalk",
            "config": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test123",
                "auth_type": "none"
            },
            "is_enabled": True,
            "description": "E2E测试创建的钉钉通道"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["message"] == "创建成功"

        # 验证通道已创建
        channel_id = data["id"]
        response = client.get(
            f"/api/v1/notification/channels/detail/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        channel = response.json()
        assert channel["name"] == channel_data["name"]
        assert channel["channel_type"] == "dingtalk"

        # 返回channel_id供后续测试使用
        return channel_id

    def test_06_create_wechat_channel(self, client, auth_headers, cleanup_channels):
        """E2E-06: 创建企业微信通知通道"""
        channel_data = {
            "name": f"E2E-Plugin-WeChat-{datetime.now().strftime('%H%M%S')}",
            "channel_type": "wechat",
            "config": {
                "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test123"
            },
            "is_enabled": True,
            "description": "E2E测试创建的企业微信通道"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

        # 验证通道已创建
        channel_id = data["id"]
        response = client.get(
            f"/api/v1/notification/channels/detail/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        channel = response.json()
        assert channel["channel_type"] == "wechat"

        return channel_id

    def test_07_set_default_channel(self, client, auth_headers, cleanup_channels):
        """E2E-07: 设置默认通知通道"""
        # 先创建一个测试通道
        channel_data = {
            "name": f"E2E-Plugin-Default-{datetime.now().strftime('%H%M%S')}",
            "channel_type": "dingtalk",
            "config": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=default"
            },
            "is_enabled": True
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )
        channel_id = response.json()["id"]

        # 设置为默认通道
        response = client.post(
            f"/api/v1/notification/channels/default/{channel_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "默认通知通道" in data["message"]

        # 验证默认通道
        response = client.get(
            "/api/v1/notification/channels/default",
            headers=auth_headers
        )
        assert response.status_code == 200
        default_channel = response.json()["data"]
        assert default_channel["id"] == channel_id

        return channel_id

    def test_08_send_message_via_plugin(self, client, auth_headers, cleanup_channels):
        """E2E-08: 通过插件发送消息"""
        # 创建通道
        channel_data = {
            "name": f"E2E-Plugin-Message-{datetime.now().strftime('%H%M%S')}",
            "channel_type": "dingtalk",
            "config": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test123",
                "auth_type": "none"
            },
            "is_enabled": True
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )
        channel_id = response.json()["id"]

        # 发送消息（可能成功或失败，取决于webhook是否有效）
        response = client.post(
            f"/api/v1/notification/channels/detail/{channel_id}/test",
            headers=auth_headers
        )

        # 只要API正常响应即可，不要求消息发送成功
        assert response.status_code in [200, 500]
        data = response.json()
        # 检查响应包含必要的字段
        assert "message" in data or "detail" in data

        return channel_id

    def test_09_check_notification_logs(self, client, auth_headers):
        """E2E-09: 查看通知日志"""
        response = client.get(
            "/api/v1/notification-logs",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # 通知日志API的响应格式可能是 {code: 0, data: {items: []}}
        assert "data" in data
        if "items" in data:
            # 直接格式
            assert "total" in data
        elif "items" in data.get("data", {}):
            # 嵌套格式
            assert "total" in data["data"]

    def test_10_list_all_channels(self, client, auth_headers):
        """E2E-10: 列出所有通知通道"""
        response = client.get(
            "/api/v1/notification/channels",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

        # 验证每个通道都有必需的字段
        for channel in data["items"]:
            assert "id" in channel
            assert "name" in channel
            assert "channel_type" in channel
            assert "is_enabled" in channel

    def test_11_complete_workflow(self, client, auth_headers, cleanup_channels):
        """E2E-11: 完整工作流测试"""
        # 1. 获取插件列表
        response = client.get(
            "/api/v1/notification/plugins",
            headers=auth_headers
        )
        assert response.status_code == 200
        plugins = response.json()["data"]
        plugin_types = [p["channel_type"] for p in plugins]

        # 2. 创建钉钉通道
        channel_data = {
            "name": f"E2E-Plugin-Workflow-{datetime.now().strftime('%H%M%S')}",
            "channel_type": "dingtalk",
            "config": {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=workflow",
                "auth_type": "none"
            },
            "is_enabled": True,
            "description": "完整工作流测试通道"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )
        channel_id = response.json()["id"]

        # 3. 验证插件支持该通道类型
        assert "dingtalk" in plugin_types

        # 4. 设置为默认通道
        response = client.post(
            f"/api/v1/notification/channels/default/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 5. 发送测试消息（可能成功或失败，取决于webhook是否有效）
        response = client.post(
            f"/api/v1/notification/channels/detail/{channel_id}/test",
            headers=auth_headers
        )
        # 只要API正常响应即可，不要求消息发送成功
        assert response.status_code in [200, 500]

        # 6. 查看通知日志
        response = client.get(
            "/api/v1/notification-logs",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 7. 删除通道
        response = client.delete(
            f"/api/v1/notification/channels/detail/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 8. 验证已删除
        response = client.get(
            f"/api/v1/notification/channels/detail/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_12_plugin_config_schema_validation(self, client, auth_headers):
        """E2E-12: 验证插件配置schema"""
        response = client.get(
            "/api/v1/notification/plugins",
            headers=auth_headers
        )

        assert response.status_code == 200
        plugins = response.json()["data"]

        # 验证钉钉插件的配置schema
        dingtalk_plugin = next(p for p in plugins if p["channel_type"] == "dingtalk")
        schema = dingtalk_plugin["config_schema"]

        assert "type" in schema
        assert "properties" in schema
        assert "required" in schema

        # 验证必需字段
        required = schema["required"]
        assert "webhook" in required
        assert "auth_type" in required

        # 验证属性定义
        properties = schema["properties"]
        assert "webhook" in properties
        assert "auth_type" in properties

        # 验证auth_type的枚举值
        auth_type_prop = properties["auth_type"]
        assert "enum" in auth_type_prop
        assert set(auth_type_prop["enum"]) == {"none", "keyword", "sign"}

    def test_13_error_handling(self, client, auth_headers):
        """E2E-13: 错误处理测试"""
        # 测试不存在的插件
        response = client.get(
            "/api/v1/notification/plugins/nonexistent",
            headers=auth_headers
        )
        assert response.status_code == 404

        # 测试无效的配置
        response = client.post(
            "/api/v1/notification/channels",
            json={
                "name": "Test",
                "channel_type": "invalid_type",
                "config": {}
            },
            headers=auth_headers
        )
        assert response.status_code == 400

        # 测试访问不存在的通道
        response = client.get(
            "/api/v1/notification/channels/detail/99999",
            headers=auth_headers
        )
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
