"""
数据库连接和会话管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 获取数据库URL
def get_database_url():
    """获取数据库URL，支持多种环境变量格式"""
    # 优先使用平台注入的 DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # 构建MySQL连接URL
    from app.config import settings
    return settings.DATABASE_URL

DATABASE_URL = get_database_url()

# 判断数据库类型
is_postgres = DATABASE_URL.startswith("postgresql")
is_mysql = DATABASE_URL.startswith("mysql")

# 创建数据库引擎
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "echo": os.getenv("DEBUG", "false").lower() == "true",
}

# MySQL 特定配置
if is_mysql:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, **engine_kwargs)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
