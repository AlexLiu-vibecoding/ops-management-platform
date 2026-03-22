"""
应用异常定义

定义应用中使用的所有自定义异常类
"""
from typing import Optional, Any


class AppException(Exception):
    """
    应用异常基类
    
    所有自定义异常都应继承此类
    """
    
    # 默认状态码和错误码
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code or self.status_code
        self.error_code = error_code or self.error_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """转换为字典，用于API响应"""
        result = {
            "error": self.error_code,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        return result


# ==================== 400 客户端错误 ====================

class BadRequestException(AppException):
    """请求参数错误"""
    status_code = 400
    error_code = "BAD_REQUEST"


class ValidationException(AppException):
    """数据验证错误"""
    status_code = 400
    error_code = "VALIDATION_ERROR"


class ResourceNotFoundException(AppException):
    """资源不存在"""
    status_code = 404
    error_code = "NOT_FOUND"


class ResourceConflictException(AppException):
    """资源冲突"""
    status_code = 409
    error_code = "CONFLICT"


# ==================== 401/403 认证授权错误 ====================

class UnauthorizedException(AppException):
    """未认证"""
    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenException(AppException):
    """权限不足"""
    status_code = 403
    error_code = "FORBIDDEN"


class TokenExpiredException(AppException):
    """Token过期"""
    status_code = 401
    error_code = "TOKEN_EXPIRED"


# ==================== 数据库相关错误 ====================

class DatabaseException(AppException):
    """数据库操作错误"""
    status_code = 500
    error_code = "DATABASE_ERROR"


class DatabaseConnectionException(DatabaseException):
    """数据库连接错误"""
    error_code = "DATABASE_CONNECTION_ERROR"


class DatabaseTimeoutException(DatabaseException):
    """数据库超时"""
    status_code = 504
    error_code = "DATABASE_TIMEOUT"


class QueryExecutionException(DatabaseException):
    """SQL执行错误"""
    status_code = 500
    error_code = "QUERY_EXECUTION_ERROR"


# ==================== 实例相关错误 ====================

class InstanceNotFoundException(ResourceNotFoundException):
    """实例不存在"""
    error_code = "INSTANCE_NOT_FOUND"


class InstanceConnectionException(AppException):
    """实例连接失败"""
    status_code = 503
    error_code = "INSTANCE_CONNECTION_FAILED"


class InstanceOfflineException(AppException):
    """实例离线"""
    status_code = 503
    error_code = "INSTANCE_OFFLINE"


# ==================== 审批相关错误 ====================

class ApprovalNotFoundException(ResourceNotFoundException):
    """审批不存在"""
    error_code = "APPROVAL_NOT_FOUND"


class ApprovalStatusException(BadRequestException):
    """审批状态错误"""
    error_code = "APPROVAL_STATUS_ERROR"


class ApprovalPermissionException(ForbiddenException):
    """审批权限错误"""
    error_code = "APPROVAL_PERMISSION_ERROR"


# ==================== 脚本相关错误 ====================

class ScriptNotFoundException(ResourceNotFoundException):
    """脚本不存在"""
    error_code = "SCRIPT_NOT_FOUND"


class ScriptExecutionException(AppException):
    """脚本执行错误"""
    status_code = 500
    error_code = "SCRIPT_EXECUTION_ERROR"


class ScriptTimeoutException(AppException):
    """脚本执行超时"""
    status_code = 504
    error_code = "SCRIPT_TIMEOUT"


# ==================== 存储相关错误 ====================

class StorageException(AppException):
    """存储操作错误"""
    status_code = 500
    error_code = "STORAGE_ERROR"


class FileNotFoundException(ResourceNotFoundException):
    """文件不存在"""
    error_code = "FILE_NOT_FOUND"


class FileTooLargeException(AppException):
    """文件过大"""
    status_code = 413
    error_code = "FILE_TOO_LARGE"


# ==================== 外部服务错误 ====================

class ExternalServiceException(AppException):
    """外部服务错误"""
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"


class DingTalkException(ExternalServiceException):
    """钉钉服务错误"""
    error_code = "DINGTALK_ERROR"


class AIException(ExternalServiceException):
    """AI服务错误"""
    error_code = "AI_SERVICE_ERROR"


# ==================== 配置相关错误 ====================

class ConfigurationException(AppException):
    """配置错误"""
    status_code = 500
    error_code = "CONFIGURATION_ERROR"


class InitializationException(AppException):
    """初始化错误"""
    status_code = 500
    error_code = "INITIALIZATION_ERROR"


# ==================== 业务逻辑错误 ====================

class BusinessException(AppException):
    """业务逻辑错误"""
    status_code = 400
    error_code = "BUSINESS_ERROR"


class RiskLevelException(BusinessException):
    """风险等级过高"""
    error_code = "RISK_LEVEL_TOO_HIGH"


class OperationNotAllowedException(BusinessException):
    """操作不允许"""
    status_code = 403
    error_code = "OPERATION_NOT_ALLOWED"
