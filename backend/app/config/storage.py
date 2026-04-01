"""
存储配置模块

提供文件存储配置，支持：
- 本地存储
- AWS S3
- 阿里云 OSS

配置优先级：
1. 数据库配置（运行时动态）
2. 环境变量配置
3. 默认值

使用方式：
```python
from app.config.storage import get_storage_settings

settings = get_storage_settings()
if settings.TYPE == "s3":
    # 使用 S3 存储
    ...
```
"""
from typing import Optional
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class StorageConfig(BaseSettings):
    """存储运行时配置"""
    
    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        extra="ignore"
    )
    
    # 存储类型: local, s3, oss
    TYPE: str = Field(default="local", description="存储类型")
    
    # 本地存储配置
    LOCAL_PATH: str = Field(
        default="/app/data/sql_files", 
        description="本地存储路径"
    )
    
    # 文件生命周期配置
    FILE_RETENTION_DAYS: int = Field(
        default=30, 
        ge=1, 
        description="文件保留天数"
    )
    
    # 大文件阈值（字符数）
    FILE_SIZE_THRESHOLD: int = Field(
        default=10000000,  # 约10MB
        ge=1000,
        description="大文件阈值(字符数)"
    )
    
    # AWS S3 配置
    S3_BUCKET: Optional[str] = Field(default=None, description="S3 存储桶名称")
    S3_ENDPOINT: Optional[str] = Field(default=None, description="S3 端点URL")
    S3_REGION: Optional[str] = Field(default="us-east-1", description="S3 区域")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 Access Key")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 Secret Key")
    
    # 阿里云 OSS 配置
    OSS_BUCKET: Optional[str] = Field(default=None, description="OSS 存储桶名称")
    OSS_ENDPOINT: Optional[str] = Field(default=None, description="OSS 端点")
    OSS_ACCESS_KEY: Optional[str] = Field(default=None, description="OSS Access Key")
    OSS_SECRET_KEY: Optional[str] = Field(default=None, description="OSS Secret Key")
    
    # ==========================================
    # 向后兼容属性（旧API使用）
    # ==========================================
    
    @computed_field
    @property
    def STORAGE_TYPE(self) -> str:
        """向后兼容：存储类型"""
        return self.TYPE
    
    @computed_field
    @property
    def LOCAL_STORAGE_PATH(self) -> str:
        """向后兼容：本地存储路径"""
        return self.LOCAL_PATH
    
    @computed_field
    @property
    def SQL_FILE_RETENTION_DAYS(self) -> int:
        """向后兼容：文件保留天数"""
        return self.FILE_RETENTION_DAYS
    
    @computed_field
    @property
    def SQL_FILE_SIZE_THRESHOLD(self) -> int:
        """向后兼容：大文件阈值"""
        return self.FILE_SIZE_THRESHOLD
    
    @computed_field
    @property
    def S3_BUCKET_NAME(self) -> Optional[str]:
        """向后兼容：S3 存储桶名称"""
        return self.S3_BUCKET
    
    @computed_field
    @property
    def S3_ENDPOINT_URL(self) -> Optional[str]:
        """向后兼容：S3 端点URL"""
        return self.S3_ENDPOINT
    
    @computed_field
    @property
    def AWS_REGION(self) -> str:
        """向后兼容：AWS 区域"""
        return self.S3_REGION
    
    @computed_field
    @property
    def AWS_ACCESS_KEY_ID(self) -> Optional[str]:
        """向后兼容：AWS Access Key ID"""
        return self.S3_ACCESS_KEY
    
    @computed_field
    @property
    def AWS_SECRET_ACCESS_KEY(self) -> Optional[str]:
        """向后兼容：AWS Secret Access Key"""
        return self.S3_SECRET_KEY
    
    @computed_field
    @property
    def OSS_BUCKET_NAME(self) -> Optional[str]:
        """向后兼容：OSS 存储桶名称"""
        return self.OSS_BUCKET
    
    @computed_field
    @property
    def OSS_ACCESS_KEY_ID(self) -> Optional[str]:
        """向后兼容：OSS Access Key ID"""
        return self.OSS_ACCESS_KEY
    
    @computed_field
    @property
    def OSS_ACCESS_KEY_SECRET(self) -> Optional[str]:
        """向后兼容：OSS Access Key Secret"""
        return self.OSS_SECRET_KEY


