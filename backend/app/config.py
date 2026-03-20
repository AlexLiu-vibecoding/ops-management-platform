"""
应用配置文件
使用固定默认密钥，简化部署流程
"""
import os
import logging
from typing import List
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================
# 固定的默认安全密钥
# 说明：
# - 开发/测试环境直接使用，开箱即用
# - 生产环境建议在 .env 中自定义密钥
# - 这些密钥是公开的，如果对安全有高要求请务必修改
# ============================================
DEFAULT_JWT_SECRET_KEY = "ops-platform-jwt-secret-key-2024-stable-do-not-change-in-prod"
DEFAULT_AES_KEY = "ops-platform-aes-key-32-characters!!"  # 正好32字符
DEFAULT_PASSWORD_SALT = "ops-platform-salt-2024"


def get_database_config():
    """从环境变量解析数据库配置，支持多种格式"""
    database_url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")
    if database_url:
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
    
    if os.getenv("DB_HOST"):
        return {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "postgres")
        }
    
    return {
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", "ops_platform")
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


class Settings:
    """应用配置 - 使用固定默认密钥，无需用户配置"""
    
    def __init__(self):
        # 应用基础配置
        self.APP_NAME = "运维管理平台"
        self.APP_VERSION = "1.0.0"
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        
        # 项目域名
        self.PROJECT_DOMAIN = os.getenv("COZE_PROJECT_DOMAIN_DEFAULT", "http://localhost:5000")
        
        # 安全配置 - 使用固定默认值或用户自定义值
        self.SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or DEFAULT_JWT_SECRET_KEY
        self.JWT_SECRET_KEY = self.SECRET_KEY
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS = 24
        
        # 密码加密配置 - 使用固定默认值
        self.PASSWORD_SALT = os.getenv("PASSWORD_SALT") or DEFAULT_PASSWORD_SALT
        aes_key = os.getenv("AES_KEY") or DEFAULT_AES_KEY
        # 确保 AES_KEY 正好 32 字符
        if len(aes_key) != 32:
            aes_key = (aes_key + "0" * 32)[:32]
        self.AES_KEY = aes_key
        
        # 数据库配置
        _db_config = get_database_config()
        self.MYSQL_HOST = _db_config["host"]
        self.MYSQL_PORT = _db_config["port"]
        self.MYSQL_USER = _db_config["user"]
        self.MYSQL_PASSWORD = _db_config["password"]
        self.MYSQL_DATABASE = _db_config["database"]
        
        # Redis配置
        _redis_config = get_redis_config()
        self.REDIS_HOST = _redis_config["host"]
        self.REDIS_PORT = _redis_config["port"]
        self.REDIS_PASSWORD = _redis_config["password"]
        self.REDIS_DB = _redis_config["db"]
        
        # 其他配置
        self.CORS_ORIGINS = ["*"]
        self.DEFAULT_PAGE_SIZE = 20
        self.MAX_PAGE_SIZE = 100
        self.MONITOR_COLLECT_INTERVAL = 10
        self.SLOW_QUERY_COLLECT_INTERVAL = 300
        self.PERFORMANCE_DATA_RETENTION_DAYS = 30
        self.SNAPSHOT_RETENTION_DAYS = 7
        self.APPROVAL_TIMEOUT_HOURS = 48
    
    @property
    def DATABASE_URL(self) -> str:
        database_url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://")
            if database_url.startswith("postgresql://") and "postgresql+psycopg2://" not in database_url:
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
            return database_url
        
        if os.getenv("DB_HOST"):
            return f"postgresql+psycopg2://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}"
        
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings():
    """获取配置实例（缓存）"""
    return Settings()


# 全局配置实例
settings = get_settings()
