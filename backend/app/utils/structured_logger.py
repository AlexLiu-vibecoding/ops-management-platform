"""
结构化日志模块

提供统一的 JSON 格式日志输出，支持：
- 请求上下文追踪
- 操作审计日志
- 性能指标记录
- 错误堆栈追踪

使用示例：
```python
from app.utils.structured_logger import get_logger, LogContext

# 获取日志器
logger = get_logger(__name__)

# 基础日志
logger.info("用户登录", user_id=1, username="admin")

# 带上下文的日志
with LogContext(request_id="abc123", user_id=1):
    logger.info("执行操作", action="create_instance")

# 性能日志
logger.performance("数据库查询", duration_ms=150, query_count=5)

# 审计日志
logger.audit("用户创建", action="create", resource="user", resource_id=2)
```
"""
import json
import logging
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from functools import wraps


# 上下文变量，用于请求链路追踪
_request_context: ContextVar[dict[str, Any]] = ContextVar("request_context")


class LogContext:
    """
    日志上下文管理器
    
    用于在请求链路中传递上下文信息
    """
    
    def __init__(self, **kwargs):
        self.new_context = kwargs
        self.old_context = None
    
    def __enter__(self):
        self.old_context = _request_context.get()
        merged = {**self.old_context, **self.new_context}
        _request_context.set(merged)
        return self
    
    def __exit__(self, *args):
        _request_context.set(self.old_context or {})


def get_request_id() -> Optional[str]:
    """获取当前请求ID"""
    return _request_context.get().get("request_id")


def get_current_user_id() -> Optional[int]:
    """获取当前用户ID"""
    return _request_context.get().get("user_id")


class StructuredLogRecord:
    """结构化日志记录"""
    
    def __init__(
        self,
        level: str,
        message: str,
        logger_name: str,
        **extra
    ):
        self.timestamp = datetime.now().isoformat()
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.context = _request_context.get()
        self.extra = extra
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger_name,
            "message": self.message,
        }
        
        # 添加上下文
        if self.context:
            result["context"] = self.context
        
        # 添加额外字段
        if self.extra:
            result["data"] = self.extra
        
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def __init__(self, json_format: bool = True):
        super().__init__()
        self.json_format = json_format
    
    def format(self, record: logging.LogRecord) -> str:
        # 提取额外字段
        extra = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                'message', 'taskName'
            ]:
                extra[key] = value
        
        # 创建结构化记录
        structured = StructuredLogRecord(
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            **extra
        )
        
        # 添加异常信息
        if record.exc_info:
            structured.extra["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }
        
        if self.json_format:
            return structured.to_json()
        else:
            # 人类可读格式
            return self._format_readable(structured)
    
    def _format_readable(self, record: StructuredLogRecord) -> str:
        """格式化为人类可读格式"""
        parts = [
            f"[{record.timestamp}]",
            f"[{record.level:5}]",
            f"[{record.logger_name}]",
            record.message
        ]
        
        if record.context:
            parts.append(f"| ctx={record.context}")
        
        if record.extra:
            parts.append(f"| data={record.extra}")
        
        return " ".join(str(p) for p in parts)


class StructuredLogger:
    """
    结构化日志器
    
    提供便捷的日志方法，支持结构化数据
    """
    
    def __init__(self, name: str, json_format: bool = True):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter(json_format=json_format))
            self._logger.addHandler(handler)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志方法"""
        self._logger.log(level, message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """错误日志"""
        if exc_info:
            kwargs["exc_info"] = sys.exc_info()
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    # ==================== 特殊日志方法 ====================
    
    def performance(self, operation: str, duration_ms: float, **kwargs):
        """
        性能日志
        
        Args:
            operation: 操作名称
            duration_ms: 耗时（毫秒）
        """
        self._log(
            logging.INFO,
            f"[PERF] {operation}",
            performance=True,
            operation=operation,
            duration_ms=round(duration_ms, 2),
            **kwargs
        )
    
    def audit(
        self,
        message: str,
        action: str,
        resource: str,
        resource_id: Optional[Any] = None,
        **kwargs
    ):
        """
        审计日志
        
        Args:
            message: 日志消息
            action: 操作类型 (create/update/delete/execute 等)
            resource: 资源类型 (user/instance/approval 等)
            resource_id: 资源ID
        """
        self._log(
            logging.INFO,
            f"[AUDIT] {message}",
            audit=True,
            action=action,
            resource=resource,
            resource_id=resource_id,
            **kwargs
        )
    
    def api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """
        API 请求日志
        
        Args:
            method: HTTP 方法
            path: 请求路径
            status_code: 响应状态码
            duration_ms: 耗时（毫秒）
        """
        self._log(
            logging.INFO,
            f"[API] {method} {path} - {status_code}",
            api=True,
            http_method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            **kwargs
        )
    
    def security(
        self,
        event: str,
        severity: str = "medium",
        **kwargs
    ):
        """
        安全事件日志
        
        Args:
            event: 事件类型 (login_failed/permission_denied/suspicious_activity 等)
            severity: 严重程度 (low/medium/high/critical)
        """
        self._log(
            logging.WARNING,
            f"[SECURITY] {event}",
            security=True,
            event=event,
            severity=severity,
            **kwargs
        )


# 日志器缓存
_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str, json_format: bool = True) -> StructuredLogger:
    """
    获取结构化日志器
    
    Args:
        name: 日志器名称（通常使用 __name__）
        json_format: 是否使用 JSON 格式
    
    Returns:
        StructuredLogger 实例
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name, json_format=json_format)
    return _loggers[name]


