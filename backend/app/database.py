"""
数据库连接和会话管理
"""
import os
import logging

logger = logging.getLogger(__name__)

# 获取数据库URL
def get_database_url():
    """获取数据库URL，支持多种环境变量格式"""
    # 优先使用平台注入的 DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info(f"使用环境变量 DATABASE_URL: {database_url[:30]}...")
        return database_url
    
    # 检查其他可能的数据库环境变量
    db_host = os.getenv("DB_HOST")
    if db_host:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "postgres")
        url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"构建数据库URL from DB_*: {url[:30]}...")
        return url
    
    # 使用 MySQL 配置
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_database = os.getenv("MYSQL_DATABASE", "mysql_platform")
    url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    logger.info(f"使用 MySQL 配置: {url[:30]}...")
    return url

DATABASE_URL = get_database_url()

# 判断数据库类型并选择合适的驱动
is_postgres = DATABASE_URL.startswith("postgresql")
is_mysql = DATABASE_URL.startswith("mysql")

# 如果是 PostgreSQL 但 URL 中没有指定驱动，添加 psycopg2 驱动
if is_postgres and "postgresql://" in DATABASE_URL and "postgresql+psycopg2://" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

logger.info(f"最终数据库URL: {DATABASE_URL[:50]}... (PostgreSQL: {is_postgres}, MySQL: {is_mysql})")

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
