"""
通用测试辅助函数

提供统一的 API 测试方法，减少重复代码
"""
from typing import Dict, Any, Optional
from httpx import Response


class APITestHelper:
    """API 测试辅助类 - 统一 API 测试方法"""

    @staticmethod
    def test_unauthorized_endpoint(
        client,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Response:
        """
        测试未授权访问

        Args:
            client: 测试客户端
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            endpoint: API 端点
            **kwargs: 传递给请求的参数

        Returns:
            Response 对象
        """
        method_func = getattr(client, method.lower())
        response = method_func(endpoint, **kwargs)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        return response

    @staticmethod
    def test_forbidden_endpoint(
        client,
        method: str,
        endpoint: str,
        token: str,
        **kwargs
    ) -> Response:
        """
        测试权限不足访问

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token
            **kwargs: 传递给请求的参数

        Returns:
            Response 对象
        """
        headers = {"Authorization": f"Bearer {token}"}
        method_func = getattr(client, method.lower())
        response = method_func(endpoint, headers=headers, **kwargs)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        return response

    @staticmethod
    def test_success_endpoint(
        client,
        method: str,
        endpoint: str,
        token: str,
        expected_status: int = 200,
        **kwargs
    ) -> Response:
        """
        测试成功访问

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token
            expected_status: 期望的状态码
            **kwargs: 传递给请求的参数

        Returns:
            Response 对象
        """
        headers = {"Authorization": f"Bearer {token}"}
        method_func = getattr(client, method.lower())
        response = method_func(endpoint, headers=headers, **kwargs)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        return response

    @staticmethod
    def test_invalid_data(
        client,
        method: str,
        endpoint: str,
        token: str,
        invalid_data: Dict[str, Any],
        expected_status: int = 422
    ) -> Response:
        """
        测试无效数据

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token
            invalid_data: 无效的数据
            expected_status: 期望的状态码

        Returns:
            Response 对象
        """
        headers = {"Authorization": f"Bearer {token}"}
        method_func = getattr(client, method.lower())
        response = method_func(endpoint, headers=headers, json=invalid_data)
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}"
        return response

    @staticmethod
    def test_not_found_endpoint(
        client,
        method: str,
        endpoint: str,
        token: str,
        **kwargs
    ) -> Response:
        """
        测试资源不存在

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token
            **kwargs: 传递给请求的参数

        Returns:
            Response 对象
        """
        headers = {"Authorization": f"Bearer {token}"}
        method_func = getattr(client, method.lower())
        response = method_func(endpoint, headers=headers, **kwargs)
        # 允许 403（权限不足）和 404（不存在）
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"
        return response


class CRUDTestMixin:
    """CRUD 操作测试混入类 - 提供通用 CRUD 测试方法"""

    def _test_create_success(
        self,
        client,
        endpoint: str,
        data: Dict[str, Any],
        token: str,
        expected_status: int = 201
    ) -> Response:
        """
        创建成功测试

        Args:
            client: 测试客户端
            endpoint: API 端点
            data: 创建数据
            token: 认证 token
            expected_status: 期望的状态码

        Returns:
            Response 对象
        """
        return APITestHelper.test_success_endpoint(
            client, "POST", endpoint, token, expected_status, json=data
        )

    def _test_list_success(
        self,
        client,
        endpoint: str,
        token: str
    ) -> Response:
        """
        列表查询成功测试

        Args:
            client: 测试客户端
            endpoint: API 端点
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_success_endpoint(
            client, "GET", endpoint, token
        )

    def _test_get_detail_success(
        self,
        client,
        endpoint: str,
        token: str
    ) -> Response:
        """
        详情查询成功测试

        Args:
            client: 测试客户端
            endpoint: API 端点
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_success_endpoint(
            client, "GET", endpoint, token
        )

    def _test_update_success(
        self,
        client,
        endpoint: str,
        data: Dict[str, Any],
        token: str
    ) -> Response:
        """
        更新成功测试

        Args:
            client: 测试客户端
            endpoint: API 端点
            data: 更新数据
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_success_endpoint(
            client, "PUT", endpoint, token, json=data
        )

    def _test_delete_success(
        self,
        client,
        endpoint: str,
        token: str
    ) -> Response:
        """
        删除成功测试

        Args:
            client: 测试客户端
            endpoint: API 端点
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_success_endpoint(
            client, "DELETE", endpoint, token
        )

    def _test_unauthorized(
        self,
        client,
        method: str,
        endpoint: str
    ) -> Response:
        """
        未授权访问测试

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点

        Returns:
            Response 对象
        """
        return APITestHelper.test_unauthorized_endpoint(
            client, method, endpoint
        )

    def _test_forbidden(
        self,
        client,
        method: str,
        endpoint: str,
        token: str
    ) -> Response:
        """
        权限不足访问测试

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_forbidden_endpoint(
            client, method, endpoint, token
        )

    def _test_not_found(
        self,
        client,
        method: str,
        endpoint: str,
        token: str
    ) -> Response:
        """
        资源不存在测试

        Args:
            client: 测试客户端
            method: HTTP 方法
            endpoint: API 端点
            token: 认证 token

        Returns:
            Response 对象
        """
        return APITestHelper.test_not_found_endpoint(
            client, method, endpoint, token
        )


class AuthTestMixin:
    """认证测试混入类 - 提供认证相关的辅助方法"""

    @staticmethod
    def make_auth_headers(token: str) -> Dict[str, str]:
        """
        创建认证头

        Args:
            token: 认证 token

        Returns:
            认证头字典
        """
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def extract_token(headers: Dict[str, str]) -> str:
        """
        从认证头中提取 token

        Args:
            headers: 认证头字典

        Returns:
            token 字符串
        """
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除 "Bearer " 前缀
        return auth_header
