"""
MySQL管理平台 - FastAPI主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import logging

from app.config import settings
from app.database import engine, Base
from app.utils.redis_client import redis_client

# 导入路由
from app.api import auth, users, environments, instances, monitor, dingtalk, approval, sql, performance, slow_query, audit

# 配置日志
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("正在启动MySQL管理平台...")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
    
    # 连接Redis
    try:
        await redis_client.connect()
        logger.info("Redis连接成功")
    except Exception as e:
        logger.warning(f"Redis连接失败，部分功能可能不可用: {e}")
    
    # 初始化默认数据
    await init_default_data()
    
    logger.info("MySQL管理平台启动完成")
    
    yield
    
    # 关闭时
    logger.info("正在关闭MySQL管理平台...")
    await redis_client.disconnect()
    logger.info("MySQL管理平台已关闭")


async def init_default_data():
    """初始化默认数据"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import User, Environment, UserRole, GlobalConfig, DingTalkChannel
    from app.utils.auth import hash_password
    
    db: Session = SessionLocal()
    try:
        # 检查是否存在超级管理员
        if not db.query(User).filter(User.role == UserRole.SUPER_ADMIN).first():
            # 创建默认超级管理员
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                real_name="超级管理员",
                email="admin@example.com",
                role=UserRole.SUPER_ADMIN,
                status=True
            )
            db.add(admin)
            logger.info("创建默认超级管理员: admin / admin123")
        
        # 检查是否存在环境
        if not db.query(Environment).first():
            # 创建默认环境
            environments = [
                Environment(name="开发环境", code="development", color="#52C41A", require_approval=False),
                Environment(name="测试环境", code="testing", color="#1890FF", require_approval=False),
                Environment(name="预发环境", code="staging", color="#FA8C16", require_approval=True),
                Environment(name="生产环境", code="production", color="#FF4D4F", require_approval=True),
            ]
            for env in environments:
                db.add(env)
            logger.info("创建默认环境配置")
        
        # 创建默认全局配置
        default_configs = [
            ("monitor_slow_query_enabled", "true", "慢查询监控全局开关"),
            ("monitor_cpu_sql_enabled", "true", "高CPU SQL监控全局开关"),
            ("monitor_performance_enabled", "true", "性能监控全局开关"),
            ("monitor_inspection_enabled", "true", "实例巡检全局开关"),
            ("monitor_collect_interval", "10", "性能监控采集间隔(秒)"),
            ("slow_query_threshold", "1.0", "慢查询阈值(秒)"),
            ("cpu_threshold", "80.0", "CPU使用率告警阈值(%)"),
            ("memory_threshold", "80.0", "内存使用率告警阈值(%)"),
            ("performance_data_retention_days", "30", "性能数据保留天数"),
            ("snapshot_retention_days", "7", "快照保留天数"),
        ]
        
        for key, value, desc in default_configs:
            if not db.query(GlobalConfig).filter(GlobalConfig.config_key == key).first():
                config = GlobalConfig(config_key=key, config_value=value, description=desc)
                db.add(config)
        
        db.commit()
        logger.info("默认数据初始化完成")
        
    except Exception as e:
        logger.error(f"默认数据初始化失败: {e}")
        db.rollback()
    finally:
        db.close()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企业级MySQL数据库管理平台",
    lifespan=lifespan
)


# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = (time.time() - start_time) * 1000
    
    # 记录日志（排除健康检查等频繁请求）
    if request.url.path not in ["/health", "/"]:
        logger.info(
            f"{request.method} {request.url.path} - "
            f"状态码: {response.status_code} - "
            f"耗时: {process_time:.2f}ms"
        )
    
    return response


# 异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数验证错误处理"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "参数验证失败",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误",
            "message": str(exc) if settings.DEBUG else "请稍后重试"
        }
    )


# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(environments.router, prefix="/api")
app.include_router(instances.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(dingtalk.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(sql.router, prefix="/api")
app.include_router(performance.router, prefix="/api")
app.include_router(slow_query.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
