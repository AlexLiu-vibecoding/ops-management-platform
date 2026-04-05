"""
批量操作API单元测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.api.batch_operations import router, BatchOperationRequest, BatchOperationResponse


class TestBatchOperationSchemas:
    """批量操作模型测试"""

    def test_batch_operation_request_basic(self):
        """测试基本请求模型"""
        request = BatchOperationRequest(
            action="delete",
            ids=[1, 2, 3],
            params={"force": True}
        )

        assert request.action == "delete"
        assert request.ids == [1, 2, 3]
        assert request.params == {"force": True}

    def test_batch_operation_request_without_params(self):
        """测试无参数的请求模型"""
        request = BatchOperationRequest(
            action="enable",
            ids=[1, 2]
        )

        assert request.action == "enable"
        assert request.ids == [1, 2]
        assert request.params is None

    def test_batch_operation_response_basic(self):
        """测试基本响应模型"""
        response = BatchOperationResponse(
            success=True,
            total=3,
            succeeded=2,
            failed=1,
            no_permission=0,
            results=[
                {"id": 1, "status": "success"},
                {"id": 2, "status": "success"},
                {"id": 3, "status": "failed", "error": "Permission denied"}
            ]
        )

        assert response.success is True
        assert response.total == 3
        assert response.succeeded == 2
        assert response.failed == 1
        assert response.no_permission == 0
        assert len(response.results) == 3

    def test_batch_operation_response_minimal(self):
        """测试最小响应模型"""
        response = BatchOperationResponse(
            success=True,
            total=2,
            succeeded=2,
            failed=0,
            no_permission=0
        )

        assert response.results == []


@pytest.mark.asyncio
class TestBatchInstancesOperation:
    """批量实例操作测试"""

    @patch('app.api.batch_operations.PermissionService')
    @patch('app.api.batch_operations.BatchOperationService')
    async def test_batch_delete_success(self, mock_batch_service_class, mock_perm_service_class):
        """测试批量删除成功"""
        from fastapi import Request
        from app.database import get_db
        from app.deps import get_current_user
        from app.models import User

        # Mock services
        mock_perm_service = MagicMock()
        mock_perm_service_class.return_value = mock_perm_service

        mock_batch_service = MagicMock()
        mock_batch_service_class.return_value = mock_batch_service

        # Mock batch operation result
        mock_batch_service.batch_delete_instances.return_value = {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "no_permission": 0
        }

        # Mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "admin"

        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        # Mock dependencies
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        response = client.post(
            "/batch/instances",
            json={
                "action": "delete",
                "ids": [1, 2]
            }
        )

        assert response.status_code == 200

    @patch('app.api.batch_operations.PermissionService')
    @patch('app.api.batch_operations.BatchOperationService')
    async def test_batch_enable_success(self, mock_batch_service_class, mock_perm_service_class):
        """测试批量启用成功"""
        mock_perm_service = MagicMock()
        mock_perm_service_class.return_value = mock_perm_service

        mock_batch_service = MagicMock()
        mock_batch_service_class.return_value = mock_batch_service
        mock_batch_service.batch_enable_instances.return_value = {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "no_permission": 0
        }

        from app.models import User
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "admin"

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        response = client.post(
            "/batch/instances",
            json={
                "action": "enable",
                "ids": [1, 2]
            }
        )

        assert response.status_code == 200

    @patch('app.api.batch_operations.PermissionService')
    async def test_batch_invalid_action(self, mock_perm_service_class):
        """测试不支持的操作"""
        mock_perm_service = MagicMock()
        mock_perm_service_class.return_value = mock_perm_service

        from app.models import User
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "admin"

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        response = client.post(
            "/batch/instances",
            json={
                "action": "invalid_action",
                "ids": [1, 2]
            }
        )

        assert response.status_code == 400


@pytest.mark.asyncio
class TestBatchApprovalsOperation:
    """批量审批操作测试"""

    @patch('app.api.batch_operations.PermissionService')
    @patch('app.api.batch_operations.BatchOperationService')
    async def test_batch_approve_success(self, mock_batch_service_class, mock_perm_service_class):
        """测试批量审批成功"""
        mock_perm_service = MagicMock()
        mock_perm_service_class.return_value = mock_perm_service

        mock_batch_service = MagicMock()
        mock_batch_service_class.return_value = mock_batch_service
        mock_batch_service.batch_approve_approvals.return_value = {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "no_permission": 0
        }

        from app.models import User
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "approver"

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        response = client.post(
            "/batch/approvals",
            json={
                "action": "approve",
                "ids": [1, 2],
                "params": {"comment": "Approved"}
            }
        )

        assert response.status_code == 200

    @patch('app.api.batch_operations.PermissionService')
    @patch('app.api.batch_operations.BatchOperationService')
    async def test_batch_reject_success(self, mock_batch_service_class, mock_perm_service_class):
        """测试批量拒绝成功"""
        mock_perm_service = MagicMock()
        mock_perm_service_class.return_value = mock_perm_service

        mock_batch_service = MagicMock()
        mock_batch_service_class.return_value = mock_batch_service
        mock_batch_service.batch_reject_approvals.return_value = {
            "total": 2,
            "succeeded": 2,
            "failed": 0,
            "no_permission": 0
        }

        from app.models import User
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "approver"

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user] = lambda: mock_user

        client = TestClient(app)

        response = client.post(
            "/batch/approvals",
            json={
                "action": "reject",
                "ids": [1, 2],
                "params": {"comment": "Rejected"}
            }
        )

        assert response.status_code == 200
