"""
应用配置模块

使用 pydantic-settings 进行统一的配置管理，提供：
- 类型安全的配置读取
- 自动从环境变量加载
- 配置验证
- 敏感信息保护

配置分类：
- app: 应用基础配置（名称、版本、调试模式等）
- database: 数据库配置（PostgreSQL/MySQL）
- redis: Redis 配置
- security: 安全配置（JWT、AES、密码盐值）
- storage: 存储配置（本地/S3/OSS）
- aws: AWS 配置
- notification: 通知配置

使用方式：
```python
from app.config import settings

# 获取数据库 URL
db_url = settings.database.url

# 获取 JWT 密钥
jwt_key = settings.security.get_jwt_secret_key()

# 兼容旧代码
db_url = settings.DATABASE_URL  # 等同于 settings.database.url
```

环境变量命名规范：
- 应用配置: APP_NAME, APP_DEBUG, APP_ENV
- 数据库配置: DATABASE_URL 或 PGHOST/PGUSER/PGPASSWORD
- Redis 配置: REDIS_URL 或 REDIS_HOST/REDIS_PASSWORD
- 安全配置: JWT_SECRET_KEY, AES_KEY, PASSWORD_SALT
- 存储配置: STORAGE_TYPE, STORAGE_LOCAL_PATH
- AWS 配置: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
"""

from functools import lru_cache

from app.config.core import (
    Settings,
    AppSettings,
    DatabaseSettings,
    RedisSettings,
    SecuritySettings,
    StorageSettings,
    AWSSettings,
    NotificationSettings,
)


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例，缓存）
    
    Returns:
        Settings 实例
    """
    return Settings()


# 全局配置实例
settings = get_settings()


# 导出
__all__ = [
    # 配置类
    "Settings",
    "AppSettings",
    "DatabaseSettings",
    "RedisSettings",
    "SecuritySettings",
    "StorageSettings",
    "AWSSettings",
    "NotificationSettings",
    # 配置实例
    "settings",
    "get_settings",
]
