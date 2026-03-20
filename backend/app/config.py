"""
应用配置文件
支持自动生成安全密钥，简化部署流程
"""
import os
import logging

# 密钥生成只使用 Python 标准库，无需额外依赖
import secrets
import string

from typing import List
from functools import lru_cache

logger = logging.getLogger(__name__)

# 全局变量存储生成的密钥
_generated_keys = {
    "jwt_secret_key": None,
    "aes_key": None,
    "password_salt": None
}


def generate_random_string(length: int = 32, hex_mode: bool = False) -> str:
    """生成随机字符串（仅使用 Python 标准库）"""
    try:
        if hex_mode:
            return secrets.token_hex(length // 2)
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(length))
    except Exception as e:
        logger.warning(f"生成随机字符串失败: {e}，使用备选方案")
        # 备选方案：使用 os.urandom
        import binascii
        return binascii.hexlify(os.urandom(length // 2)).decode()[:length]


def ensure_security_keys():
    """
    确保安全密钥已设置，如果未设置则自动生成
    仅使用 Python 标准库，无需安装额外依赖
    """
    global _generated_keys
    
    # 如果已经生成过，直接返回
    if _generated_keys["jwt_secret_key"]:
        return _generated_keys
    
    # 默认值标识
    default_jwt_key = "your-super-secret-jwt-key-at-least-32-characters"
    default_aes_key = "this-is-aes-key-32-bytes-long!!"
    default_salt = "mysql-platform-salt"
    
    # 从环境变量读取
    jwt_key = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "")
    aes_key = os.getenv("AES_KEY", "")
    salt = os.getenv("PASSWORD_SALT", "")
    
    # 检查是否需要生成新密钥
    need_generate = []
    
    if not jwt_key or jwt_key == default_jwt_key:
        jwt_key = generate_random_string(64, hex_mode=True)
        need_generate.append(("JWT_SECRET_KEY", jwt_key))
    
    if not aes_key or aes_key == default_aes_key or len(aes_key) != 32:
        aes_key = generate_random_string(32, hex_mode=False)
        need_generate.append(("AES_KEY", aes_key))
    
    if not salt or salt == default_salt:
        salt = generate_random_string(16, hex_mode=True)
        need_generate.append(("PASSWORD_SALT", salt))
    
    # 如果需要生成密钥，保存到 .env 文件
    if need_generate:
        try:
            _save_keys_to_env(need_generate)
        except Exception as e:
            logger.warning(f"保存密钥到 .env 文件失败: {e}，密钥仅在内存中有效")
    
    # 保存到全局变量
    _generated_keys["jwt_secret_key"] = jwt_key
    _generated_keys["aes_key"] = aes_key
    _generated_keys["password_salt"] = salt
    
    return _generated_keys


def _save_keys_to_env(keys_to_save: list):
    """保存密钥到 .env 文件"""
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    
    logger.info("=" * 60)
    logger.info("🔐 自动生成安全密钥（首次启动）")
    logger.info("=" * 60)
    
    # 读取现有 .env 内容
    existing_lines = []
    existing_keys = set()
    
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    existing_lines.append(line)
                    if "=" in line and not line.strip().startswith("#"):
                        key = line.split("=")[0].strip()
                        existing_keys.add(key)
        except Exception as e:
            logger.warning(f"读取 .env 文件失败: {e}")
            existing_lines = []
    
    # 更新或添加密钥
    new_lines = []
    updated_keys = set()
    
    for line in existing_lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            for new_key, new_value in keys_to_save:
                if key == new_key:
                    line = f"{new_key}={new_value}\n"
                    updated_keys.add(new_key)
                    logger.info(f"  ✓ {new_key}: 已自动生成")
                    break
        new_lines.append(line)
    
    # 添加未更新的密钥
    for new_key, new_value in keys_to_save:
        if new_key not in updated_keys:
            new_lines.append(f"{new_key}={new_value}\n")
            logger.info(f"  ✓ {new_key}: 已自动生成")
    
    # 写入文件
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info("-" * 60)
        logger.info(f"📁 密钥已保存到: {env_file}")
        logger.info("⚠️  请妥善保管此文件，不要提交到公开仓库！")
        logger.info("=" * 60)
    except PermissionError:
        logger.warning(f"无权限写入 {env_file}，密钥仅在内存中有效")
    except Exception as e:
        logger.warning(f"写入 .env 文件失败: {e}")


def get_database_config():
    """从环境变量解析数据库配置，支持多种格式"""
    # 优先使用 DATABASE_URL（平台标准格式）
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


def get_settings_class():
    """延迟加载 Settings 类，确保依赖已安装"""
    # 延迟导入 pydantic_settings，避免在依赖未安装时报错
    try:
        from pydantic_settings import BaseSettings
    except ImportError:
        # 如果 pydantic_settings 未安装，使用简单的替代类
        logger.warning("pydantic_settings 未安装，使用简化配置")
        return _SimpleSettings
    
    # 确保密钥已生成
    keys = ensure_security_keys()
    _db_config = get_database_config()
    _redis_config = get_redis_config()
    
    class Settings(BaseSettings):
        """应用配置"""
        # 应用基础配置
        APP_NAME: str = "运维管理平台"
        APP_VERSION: str = "1.0.0"
        DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        
        # 项目域名
        PROJECT_DOMAIN: str = os.getenv("COZE_PROJECT_DOMAIN_DEFAULT", "http://localhost:5000")
        
        # 安全配置（使用自动生成的值）
        SECRET_KEY: str = keys["jwt_secret_key"]
        JWT_SECRET_KEY: str = keys["jwt_secret_key"]
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_HOURS: int = 24
        
        # 密码加密配置
        PASSWORD_SALT: str = keys["password_salt"]
        AES_KEY: str = keys["aes_key"]
        
        # 数据库配置
        MYSQL_HOST: str = _db_config["host"]
        MYSQL_PORT: int = _db_config["port"]
        MYSQL_USER: str = _db_config["user"]
        MYSQL_PASSWORD: str = _db_config["password"]
        MYSQL_DATABASE: str = _db_config["database"]
        
        # Redis配置
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
        MONITOR_COLLECT_INTERVAL: int = 10
        SLOW_QUERY_COLLECT_INTERVAL: int = 300
        PERFORMANCE_DATA_RETENTION_DAYS: int = 30
        SNAPSHOT_RETENTION_DAYS: int = 7
        
        # 审批配置
        APPROVAL_TIMEOUT_HOURS: int = 48
        
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
        
        class Config:
            env_file = ".env"
            case_sensitive = True
    
    return Settings


class _SimpleSettings:
    """简化配置类（pydantic_settings 未安装时使用）"""
    def __init__(self):
        keys = ensure_security_keys()
        _db_config = get_database_config()
        _redis_config = get_redis_config()
        
        self.APP_NAME = "运维管理平台"
        self.APP_VERSION = "1.0.0"
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.PROJECT_DOMAIN = os.getenv("COZE_PROJECT_DOMAIN_DEFAULT", "http://localhost:5000")
        
        self.SECRET_KEY = keys["jwt_secret_key"]
        self.JWT_SECRET_KEY = keys["jwt_secret_key"]
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_HOURS = 24
        
        self.PASSWORD_SALT = keys["password_salt"]
        self.AES_KEY = keys["aes_key"]
        
        self.MYSQL_HOST = _db_config["host"]
        self.MYSQL_PORT = _db_config["port"]
        self.MYSQL_USER = _db_config["user"]
        self.MYSQL_PASSWORD = _db_config["password"]
        self.MYSQL_DATABASE = _db_config["database"]
        
        self.REDIS_HOST = _redis_config["host"]
        self.REDIS_PORT = _redis_config["port"]
        self.REDIS_PASSWORD = _redis_config["password"]
        self.REDIS_DB = _redis_config["db"]
        
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
    SettingsClass = get_settings_class()
    return SettingsClass()


# 创建全局 settings 实例
settings = get_settings()
