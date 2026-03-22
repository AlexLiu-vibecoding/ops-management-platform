"""
全局异常处理器

提供统一的异常捕获和处理，确保API返回格式一致
"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    应用自定义异常处理器
    
    统一处理所有 AppException 及其子类
    """
    # 记录错误日志
    log_data = {
        "error_code": exc.error_code,
        "message": exc.message,
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code
    }
    
    if exc.status_code >= 500:
        logger.error(f"服务端错误: {log_data}")
    else:
        logger.warning(f"客户端错误: {log_data}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    HTTP 异常处理器
    
    处理 FastAPI/Starlette 的标准 HTTP 异常
    """
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}, 路径: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": str(exc.detail)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    请求验证异常处理器
    
    处理 Pydantic 验证错误，返回详细的错误信息
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"参数验证失败: 路径={request.url.path}, 错误={errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "请求参数验证失败",
            "details": errors
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    SQLAlchemy 异常处理器
    
    统一处理数据库相关异常
    """
    error_msg = str(exc)
    
    # 隐藏敏感信息
    if "password" in error_msg.lower():
        error_msg = "数据库连接错误"
    elif "connection" in error_msg.lower():
        error_msg = "数据库连接失败"
    
    logger.error(f"数据库异常: {type(exc).__name__}, 路径={request.url.path}, 错误={str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DATABASE_ERROR",
            "message": error_msg
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器
    
    兜底处理所有未捕获的异常
    """
    # 记录完整的错误堆栈
    logger.error(
        f"未处理的异常: {type(exc).__name__}, "
        f"路径={request.url.path}, "
        f"方法={request.method}, "
        f"错误={str(exc)}\n"
        f"堆栈:\n{traceback.format_exc()}"
    )
    
    # 生产环境不暴露详细错误信息
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试"
        }
    )


def register_exception_handlers(app):
    """
    注册所有异常处理器
    
    在 FastAPI 应用启动时调用
    """
    # 自定义应用异常
    app.add_exception_handler(AppException, app_exception_handler)
    
    # HTTP 异常
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 参数验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # SQLAlchemy 异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # 通用异常（兜底）
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("异常处理器注册完成")
