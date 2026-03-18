"""
应用配置文件
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


def get_database_config():
    """从环境变量解析数据库配置，支持多种格式"""
    # 优先使用 DATABASE_URL（平台标准格式）
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # 解析 DATABASE_URL: postgresql://user:pass@host:port/dbname
        # 或 mysql://user:pass@host:port/dbname
        import re
        match = re.match(r"(?:mysql|postgresql)://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", database_url)
        if match:
            return {
                "user": match.group(1),
                "password": match.group(2),
                "host": match.group(3),
                "port": int(match.group(4)),
                "database": match.group(5)
            }
    
    # 使用 DB_* 格式环境变量
    if os.getenv("DB_HOST"):
        return {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "postgres")
        }
    
    # 使用 MYSQL_* 格式环境变量
    return {
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", "mysql_platform")
    }


def get_redis_config():
    """从环境变量解析Redis配置"""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        import re
        match = re.match(r"redis://(?::([^@]+)@)?([^:]+):(\d+)(?:/(\d+))?", redis_url)
        if match:
            return {
                "password": match.group(1) or "",
                "host": match.group(2),
                "port": int(match.group(3)),
                "db": int(match.group(4)) if match.group(4) else 0
            }
    
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": os.getenv("REDIS_PASSWORD", ""),
        "db": int(os.getenv("REDIS_DB", "0"))
    }


class Settings(BaseSettings):
    """应用配置"""
    # 应用基础配置
    APP_NAME: str = "MySQL管理平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # 项目域名（用于生成审批链接）
    PROJECT_DOMAIN: str = os.getenv("COZE_PROJECT_DOMAIN_DEFAULT", "http://localhost:5000")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 2
    
    # 密码加密配置
    PASSWORD_SALT: str = os.getenv("PASSWORD_SALT", "mysql-platform-salt")
    AES_KEY: str = os.getenv("AES_KEY", "this-is-aes-key-32-bytes-long!!")
    
    # 数据库配置（自动从环境变量解析）
    _db_config = get_database_config()
    MYSQL_HOST: str = _db_config["host"]
    MYSQL_PORT: int = _db_config["port"]
    MYSQL_USER: str = _db_config["user"]
    MYSQL_PASSWORD: str = _db_config["password"]
    MYSQL_DATABASE: str = _db_config["database"]
    
    # Redis配置（自动从环境变量解析）
    _redis_config = get_redis_config()
    REDIS_HOST: str = _redis_config["host"]
    REDIS_PORT: int = _redis_config["port"]
    REDIS_PASSWORD: str = _redis_config["password"]
    REDIS_DB: int = _redis_config["db"]
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["*"]
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # 监控配置
    MONITOR_COLLECT_INTERVAL: int = 10  # 性能监控采集间隔（秒）
    SLOW_QUERY_COLLECT_INTERVAL: int = 300  # 慢查询采集间隔（秒）
    PERFORMANCE_DATA_RETENTION_DAYS: int = 30  # 性能数据保留天数
    SNAPSHOT_RETENTION_DAYS: int = 7  # 快照保留天数
    
    # 审批配置
    APPROVAL_TIMEOUT_HOURS: int = 48  # 审批超时时间（小时）
    
    @property
    def DATABASE_URL(self) -> str:
        """数据库连接URL"""
        import os
        # 优先使用环境变量中的 DATABASE_URL
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # 支持 postgres:// 和 postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://")
            if database_url.startswith("postgresql://") and "postgresql+psycopg2://" not in database_url:
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
            return database_url
        
        # 检查是否使用 DB_* 环境变量（PostgreSQL）
        if os.getenv("DB_HOST"):
            return f"postgresql+psycopg2://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}"
        
        # 默认使用 MySQL 配置
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()


settings = get_settings()
