"""
数据库连接和会话管理
"""
import os
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def get_database_url():
    """获取数据库URL，支持多种环境变量格式"""
    # 打印所有相关环境变量用于调试
    logger.info("=" * 50)
    logger.info("数据库连接配置调试信息:")
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', '<未设置>')[:50] if os.getenv('DATABASE_URL') else '<未设置>'}")
    logger.info(f"DB_HOST: {os.getenv('DB_HOST', '<未设置>')}")
    logger.info(f"MYSQL_HOST: {os.getenv('MYSQL_HOST', '<未设置>')}")
    logger.info("=" * 50)
    
    # 1. 优先使用平台注入的 DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # 支持 postgres:// 和 postgresql:// 两种格式
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://")
            logger.info(f"转换 postgres:// 为 postgresql://")
        
        # 如果是 PostgreSQL 但没有指定驱动，添加 psycopg2 驱动
        if database_url.startswith("postgresql://") and "postgresql+psycopg2://" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
            logger.info(f"添加 psycopg2 驱动到 PostgreSQL URL")
        
        logger.info(f"使用 DATABASE_URL 环境变量")
        return database_url
    
    # 2. 检查 DB_* 格式环境变量
    db_host = os.getenv("DB_HOST")
    if db_host:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "postgres")
        url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"使用 DB_* 环境变量构建 PostgreSQL URL")
        return url
    
    # 3. 检查 MYSQL_* 格式环境变量（仅当明确设置了 MYSQL_HOST 时使用）
    mysql_host = os.getenv("MYSQL_HOST")
    if mysql_host:
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", "root")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_database = os.getenv("MYSQL_DATABASE", "mysql_platform")
        url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
        logger.info(f"使用 MYSQL_* 环境变量构建 MySQL URL")
        return url
    
    # 4. 没有配置数据库环境变量，抛出错误
    logger.error("未检测到数据库环境变量！请设置 DATABASE_URL、DB_* 或 MYSQL_* 环境变量")
    raise ValueError(
        "数据库配置缺失！请设置以下环境变量之一：\n"
        "  - DATABASE_URL=postgresql://user:pass@host:port/dbname\n"
        "  - DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME\n"
        "  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_DATABASE"
    )

# 获取数据库URL
try:
    DATABASE_URL = get_database_url()
    logger.info(f"最终数据库URL: {DATABASE_URL[:60]}...")
except ValueError as e:
    logger.error(str(e))
    # 使用一个会导致明确错误的默认值，而不是静默地尝试 localhost
    DATABASE_URL = "sqlite:///:memory:"  # 临时使用内存数据库，会在后续操作中失败

# 判断数据库类型
is_postgres = "postgresql" in DATABASE_URL
is_mysql = "mysql" in DATABASE_URL

logger.info(f"数据库类型检测: PostgreSQL={is_postgres}, MySQL={is_mysql}")

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

# PostgreSQL 特定配置  
if is_postgres:
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
