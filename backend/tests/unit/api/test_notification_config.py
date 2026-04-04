#!/usr/bin/env python3
"""
通知配置 API 单元测试

测试范围：
1. 通知模板 CRUD 操作
2. 模板启用/禁用
3. 模板预览
4. 模板变量验证

改进：
1. 完整的配置管理流程测试
2. 权限验证测试
3. 边界条件测试
4. 错误处理测试

运行方式:
    cd /workspace/projects/backend

    # 运行所有通知配置 API 测试
    python -m pytest tests/unit/api/test_notification_config.py -v

    # 运行特定测试
    python -m pytest tests/unit/api/test_notification_config.py::TestNotificationConfigAPI -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import User, UserRole, NotificationTemplate
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
def test_template(db_session):
    """创建测试模板"""
    template = NotificationTemplate(
        name="测试模板",
        notification_type="approval",
        sub_type="new",
        title_template="变更审批通知",
        content_template="变更详情: {title}",
        is_enabled=True,
        is_default=True
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    yield template
    # 清理
    db_session.delete(template)
    db_session.commit()


@pytest.mark.unit
class TestNotificationConfigAPI:
    """通知配置 API 测试"""

    def test_list_templates_unauthorized(self, client):
        """测试未授权获取模板列表"""
        response = client.get("/api/v1/notification-templates")
        assert response.status_code == 401

    def test_list_templates_success(self, client, admin_headers, test_template):
        """测试成功获取模板列表"""
        response = client.get("/api/v1/notification-templates", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]

    def test_list_templates_filter_by_type(self, client, admin_headers, test_template):
        """测试按类型筛选模板"""
        response = client.get(
            "/api/v1/notification-templates?notification_type=approval",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data["data"]

    def test_create_template_unauthorized(self, client):
        """测试未授权创建模板"""
        response = client.post(
            "/api/v1/notification-templates",
            json={
                "name": "测试",
                "notification_type": "approval",
                "title_template": "测试",
                "content_template": "内容"
            }
        )
        assert response.status_code == 401

    def test_create_template_forbidden(self, client, operator_headers):
        """测试操作员创建模板（禁止）"""
        response = client.post(
            "/api/v1/notification-templates",
            json={
                "name": "测试",
                "notification_type": "approval",
                "title_template": "测试",
                "content_template": "内容"
            },
            headers=operator_headers
        )
        assert response.status_code == 403

    def test_create_template_success(self, client, admin_headers):
        """测试成功创建模板"""
        template_data = {
            "name": "新建模板",
            "notification_type": "alert",
            "sub_type": "cpu",
            "title_template": "告警: {alert_title}",
            "content_template": "告警详情: {alert_level}",
            "is_enabled": True,
            "is_default": False
        }

        response = client.post(
            "/api/v1/notification-templates",
            json=template_data,
            headers=admin_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "success" in data

        # 清理
        if "id" in data:
            template_id = data["id"]
            client.delete(f"/api/v1/notification-templates/{template_id}", headers=admin_headers)

    def test_create_template_invalid_type(self, client, admin_headers):
        """测试创建无效类型的模板"""
        template_data = {
            "name": "无效模板",
            "notification_type": "invalid_type",
            "title_template": "测试",
            "content_template": "内容"
        }

        response = client.post(
            "/api/v1/notification-templates",
            json=template_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_get_template_success(self, client, admin_headers, test_template):
        """测试成功获取模板详情"""
        response = client.get(
            f"/api/v1/notification-templates/{test_template.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_template.id
        assert data["name"] == test_template.name

    def test_get_template_not_found(self, client, admin_headers):
        """测试获取不存在的模板"""
        response = client.get("/api/v1/notification-templates/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_template_success(self, client, admin_headers, test_template):
        """测试成功更新模板"""
        update_data = {
            "name": "更新后名称",
            "description": "更新后描述",
            "is_enabled": False
        }

        response = client.put(
            f"/api/v1/notification-templates/{test_template.id}",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_update_template_not_found(self, client, admin_headers):
        """测试更新不存在的模板"""
        update_data = {"name": "更新"}

        response = client.put(
            "/api/v1/notification-templates/99999",
            json=update_data,
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_delete_template_success(self, client, admin_headers, db_session):
        """测试成功删除模板"""
        # 创建测试模板
        template = NotificationTemplate(
            name="待删除模板",
            notification_type="alert",
            title_template="测试",
            content_template="内容",
            is_enabled=True,
            is_default=False
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)

        # 删除模板
        response = client.delete(
            f"/api/v1/notification-templates/{template.id}",
            headers=admin_headers
        )
        assert response.status_code == 200

        # 验证删除
        deleted = db_session.query(NotificationTemplate).filter_by(id=template.id).first()
        assert deleted is None

    def test_delete_template_not_found(self, client, admin_headers):
        """测试删除不存在的模板"""
        response = client.delete("/api/v1/notification-templates/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_enable_template_success(self, client, admin_headers, test_template):
        """测试成功启用模板"""
        # 先禁用模板
        test_template.is_enabled = False
        db_session.commit()

        # 启用模板
        response = client.post(
            f"/api/v1/notification-templates/{test_template.id}/enable",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_disable_template_success(self, client, admin_headers, test_template):
        """测试成功禁用模板"""
        # 先启用模板
        test_template.is_enabled = True
        db_session.commit()

        # 禁用模板
        response = client.post(
            f"/api/v1/notification-templates/{test_template.id}/disable",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_preview_template_success(self, client, admin_headers, test_template):
        """测试成功预览模板"""
        preview_data = {
            "title": "审批标题",
            "content": "审批内容"
        }

        response = client.post(
            f"/api/v1/notification-templates/{test_template.id}/preview",
            json=preview_data,
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data

    def test_preview_template_with_sub_type(self, client, admin_headers, test_template):
        """测试预览细分类型模板"""
        preview_data = {
            "title": "测试标题",
            "content": "测试内容"
        }

        response = client.post(
            f"/api/v1/notification-templates/{test_template.id}/preview?sub_type=new",
            json=preview_data,
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_get_template_variables(self, client, admin_headers):
        """测试获取模板变量"""
        response = client.get(
            "/api/v1/notification-templates/variables/approval",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_template_variables_invalid_type(self, client, admin_headers):
        """测试获取无效类型的模板变量"""
        response = client.get(
            "/api/v1/notification-templates/variables/invalid_type",
            headers=admin_headers
        )
        assert response.status_code in [400, 404]

    def test_batch_delete_templates(self, client, admin_headers, db_session):
        """测试批量删除模板"""
        # 创建多个测试模板
        template_ids = []
        for i in range(3):
            template = NotificationTemplate(
                name=f"批量删除{i}",
                notification_type="alert",
                title_template="测试",
                content_template="内容",
                is_enabled=False,
                is_default=False
            )
            db_session.add(template)
            db_session.commit()
            db_session.refresh(template)
            template_ids.append(template.id)

        # 批量删除
        response = client.post(
            "/api/v1/notification-templates/batch-delete",
            json={"ids": template_ids},
            headers=admin_headers
        )
        assert response.status_code in [200, 207]  # 207 表示部分成功
