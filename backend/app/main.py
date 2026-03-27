"""
一站式运维平台 - FastAPI主应用
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import time
import logging

# 启动自检
from app.startup_check import run_startup_check
if not run_startup_check():
    print("启动自检失败，服务无法启动！")
    sys.exit(1)

from app.config import settings
from app.database import engine, Base
from app.utils.redis_client import redis_client
from app.services.scheduler import approval_scheduler
from app.services.task_scheduler import task_scheduler
from app.core import register_exception_handlers

# 导入路由
from app.api import auth, users, environments, instances, monitor, dingtalk, approval, sql, performance, slow_query, audit, menu, init, scripts, scheduled_tasks, notification, sql_optimizer, dashboard, redis, storage, system, aws_regions, alerts, monitor_ext, inspection
from app.api import rdb_instances, redis_instances, batch_operations

# 配置日志（统一配置，确保只调用一次）
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True  # 强制覆盖已有配置，防止重复
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting OPS Management Platform...")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/checked")
    except Exception as e:
        logger.error(f"Database table creation failed: {e}")
    
    # 连接Redis
    try:
        await redis_client.connect()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed, some features may not be available: {e}")
    
    # 启动定时任务调度器
    try:
        approval_scheduler.start()
        logger.info("Approval scheduler started successfully")
    except Exception as e:
        logger.error(f"Approval scheduler startup failed: {e}")
    
    # 启动任务调度器
    try:
        task_scheduler.start()
        logger.info("Task scheduler started successfully")
    except Exception as e:
        logger.error(f"Task scheduler startup failed: {e}")
    
    # 初始化默认数据
    await init_default_data()
    
    logger.info("Ops Management Platform started successfully")
    
    yield
    
    # 关闭时
    logger.info("Shutting down Ops Management Platform...")
    approval_scheduler.stop()
    task_scheduler.stop()
    await redis_client.disconnect()
    logger.info("Ops Management Platform shutdown complete")


async def init_dev_instance(db):
    """开发环境：自动创建测试用的 PostgreSQL 实例"""
    import os
    from urllib.parse import urlparse
    from app.models import RDBInstance, Environment, RDBType
    from app.utils.auth import encrypt_instance_password
    
    # 仅在开发环境执行
    if os.getenv("COZE_PROJECT_ENV", "DEV") != "DEV":
        return
    
    # 检查是否已存在开发测试实例
    existing = db.query(RDBInstance).filter(RDBInstance.name == "开发测试实例(PostgreSQL)").first()
    if existing:
        logger.info("Dev test instance already exists, skipping creation")
        return
    
    # 从环境变量获取 PostgreSQL 连接信息
    pg_url = os.getenv("PGDATABASE_URL") or os.getenv("DATABASE_URL")
    if not pg_url:
        logger.info("PostgreSQL connection info not found, skipping dev instance creation")
        return
    
    try:
        parsed = urlparse(pg_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        username = parsed.username or "postgres"
        password = parsed.password or ""
        database = parsed.path.lstrip("/") if parsed.path else "postgres"
        
        # 获取开发环境
        dev_env = db.query(Environment).filter(Environment.code == "development").first()
        
        # 创建实例
        instance = RDBInstance(
            name="开发测试实例(PostgreSQL)",
            db_type=RDBType.POSTGRESQL,
            host=host,
            port=port,
            username=username,
            password_encrypted=encrypt_instance_password(password),
            environment_id=dev_env.id if dev_env else None,
            description=f"开发环境自动创建 - 数据库: {database}",
            status=True
        )
        db.add(instance)
        logger.info(f"Dev environment: auto-creating PostgreSQL test instance - {host}:{port}")
    except Exception as e:
        logger.warning(f"Failed to create dev test instance: {e}")


async def init_default_data():
    """初始化默认数据"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import User, Environment, UserRole, GlobalConfig, DingTalkChannel, SystemInitState
    from app.utils.auth import hash_password
    
    db: Session = SessionLocal()
    try:
        # 检查是否已完成初始化
        init_state = db.query(SystemInitState).filter(
            SystemInitState.step == "system_init",
            SystemInitState.status == "completed"
        ).first()
        
        # 如果系统未初始化，跳过管理员创建（等待配置向导）
        if not init_state:
            logger.info("System not initialized, please complete initialization via setup wizard")
            # 只创建默认环境配置
            if not db.query(Environment).first():
                environments = [
                    Environment(name="开发环境", code="development", color="#52C41A", require_approval=False),
                    Environment(name="测试环境", code="testing", color="#1890FF", require_approval=False),
                    Environment(name="预发环境", code="staging", color="#FA8C16", require_approval=True),
                    Environment(name="生产环境", code="production", color="#FF4D4F", require_approval=True),
                ]
                for env in environments:
                    db.add(env)
                logger.info("Creating default environment configuration")
            db.commit()
            return
        
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
            logger.info("Creating default super admin: admin")
        
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
            logger.info("Creating default environment configuration")
        
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
        
        # 开发环境：自动创建测试用的 PostgreSQL 实例
        await init_dev_instance(db)
        
        db.commit()
        logger.info("Default data initialization complete")
        
    except Exception as e:
        logger.error(f"Default data initialization failed: {e}")
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request middleware"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (time.time() - start_time) * 1000
    
    # Log (exclude frequent requests like health check)
    if request.url.path not in ["/health", "/"]:
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.2f}ms"
        )
    
    return response


