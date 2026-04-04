"""
API 错误码定义和统一响应格式

提供：
- 标准化错误码定义
- 统一响应格式
- 错误处理装饰器
- OpenAPI 文档增强

使用示例：
```python
from app.utils.api_response import (
    ApiResponse, ErrorCodes, api_error, api_success
)

# 成功响应
@api_success
def get_user(user_id: int):
    return user_service.get(user_id)

# 错误响应
raise api_error(ErrorCodes.USER_NOT_FOUND, user_id=1)

# 直接返回
return ApiResponse.success(data=user)
return ApiResponse.error(ErrorCodes.VALIDATION_ERROR, message="参数错误")
```
"""
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(StrEnum):
    """
    错误码枚举
    
    命名规范：<模块>_<操作>_<错误类型>
    
    错误码范围：
    - 1xxx: 通用错误
    - 2xxx: 认证授权错误
    - 3xxx: 用户相关错误
    - 4xxx: 实例相关错误
    - 5xxx: 审批相关错误
    - 6xxx: 监控相关错误
    - 7xxx: 系统相关错误
    """
    
    # ==================== 通用错误 1xxx ====================
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    OPERATION_FAILED = "OPERATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # ==================== 认证授权错误 2xxx ====================
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_EXPIRED = "PASSWORD_EXPIRED"
    
    # ==================== 用户相关错误 3xxx ====================
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    USER_EMAIL_EXISTS = "USER_EMAIL_EXISTS"
    USER_PHONE_EXISTS = "USER_PHONE_EXISTS"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    PASSWORD_MISMATCH = "PASSWORD_MISMATCH"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
    
    # ==================== 实例相关错误 4xxx ====================
    INSTANCE_NOT_FOUND = "INSTANCE_NOT_FOUND"
    INSTANCE_CONNECTION_FAILED = "INSTANCE_CONNECTION_FAILED"
    INSTANCE_ALREADY_EXISTS = "INSTANCE_ALREADY_EXISTS"
    INSTANCE_TYPE_UNSUPPORTED = "INSTANCE_TYPE_UNSUPPORTED"
    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    QUERY_EXECUTION_FAILED = "QUERY_EXECUTION_FAILED"
    BACKUP_FAILED = "BACKUP_FAILED"
    
    # ==================== 审批相关错误 5xxx ====================
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    APPROVAL_ALREADY_PROCESSED = "APPROVAL_ALREADY_PROCESSED"
    APPROVAL_NOT_PENDING = "APPROVAL_NOT_PENDING"
    APPROVAL_PERMISSION_DENIED = "APPROVAL_PERMISSION_DENIED"
    SQL_RISK_TOO_HIGH = "SQL_RISK_TOO_HIGH"
    ROLLBACK_GENERATION_FAILED = "ROLLBACK_GENERATION_FAILED"
    SCHEDULE_TIME_INVALID = "SCHEDULE_TIME_INVALID"
    
    # ==================== 监控相关错误 6xxx ====================
    MONITOR_NOT_CONFIGURED = "MONITOR_NOT_CONFIGURED"
    SLOW_QUERY_NOT_FOUND = "SLOW_QUERY_NOT_FOUND"
    PERFORMANCE_DATA_UNAVAILABLE = "PERFORMANCE_DATA_UNAVAILABLE"
    ALERT_RULE_NOT_FOUND = "ALERT_RULE_NOT_FOUND"
    ALERT_ALREADY_EXISTS = "ALERT_ALREADY_EXISTS"
    
    # ==================== 系统相关错误 7xxx ====================
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_UPDATE_FAILED = "CONFIG_UPDATE_FAILED"
    STORAGE_CONNECTION_FAILED = "STORAGE_CONNECTION_FAILED"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    SCHEDULER_NOT_RUNNING = "SCHEDULER_NOT_RUNNING"