@lru_cache()
def get_storage_settings() -> StorageConfig:
    """
    获取存储配置实例（缓存）
    
    Returns:
        StorageConfig 实例
    """
    return StorageConfig()


def get_storage_settings_from_db() -> dict:
    """
    从数据库读取存储配置
    
    Returns:
        配置字典，如果数据库没有配置则返回空字典
    """
    try:
        from app.database import SessionLocal
        from app.models import GlobalConfig
        
        db = SessionLocal()
        try:
            config_keys = [
                "storage_type",
                "sql_file_retention_days", 
                "sql_file_size_threshold",
                "local_storage_path",
                "s3_bucket_name",
                "aws_region",
                "s3_endpoint_url",
                "aws_access_key_id",
                "aws_secret_access_key",
                "oss_bucket_name",
                "oss_endpoint",
                "oss_access_key_id",
                "oss_access_key_secret"
            ]
            
            configs = {}
            for key in config_keys:
                config = db.query(GlobalConfig).filter(
                    GlobalConfig.config_key == key
                ).first()
                if config:
                    configs[key] = config.config_value
            
            return configs
        finally:
            db.close()
    except Exception:
        return {}


def get_effective_storage_settings() -> StorageConfig:
    """
    获取有效的存储配置
    
    优先级：数据库配置 > 环境变量
    
    注意：此函数不缓存，每次调用都会查询数据库
    用于运行时动态获取最新配置
    
    Returns:
        StorageConfig 实例
    """
    # 获取环境变量配置作为基础
    base_settings = get_storage_settings()
    
    # 从数据库读取配置覆盖
    db_configs = get_storage_settings_from_db()
    
    if not db_configs:
        return base_settings
    
    # 创建新的配置对象，用数据库配置覆盖
    settings_dict = {
        'TYPE': db_configs.get('storage_type', base_settings.TYPE),
        'LOCAL_PATH': db_configs.get('local_storage_path', base_settings.LOCAL_PATH),
        'FILE_RETENTION_DAYS': int(db_configs.get('sql_file_retention_days', base_settings.FILE_RETENTION_DAYS)),
        'FILE_SIZE_THRESHOLD': int(db_configs.get('sql_file_size_threshold', base_settings.FILE_SIZE_THRESHOLD)),
        # AWS S3 配置
        'S3_ACCESS_KEY': db_configs.get('aws_access_key_id') or base_settings.S3_ACCESS_KEY,
        'S3_SECRET_KEY': db_configs.get('aws_secret_access_key') or base_settings.S3_SECRET_KEY,
        'S3_REGION': db_configs.get('aws_region', base_settings.S3_REGION),
        'S3_BUCKET': db_configs.get('s3_bucket_name', base_settings.S3_BUCKET),
        'S3_ENDPOINT': db_configs.get('s3_endpoint_url', base_settings.S3_ENDPOINT),
        # 阿里云 OSS 配置
        'OSS_ACCESS_KEY': db_configs.get('oss_access_key_id') or base_settings.OSS_ACCESS_KEY,
        'OSS_SECRET_KEY': db_configs.get('oss_access_key_secret') or base_settings.OSS_SECRET_KEY,
        'OSS_ENDPOINT': db_configs.get('oss_endpoint', base_settings.OSS_ENDPOINT),
        'OSS_BUCKET': db_configs.get('oss_bucket_name', base_settings.OSS_BUCKET),
    }
    
    return StorageConfig(**settings_dict)


# 向后兼容别名
StorageSettings = StorageConfig


# 导出
__all__ = [
    "StorageConfig",
    "StorageSettings",  # 向后兼容
    "get_storage_settings",
    "get_storage_settings_from_db",
    "get_effective_storage_settings",
]
