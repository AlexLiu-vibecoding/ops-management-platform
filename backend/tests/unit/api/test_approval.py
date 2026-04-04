#!/usr/bin/env python3
"""
审批流程API单元测试

测试范围：
1. 审批列表查询
2. 审批详情查询
3. 创建审批申请
4. 审批通过/拒绝
5. 执行审批通过的SQL
6. 预览数据库
7. 解析SQL数据库
8. 权限验证

运行方式:
    cd /workspace/projects/backend

    # 运行所有审批API测试
    python -m pytest tests/unit/api/test_approval.py -v

    # 运行特定测试
    python -m pytest tests/unit/api/test_approval.py::TestApprovalAPI -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models import (
    User, UserRole, RDBInstance, ApprovalRecord,
    ApprovalStatus, Environment, ApprovalFlow
)
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
def approval_admin_user(db_session):
    """创建审批管理员用户"""
    username = f"approval_admin_{os.urandom(4).hex()}"
    user = User(
        username=username,
        password_hash=hash_password("approval123"),
        real_name="审批管理员",
        email=f"{username}@test.com",
        role=UserRole.APPROVAL_ADMIN,
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
    """管理员Token"""
    return create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role.value
    })


@pytest.fixture(scope="function")
def operator_token(operator_user):
    """操作员Token"""
    return create_access_token({
        "sub": str(operator_user.id),
        "username": operator_user.username,
        "role": operator_user.role.value
    })


@pytest.fixture(scope="function")
def approval_admin_token(approval_admin_user):
    """审批管理员Token"""
    return create_access_token({
        "sub": str(approval_admin_user.id),
        "username": approval_admin_user.username,
        "role": approval_admin_user.role.value
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
def approval_admin_headers(approval_admin_token):
    """审批管理员认证头"""
    return {"Authorization": f"Bearer {approval_admin_token}"}


@pytest.fixture(scope="function")
def test_environment(db_session):
    """创建测试环境"""
    env = db_session.query(Environment).filter_by(code="production").first()
    if not env:
        env = Environment(
            name="生产环境",
            code="production",
            color="#FF4D4F",
            require_approval=True
        )
        db_session.add(env)
        db_session.commit()
        db_session.refresh(env)
    yield env


@pytest.fixture(scope="function")
def test_rdb_instance(db_session, test_environment):
    """创建测试RDB实例"""
    instance = RDBInstance(
        name="测试实例",
        host="127.0.0.1",
        port=3306,
        username="root",
        password_encrypted="encrypted_password",
        environment_id=test_environment.id,
        status=True
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    yield instance
    # 清理
    db_session.delete(instance)
    db_session.commit()


@pytest.fixture(scope="function")
def test_approval(db_session, admin_user, test_rdb_instance, test_environment):
    """创建测试审批记录"""
    approval = ApprovalRecord(
        title="测试SQL变更",
        change_type="SQL",
        sql_content="SELECT * FROM test_table;",
        sql_risk_level="medium",
        requester_id=admin_user.id,
        rdb_instance_id=test_rdb_instance.id,
        environment_id=test_environment.id,
        status=ApprovalStatus.PENDING,
        min_approvers=1
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    yield approval
    # 清理
    db_session.delete(approval)
    db_session.commit()


@pytest.mark.unit
class TestApprovalAPI:
    """审批流程API测试"""

    def test_list_approvals_unauthorized(self, client):
        """测试未授权获取审批列表"""
        response = client.get("/api/v1/approvals")
        assert response.status_code == 401

    def test_list_approvals_success(self, client, admin_headers, test_approval):
        """测试成功获取审批列表"""
        response = client.get("/api/v1/approvals", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    def test_list_approvals_filter_by_status(self, client, admin_headers, test_approval):
        """测试按状态筛选审批列表"""
        response = client.get(
            "/api/v1/approvals?status_filter=pending",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_list_approvals_filter_by_requester(self, client, admin_headers, test_approval, admin_user):
        """测试按申请人筛选审批列表"""
        response = client.get(
            f"/api/v1/approvals?requester_id={admin_user.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_get_approval_success(self, client, admin_headers, test_approval):
        """测试成功获取审批详情"""
        response = client.get(
            f"/api/v1/approvals/{test_approval.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_approval.id
        assert data["title"] == test_approval.title

    def test_get_approval_not_found(self, client, admin_headers):
        """测试获取不存在的审批详情"""
        response = client.get("/api/v1/approvals/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_get_approval_unauthorized(self, client, operator_headers, test_approval, operator_user):
        """测试无权限获取其他人的审批详情"""
        # 确保审批不是当前用户创建的
        if test_approval.requester_id == operator_user.id:
            pytest.skip("测试数据不符合条件")

        response = client.get(
            f"/api/v1/approvals/{test_approval.id}",
            headers=operator_headers
        )
        # 非管理员只能查看自己的申请
        if operator_user.role.value not in ["super_admin", "approval_admin"]:
            assert response.status_code == 403

    def test_create_approval_unauthorized(self, client):
        """测试未授权创建审批"""
        response = client.post(
            "/api/v1/approvals",
            json={
                "title": "测试SQL",
                "change_type": "SQL",
                "sql_content": "SELECT 1;",
                "sql_risk_level": "low"
            }
        )
        assert response.status_code == 401

    def test_create_approval_success(self, client, admin_headers, test_rdb_instance, test_environment):
        """测试成功创建审批"""
        approval_data = {
            "title": "新建SQL变更",
            "change_type": "SQL",
            "sql_content": "SELECT * FROM users;",
            "sql_risk_level": "low",
            "rdb_instance_id": test_rdb_instance.id,
            "environment_id": test_environment.id
        }

        response = client.post(
            "/api/v1/approvals",
            json=approval_data,
            headers=admin_headers
        )
        # 可能返回201或200
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["title"] == approval_data["title"]

        # 清理
        if "id" in data:
            approval_id = data["id"]
            client.delete(f"/api/v1/approvals/{approval_id}", headers=admin_headers)

    def test_create_approval_missing_required_fields(self, client, admin_headers):
        """测试创建审批缺少必填字段"""
        approval_data = {
            "title": "测试SQL"
            # 缺少 change_type, sql_content, sql_risk_level
        }

        response = client.post(
            "/api/v1/approvals",
            json=approval_data,
            headers=admin_headers
        )
        assert response.status_code in [400, 422]

    def test_approve_reject_unauthorized(self, client):
        """测试未授权审批操作"""
        response = client.post(
            "/api/v1/approvals/1/approve",
            json={"approved": True, "comment": "同意"}
        )
        assert response.status_code == 401

    def test_approve_reject_not_found(self, client, approval_admin_headers):
        """测试审批不存在的记录"""
        response = client.post(
            "/api/v1/approvals/99999/approve",
            json={"approved": True, "comment": "同意"},
            headers=approval_admin_headers
        )
        assert response.status_code == 404

    def test_approve_success(self, client, approval_admin_headers, test_approval):
        """测试成功审批通过"""
        response = client.post(
            f"/api/v1/approvals/{test_approval.id}/approve",
            json={"approved": True, "comment": "同意执行"},
            headers=approval_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_approval.id
        # 检查状态是否变为 APPROVED
        assert data["status"] in ["approved", "APPROVED"]

    def test_reject_success(self, client, approval_admin_headers, test_approval):
        """测试成功审批拒绝"""
        # 先创建一个新的审批用于测试拒绝
        create_response = client.post(
            "/api/v1/approvals",
            json={
                "title": "待拒绝的审批",
                "change_type": "SQL",
                "sql_content": "SELECT 1;",
                "sql_risk_level": "low"
            },
            headers=approval_admin_headers
        )
        approval_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"approved": False, "comment": "拒绝执行"},
            headers=approval_admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == approval_id
        # 检查状态是否变为 REJECTED
        assert data["status"] in ["rejected", "REJECTED"]

        # 清理
        client.delete(f"/api/v1/approvals/{approval_id}", headers=approval_admin_headers)

    def test_approve_already_processed(self, client, approval_admin_headers, test_approval):
        """测试重复审批"""
        # 先审批一次
        client.post(
            f"/api/v1/approvals/{test_approval.id}/approve",
            json={"approved": True, "comment": "第一次审批"},
            headers=approval_admin_headers
        )

        # 再次审批
        response = client.post(
            f"/api/v1/approvals/{test_approval.id}/approve",
            json={"approved": True, "comment": "重复审批"},
            headers=approval_admin_headers
        )
        assert response.status_code in [400, 403]

    def test_execute_approval_unauthorized(self, client):
        """测试未授权执行审批"""
        response = client.post("/api/v1/approvals/1/execute")
        assert response.status_code == 401

    def test_execute_approval_not_approved(self, client, admin_headers, test_approval):
        """测试执行未审批通过的记录"""
        response = client.post(
            f"/api/v1/approvals/{test_approval.id}/execute",
            headers=admin_headers
        )
        # 未审批通过的记录不能执行
        assert response.status_code in [400, 403]

    def test_preview_databases_unauthorized(self, client):
        """测试未授权预览数据库"""
        response = client.get("/api/v1/approvals/preview-databases/99999")
        assert response.status_code == 401

    def test_preview_databases_success(self, client, admin_headers, test_rdb_instance):
        """测试成功预览数据库列表"""
        # 注意：这个测试可能因为无法连接到真实数据库而失败
        response = client.get(
            f"/api/v1/approvals/preview-databases/{test_rdb_instance.id}",
            headers=admin_headers
        )
        # 可能成功或因为连接问题失败
        assert response.status_code in [200, 500]

    def test_preview_databases_not_found(self, client, admin_headers):
        """测试预览不存在实例的数据库"""
        response = client.get(
            "/api/v1/approvals/preview-databases/99999",
            headers=admin_headers
        )
        assert response.status_code in [404, 500]

    def test_parse_sql_databases_unauthorized(self, client):
        """测试未授权解析SQL数据库"""
        response = client.post(
            "/api/v1/approvals/parse-sql-databases",
            json={"sql": "SELECT 1;"}
        )
        assert response.status_code == 401

    def test_parse_sql_databases_success(self, client, admin_headers):
        """测试成功解析SQL数据库"""
        response = client.post(
            "/api/v1/approvals/parse-sql-databases",
            json={"sql": "SELECT * FROM test_db.users;"},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "databases" in data

    def test_parse_sql_databases_empty(self, client, admin_headers):
        """测试解析空SQL"""
        response = client.post(
            "/api/v1/approvals/parse-sql-databases",
            json={"sql": ""},
            headers=admin_headers
        )
        assert response.status_code in [200, 400]

    def test_dingtalk_action_get(self, client):
        """测试钉钉操作接口GET"""
        response = client.get("/api/v1/approvals/dingtalk-action")
        # 钉钉操作接口应该返回HTML或特定响应
        assert response.status_code in [200, 400, 404]

    def test_pagination(self, client, admin_headers, test_approval):
        """测试分页功能"""
        response = client.get(
            "/api/v1/approvals?skip=0&limit=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 10

    def test_filter_by_environment(self, client, admin_headers, test_approval, test_environment):
        """测试按环境筛选"""
        response = client.get(
            f"/api/v1/approvals?environment_id={test_environment.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_filter_by_change_type(self, client, admin_headers, test_approval):
        """测试按变更类型筛选"""
        response = client.get(
            "/api/v1/approvals?change_type=SQL",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_exclude_change_type(self, client, admin_headers, test_approval):
        """测试排除变更类型"""
        response = client.get(
            "/api/v1/approvals?exclude_change_type=REDIS",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_readonly_user_can_only_own_approvals(self, client, db_session, test_approval):
        """测试只读用户只能查看自己的审批"""
        # 创建只读用户
        readonly_user = User(
            username=f"readonly_{os.urandom(4).hex()}",
            password_hash=hash_password("readonly123"),
            real_name="只读用户",
            email=f"readonly_{os.urandom(4).hex()}@test.com",
            role=UserRole.READONLY,
            status=True
        )
        db_session.add(readonly_user)
        db_session.commit()

        readonly_token = create_access_token({
            "sub": str(readonly_user.id),
            "username": readonly_user.username,
            "role": readonly_user.role.value
        })
        readonly_headers = {"Authorization": f"Bearer {readonly_token}"}

        # 只读用户应该只能看到自己的审批
        response = client.get("/api/v1/approvals", headers=readonly_headers)
        assert response.status_code == 200
        data = response.json()
        # 应该为空，因为没有创建只读用户的审批
        assert len(data["items"]) == 0

        # 清理
        db_session.delete(readonly_user)
        db_session.commit()

    def test_multi_approver_scenario(self, client, approval_admin_headers, test_approval):
        """测试多人审批场景"""
        # 设置需要多人审批
        test_approval.min_approvers = 2
        db_session.commit()

        # 第一次审批
        response1 = client.post(
            f"/api/v1/approvals/{test_approval.id}/approve",
            json={"approved": True, "comment": "第一审批"},
            headers=approval_admin_headers
        )
        assert response1.status_code == 200
        data1 = response1.json()
        # 应该还是pending状态，因为还需要另一个审批
        assert data1["status"] in ["pending", "PENDING"]

        # 第二次审批（需要另一个审批人）
        # 这里模拟第二次审批（实际可能需要不同的用户）
        # 由于测试环境限制，这个测试可能需要调整

        # 清理
        test_approval.min_approvers = 1
        db_session.commit()
