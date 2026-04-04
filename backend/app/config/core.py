"""
核心配置模块

使用 pydantic-settings 进行配置管理：
- 类型安全的配置读取
- 自动从环境变量加载
- 配置验证
- 敏感信息保护

配置优先级：
1. 环境变量（最高优先级）
2. .env 文件
3. 默认值

配置分类：
- AppSettings: 应用基础配置
- DatabaseSettings: 数据库配置
- RedisSettings: Redis 配置
- SecuritySettings: 安全配置
- StorageSettings: 存储配置
- AWSSettings: AWS 配置
- Settings: 统一配置入口
"""
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """应用基础配置"""
    
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        extra="ignore"
    )
    
    # 应用信息
    NAME: str = Field(default="OpsCenter", description="应用名称")
    VERSION: str = Field(default="1.0.0", description="应用版本")
    DESCRIPTION: str = Field(default="运维管理平台", description="应用描述")
    
    # 运行配置
    DEBUG: bool = Field(default=False, description="调试模式")
    ENV: str = Field(default="production", description="运行环境: development/staging/production")
    
    # 项目域名
    PROJECT_DOMAIN: Optional[str] = Field(
        default=None,
        description="项目域名，用于生成回调URL等"
    )
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = Field(default=20, ge=1, le=100, description="默认分页大小")
    MAX_PAGE_SIZE: int = Field(default=100, ge=1, le=1000, description="最大分页大小")
    
    # 监控配置
    MONITOR_COLLECT_INTERVAL: int = Field(default=60, ge=10, description="监控数据采集间隔(秒)")
    SLOW_QUERY_COLLECT_INTERVAL: int = Field(default=300, ge=60, description="慢查询采集间隔(秒)")
    PERFORMANCE_DATA_RETENTION_DAYS: int = Field(default=30, ge=1, description="性能数据保留天数")
    SNAPSHOT_RETENTION_DAYS: int = Field(default=7, ge=1, description="快照保留天数")
    
    # 审批配置
    APPROVAL_TIMEOUT_HOURS: int = Field(default=48, ge=1, description="审批超时时间(小时)")


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # PostgreSQL 连接 URL（优先）
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="PostgreSQL 连接 URL，格式: postgresql://user:pass@host:port/db"
    )
    
    # PostgreSQL 分离配置
    PGHOST: Optional[str] = Field(default=None, description="PostgreSQL 主机")
    PGPORT: int = Field(default=5432, description="PostgreSQL 端口")
    PGUSER: Optional[str] = Field(default=None, description="PostgreSQL 用户名")
    PGPASSWORD: Optional[str] = Field(default=None, description="PostgreSQL 密码")
    PGDATABASE: Optional[str] = Field(default=None, description="PostgreSQL 数据库名")
    
    # MySQL 分离配置（兼容）
    MYSQL_HOST: Optional[str] = Field(default=None, description="MySQL 主机")
    MYSQL_PORT: int = Field(default=3306, description="MySQL 端口")
    MYSQL_USER: Optional[str] = Field(default=None, description="MySQL 用户名")
    MYSQL_PASSWORD: Optional[str] = Field(default=None, description="MySQL 密码")
    MYSQL_DATABASE: Optional[str] = Field(default=None, description="MySQL 数据库名")
    
    # 连接池配置
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, description="连接池最大溢出数")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="连接池超时时间(秒)")
    DB_POOL_RECYCLE: int = Field(default=3600, ge=60, description="连接回收时间(秒)")
    
    @property
    def url(self) -> str:
        """
        获取数据库连接 URL
        
        优先级：
        1. DATABASE_URL 环境变量
        2. PostgreSQL 分离配置 (PGHOST, PGUSER 等)
        3. MySQL 分离配置 (MYSQL_HOST, MYSQL_USER 等)
        
        Returns:
            数据库连接 URL
        """
        # 优先使用 DATABASE_URL
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # 标准化 PostgreSQL URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://")
            if url.startswith("postgresql://") and "postgresql+psycopg2://" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://")
            return url
        
        # PostgreSQL 分离配置
        if self.PGHOST and self.PGUSER:
            password = self.PGPASSWORD or ""
            return f"postgresql+psycopg2://{self.PGUSER}:{password}@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE or 'postgres'}"
        
        # MySQL 分离配置
        if self.MYSQL_HOST and self.MYSQL_USER:
            password = self.MYSQL_PASSWORD or ""
            db = self.MYSQL_DATABASE or "ops_platform"
            return f"mysql+pymysql://{self.MYSQL_USER}:{password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{db}"
        
        # 默认 SQLite（开发用）
        return "sqlite:///./ops_platform.db"