# ==================== 装饰器 ====================

def log_performance(operation: str = None):
    """
    性能日志装饰器
    
    用法：
        @log_performance("数据库查询")
        def query_data():
            ...
    """
    def decorator(func):
        op_name = operation or func.__name__
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.performance(op_name, duration)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.performance(op_name, duration, error=str(e))
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.performance(op_name, duration)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.performance(op_name, duration, error=str(e))
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_audit(action: str, resource: str):
    """
    审计日志装饰器
    
    用法：
        @log_audit(action="create", resource="user")
        def create_user(user_data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            try:
                result = func(*args, **kwargs)
                # 尝试获取资源ID
                resource_id = getattr(result, 'id', None) if result else None
                logger.audit(
                    f"{action} {resource}",
                    action=action,
                    resource=resource,
                    resource_id=resource_id
                )
                return result
            except Exception as e:
                logger.audit(
                    f"{action} {resource} failed",
                    action=action,
                    resource=resource,
                    error=str(e)
                )
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            try:
                result = await func(*args, **kwargs)
                resource_id = getattr(result, 'id', None) if result else None
                logger.audit(
                    f"{action} {resource}",
                    action=action,
                    resource=resource,
                    resource_id=resource_id
                )
                return result
            except Exception as e:
                logger.audit(
                    f"{action} {resource} failed",
                    action=action,
                    resource=resource,
                    error=str(e)
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ==================== FastAPI 中间件 ====================

class RequestLoggingMiddleware:
    """
    请求日志中间件
    
    自动记录所有 API 请求
    """
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("api.request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import uuid
        from datetime import datetime
        
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        method = scope["method"]
        path = scope["path"]
        
        # 设置上下文
        with LogContext(request_id=request_id):
            start_time = time.time()
            
            # 记录请求开始
            self.logger.debug(
                f"Request started: {method} {path}",
                http_method=method,
                path=path
            )
            
            # 包装 send 以捕获状态码
            status_code = 200
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
                
                # 记录请求完成
                duration = (time.time() - start_time) * 1000
                self.logger.api_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration
                )
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                self.logger.error(
                    f"Request failed: {method} {path}",
                    exc_info=True,
                    http_method=method,
                    path=path,
                    duration_ms=round(duration, 2),
                    error=str(e)
                )
                raise


# ==================== 导出 ====================

__all__ = [
    "get_logger",
    "LogContext",
    "StructuredLogger",
    "log_performance",
    "log_audit",
    "RequestLoggingMiddleware",
    "get_request_id",
    "get_current_user_id",
]
