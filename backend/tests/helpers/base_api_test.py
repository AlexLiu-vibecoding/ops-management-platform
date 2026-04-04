"""
API 测试基类

提供通用的 API 测试基类，减少重复代码
"""
import pytest
from typing import Optional, List, Dict, Any, Callable
from httpx import Response

from .test_helpers import APITestHelper, CRUDTestMixin, AuthTestMixin


class BaseAPITest:
    """API 测试基类 - 提供通用的测试方法和断言"""

    @pytest.fixture(autouse=True)
    def setup_test_helper(self, client):
        """
        自动设置测试辅助类
        这个 fixture 会自动运行，为每个测试用例设置辅助类
        """
        self.helper = APITestHelper()
        self.auth_helper = AuthTestMixin()
        self.client = client

    def assert_response(
        self,
        response: Response,
        expected_status: int,
        message: Optional[str] = None
    ) -> None:
        """
        断言响应状态码

        Args:
            response: HTTP 响应对象
            expected_status: 期望的状态码
            message: 自定义错误消息
        """
        if message:
            assert response.status_code == expected_status, \
                f"{message}: Expected {expected_status}, got {response.status_code}"
        else:
            assert response.status_code == expected_status, \
                f"Expected {expected_status}, got {response.status_code}"

    def assert_response_has_keys(
        self,
        response: Response,
        required_keys: List[str]
    ) -> Dict[str, Any]:
        """
        断言响应包含指定的键

        Args:
            response: HTTP 响应对象
            required_keys: 必须包含的键列表

        Returns:
            响应的 JSON 数据
        """
        data = response.json()
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise AssertionError(f"Missing keys in response: {missing_keys}")
        return data

    def assert_response_not_has_keys(
        self,
        response: Response,
        forbidden_keys: List[str]
    ) -> Dict[str, Any]:
        """
        断言响应不包含指定的键

        Args:
            response: HTTP 响应对象
            forbidden_keys: 不应该包含的键列表

        Returns:
            响应的 JSON 数据
        """
        data = response.json()
        found_keys = [key for key in forbidden_keys if key in data]
        if found_keys:
            raise AssertionError(f"Unexpected keys in response: {found_keys}")
        return data

    def get_response_data(self, response: Response) -> Dict[str, Any]:
        """
        获取响应的 JSON 数据

        Args:
            response: HTTP 响应对象

        Returns:
            响应的 JSON 数据
        """
        return response.json()

    def extract_id_from_response(
        self,
        response: Response,
        id_key: str = "id"
    ) -> int:
        """
        从响应中提取 ID

        Args:
            response: HTTP 响应对象
            id_key: ID 的键名

        Returns:
            ID 值
        """
        data = self.get_response_data(response)
        if id_key not in data:
            raise AssertionError(f"Response does not contain '{id_key}' key")
        return data[id_key]


class BaseCRUDTest(BaseAPITest, CRUDTestMixin):
    """
    CRUD 测试基类
    提供通用的 CRUD 测试方法，子类只需定义端点和数据工厂

    使用示例:
        class TestScriptsAPI(BaseCRUDTest):
            endpoint_base = "scripts"

            def get_create_data(self):
                return {"name": "test", "content": "print('hello')"}
    """

    # 子类需要覆盖这些属性
    endpoint_base: str = ""  # 例如: "scripts", "ai-models"
    create_data_factory: Optional[Callable] = None  # 创建数据工厂函数

    def test_unauthorized_access_list(self):
        """测试未授权访问列表"""
        self.helper.test_unauthorized_endpoint(
            self.client, "GET", f"/api/v1/{self.endpoint_base}"
        )

    def test_unauthorized_access_create(self):
        """测试未授权访问创建"""
        self.helper.test_unauthorized_endpoint(
            self.client, "POST", f"/api/v1/{self.endpoint_base}"
        )

    def test_unauthorized_access_update(self):
        """测试未授权访问更新"""
        self.helper.test_unauthorized_endpoint(
            self.client, "PUT", f"/api/v1/{self.endpoint_base}/1"
        )

    def test_unauthorized_access_delete(self):
        """测试未授权访问删除"""
        self.helper.test_unauthorized_endpoint(
            self.client, "DELETE", f"/api/v1/{self.endpoint_base}/1"
        )

    def test_list_success(self, admin_headers):
        """测试列表查询成功"""
        token = self.auth_helper.extract_token(admin_headers)
        return self.helper.test_success_endpoint(
            self.client, "GET", f"/api/v1/{self.endpoint_base}",
            token
        )

    def test_create_success(self, admin_headers):
        """测试创建成功"""
        if not self.create_data_factory:
            pytest.skip("create_data_factory not defined")

        data = self.create_data_factory()
        token = self.auth_helper.extract_token(admin_headers)
        return self.helper.test_success_endpoint(
            self.client, "POST", f"/api/v1/{self.endpoint_base}",
            token, 201, json=data
        )

    def test_invalid_data(self, admin_headers):
        """测试无效数据"""
        if not self.create_data_factory:
            pytest.skip("create_data_factory not defined")

        token = self.auth_helper.extract_token(admin_headers)
        return self.helper.test_invalid_data(
            self.client, "POST", f"/api/v1/{self.endpoint_base}",
            token, {"invalid": "data"}
        )


class BaseErrorHandlingTest:
    """
    错误处理测试基类
    提供通用的错误处理测试方法

    使用示例:
        class TestScriptsAPIErrorHandling(BaseErrorHandlingTest):
            endpoint_base = "scripts"
    """

    endpoint_base: str = ""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get(f"/api/v1/{self.endpoint_base}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_unauthorized_create(self, client):
        """测试未授权创建"""
        response = client.post(f"/api/v1/{self.endpoint_base}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_unauthorized_update(self, client):
        """测试未授权更新"""
        response = client.put(f"/api/v1/{self.endpoint_base}/1")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_unauthorized_delete(self, client):
        """测试未授权删除"""
        response = client.delete(f"/api/v1/{self.endpoint_base}/1")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_forbidden_access(self, client, operator_token):
        """测试权限不足访问"""
        response = client.get(
            f"/api/v1/{self.endpoint_base}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"

    def test_invalid_data_create(self, client, admin_headers):
        """测试创建时提供无效数据"""
        response = client.post(
            f"/api/v1/{self.endpoint_base}",
            json={"invalid": "data"},
            headers=admin_headers
        )
        assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"

    def test_not_found_get(self, client, admin_headers):
        """测试获取不存在的资源"""
        response = client.get(
            f"/api/v1/{self.endpoint_base}/99999",
            headers=admin_headers
        )
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"

    def test_not_found_update(self, client, admin_headers):
        """测试更新不存在的资源"""
        response = client.put(
            f"/api/v1/{self.endpoint_base}/99999",
            json={"name": "updated"},
            headers=admin_headers
        )
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"

    def test_not_found_delete(self, client, operator_token):
        """测试删除不存在的资源"""
        response = client.delete(
            f"/api/v1/{self.endpoint_base}/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"
