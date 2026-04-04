"""
API响应工具测试
"""
import pytest
from unittest.mock import patch
from fastapi import HTTPException, status

from app.utils.api_response import (
    ErrorCode, ErrorDefinition, ErrorDefinitions,
    ApiResponse, ApiError, api_error
)


class TestErrorCode:
    """错误码枚举测试"""

    def test_error_code_values(self):
        """测试错误码值"""
        assert ErrorCode.UNKNOWN_ERROR.value == "UNKNOWN_ERROR"
        assert ErrorCode.UNAUTHORIZED.value == "UNAUTHORIZED"
        assert ErrorCode.USER_NOT_FOUND.value == "USER_NOT_FOUND"
        assert ErrorCode.INSTANCE_NOT_FOUND.value == "INSTANCE_NOT_FOUND"

    def test_error_code_categories(self):
        """测试错误码分类"""
        # 通用错误
        assert ErrorCode.VALIDATION_ERROR.value.startswith("VALIDATION")
        assert ErrorCode.RESOURCE_NOT_FOUND.value.startswith("RESOURCE")

        # 认证授权错误
        assert ErrorCode.TOKEN_EXPIRED.value.startswith("TOKEN")
        assert ErrorCode.PERMISSION_DENIED.value.startswith("PERMISSION")

        # 用户相关错误
        assert ErrorCode.USER_NOT_FOUND.value.startswith("USER")
        assert ErrorCode.INVALID_PASSWORD.value.startswith("INVALID")

        # 实例相关错误
        assert ErrorCode.INSTANCE_NOT_FOUND.value.startswith("INSTANCE")
        assert ErrorCode.QUERY_EXECUTION_FAILED.value.startswith("QUERY")

        # 审批相关错误
        assert ErrorCode.APPROVAL_NOT_FOUND.value.startswith("APPROVAL")
        assert ErrorCode.SQL_RISK_TOO_HIGH.value.startswith("SQL")

        # 监控相关错误
        assert ErrorCode.MONITOR_NOT_CONFIGURED.value.startswith("MONITOR")

        # 系统相关错误
        assert ErrorCode.CONFIG_NOT_FOUND.value.startswith("CONFIG")


class TestErrorDefinition:
    """错误定义测试"""

    def test_error_definition_default_status(self):
        """测试默认HTTP状态码"""
        error = ErrorDefinition(
            code=ErrorCode.VALIDATION_ERROR,
            message="参数错误"
        )

        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "参数错误"
        assert error.http_status == status.HTTP_400_BAD_REQUEST
        assert error.details is None

    def test_error_definition_custom_status(self):
        """测试自定义HTTP状态码"""
        error = ErrorDefinition(
            code=ErrorCode.UNKNOWN_ERROR,
            message="服务器错误",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="详细错误信息"
        )

        assert error.http_status == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.details == "详细错误信息"


