"""
数据库连接和会话管理
"""
import os
import logging
import sys

# 只创建 logger，不重复配置 basicConfig（由 main.py 统一配置）
logger = logging.getLogger(__name__)

# 尝试从 workload identity 加载环境变量
_env_loaded = False

def _load_env_from_workload_identity():
    """从 workload identity 加载环境变量"""
    global _env_loaded
    if _env_loaded:
        return
    
    try:
        from coze_workload_identity import Client
        client = Client()
        env_vars = client.get_project_env_vars()
        client.close()
        
        for env_var in env_vars:
            if not os.getenv(env_var.key):
                os.environ[env_var.key] = env_var.value
        
        _env_loaded = True
        logger.info("成功从 workload identity 加载环境变量")
    except ImportError:
        logger.info("coze_workload_identity 未安装，跳过")
    except Exception as e:
        logger.warning(f"从 workload identity 加载环境变量失败: {e}")

# 启动时加载环境变量
_load_env_from_workload_identity()


def get_database_url():
    """获取数据库URL，支持多种环境变量格式"""
    # 打印所有相关环境变量用于调试
    logger.info("=" * 50)
    logger.info("数据库连接配置调试信息:")
    logger.info(f"PGDATABASE_URL: {os.getenv('PGDATABASE_URL', '<未设置>')[:60] if os.getenv('PGDATABASE_URL') else '<未设置>'}")
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', '<未设置>')[:50] if os.getenv('DATABASE_URL') else '<未设置>'}")
    logger.info(f"PGHOST: {os.getenv('PGHOST', '<未设置>')}")
    logger.info(f"DB_HOST: {os.getenv('DB_HOST', '<未设置>')}")
    logger.info(f"MYSQL_HOST: {os.getenv('MYSQL_HOST', '<未设置>')}")
    logger.info("=" * 50)
    
    # 1. 优先使用平台注入的 PGDATABASE_URL (火山引擎 PostgreSQL)
    pgdatabase_url = os.getenv("PGDATABASE_URL")
    if pgdatabase_url:
        # 处理 URL 中的参数，添加 psycopg2 驱动
        if pgdatabase_url.startswith("postgresql://"):
            # 如果有查询参数，保留它们
            if "?" in pgdatabase_url:
                base_url, params = pgdatabase_url.split("?", 1)
                url = f"postgresql+psycopg2://{base_url[13:]}?{params}"
            else:
                url = pgdatabase_url.replace("postgresql://", "postgresql+psycopg2://")
        else:
            url = pgdatabase_url
        logger.info("使用 PGDATABASE_URL 环境变量 (平台 PostgreSQL)")
        return url
    
    # 2. 检查 DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # 支持 postgres:// 和 postgresql:// 两种格式
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://")
        
        # 如果是 PostgreSQL 但没有指定驱动，添加 psycopg2 驱动
        if database_url.startswith("postgresql://") and "postgresql+psycopg2://" not in database_url:
            if "?" in database_url:
                base_url, params = database_url.split("?", 1)
                database_url = f"postgresql+psycopg2://{base_url[13:]}?{params}"
            else:
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
        
        logger.info("使用 DATABASE_URL 环境变量")
        return database_url
    
    # 3. 检查 PGHOST 等 PostgreSQL 环境变量（标准 libpg 格式）
    pg_host = os.getenv("PGHOST")
    if pg_host:
        pg_user = os.getenv("PGUSER", "postgres")
        pg_password = os.getenv("PGPASSWORD", "")
        pg_port = os.getenv("PGPORT", "5432")
        pg_database = os.getenv("PGDATABASE", "postgres")
        pg_sslmode = os.getenv("PGSSLMODE", "require")
        
        url = f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}?sslmode={pg_sslmode}"
        logger.info("使用 PGHOST 等 PostgreSQL 环境变量")
        return url
    
    # 4. 检查 DB_* 格式环境变量
    db_host = os.getenv("DB_HOST")
    if db_host:
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "postgres")
        url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info("使用 DB_* 环境变量构建 PostgreSQL URL")
        return url
    
    # 5. 检查 MYSQL_* 格式环境变量（仅当明确设置了 MYSQL_HOST 时使用）
    mysql_host = os.getenv("MYSQL_HOST")
    if mysql_host:
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", "root")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_database = os.getenv("MYSQL_DATABASE", "mysql_platform")
        url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
        logger.info("使用 MYSQL_* 环境变量构建 MySQL URL")
        return url
    
    # 6. 没有配置数据库环境变量，抛出错误
    logger.error("未检测到数据库环境变量！请设置以下环境变量之一：")
    logger.error("  - PGDATABASE_URL (平台 PostgreSQL)")
    logger.error("  - DATABASE_URL")
    logger.error("  - PGHOST, PGUSER, PGPASSWORD, PGPORT, PGDATABASE")
    logger.error("  - DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME")
    logger.error("  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_DATABASE")
    raise ValueError(
        "数据库配置缺失！请设置以下环境变量之一：\n"
        "  - PGDATABASE_URL=postgresql://user:pass@host:port/db\n"
        "  - DATABASE_URL=postgresql://user:pass@host:port/db\n"
        "  - PGHOST, PGUSER, PGPASSWORD, PGPORT, PGDATABASE\n"
        "  - DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME\n"
        "  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_DATABASE"
    )

# 获取数据库URL
try:
    DATABASE_URL = get_database_url()
    logger.info(f"最终数据库URL: {DATABASE_URL}")
except ValueError as e:
    logger.error(str(e))
    # 不再使用 SQLite fallback，直接抛出错误
    raise

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
