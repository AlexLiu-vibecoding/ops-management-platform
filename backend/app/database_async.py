"""
异步数据库连接和会话管理

提供异步数据库操作支持，使用 SQLAlchemy 2.0 异步 API

架构设计：
- 同步和异步数据库并存（渐进式迁移）
- 新代码推荐使用异步 API
- 旧代码保持同步 API 兼容

使用方式：
```python
# 异步 API 端点
from app.database_async import get_async_db

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

# 异步 Service
from app.database_async import AsyncSessionLocal

async with AsyncSessionLocal() as session:
    async with session.begin():
        result = await session.execute(select(User))
```

依赖：
- PostgreSQL: asyncpg
- MySQL: aiomysql
"""
import os
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import text
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


def get_async_database_url() -> str:
    """
    获取异步数据库 URL
    
    将同步驱动替换为异步驱动：
    - psycopg2 -> asyncpg
    - pymysql -> aiomysql
    
    Returns:
        异步数据库连接 URL
    """
    # 获取同步 URL
    from app.database import DATABASE_URL
    
    url = DATABASE_URL
    
    # PostgreSQL: psycopg2 -> asyncpg
    if "postgresql+psycopg2://" in url:
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif "postgresql://" in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    # MySQL: pymysql -> aiomysql
    elif "mysql+pymysql://" in url:
        url = url.replace("mysql+pymysql://", "mysql+aiomysql://")
    elif "mysql://" in url:
        url = url.replace("mysql://", "mysql+aiomysql://")
    
    # 处理 asyncpg 不支持的参数
    if "postgresql+asyncpg://" in url and "?" in url:
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 移除 asyncpg 不支持的参数
        unsupported = ['sslmode', 'channel_binding', 'gssencmode', 'target_session_attrs']
        for key in unsupported:
            params.pop(key, None)
        
        # 重建 URL
        new_query = urlencode(params, doseq=True)
        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    
    return url


# 异步数据库 URL
ASYNC_DATABASE_URL = get_async_database_url()

# 判断数据库类型
is_postgres = "postgresql" in ASYNC_DATABASE_URL
is_mysql = "mysql" in ASYNC_DATABASE_URL


def create_async_engine_instance() -> AsyncEngine:
    """
    创建异步数据库引擎
    
    Returns:
        异步数据库引擎
    """
    engine_kwargs = {
        "echo": os.getenv("DEBUG", "false").lower() == "true",
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
    
    # 连接池配置
    if is_postgres:
        # PostgreSQL 推荐 asyncpg
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        # asyncpg 特定配置
        engine_kwargs["connect_args"] = {
            "timeout": 10,
        }
    elif is_mysql:
        # MySQL 使用 aiomysql
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        # aiomysql 特定配置
        engine_kwargs["connect_args"] = {
            "connect_timeout": 10,
        }
    
    return create_async_engine(ASYNC_DATABASE_URL, **engine_kwargs)


# 创建异步引擎
async_engine = create_async_engine_instance()

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（依赖注入）
    
    用于 FastAPI 异步端点：
    ```python
    @router.get("/users")
    async def list_users(db: AsyncSession = Depends(get_async_db)):
        ...
    ```
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_context():
    """
    异步数据库会话上下文管理器
    
    用于后台任务或非 API 场景：
    ```python
    async with get_async_db_context() as db:
        result = await db.execute(select(User))
    ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def test_async_connection() -> bool:
    """
    测试异步数据库连接
    
    Returns:
        连接是否成功
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ 异步数据库连接测试成功")
        return True
    except Exception as e:
        logger.error(f"❌ 异步数据库连接测试失败: {e}")
        return False


async def close_async_engine():
    """
    关闭异步数据库引擎
    
    应用关闭时调用，清理连接池
    """
    await async_engine.dispose()
    logger.info("异步数据库引擎已关闭")


# 导出
__all__ = [
    # 异步引擎和会话
    "async_engine",
    "AsyncSessionLocal",
    # 依赖注入
    "get_async_db",
    "get_async_db_context",
    # 工具函数
    "test_async_connection",
    "close_async_engine",
    # 常量
    "ASYNC_DATABASE_URL",
]
