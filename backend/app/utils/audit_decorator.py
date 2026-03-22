"""
审计日志装饰器

提供审计日志记录能力：
- 函数装饰器自动记录操作
- 异步支持
- 自动提取请求信息
"""
import json
import logging
import functools
import time
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List
from enum import StrEnum

from fastapi import Request
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import AuditLog, User

logger = logging.getLogger(__name__)


class OperationType(StrEnum):
    """操作类型枚举"""
    # 实例管理
    INSTANCE_CREATE = "INSTANCE_CREATE"
    INSTANCE_UPDATE = "INSTANCE_UPDATE"
    INSTANCE_DELETE = "INSTANCE_DELETE"
    INSTANCE_TEST_CONNECTION = "INSTANCE_TEST_CONNECTION"
    
    # 数据库变更
    DB_CHANGE_CREATE = "DB_CHANGE_CREATE"
    DB_CHANGE_UPDATE = "DB_CHANGE_UPDATE"
    DB_CHANGE_DELETE = "DB_CHANGE_DELETE"
    DB_CHANGE_SUBMIT = "DB_CHANGE_SUBMIT"
    DB_CHANGE_WITHDRAW = "DB_CHANGE_WITHDRAW"
    
    # 审批流程
    APPROVAL_APPROVE = "APPROVAL_APPROVE"
    APPROVAL_REJECT = "APPROVAL_REJECT"
    APPROVAL_EXECUTE = "APPROVAL_EXECUTE"
    APPROVAL_SCHEDULE = "APPROVAL_SCHEDULE"
    APPROVAL_CANCEL_SCHEDULE = "APPROVAL_CANCEL_SCHEDULE"
    
    # 监控管理
    MONITOR_SWITCH_ENABLE = "MONITOR_SWITCH_ENABLE"
    MONITOR_SWITCH_DISABLE = "MONITOR_SWITCH_DISABLE"
    MONITOR_THRESHOLD_UPDATE = "MONITOR_THRESHOLD_UPDATE"
    MONITOR_CONFIG_UPDATE = "MONITOR_CONFIG_UPDATE"
    
    # 告警管理
    ALERT_ACKNOWLEDGE = "ALERT_ACKNOWLEDGE"
    ALERT_RESOLVE = "ALERT_RESOLVE"
    ALERT_SUPPRESS = "ALERT_SUPPRESS"
    
    # 脚本执行
    SCRIPT_CREATE = "SCRIPT_CREATE"
    SCRIPT_UPDATE = "SCRIPT_UPDATE"
    SCRIPT_DELETE = "SCRIPT_DELETE"
    SCRIPT_EXECUTE = "SCRIPT_EXECUTE"
    
    # 定时任务
    SCHEDULE_CREATE = "SCHEDULE_CREATE"
    SCHEDULE_UPDATE = "SCHEDULE_UPDATE"
    SCHEDULE_DELETE = "SCHEDULE_DELETE"
    SCHEDULE_ENABLE = "SCHEDULE_ENABLE"
    SCHEDULE_DISABLE = "SCHEDULE_DISABLE"
    SCHEDULE_TRIGGER = "SCHEDULE_TRIGGER"
    
    # 用户管理
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    USER_PASSWORD_RESET = "USER_PASSWORD_RESET"
    
    # 角色权限
    ROLE_CREATE = "ROLE_CREATE"
    ROLE_UPDATE = "ROLE_UPDATE"
    ROLE_DELETE = "ROLE_DELETE"
    ROLE_ASSIGN = "ROLE_ASSIGN"
    
    # 系统配置
    SYSTEM_CONFIG_UPDATE = "SYSTEM_CONFIG_UPDATE"
    SYSTEM_CONFIG_RESET = "SYSTEM_CONFIG_RESET"
    
    # 数据操作
    DATA_EXPORT = "DATA_EXPORT"
    DATA_IMPORT = "DATA_IMPORT"
    DATA_BACKUP = "DATA_BACKUP"
    DATA_RESTORE = "DATA_RESTORE"
    
    # 登录登出
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    
    # 其他
    OTHER = "OTHER"


