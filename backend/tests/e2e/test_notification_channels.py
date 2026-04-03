#!/usr/bin/env python3
"""
通知通道管理 E2E 测试用例

测试范围：
1. 通道 CRUD 操作
2. 通道绑定管理
3. 静默规则管理
4. 频率限制管理
5. 通道测试功能

运行方式:
    cd /workspace/projects/backend
    python -m pytest tests/e2e/test_notification_channels.py -v
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, UserRole
from app.utils.auth import hash_password, create_access_token


class TestNotificationChannels:
    """通知通道管理 E2E 测试类"""

    @pytest.fixture(scope="function")
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture(scope="function")
    def admin_token(self):
        """创建管理员用户的认证令牌"""
        db = SessionLocal()
        try:
            # 检查是否已存在 admin 用户
            user = db.query(User).filter_by(username="admin").first()
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
                db.add(user)
                db.commit()
                db.refresh(user)

            # 创建访问令牌
            token = create_access_token({
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value
            })
            return token
        finally:
            db.close()

    @pytest.fixture(scope="function")
    def auth_headers(self, admin_token):
        """创建认证请求头"""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="function")
    def test_channel(self, client, auth_headers):
        """创建测试通道，测试结束后自动清理"""
        # 创建测试通道
        channel_data = {
            "name": "E2E测试通道",
            "channel_type": "webhook",
            "config": {
                "url": "https://example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            "is_enabled": True,
            "description": "E2E测试用"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )
        assert response.status_code == 201, f"创建通道失败: {response.text}"
        channel_id = response.json()["id"]

        yield channel_id

        # 清理：删除测试通道
        client.delete(f"/api/v1/notification/channels/{channel_id}", headers=auth_headers)

    def test_list_channels(self, client, auth_headers):
        """测试获取通道列表"""
        response = client.get("/api/v1/notification/channels", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

        # 验证返回的通道数据格式
        if data["items"]:
            channel = data["items"][0]
            assert "id" in channel
            assert "name" in channel
            assert "channel_type" in channel
            assert "config" in channel
            assert "is_enabled" in channel
            assert "silence_rules_count" in channel
            assert "rate_limits_count" in channel

    def test_create_channel(self, client, auth_headers):
        """测试创建通道"""
        channel_data = {
            "name": "测试创建通道",
            "channel_type": "webhook",
            "config": {
                "url": "https://example.com/webhook",
                "method": "POST"
            },
            "is_enabled": True,
            "description": "测试描述"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        result = response.json()
        assert "id" in result
        assert result["message"] == "创建成功"

        # 清理
        client.delete(f"/api/v1/notification/channels/{result['id']}", headers=auth_headers)

    def test_create_channel_duplicate_name(self, client, auth_headers, test_channel):
        """测试创建通道时名称重复"""
        channel_data = {
            "name": "E2E测试通道",  # 与 test_channel 同名
            "channel_type": "webhook",
            "config": {"url": "https://example.com/webhook"},
            "is_enabled": True
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "名称已存在" in response.json()["detail"]

    def test_get_channel_detail(self, client, auth_headers, test_channel):
        """测试获取通道详情"""
        response = client.get(
            f"/api/v1/notification/channels/detail/{test_channel}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_channel
        assert data["name"] == "E2E测试通道"
        assert data["channel_type"] == "webhook"
        assert "config" in data

    def test_update_channel(self, client, auth_headers, test_channel):
        """测试更新通道"""
        update_data = {
            "name": "E2E测试通道-已更新",
            "channel_type": "webhook",
            "config": {
                "url": "https://example.com/webhook-updated",
                "method": "POST"
            },
            "is_enabled": True,
            "description": "已更新的描述"
        }

        response = client.put(
            f"/api/v1/notification/channels/{test_channel}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["message"] == "更新成功"

        # 验证更新
        response = client.get(
            f"/api/v1/notification/channels/detail/{test_channel}",
            headers=auth_headers
        )
        data = response.json()
        assert data["name"] == "E2E测试通道-已更新"
        assert data["description"] == "已更新的描述"

    def test_delete_channel(self, client, auth_headers):
        """测试删除通道"""
        # 先创建一个通道
        channel_data = {
            "name": "待删除通道",
            "channel_type": "webhook",
            "config": {"url": "https://example.com/webhook"},
            "is_enabled": True
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=auth_headers
        )
        channel_id = response.json()["id"]

        # 删除通道
        response = client.delete(
            f"/api/v1/notification/channels/{channel_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["message"] == "删除成功"

        # 验证已删除
        response = client.get(
            f"/api/v1/notification/channels/detail/{channel_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_test_channel(self, client, auth_headers, test_channel):
        """测试通道测试功能"""
        response = client.post(
            f"/api/v1/notification/channels/detail/{test_channel}/test",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "detail" in data

    def test_channel_bindings(self, client, auth_headers, test_channel):
        """测试通道绑定管理"""
        # 1. 获取绑定列表（初始为空）
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/bindings",
            headers=auth_headers
        )
        assert response.status_code == 200
        initial_count = response.json()["total"]

        # 2. 创建绑定
        binding_data = {
            "notification_type": "alert",
            "environment_id": None,
            "rdb_instance_id": None,
            "redis_instance_id": None,
            "scheduled_task_id": None
        }

        response = client.post(
            f"/api/v1/notification/channels/{test_channel}/bindings",
            json=binding_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        binding_id = response.json()["id"]

        # 3. 验证绑定已创建
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/bindings",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == initial_count + 1

        # 4. 删除绑定
        response = client.delete(
            f"/api/v1/notification/channels/{test_channel}/bindings/{binding_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

        # 5. 验证已删除
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/bindings",
            headers=auth_headers
        )
        assert response.json()["total"] == initial_count

    def test_silence_rules(self, client, auth_headers, test_channel):
        """测试通道静默规则管理"""
        # 1. 获取静默规则列表（初始为空）
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/silence-rules",
            headers=auth_headers
        )
        assert response.status_code == 200
        initial_count = response.json()["total"]

        # 2. 创建静默规则
        rule_data = {
            "name": "测试静默规则",
            "silence_type": "once",
            "start_time": "2026-01-01T00:00:00",
            "end_time": "2026-01-02T00:00:00",
            "description": "测试用"
        }

        response = client.post(
            f"/api/v1/notification/channels/{test_channel}/silence-rules",
            json=rule_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        rule_id = response.json()["id"]

        # 3. 验证规则已创建
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/silence-rules",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == initial_count + 1

        # 4. 更新规则
        update_data = {
            "name": "测试静默规则-已更新",
            "silence_type": "daily",
            "start_time": "2026-01-01T00:00:00",
            "end_time": "2026-01-02T00:00:00"
        }

        response = client.put(
            f"/api/v1/notification/channels/{test_channel}/silence-rules/{rule_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200

        # 5. 删除规则
        response = client.delete(
            f"/api/v1/notification/channels/{test_channel}/silence-rules/{rule_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_rate_limits(self, client, auth_headers, test_channel):
        """测试通道频率限制管理"""
        # 1. 获取频率限制列表（初始为空）
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/rate-limits",
            headers=auth_headers
        )
        assert response.status_code == 200
        initial_count = response.json()["total"]

        # 2. 创建频率限制
        limit_data = {
            "name": "测试频率限制",
            "time_window": 60,
            "max_count": 10,
            "description": "测试用"
        }

        response = client.post(
            f"/api/v1/notification/channels/{test_channel}/rate-limits",
            json=limit_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        limit_id = response.json()["id"]

        # 3. 验证已创建
        response = client.get(
            f"/api/v1/notification/channels/{test_channel}/rate-limits",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == initial_count + 1

        # 4. 删除频率限制
        response = client.delete(
            f"/api/v1/notification/channels/{test_channel}/rate-limits/{limit_id}",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        # 未提供认证信息
        response = client.get("/api/v1/notification/channels")
        assert response.status_code == 401

        # 错误的认证令牌
        response = client.get(
            "/api/v1/notification/channels",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])
