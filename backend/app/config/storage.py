"""
存储配置
支持本地存储、AWS S3、阿里云 OSS 等多种后端
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