# 操作类型中文标签映射
OPERATION_TYPE_LABELS = {
    OperationType.INSTANCE_CREATE: "创建实例",
    OperationType.INSTANCE_UPDATE: "更新实例",
    OperationType.INSTANCE_DELETE: "删除实例",
    OperationType.INSTANCE_TEST_CONNECTION: "测试连接",
    
    OperationType.DB_CHANGE_CREATE: "创建变更申请",
    OperationType.DB_CHANGE_UPDATE: "更新变更申请",
    OperationType.DB_CHANGE_DELETE: "删除变更申请",
    OperationType.DB_CHANGE_SUBMIT: "提交变更申请",
    OperationType.DB_CHANGE_WITHDRAW: "撤回变更申请",
    
    OperationType.APPROVAL_APPROVE: "审批通过",
    OperationType.APPROVAL_REJECT: "审批拒绝",
    OperationType.APPROVAL_EXECUTE: "执行变更",
    OperationType.APPROVAL_SCHEDULE: "定时执行",
    OperationType.APPROVAL_CANCEL_SCHEDULE: "取消定时",
    
    OperationType.MONITOR_SWITCH_ENABLE: "启用监控",
    OperationType.MONITOR_SWITCH_DISABLE: "禁用监控",
    OperationType.MONITOR_THRESHOLD_UPDATE: "更新告警阈值",
    OperationType.MONITOR_CONFIG_UPDATE: "更新监控配置",
    
    OperationType.ALERT_ACKNOWLEDGE: "确认告警",
    OperationType.ALERT_RESOLVE: "解决告警",
    OperationType.ALERT_SUPPRESS: "屏蔽告警",
    
    OperationType.SCRIPT_CREATE: "创建脚本",
    OperationType.SCRIPT_UPDATE: "更新脚本",
    OperationType.SCRIPT_DELETE: "删除脚本",
    OperationType.SCRIPT_EXECUTE: "执行脚本",
    
    OperationType.SCHEDULE_CREATE: "创建定时任务",
    OperationType.SCHEDULE_UPDATE: "更新定时任务",
    OperationType.SCHEDULE_DELETE: "删除定时任务",
    OperationType.SCHEDULE_ENABLE: "启用定时任务",
    OperationType.SCHEDULE_DISABLE: "禁用定时任务",
    OperationType.SCHEDULE_TRIGGER: "手动触发定时任务",
    
    OperationType.USER_CREATE: "创建用户",
    OperationType.USER_UPDATE: "更新用户",
    OperationType.USER_DELETE: "删除用户",
    OperationType.USER_PASSWORD_RESET: "重置密码",
    
    OperationType.ROLE_CREATE: "创建角色",
    OperationType.ROLE_UPDATE: "更新角色",
    OperationType.ROLE_DELETE: "删除角色",
    OperationType.ROLE_ASSIGN: "分配角色",
    
    OperationType.SYSTEM_CONFIG_UPDATE: "更新系统配置",
    OperationType.SYSTEM_CONFIG_RESET: "重置系统配置",
    
    OperationType.DATA_EXPORT: "导出数据",
    OperationType.DATA_IMPORT: "导入数据",
    OperationType.DATA_BACKUP: "备份数据",
    OperationType.DATA_RESTORE: "恢复数据",
    
    OperationType.LOGIN: "登录",
    OperationType.LOGOUT: "登出",
    OperationType.LOGIN_FAILED: "登录失败",
    
    OperationType.OTHER: "其他操作",
}


def get_operation_label(operation_type: str) -> str:
    """获取操作类型的中文标签"""
    return OPERATION_TYPE_LABELS.get(OperationType(operation_type), operation_type)