class ErrorDefinition:
    """错误定义"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details


class ErrorDefinitions:
    """错误定义集合"""
    
    # 通用错误
    UNKNOWN_ERROR = ErrorDefinition(
        ErrorCode.UNKNOWN_ERROR,
        "未知错误，请稍后重试",
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    VALIDATION_ERROR = ErrorDefinition(
        ErrorCode.VALIDATION_ERROR,
        "请求参数验证失败",
        status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    RESOURCE_NOT_FOUND = ErrorDefinition(
        ErrorCode.RESOURCE_NOT_FOUND,
        "请求的资源不存在",
        status.HTTP_404_NOT_FOUND
    )
    RESOURCE_ALREADY_EXISTS = ErrorDefinition(
        ErrorCode.RESOURCE_ALREADY_EXISTS,
        "资源已存在",
        status.HTTP_409_CONFLICT
    )
    RATE_LIMIT_EXCEEDED = ErrorDefinition(
        ErrorCode.RATE_LIMIT_EXCEEDED,
        "请求频率超限，请稍后重试",
        status.HTTP_429_TOO_MANY_REQUESTS
    )
    
    # 认证授权错误
    UNAUTHORIZED = ErrorDefinition(
        ErrorCode.UNAUTHORIZED,
        "未登录或登录已过期",
        status.HTTP_401_UNAUTHORIZED
    )
    TOKEN_EXPIRED = ErrorDefinition(
        ErrorCode.TOKEN_EXPIRED,
        "登录凭证已过期，请重新登录",
        status.HTTP_401_UNAUTHORIZED
    )
    TOKEN_INVALID = ErrorDefinition(
        ErrorCode.TOKEN_INVALID,
        "无效的登录凭证",
        status.HTTP_401_UNAUTHORIZED
    )
    PERMISSION_DENIED = ErrorDefinition(
        ErrorCode.PERMISSION_DENIED,
        "权限不足，无法执行此操作",
        status.HTTP_403_FORBIDDEN
    )
    ACCOUNT_DISABLED = ErrorDefinition(
        ErrorCode.ACCOUNT_DISABLED,
        "账户已被禁用",
        status.HTTP_403_FORBIDDEN
    )
    LOGIN_FAILED = ErrorDefinition(
        ErrorCode.LOGIN_FAILED,
        "用户名或密码错误",
        status.HTTP_401_UNAUTHORIZED
    )
    
    # 用户错误
    USER_NOT_FOUND = ErrorDefinition(
        ErrorCode.USER_NOT_FOUND,
        "用户不存在",
        status.HTTP_404_NOT_FOUND
    )
    USER_ALREADY_EXISTS = ErrorDefinition(
        ErrorCode.USER_ALREADY_EXISTS,
        "用户名已存在",
        status.HTTP_409_CONFLICT
    )
    INVALID_PASSWORD = ErrorDefinition(
        ErrorCode.INVALID_PASSWORD,
        "密码错误",
        status.HTTP_400_BAD_REQUEST
    )
    
    # 实例错误
    INSTANCE_NOT_FOUND = ErrorDefinition(
        ErrorCode.INSTANCE_NOT_FOUND,
        "实例不存在",
        status.HTTP_404_NOT_FOUND
    )
    INSTANCE_CONNECTION_FAILED = ErrorDefinition(
        ErrorCode.INSTANCE_CONNECTION_FAILED,
        "实例连接失败",
        status.HTTP_503_SERVICE_UNAVAILABLE
    )
    DATABASE_NOT_FOUND = ErrorDefinition(
        ErrorCode.DATABASE_NOT_FOUND,
        "数据库不存在",
        status.HTTP_404_NOT_FOUND
    )
    QUERY_EXECUTION_FAILED = ErrorDefinition(
        ErrorCode.QUERY_EXECUTION_FAILED,
        "SQL 执行失败",
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    # 审批错误
    APPROVAL_NOT_FOUND = ErrorDefinition(
        ErrorCode.APPROVAL_NOT_FOUND,
        "审批记录不存在",
        status.HTTP_404_NOT_FOUND
    )
    APPROVAL_ALREADY_PROCESSED = ErrorDefinition(
        ErrorCode.APPROVAL_ALREADY_PROCESSED,
        "该审批已处理，无法重复操作",
        status.HTTP_400_BAD_REQUEST
    )
    APPROVAL_NOT_PENDING = ErrorDefinition(
        ErrorCode.APPROVAL_NOT_PENDING,
        "审批状态不正确",
        status.HTTP_400_BAD_REQUEST
    )
    SQL_RISK_TOO_HIGH = ErrorDefinition(
        ErrorCode.SQL_RISK_TOO_HIGH,
        "SQL 风险等级过高，无法提交",
        status.HTTP_400_BAD_REQUEST
    )
    
    # 系统错误
    CONFIG_NOT_FOUND = ErrorDefinition(
        ErrorCode.CONFIG_NOT_FOUND,
        "配置项不存在",
        status.HTTP_404_NOT_FOUND
    )
    STORAGE_CONNECTION_FAILED = ErrorDefinition(
        ErrorCode.STORAGE_CONNECTION_FAILED,
        "存储服务连接失败",
        status.HTTP_503_SERVICE_UNAVAILABLE
    )
    FILE_NOT_FOUND = ErrorDefinition(
        ErrorCode.FILE_NOT_FOUND,
        "文件不存在",
        status.HTTP_404_NOT_FOUND
    )


class ApiResponse(BaseModel):
    """
    统一 API 响应格式
    
    成功响应：
    {
        "success": true,
        "data": {...},
        "message": "操作成功"
    }
    
    错误响应：
    {
        "success": false,
        "error": {
            "code": "USER_NOT_FOUND",
            "message": "用户不存在",
            "details": "用户ID 999 不存在"
        },
        "request_id": "abc123"
    }
    """
    
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[dict[str, Any]] = None
    request_id: Optional[str] = None
    
    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = "操作成功"
    ) -> "ApiResponse":
        """创建成功响应"""
        from app.utils.structured_logger import get_request_id
        return cls(
            success=True,
            data=data,
            message=message,
            request_id=get_request_id()
        )
    
    @classmethod
    def error(
        cls,
        error_def: ErrorDefinition,
        message: Optional[str] = None,
        details: Optional[str] = None,
        **extra
    ) -> "ApiResponse":
        """创建错误响应"""
        from app.utils.structured_logger import get_request_id
        error_data = {
            "code": error_def.code.value,
            "message": message or error_def.message,
        }
        if details:
            error_data["details"] = details
        if extra:
            error_data["extra"] = extra
        
        return cls(
            success=False,
            error=error_data,
            request_id=get_request_id()
        )
    
    def to_json_response(self, status_code: Optional[int] = None) -> JSONResponse:
        """转换为 FastAPI JSONResponse"""
        return JSONResponse(
            status_code=status_code or status.HTTP_200_OK,
            content=self.model_dump(exclude_none=True)
        )


class ApiError(HTTPException):
    """
    API 错误异常
    
    使用示例：
        raise ApiError(ErrorDefinitions.USER_NOT_FOUND, user_id=1)
    """
    
    def __init__(
        self,
        error_def: ErrorDefinition,
        message: Optional[str] = None,
        details: Optional[str] = None,
        **extra
    ):
        self.error_def = error_def
        self.message = message or error_def.message
        self.details = details
        self.extra = extra
        super().__init__(
            status_code=error_def.http_status,
            detail={
                "code": error_def.code.value,
                "message": self.message,
                "details": details,
                **extra
            }
        )


def api_error(
    error_def: ErrorDefinition,
    message: Optional[str] = None,
    details: Optional[str] = None,
    **extra
) -> ApiError:
    """
    创建 API 错误
    
    用法：
        raise api_error(ErrorDefinitions.USER_NOT_FOUND, user_id=1)
    """
    return ApiError(error_def, message, details, **extra)


# ==================== 异常处理器 ====================

async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """API 错误处理器"""
    from app.utils.structured_logger import get_request_id
    
    response = {
        "success": False,
        "error": {
            "code": exc.error_def.code.value,
            "message": exc.message,
        },
        "request_id": get_request_id()
    }
    
    if exc.details:
        response["error"]["details"] = exc.details
    if exc.extra:
        response["error"]["extra"] = exc.extra
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用错误处理器"""
    from app.utils.structured_logger import get_request_id
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.UNKNOWN_ERROR.value,
                "message": "服务器内部错误，请稍后重试"
            },
            "request_id": get_request_id()
        }
    )


# ==================== 导出 ====================

__all__ = [
    "ErrorCode",
    "ErrorDefinition",
    "ErrorDefinitions",
    "ApiResponse",
    "ApiError",
    "api_error",
    "api_error_handler",
    "generic_error_handler",
]
