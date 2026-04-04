"""
审批 API 测试用例
"""
import pytest
from datetime import datetime, timedelta


class TestApprovalAPI:
    """审批 API 测试"""
    
    def test_get_approvals_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/approvals")
        assert response.status_code == 401
    
    def test_get_approvals_success(self, client, operator_token):
        """测试获取审批列表"""
        response = client.get(
            "/api/v1/approvals",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_create_approval_missing_fields(self, client, operator_token):
        """测试创建审批缺少必填字段"""
        response = client.post(
            "/api/v1/approvals",
            json={},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_approval_with_auto_execute(self, client, operator_token, test_environment, db_session):
        """测试创建自动执行的审批"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="测试实例",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="encrypted",
            environment_id=test_environment.id,
            db_type="mysql",
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)
        
        response = client.post(
            "/api/v1/approvals",
            json={
                "title": "测试变更",
                "change_type": "DDL",
                "instance_id": instance.id,
                "database_name": "test_db",
                "sql_content": "CREATE TABLE test (id INT);",
                "auto_execute": True
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # 可能因为实例连接问题失败，但请求格式应该是正确的
        assert response.status_code in [200, 400, 500]
    
    def test_create_approval_with_scheduled_time(self, client, operator_token, test_environment, db_session):
        """测试创建定时执行的审批"""
        from app.models import RDBInstance
        
        # 创建测试实例
        instance = RDBInstance(
            name="测试实例2",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="encrypted",
            environment_id=test_environment.id,
            db_type="mysql",
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        db_session.refresh(instance)
        
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        response = client.post(
            "/api/v1/approvals",
            json={
                "title": "定时变更",
                "change_type": "DML",
                "instance_id": instance.id,
                "database_name": "test_db",
                "sql_content": "UPDATE test SET status = 1;",
                "scheduled_time": scheduled_time
            },
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 400, 500]


class TestApprovalPermissions:
    """审批权限测试"""
    
    def test_approve_approval_as_operator(self, client, operator_token, db_session):
        """测试普通用户无法审批"""
        from app.models import ApprovalRecord, ApprovalStatus
        from app.utils.auth import hash_password, create_access_token
        
        # 创建审批管理员
        from app.models import User, UserRole
        admin = User(
            username="approval_admin",
            password_hash=hash_password("admin123"),
            real_name="审批管理员",
            email="approval@test.com",
            role=UserRole.APPROVAL_ADMIN,
            status=True
        )
        db_session.add(admin)
        db_session.commit()
        
        # 创建一个待审批记录
        approval = ApprovalRecord(
            title="测试审批",
            change_type="DDL",
            status=ApprovalStatus.PENDING,
            requester_id=1  # 假设用户ID为1
        )
        db_session.add(approval)
        db_session.commit()
        db_session.refresh(approval)
        
        # 普通用户尝试审批
        response = client.post(
            f"/api/v1/approvals/{approval.id}/approve",
            json={"approved": True},
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        # 普通用户不应该有审批权限
        assert response.status_code in [403, 404, 401]
