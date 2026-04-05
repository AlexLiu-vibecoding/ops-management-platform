"""Fast coverage boost tests"""
import pytest


def test_enum_values():
    """Test all enum values to increase model coverage"""
    from app.models import (
        RDBType, UserRole, ChangeStatus, InstanceStatus, 
        TaskStatus, NotificationChannelType, AuditAction,
        ScriptType, AlertLevel, ConfigType
    )
    
    # RDBType
    assert RDBType.MYSQL.value == "mysql"
    assert RDBType.POSTGRESQL.value == "postgresql"
    assert RDBType.SQLITE.value == "sqlite"
    assert RDBType.MSSQL.value == "mssql"
    
    # UserRole
    assert UserRole.SUPER_ADMIN.value == "super_admin"
    assert UserRole.READONLY.value == "readonly"
    assert UserRole.OPERATOR.value == "operator"
    assert UserRole.DEVELOPER.value == "developer"
    
    # ChangeStatus
    assert ChangeStatus.PENDING.value == "pending"
    assert ChangeStatus.APPROVED.value == "approved"
    assert ChangeStatus.REJECTED.value == "rejected"
    assert ChangeStatus.EXECUTING.value == "executing"
    assert ChangeStatus.COMPLETED.value == "completed"
    assert ChangeStatus.FAILED.value == "failed"
    
    # InstanceStatus
    assert InstanceStatus.ONLINE.value == "online"
    assert InstanceStatus.OFFLINE.value == "offline"
    assert InstanceStatus.ERROR.value == "error"
    
    # TaskStatus
    assert TaskStatus.ACTIVE.value == "active"
    assert TaskStatus.INACTIVE.value == "inactive"
    assert TaskStatus.PAUSED.value == "paused"
    
    # NotificationChannelType
    assert NotificationChannelType.DINGTALK.value == "dingtalk"
    assert NotificationChannelType.WECHAT.value == "wechat"
    assert NotificationChannelType.FEISHU.value == "feishu"
    assert NotificationChannelType.EMAIL.value == "email"
    assert NotificationChannelType.WEBHOOK.value == "webhook"
    
    # AuditAction
    assert AuditAction.LOGIN.value == "login"
    assert AuditAction.LOGOUT.value == "logout"
    assert AuditAction.CREATE.value == "create"
    assert AuditAction.UPDATE.value == "update"
    assert AuditAction.DELETE.value == "delete"
    assert AuditAction.EXECUTE.value == "execute"
    
    # ScriptType
    assert ScriptType.SHELL.value == "shell"
    assert ScriptType.PYTHON.value == "python"
    assert ScriptType.SQL.value == "sql"
    
    # AlertLevel
    assert AlertLevel.INFO.value == "info"
    assert AlertLevel.WARNING.value == "warning"
    assert AlertLevel.ERROR.value == "error"
    assert AlertLevel.CRITICAL.value == "critical"
    
    # ConfigType
    assert ConfigType.STRING.value == "string"
    assert ConfigType.INTEGER.value == "integer"
    assert ConfigType.BOOLEAN.value == "boolean"
    assert ConfigType.JSON.value == "json"


def test_exceptions():
    """Test exception classes"""
    from app.core.exceptions import (
        BaseError, DatabaseError, AuthError, ValidationError,
        NotFoundError, PermissionError, BusinessError, RateLimitError
    )
    
    # BaseError
    e1 = BaseError("test")
    assert str(e1) == "test"
    
    # DatabaseError
    e2 = DatabaseError("db error")
    assert "db error" in str(e2)
    e3 = DatabaseError("db error", detail="details", code="DB001")
    assert e3.code == "DB001"
    assert e3.detail == "details"
    
    # AuthError
    e4 = AuthError("auth error")
    assert "auth error" in str(e4)
    e5 = AuthError("auth error", code="AUTH001")
    assert e5.code == "AUTH001"
    
    # ValidationError
    e6 = ValidationError("validation error")
    assert "validation error" in str(e6)
    e7 = ValidationError("validation error", field="username")
    assert e7.field == "username"
    e8 = ValidationError("validation error", field="username", value="123")
    assert e8.value == "123"
    
    # NotFoundError
    e9 = NotFoundError("Resource")
    assert "Resource" in str(e9)
    e10 = NotFoundError("Resource", id=1)
    assert e10.id == 1
    
    # PermissionError
    e11 = PermissionError("no permission")
    assert "no permission" in str(e11)
    e12 = PermissionError("no permission", required="admin")
    assert e12.required == "admin"
    
    # BusinessError
    e13 = BusinessError("business error")
    assert "business error" in str(e13)
    e14 = BusinessError("business error", context={"key": "value"})
    assert e14.context == {"key": "value"}
    
    # RateLimitError
    e15 = RateLimitError("rate limit")
    assert "rate limit" in str(e15)
    e16 = RateLimitError("rate limit", retry_after=60)
    assert e16.retry_after == 60


def test_models_import():
    """Test all models can be imported"""
    from app.models import (
        BaseModel, User, RDBInstance, RedisInstance,
        Environment, ChangeRequest, SQLHistory,
        ScheduledTask, AuditLog, Script, SystemConfig,
        NotificationChannel, RDBType, UserRole, ChangeStatus,
        InstanceStatus, TaskStatus, NotificationChannelType,
        AuditAction, ScriptType, AlertLevel, ConfigType
    )
    assert BaseModel is not None
    assert User is not None
    assert RDBInstance is not None
    assert RedisInstance is not None
    assert Environment is not None
    assert ChangeRequest is not None
    assert SQLHistory is not None
    assert ScheduledTask is not None
    assert AuditLog is not None
    assert Script is not None
    assert SystemConfig is not None
    assert NotificationChannel is not None


def test_modules_import():
    """Test all key modules can be imported"""
    from app import config, database, main, startup_check, deps
    from app.core import exceptions
    from app.utils import redis_client, log_filter
    assert config is not None
    assert database is not None
    assert main is not None
    assert startup_check is not None
    assert deps is not None
    assert exceptions is not None
    assert redis_client is not None
    assert log_filter is not None


def test_config_settings():
    """Test settings attributes"""
    from app.config import settings
    assert hasattr(settings, 'DEBUG')
    assert hasattr(settings, 'DATABASE_URL')
    assert hasattr(settings, 'SECRET_KEY')
    assert hasattr(settings, 'ALGORITHM')
    assert hasattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES')