def audit_log(
    operation_type: OperationType,
    get_instance_id: Optional[Callable] = None,
    get_instance_name: Optional[Callable] = None,
    get_environment_id: Optional[Callable] = None,
    get_environment_name: Optional[Callable] = None,
    get_detail: Optional[Callable] = None,
    extract_user: bool = True
):
    """
    审计日志装饰器
    
    用法示例：
    ```python
    @audit_log(
        operation_type=OperationType.INSTANCE_CREATE,
        get_detail=lambda self, request, data: f"创建实例 {data.name}"
    )
    async def create_instance(request: Request, data: InstanceCreate, db: Session = Depends(get_db)):
        ...
    ```
    
    Args:
        operation_type: 操作类型
        get_instance_id: 获取实例ID的函数，参数与被装饰函数相同
        get_instance_name: 获取实例名称的函数
        get_environment_id: 获取环境ID的函数
        get_environment_name: 获取环境名称的函数
        get_detail: 获取操作详情的函数
        extract_user: 是否自动提取用户信息（从 current_user 参数）
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 获取请求信息
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')

            # 初始化审计日志数据
            audit_data = {
                "operation_type": operation_type.value,
                "request_method": None,
                "request_path": None,
                "request_ip": None,
                "request_params": None,
                "user_id": None,
                "username": None,
            }
            
            # 提取请求信息
            if request and isinstance(request, Request):
                audit_data["request_method"] = request.method
                audit_data["request_path"] = str(request.url.path)
                audit_data["request_ip"] = get_client_ip(request)
                
                # 提取请求参数
                try:
                    if request.method in ["POST", "PUT", "PATCH"]:
                        # 注意：读取 body 后需要重新设置，否则后续无法读取
                        body = await request.body()
                        if body:
                            audit_data["request_params"] = body.decode('utf-8')[:2000]
                    elif request.method == "GET":
                        audit_data["request_params"] = str(request.query_params)[:2000]
                except Exception as e:
                    logger.debug(f"提取请求参数失败: {e}")
            
            # 提取用户信息
            if extract_user and current_user:
                if isinstance(current_user, User):
                    audit_data["user_id"] = current_user.id
                    audit_data["username"] = current_user.username
            
            # 调用自定义提取函数
            try:
                if get_instance_id:
                    audit_data["instance_id"] = get_instance_id(*args, **kwargs)
                if get_instance_name:
                    audit_data["instance_name"] = get_instance_name(*args, **kwargs)
                if get_environment_id:
                    audit_data["environment_id"] = get_environment_id(*args, **kwargs)
                if get_environment_name:
                    audit_data["environment_name"] = get_environment_name(*args, **kwargs)
                if get_detail:
                    audit_data["operation_detail"] = get_detail(*args, **kwargs)
            except Exception as e:
                logger.debug(f"提取自定义审计信息失败: {e}")
            
            # 执行原函数
            try:
                result = await func(*args, **kwargs)
                audit_data["response_code"] = 200
                audit_data["response_message"] = "操作成功"
                return result
            except Exception as e:
                audit_data["response_code"] = 500
                audit_data["response_message"] = str(e)[:500]
                raise
            finally:
                # 计算执行耗时
                audit_data["execution_time"] = (time.time() - start_time) * 1000
                
                # 异步写入审计日志
                await write_audit_log(audit_data)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 获取请求信息
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            # 初始化审计日志数据
            audit_data = {
                "operation_type": operation_type.value,
                "request_method": None,
                "request_path": None,
                "request_ip": None,
                "request_params": None,
                "user_id": None,
                "username": None,
            }
            
            # 提取请求信息
            if request and isinstance(request, Request):
                audit_data["request_method"] = request.method
                audit_data["request_path"] = str(request.url.path)
                audit_data["request_ip"] = get_client_ip(request)
            
            # 提取用户信息
            if extract_user and current_user:
                if isinstance(current_user, User):
                    audit_data["user_id"] = current_user.id
                    audit_data["username"] = current_user.username
            
            # 执行原函数
            try:
                result = func(*args, **kwargs)
                audit_data["response_code"] = 200
                audit_data["response_message"] = "操作成功"
                return result
            except Exception as e:
                audit_data["response_code"] = 500
                audit_data["response_message"] = str(e)[:500]
                raise
            finally:
                # 计算执行耗时
                audit_data["execution_time"] = (time.time() - start_time) * 1000
                
                # 同步写入审计日志
                write_audit_log_sync(audit_data)
        
        # 根据函数类型选择包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def write_audit_log(data: dict[str, Any]):
    """
    异步写入审计日志
    
    Args:
        data: 审计日志数据
    """
    try:
        db = SessionLocal()
        try:
            audit_log = AuditLog(
                user_id=data.get("user_id"),
                username=data.get("username"),
                instance_id=data.get("instance_id"),
                instance_name=data.get("instance_name"),
                environment_id=data.get("environment_id"),
                environment_name=data.get("environment_name"),
                operation_type=data.get("operation_type"),
                operation_detail=data.get("operation_detail"),
                request_ip=data.get("request_ip"),
                request_method=data.get("request_method"),
                request_path=data.get("request_path"),
                request_params=data.get("request_params"),
                response_code=data.get("response_code"),
                response_message=data.get("response_message"),
                execution_time=data.get("execution_time"),
            )
            db.add(audit_log)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"写入审计日志失败: {e}")


def write_audit_log_sync(data: dict[str, Any]):
    """
    同步写入审计日志
    
    Args:
        data: 审计日志数据
    """
    try:
        db = SessionLocal()
        try:
            audit_log = AuditLog(
                user_id=data.get("user_id"),
                username=data.get("username"),
                instance_id=data.get("instance_id"),
                instance_name=data.get("instance_name"),
                environment_id=data.get("environment_id"),
                environment_name=data.get("environment_name"),
                operation_type=data.get("operation_type"),
                operation_detail=data.get("operation_detail"),
                request_ip=data.get("request_ip"),
                request_method=data.get("request_method"),
                request_path=data.get("request_path"),
                request_params=data.get("request_params"),
                response_code=data.get("response_code"),
                response_message=data.get("response_message"),
                execution_time=data.get("execution_time"),
            )
            db.add(audit_log)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"写入审计日志失败: {e}")


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实IP
    
    Args:
        request: FastAPI Request 对象
        
    Returns:
        客户端IP地址
    """
    # 尝试从代理头获取
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 可能有多个IP，取第一个
        return forwarded_for.split(",")[0].strip()
    
    # 尝试从其他代理头获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # 从连接获取
    if request.client:
        return request.client.host
    
    return "unknown"


