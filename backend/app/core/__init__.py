"""
核心模块

包含异常定义、异常处理器等核心功能
"""
from app.core.exceptions import (
    AppException,
    BadRequestException,
    ValidationException,
    ResourceNotFoundException,
    ResourceConflictException,
    UnauthorizedException,
    ForbiddenException,
    TokenExpiredException,
    DatabaseException,
    DatabaseConnectionException,
    DatabaseTimeoutException,
    QueryExecutionException,
    InstanceNotFoundException,
    InstanceConnectionException,
    InstanceOfflineException,
    ApprovalNotFoundException,
    ApprovalStatusException,
    ApprovalPermissionException,
    ScriptNotFoundException,
    ScriptExecutionException,
    ScriptTimeoutException,
    StorageException,
    FileNotFoundException,
    FileTooLargeException,
    ExternalServiceException,
    DingTalkException,
    AIException,
    ConfigurationException,
    InitializationException,
    BusinessException,
    RiskLevelException,
    OperationNotAllowedException,
)
from app.core.handlers import register_exception_handlers

__all__ = [
    # 基础异常
    "AppException",
    
    # 客户端错误
    "BadRequestException",
    "ValidationException",
    "ResourceNotFoundException",
    "ResourceConflictException",
    
    # 认证授权
    "UnauthorizedException",
    "ForbiddenException",
    "TokenExpiredException",
    
    # 数据库
    "DatabaseException",
    "DatabaseConnectionException",
    "DatabaseTimeoutException",
    "QueryExecutionException",
    
    # 实例
    "InstanceNotFoundException",
    "InstanceConnectionException",
    "InstanceOfflineException",
    
    # 审批
    "ApprovalNotFoundException",
    "ApprovalStatusException",
    "ApprovalPermissionException",
    
    # 脚本
    "ScriptNotFoundException",
    "ScriptExecutionException",
    "ScriptTimeoutException",
    
    # 存储
    "StorageException",
    "FileNotFoundException",
    "FileTooLargeException",
    
    # 外部服务
    "ExternalServiceException",
    "DingTalkException",
    "AIException",
    
    # 配置
    "ConfigurationException",
    "InitializationException",
    
    # 业务
    "BusinessException",
    "RiskLevelException",
    "OperationNotAllowedException",
    
    # 处理器
    "register_exception_handlers",
]
