"""
应用配置文件
支持自动生成安全密钥，简化部署流程
"""
import os
import secrets
import string
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


def generate_random_string(length: int = 32, hex: bool = False) -> str:
    """生成随机字符串"""
    if hex:
        return secrets.token_hex(length // 2)
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))


def generate_aes_key() -> str:
    """生成 32 字符的 AES 密钥"""
    return generate_random_string(32)


def ensure_security_keys():
    """
    确保安全密钥已设置，如果使用默认值则自动生成并保存
    """
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    
    # 默认值标识（用于检测是否需要生成）
    default_jwt_key = "your-super-secret-jwt-key-at-least-32-characters"
    default_aes_key = "this-is-aes-key-32-bytes-long!!"
    default_salt = "mysql-platform-salt"
    
    # 从环境变量读取当前值
    jwt_key = os.getenv("JWT_SECRET_KEY", "")
    aes_key = os.getenv("AES_KEY", "")
    salt = os.getenv("PASSWORD_SALT", "")
    
    # 兼容旧的环境变量名
    if not jwt_key:
        jwt_key = os.getenv("SECRET_KEY", "")
    
    # 检查是否需要生成新密钥
    need_generate = []
    
    if not jwt_key or jwt_key == default_jwt_key:
        jwt_key = generate_random_string(64, hex=True)
        need_generate.append(("JWT_SECRET_KEY", jwt_key))
    
    if not aes_key or aes_key == default_aes_key or len(aes_key) != 32:
        aes_key = generate_aes_key()
        need_generate.append(("AES_KEY", aes_key))
    
    if not salt or salt == default_salt:
        salt = generate_random_string(16, hex=True)
        need_generate.append(("PASSWORD_SALT", salt))
    
    # 如果需要生成密钥，保存到 .env 文件
    if need_generate:
        logger.info("=" * 60)
        logger.info("🔐 自动生成安全密钥（首次启动）")
        logger.info("=" * 60)
        
        # 读取现有 .env 内容
        existing_lines = []
        existing_keys = set()
        
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    existing_lines.append(line)
                    if "=" in line and not line.strip().startswith("#"):
                        key = line.split("=")[0].strip()
                        existing_keys.add(key)
        
        # 更新或添加密钥
        new_lines = []
        updated_keys = set()
        
        for line in existing_lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                for new_key, new_value in need_generate:
                    if key == new_key:
                        line = f"{new_key}={new_value}\n"
                        updated_keys.add(new_key)
                        logger.info(f"  ✓ {new_key}: 已自动生成")
                        break
            new_lines.append(line)
        
        # 添加未更新的密钥
        for new_key, new_value in need_generate:
            if new_key not in updated_keys:
                new_lines.append(f"{new_key}={new_value}\n")
                logger.info(f"  ✓ {new_key}: 已自动生成")
        
        # 写入文件
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        logger.info("-" * 60)
        logger.info(f"📁 密钥已保存到: {env_file}")
        logger.info("⚠️  请妥善保管此文件，不要提交到公开仓库！")
        logger.info("=" * 60)
        
        # 更新环境变量
        for new_key, new_value in need_generate:
            os.environ[new_key] = new_value
    
    return jwt_key, aes_key, salt


# 在模块加载时确保密钥存在
_jwt_key, _aes_key, _salt = ensure_security_keys()


def get_database_config():
    """从环境变量解析数据库配置，支持多种格式"""
    # 优先使用 DATABASE_URL（平台标准格式）
    database_url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")
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


class Settings(BaseSettings):
    """应用配置"""
    # 应用基础配置
    APP_NAME: str = "运维管理平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # 项目域名（用于生成审批链接）
    PROJECT_DOMAIN: str = os.getenv("COZE_PROJECT_DOMAIN_DEFAULT", "http://localhost:5000")
    
    # 安全配置（使用自动生成的值）
    SECRET_KEY: str = _jwt_key
    JWT_SECRET_KEY: str = _jwt_key  # 新变量名
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24  # 登录有效期延长到 24 小时
    
    # 密码加密配置（使用自动生成的值）
    PASSWORD_SALT: str = _salt
    AES_KEY: str = _aes_key
    
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
        # 优先使用环境变量中的 DATABASE_URL
        database_url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL")
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