class AuditLogger:
    """
    审计日志记录器
    
    用于在代码中手动记录审计日志
    """
    
    @staticmethod
    async def log(
        operation_type: OperationType,
        user: Optional[User] = None,
        instance_id: Optional[int] = None,
        instance_name: Optional[str] = None,
        environment_id: Optional[int] = None,
        environment_name: Optional[str] = None,
        detail: Optional[str] = None,
        request: Optional[Request] = None,
        response_code: int = 200,
        response_message: str = "操作成功"
    ):
        """
        手动记录审计日志
        
        Args:
            operation_type: 操作类型
            user: 用户对象
            instance_id: 实例ID
            instance_name: 实例名称
            environment_id: 环境ID
            environment_name: 环境名称
            detail: 操作详情
            request: Request 对象
            response_code: 响应码
            response_message: 响应消息
        """
        data = {
            "operation_type": operation_type.value,
            "response_code": response_code,
            "response_message": response_message,
        }
        
        if user:
            data["user_id"] = user.id
            data["username"] = user.username
        
        if instance_id:
            data["instance_id"] = instance_id
        if instance_name:
            data["instance_name"] = instance_name
        if environment_id:
            data["environment_id"] = environment_id
        if environment_name:
            data["environment_name"] = environment_name
        if detail:
            data["operation_detail"] = detail
        
        if request:
            data["request_method"] = request.method
            data["request_path"] = str(request.url.path)
            data["request_ip"] = get_client_ip(request)
        
        await write_audit_log(data)
    
    @staticmethod
    def log_sync(
        operation_type: OperationType,
        user: Optional[User] = None,
        instance_id: Optional[int] = None,
        instance_name: Optional[str] = None,
        environment_id: Optional[int] = None,
        environment_name: Optional[str] = None,
        detail: Optional[str] = None,
        request: Optional[Request] = None,
        response_code: int = 200,
        response_message: str = "操作成功"
    ):
        """
        同步记录审计日志
        """
        data = {
            "operation_type": operation_type.value,
            "response_code": response_code,
            "response_message": response_message,
        }
        
        if user:
            data["user_id"] = user.id
            data["username"] = user.username
        
        if instance_id:
            data["instance_id"] = instance_id
        if instance_name:
            data["instance_name"] = instance_name
        if environment_id:
            data["environment_id"] = environment_id
        if environment_name:
            data["environment_name"] = environment_name
        if detail:
            data["operation_detail"] = detail
        
        if request:
            data["request_method"] = request.method
            data["request_path"] = str(request.url.path)
            data["request_ip"] = get_client_ip(request)
        
        write_audit_log_sync(data)


# 导出
__all__ = [
    'audit_log',
    'AuditLogger',
    'OperationType',
    'get_operation_label',
    'get_client_ip',
]