# 注册统一异常处理器
register_exception_handlers(app)


# 注册API路由 (v1版本)
app.include_router(init.router, prefix="/api/v1")  # 初始化API放在最前面
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(environments.router, prefix="/api/v1")
app.include_router(instances.router, prefix="/api/v1")  # 实例管理（向后兼容）
app.include_router(rdb_instances.router, prefix="/api/v1")  # RDB 实例管理
app.include_router(redis_instances.router, prefix="/api/v1")  # Redis 实例管理
app.include_router(monitor.router, prefix="/api/v1")
app.include_router(dingtalk.router, prefix="/api/v1")
app.include_router(approval.router, prefix="/api/v1")
app.include_router(sql.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(slow_query.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(menu.router, prefix="/api/v1")
app.include_router(scripts.router, prefix="/api/v1")  # 脚本管理
app.include_router(scheduled_tasks.router, prefix="/api/v1")  # 定时任务
app.include_router(notification.router, prefix="/api/v1")  # 通知管理
app.include_router(sql_optimizer.router, prefix="/api/v1")  # SQL优化器
app.include_router(dashboard.router, prefix="/api/v1")  # 仪表盘
app.include_router(redis.router, prefix="/api/v1")  # Redis管理（旧，保留兼容）
app.include_router(storage.router, prefix="/api/v1")  # 存储管理
app.include_router(system.router, prefix="/api/v1")  # 系统配置
app.include_router(aws_regions.router, prefix="/api/v1")  # AWS区域配置
app.include_router(alerts.router, prefix="/api/v1")  # 告警中心
app.include_router(monitor_ext.router, prefix="/api/v1")  # 监控扩展（主从复制、锁、事务）
app.include_router(inspection.router, prefix="/api/v1")  # 巡检报告
app.include_router(batch_operations.router, prefix="/api/v1")  # 批量操作


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": settings.APP_VERSION}


# API根路径
@app.get("/api")
async def api_root():
    """API根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# 挂载前端静态文件（如果存在）
static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    logger.info(f"前端静态文件已挂载: {static_dir}")


# 前端页面路由（必须在最后）
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """服务前端页面（SPA路由支持）"""
    # 排除API路由
    if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    # 检查静态文件目录是否存在
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
    
    if not static_dir.exists():
        return {"message": "MySQL管理平台 API服务", "docs": "/docs", "version": settings.APP_VERSION}
    
    # 检查是否是静态文件请求
    file_path = static_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # 返回index.html（SPA路由）
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return {"message": "MySQL管理平台 API服务", "docs": "/docs", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