class TestErrorDefinitions:
    """错误定义集合测试"""

    def test_common_errors(self):
        """测试通用错误定义"""
        assert ErrorDefinitions.UNKNOWN_ERROR.http_status == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert ErrorDefinitions.VALIDATION_ERROR.http_status == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert ErrorDefinitions.RESOURCE_NOT_FOUND.http_status == status.HTTP_404_NOT_FOUND
        assert ErrorDefinitions.RESOURCE_ALREADY_EXISTS.http_status == status.HTTP_409_CONFLICT

    def test_auth_errors(self):
        """测试认证授权错误定义"""
        assert ErrorDefinitions.UNAUTHORIZED.http_status == status.HTTP_401_UNAUTHORIZED
        assert ErrorDefinitions.TOKEN_EXPIRED.http_status == status.HTTP_401_UNAUTHORIZED
        assert ErrorDefinitions.PERMISSION_DENIED.http_status == status.HTTP_403_FORBIDDEN
        assert "权限不足" in ErrorDefinitions.PERMISSION_DENIED.message

    def test_user_errors(self):
        """测试用户相关错误定义"""
        assert ErrorDefinitions.USER_NOT_FOUND.http_status == status.HTTP_404_NOT_FOUND
        assert ErrorDefinitions.LOGIN_FAILED.http_status == status.HTTP_401_UNAUTHORIZED
        assert "用户名或密码错误" in ErrorDefinitions.LOGIN_FAILED.message

    def test_instance_errors(self):
        """测试实例相关错误定义"""
        assert ErrorDefinitions.INSTANCE_NOT_FOUND.http_status == status.HTTP_404_NOT_FOUND
        assert ErrorDefinitions.QUERY_EXECUTION_FAILED.http_status == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestApiResponse:
    """API响应工具测试"""

    @patch("app.utils.structured_logger.get_request_id")
    def test_success_response(self, mock_get_request_id):
        """测试成功响应"""
        mock_get_request_id.return_value = "test-request-id"

        response = ApiResponse.success(
            data={"id": 1, "name": "test"},
            message="操作成功"
        )

        assert response.success is True
        assert response.message == "操作成功"
        assert response.data["id"] == 1
        assert response.data["name"] == "test"

    @patch("app.utils.structured_logger.get_request_id")
    def test_success_response_no_data(self, mock_get_request_id):
        """测试无数据的成功响应"""
        mock_get_request_id.return_value = "test-request-id"

        response = ApiResponse.success(message="操作成功")

        assert response.success is True
        assert response.data is None

    @patch("app.utils.structured_logger.get_request_id")
    def test_error_response(self, mock_get_request_id):
        """测试错误响应"""
        mock_get_request_id.return_value = "test-request-id"

        response = ApiResponse.error(
            error_def=ErrorDefinitions.USER_NOT_FOUND,
            message="用户不存在"
        )

        assert response.success is False
        assert response.error["code"] == "USER_NOT_FOUND"
        assert response.error["message"] == "用户不存在"

    @patch("app.utils.structured_logger.get_request_id")
    def test_error_response_with_details(self, mock_get_request_id):
        """测试带详细信息的错误响应"""
        mock_get_request_id.return_value = "test-request-id"

        response = ApiResponse.error(
            error_def=ErrorDefinitions.VALIDATION_ERROR,
            message="参数验证失败",
            details={"field": "email", "error": "格式错误"}
        )

        assert response.success is False
        assert response.error["code"] == "VALIDATION_ERROR"

    @patch("app.utils.structured_logger.get_request_id")
    def test_to_json_response(self, mock_get_request_id):
        """测试转换为JSONResponse"""
        mock_get_request_id.return_value = "test-request-id"

        response = ApiResponse.success(data={"id": 1})
        json_response = response.to_json_response()

        assert json_response.status_code == 200


class TestApiError:
    """API错误异常测试"""

    def test_exception_with_error_definition(self):
        """测试使用错误定义创建异常"""
        exc = ApiError(ErrorDefinitions.USER_NOT_FOUND)

        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail["code"] == "USER_NOT_FOUND"
        assert "用户不存在" in exc.detail["message"]

    def test_exception_with_custom_message(self):
        """测试使用自定义消息创建异常"""
        exc = ApiError(
            ErrorDefinitions.VALIDATION_ERROR,
            message="自定义错误消息"
        )

        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert exc.detail["code"] == "VALIDATION_ERROR"
        assert exc.detail["message"] == "自定义错误消息"

    def test_exception_with_details(self):
        """测试带详细信息的异常"""
        exc = ApiError(
            ErrorDefinitions.VALIDATION_ERROR,
            details={"errors": [{"field": "name", "msg": "不能为空"}]}
        )

        assert exc.detail["details"]["errors"][0]["field"] == "name"

    def test_exception_with_extra(self):
        """测试带额外参数的异常"""
        exc = ApiError(
            ErrorDefinitions.USER_NOT_FOUND,
            user_id=123
        )

        assert exc.detail["user_id"] == 123


class TestApiErrorFunction:
    """API错误辅助函数测试"""

    def test_api_error_with_error_definition(self):
        """测试使用错误定义创建异常"""
        exc = api_error(ErrorDefinitions.USER_NOT_FOUND)

        assert isinstance(exc, ApiError)
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_api_error_with_custom_message(self):
        """测试使用自定义消息创建异常"""
        exc = api_error(
            ErrorDefinitions.INSTANCE_CONNECTION_FAILED,
            message="连接超时"
        )

        assert exc.detail["code"] == "INSTANCE_CONNECTION_FAILED"
        assert "连接超时" in exc.detail["message"]

    def test_api_error_with_extra(self):
        """测试带额外参数的错误"""
        exc = api_error(
            ErrorDefinitions.USER_NOT_FOUND,
            user_id=123
        )

        assert exc.detail["user_id"] == 123
