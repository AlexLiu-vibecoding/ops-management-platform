"""
存储配置
支持本地存储、AWS S3、阿里云 OSS 等多种后端
配置优先级：数据库配置 > 环境变量
"""
from pydantic_settings import BaseSettings
from typing import Optional, Literal
from functools import lru_cache


class StorageSettings(BaseSettings):
    """存储配置"""
    
    # 存储类型: local, s3, oss
    STORAGE_TYPE: str = "local"
    
    # 本地存储配置
    LOCAL_STORAGE_PATH: str = "/app/data/sql_files"
    
    # 文件生命周期（天数）
    SQL_FILE_RETENTION_DAYS: int = 30
    
    # 大文件阈值（字符数），超过此大小存文件
    SQL_FILE_SIZE_THRESHOLD: int = 10000  # 约10KB
    
    # AWS S3 配置
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None  # 用于兼容 S3 的其他服务
    
    # 阿里云 OSS 配置
    OSS_ACCESS_KEY_ID: Optional[str] = None
    OSS_ACCESS_KEY_SECRET: Optional[str] = None
    OSS_ENDPOINT: Optional[str] = None  # 如 oss-cn-hangzhou.aliyuncs.com
    OSS_BUCKET_NAME: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_storage_settings() -> StorageSettings:
    """获取存储配置（缓存）"""
    return StorageSettings()


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
                "oss_bucket_name",
                "oss_endpoint"
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


def get_effective_storage_settings() -> StorageSettings:
    """
    获取有效的存储配置
    
    优先级：数据库配置 > 环境变量
    
    注意：此函数不缓存，每次调用都会查询数据库
    用于运行时动态获取最新配置
    """
    # 获取环境变量配置作为基础
    base_settings = get_storage_settings()
    
    # 从数据库读取配置覆盖
    db_configs = get_storage_settings_from_db()
    
    if not db_configs:
        return base_settings
    
    # 创建新的配置对象，用数据库配置覆盖
    settings_dict = {
        'STORAGE_TYPE': db_configs.get('storage_type', base_settings.STORAGE_TYPE),
        'LOCAL_STORAGE_PATH': db_configs.get('local_storage_path', base_settings.LOCAL_STORAGE_PATH),
        'SQL_FILE_RETENTION_DAYS': int(db_configs.get('sql_file_retention_days', base_settings.SQL_FILE_RETENTION_DAYS)),
        'SQL_FILE_SIZE_THRESHOLD': int(db_configs.get('sql_file_size_threshold', base_settings.SQL_FILE_SIZE_THRESHOLD)),
        'AWS_ACCESS_KEY_ID': base_settings.AWS_ACCESS_KEY_ID,
        'AWS_SECRET_ACCESS_KEY': base_settings.AWS_SECRET_ACCESS_KEY,
        'AWS_REGION': db_configs.get('aws_region', base_settings.AWS_REGION),
        'S3_BUCKET_NAME': db_configs.get('s3_bucket_name', base_settings.S3_BUCKET_NAME),
        'S3_ENDPOINT_URL': db_configs.get('s3_endpoint_url', base_settings.S3_ENDPOINT_URL),
        'OSS_ACCESS_KEY_ID': base_settings.OSS_ACCESS_KEY_ID,
        'OSS_ACCESS_KEY_SECRET': base_settings.OSS_ACCESS_KEY_SECRET,
        'OSS_ENDPOINT': db_configs.get('oss_endpoint', base_settings.OSS_ENDPOINT),
        'OSS_BUCKET_NAME': db_configs.get('oss_bucket_name', base_settings.OSS_BUCKET_NAME),
    }
    
    return StorageSettings(**settings_dict)
