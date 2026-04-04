#!/usr/bin/env python3
"""
通知通道 API 单元测试

测试范围：
1. 通道 CRUD 操作
2. 通道测试
3. 通道启用/禁用
4. 静默规则管理
5. 频率限制管理

改进：
1. 完整的通道管理流程测试
2. 权限验证测试
3. 边界条件测试
4. 错误处理测试

运行方式:
    cd /workspace/projects/backend

    # 运行所有通知通道 API 测试
    python -m pytest tests/unit/api/test_notification_channels.py -v

    # 运行特定测试
    python -m pytest tests/unit/api/test_notification_channels.py::TestNotificationChannelsAPI -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole
from app.models.notification_new import NotificationChannel
from app.utils.auth import hash_password, create_access_token


@pytest.fixture(scope="function")
def admin_user(db_session):
    """创建管理员用户"""
    user = db_session.query(User).filter_by(username="admin").first()
    if not user:
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
    yield user


@pytest.fixture(scope="function")
def operator_user(db_session):
    """创建操作员用户"""
    username = f"operator_{os.urandom(4).hex()}"
    user = User(
        username=username,
        password_hash=hash_password("operator123"),
        real_name="操作员",
        email=f"{username}@test.com",
        role=UserRole.OPERATOR,
        status=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    # 清理
    db_session.delete(user)
    db_session.commit()


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """管理员 Token"""
    return create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role.value
    })


@pytest.fixture(scope="function")
def operator_token(operator_user):
    """操作员 Token"""
    return create_access_token({
        "sub": str(operator_user.id),
        "username": operator_user.username,
        "role": operator_user.role.value
    })


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="function")
def operator_headers(operator_token):
    """操作员认证头"""
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture(scope="function")
def test_channel(db_session):
    """创建测试通道"""
    channel = NotificationChannel(
        name="测试通道",
        channel_type="dingtalk",
        config={"webhook": "https://oapi.dingtalk.com/robot/send?access_token=test", "auth_type": "none"},
        is_enabled=True,
        description="测试用通道"
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    yield channel
    # 清理
    db_session.delete(channel)
    db_session.commit()


@pytest.mark.unit
class TestNotificationChannelsAPI:
    """通知通道 API 测试"""

    def test_list_channels_unauthorized(self, client):
        """测试未授权获取通道列表"""
        response = client.get("/api/v1/notification/channels")
        assert response.status_code == 401

    def test_list_channels_success(self, client, admin_headers, test_channel):
        """测试成功获取通道列表"""
        response = client.get("/api/v1/notification/channels", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_channels_filter_by_type(self, client, admin_headers, test_channel):
        """测试按类型筛选通道"""
        response = client.get(
            "/api/v1/notification/channels?channel_type=dingtalk",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_create_channel_unauthorized(self, client):
        """测试未授权创建通道"""
        response = client.post(
            "/api/v1/notification/channels",
            json={"name": "测试", "channel_type": "dingtalk"}
        )
        assert response.status_code == 401

    def test_create_channel_forbidden(self, client, operator_headers):
        """测试操作员创建通道（禁止）"""
        response = client.post(
            "/api/v1/notification/channels",
            json={"name": "测试", "channel_type": "dingtalk"},
            headers=operator_headers
        )
        assert response.status_code == 403

    def test_create_channel_dingtalk_no_auth(self, client, admin_headers):
        """测试创建钉钉通道（无认证）"""
        channel_data = {
            "name": "测试钉钉通道",
            "channel_type": "dingtalk",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test123",
            "auth_type": "none",
            "is_enabled": True,
            "description": "测试描述"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "success" in data

        # 清理
        if "id" in data:
            channel_id = data["id"]
            client.delete(f"/api/v1/notification/channels/{channel_id}", headers=admin_headers)

    def test_create_channel_dingtalk_with_keyword(self, client, admin_headers):
        """测试创建钉钉通道（关键词认证）"""
        channel_data = {
            "name": "测试关键词通道",
            "channel_type": "dingtalk",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "auth_type": "keyword",
            "keywords": ["告警", "通知"],
            "is_enabled": True
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

        # 清理
        data = response.json()
        if "id" in data:
            channel_id = data["id"]
            client.delete(f"/api/v1/notification/channels/{channel_id}", headers=admin_headers)

    def test_create_channel_invalid_type(self, client, admin_headers):
        """测试创建无效类型的通道"""
        channel_data = {
            "name": "无效通道",
            "channel_type": "invalid_type",
            "webhook": "https://example.com/webhook"
        }

        response = client.post(
            "/api/v1/notification/channels",
            json=channel_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_get_channel_success(self, client, admin_headers, test_channel):
        """测试成功获取通道详情"""
        response = client.get(
            f"/api/v1/notification/channels/{test_channel.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_channel.id
        assert data["name"] == test_channel.name

    def test_get_channel_not_found(self, client, admin_headers):
        """测试获取不存在的通道"""
        response = client.get("/api/v1/notification/channels/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_channel_success(self, client, admin_headers, test_channel):
        """测试成功更新通道"""
        update_data = {
            "name": "更新后名称",
            "description": "更新后描述",
            "is_enabled": False
        }

        response = client.put(
            f"/api/v1/notification/channels/{test_channel.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_update_channel_not_found(self, client, admin_headers):
        """测试更新不存在的通道"""
        update_data = {"name": "更新"}

        response = client.put(
            "/api/v1/notification/channels/99999",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_channel_success(self, client, admin_headers, db_session):
        """测试成功删除通道"""
        # 创建测试通道
        channel = NotificationChannel(
            name="待删除通道",
            channel_type="dingtalk",
            webhook="https://test.com/webhook",
            auth_type="none"
        )
        db_session.add(channel)
        db_session.commit()
        db_session.refresh(channel)

        # 删除通道
        response = client.delete(
            f"/api/v1/notification/channels/{channel.id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # 验证删除
        deleted = db_session.query(NotificationChannel).filter_by(id=channel.id).first()
        assert deleted is None

    def test_delete_channel_not_found(self, client, admin_headers):
        """测试删除不存在的通道"""
        response = client.delete("/api/v1/notification/channels/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_test_channel_unauthorized(self, client):
        """测试未授权测试通道"""
        response = client.post("/api/v1/notification/channels/1/test")
        assert response.status_code == 401

    def test_test_channel_not_found(self, client, admin_headers):
        """测试不存在的通道"""
        response = client.post(
            "/api/v1/notification/channels/99999/test",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_enable_channel_success(self, client, admin_headers, test_channel):
        """测试成功启用通道"""
        # 先禁用通道
        test_channel.is_enabled = False
        db_session.commit()

        # 启用通道
        response = client.post(
            f"/api/v1/notification/channels/{test_channel.id}/enable",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_disable_channel_success(self, client, admin_headers, test_channel):
        """测试成功禁用通道"""
        # 先启用通道
        test_channel.is_enabled = True
        db_session.commit()

        # 禁用通道
        response = client.post(
            f"/api/v1/notification/channels/{test_channel.id}/disable",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_batch_delete_channels(self, client, admin_headers, db_session):
        """测试批量删除通道"""
        # 创建多个测试通道
        channel_ids = []
        for i in range(3):
            channel = NotificationChannel(
                name=f"批量删除{i}",
                channel_type="dingtalk",
                webhook=f"https://test{i}.com/webhook",
                auth_type="none"
            )
            db_session.add(channel)
            db_session.commit()
            db_session.refresh(channel)
            channel_ids.append(channel.id)

        # 批量删除
        response = client.post(
            "/api/v1/notification/channels/batch-delete",
            json={"ids": channel_ids},
            headers=admin_headers
        )
        assert response.status_code in [200, 207]  # 207 表示部分成功