class RedisSettings(BaseSettings):
    """Redis 配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # Redis 连接 URL（优先）
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis 连接 URL，格式: redis://[:password@]host:port/db"
    )
    
    # 分离配置
    REDIS_HOST: str = Field(default="localhost", description="Redis 主机")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535, description="Redis 端口")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis 密码")
    REDIS_DB: int = Field(default=0, ge=0, le=15, description="Redis 数据库索引")
    
    # 连接池配置
    REDIS_POOL_SIZE: int = Field(default=10, ge=1, description="Redis 连接池大小")
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1, description="Redis Socket 超时(秒)")
    
    @property
    def url(self) -> str:
        """
        获取 Redis 连接 URL
        
        Returns:
            Redis 连接 URL
        """
        if self.REDIS_URL:
            return self.REDIS_URL
        
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class SecuritySettings(BaseSettings):
    """
    安全配置
    
    重要：生产环境必须设置以下配置：
    - JWT_SECRET_KEY: JWT 签名密钥
    - AES_KEY: 数据加密密钥（必须32字符）
    - PASSWORD_SALT: 密码哈希盐值
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # JWT 配置
    JWT_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="JWT 签名密钥（生产环境必须设置）"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 签名算法")
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = Field(
        default=24,
        ge=1,
        le=168,  # 最长7天
        description="访问令牌过期时间(小时)"
    )
    
    # 数据加密配置
    AES_KEY: Optional[str] = Field(
        default=None,
        description="AES 加密密钥（必须32字符）"
    )
    
    # 密码哈希配置
    PASSWORD_SALT: Optional[str] = Field(
        default=None,
        description="密码哈希盐值"
    )
    
    # 会话配置
    SESSION_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24小时
        ge=1,
        description="会话过期时间(分钟)"
    )
    
    @field_validator("AES_KEY")
    @classmethod
    def validate_aes_key(cls, v: Optional[str]) -> Optional[str]:
        """验证 AES 密钥长度"""
        if v is not None and len(v) != 32:
            raise ValueError("AES_KEY 必须是 32 个字符")
        return v
    
    def get_jwt_secret_key(self) -> str:
        """
        获取 JWT 密钥
        
        生产环境检查：如果未设置，发出警告
        
        Returns:
            JWT 密钥
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        
        # 开发环境使用默认密钥（警告）
        logger.warning(
            "⚠️  JWT_SECRET_KEY 未设置，使用开发默认密钥。"
            "生产环境请设置 JWT_SECRET_KEY 环境变量！"
        )
        return "dev-jwt-secret-key-please-change-in-production"
    
    def get_aes_key(self) -> str:
        """
        获取 AES 密钥
        
        Returns:
            32字符的 AES 密钥
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if self.AES_KEY:
            return self.AES_KEY
        
        # 开发环境使用默认密钥（警告）
        logger.warning(
            "⚠️  AES_KEY 未设置，使用开发默认密钥。"
            "生产环境请设置 AES_KEY 环境变量（32字符）！"
        )
        return "dev-aes-key-32-characters-please!"
    
    def get_password_salt(self) -> str:
        """
        获取密码盐值
        
        Returns:
            密码盐值
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if self.PASSWORD_SALT:
            return self.PASSWORD_SALT
        
        logger.warning(
            "⚠️  PASSWORD_SALT 未设置，使用开发默认盐值。"
            "生产环境请设置 PASSWORD_SALT 环境变量！"
        )
        return "dev-password-salt"


class StorageSettings(BaseSettings):
    """存储配置"""
    
    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        extra="ignore"
    )
    
    # 存储类型
    TYPE: str = Field(
        default="local",
        description="存储类型: local, s3, oss"
    )
    
    # 本地存储配置
    LOCAL_PATH: str = Field(
        default="/app/data/sql_files",
        description="本地存储路径"
    )
    
    # 文件生命周期
    FILE_RETENTION_DAYS: int = Field(
        default=30,
        ge=1,
        description="文件保留天数"
    )
    
    # 大文件阈值
    FILE_SIZE_THRESHOLD: int = Field(
        default=10000000,  # 10MB
        ge=1000,
        description="大文件阈值(字符数)"
    )
    
    # S3 兼容存储配置
    S3_BUCKET: Optional[str] = Field(default=None, description="S3 存储桶名称")
    S3_ENDPOINT: Optional[str] = Field(default=None, description="S3 端点URL")
    S3_REGION: Optional[str] = Field(default=None, description="S3 区域")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 Access Key")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 Secret Key")
    
    # 阿里云 OSS 配置
    OSS_BUCKET: Optional[str] = Field(default=None, description="OSS 存储桶名称")
    OSS_ENDPOINT: Optional[str] = Field(default=None, description="OSS 端点")
    OSS_ACCESS_KEY: Optional[str] = Field(default=None, description="OSS Access Key")
    OSS_SECRET_KEY: Optional[str] = Field(default=None, description="OSS Secret Key")


class AWSSettings(BaseSettings):
    """AWS 配置"""
    
    model_config = SettingsConfigDict(
        env_prefix="AWS_",
        env_file=".env",
        extra="ignore"
    )
    
    # AWS 凭证
    ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key ID")
    SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    REGION: str = Field(default="us-east-1", description="AWS 区域")
    
    # RDS 配置
    RDS_ENABLED: bool = Field(default=False, description="是否启用 RDS 集成")
    
    @property
    def is_configured(self) -> bool:
        """检查 AWS 是否已配置"""
        return bool(self.ACCESS_KEY_ID and self.SECRET_ACCESS_KEY)


class NotificationSettings(BaseSettings):
    """通知配置"""
    
    model_config = SettingsConfigDict(
        env_prefix="NOTIFICATION_",
        env_file=".env",
        extra="ignore"
    )
    
    # 钉钉配置
    DINGTALK_ENABLED: bool = Field(default=False, description="是否启用钉钉通知")
    DINGTALK_WEBHOOK: Optional[str] = Field(default=None, description="钉钉机器人 Webhook URL")
    DINGTALK_SECRET: Optional[str] = Field(default=None, description="钉钉机器人签名密钥")
    
    # 邮件配置
    EMAIL_ENABLED: bool = Field(default=False, description="是否启用邮件通知")
    EMAIL_SMTP_HOST: Optional[str] = Field(default=None, description="SMTP 服务器地址")
    EMAIL_SMTP_PORT: int = Field(default=587, description="SMTP 端口")
    EMAIL_SMTP_USER: Optional[str] = Field(default=None, description="SMTP 用户名")
    EMAIL_SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP 密码")
    EMAIL_FROM: Optional[str] = Field(default=None, description="发件人地址")


class Settings(BaseSettings):
    """
    统一配置入口
    
    使用方式：
    ```python
    from app.config import settings
    
    # 获取数据库 URL
    db_url = settings.database.url
    
    # 获取 JWT 密钥
    jwt_key = settings.security.get_jwt_secret_key()
    ```
    
    环境变量命名规范：
    - 应用配置: APP_NAME, APP_DEBUG
    - 数据库配置: DATABASE_URL, PGHOST, MYSQL_HOST
    - Redis 配置: REDIS_URL, REDIS_HOST
    - 安全配置: JWT_SECRET_KEY, AES_KEY
    - 存储配置: STORAGE_TYPE, STORAGE_LOCAL_PATH
    - AWS 配置: AWS_ACCESS_KEY_ID, AWS_REGION
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )
    
    # 子配置
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)
    
    # 兼容旧配置的属性
    @property
    def APP_NAME(self) -> str:
        """兼容旧代码"""
        return self.app.NAME
    
    @property
    def APP_VERSION(self) -> str:
        """兼容旧代码"""
        return self.app.VERSION
    
    @property
    def APP_ENV(self) -> str:
        """兼容旧代码"""
        return self.app.ENV
    
    @property
    def SECRET_KEY(self) -> str:
        """兼容旧代码"""
        return self.security.get_jwt_secret_key()
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        """兼容旧代码"""
        return self.security.get_jwt_secret_key()
    
    @property
    def ALGORITHM(self) -> str:
        """兼容旧代码"""
        return self.security.JWT_ALGORITHM
    
    @property
    def ACCESS_TOKEN_EXPIRE_HOURS(self) -> int:
        """兼容旧代码"""
        return self.security.JWT_ACCESS_TOKEN_EXPIRE_HOURS
    
    @property
    def AES_KEY(self) -> str:
        """兼容旧代码"""
        return self.security.get_aes_key()
    
    @property
    def PASSWORD_SALT(self) -> str:
        """兼容旧代码"""
        return self.security.get_password_salt()
    
    @property
    def DATABASE_URL(self) -> str:
        """兼容旧代码"""
        return self.database.url
    
    @property
    def REDIS_URL(self) -> str:
        """兼容旧代码"""
        return self.redis.url
    
    @property
    def REDIS_HOST(self) -> str:
        """兼容旧代码"""
        return self.redis.REDIS_HOST
    
    @property
    def REDIS_PORT(self) -> int:
        """兼容旧代码"""
        return self.redis.REDIS_PORT
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        """兼容旧代码"""
        return self.redis.REDIS_PASSWORD
    
    @property
    def REDIS_DB(self) -> int:
        """兼容旧代码"""
        return self.redis.REDIS_DB
    
    @property
    def PROJECT_DOMAIN(self) -> Optional[str]:
        """兼容旧代码"""
        return self.app.PROJECT_DOMAIN
    
    @property
    def DEBUG(self) -> bool:
        """兼容旧代码"""
        return self.app.DEBUG
    
    def check_production_config(self) -> list[str]:
        """
        检查生产环境配置是否完整
        
        Returns:
            缺失或问题的配置列表
        """
        issues = []
        
        if self.app.ENV == "production":
            # 检查安全配置
            if not self.security.JWT_SECRET_KEY:
                issues.append("JWT_SECRET_KEY 未设置")
            if not self.security.AES_KEY:
                issues.append("AES_KEY 未设置")
            if not self.security.PASSWORD_SALT:
                issues.append("PASSWORD_SALT 未设置")
            
            # 检查数据库配置
            if not self.database.url or self.database.url.startswith("sqlite"):
                issues.append("生产环境不应使用 SQLite 数据库")
            
            # 检查 Redis 配置
            if not self.redis.REDIS_URL and self.redis.REDIS_HOST == "localhost":
                issues.append("生产环境建议配置 Redis")
        
        return issues
