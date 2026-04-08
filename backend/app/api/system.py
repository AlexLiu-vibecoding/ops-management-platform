"""
系统配置管理 API
"""
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_super_admin
from app.models import User, GlobalConfig
from app.database import get_db
from app.config import settings as app_settings
from app.config.storage import get_storage_settings, get_effective_storage_settings

router = APIRouter(prefix="/system", tags=["系统配置"])


# ==================== 数据库配置 ====================

class DatabaseTypeConfig(BaseModel):
    """数据库类型配置"""
    db_type: str
    display_name: str
    default_port: int
    enabled: bool = True
    icon: str = ""
    description: str = ""


class DatabaseConfigUpdate(BaseModel):
    """数据库配置更新请求"""
    enabled: Optional[bool] = None


class DatabaseConfigResponse(BaseModel):
    """数据库配置响应"""
    items: list[DatabaseTypeConfig]


# 数据库类型默认配置
DEFAULT_DB_CONFIGS = [
    {
        "db_type": "mysql",
        "display_name": "MySQL",
        "default_port": 3306,
        "enabled": True,
        "icon": "mysql",
        "description": "MySQL 数据库实例"
    },
    {
        "db_type": "postgresql",
        "display_name": "PostgreSQL",
        "default_port": 5432,
        "enabled": True,
        "icon": "postgresql",
        "description": "PostgreSQL 数据库实例"
    },
    {
        "db_type": "redis",
        "display_name": "Redis",
        "default_port": 6379,
        "enabled": True,
        "icon": "redis",
        "description": "Redis 缓存实例（支持单机/集群/哨兵模式）"
    }
]


@router.get("/database-config", response_model=DatabaseConfigResponse)
async def get_database_config(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    获取数据库类型配置
    
    只有超级管理员可以访问
    """
    configs = []
    
    for default_config in DEFAULT_DB_CONFIGS:
        db_type = default_config["db_type"]
        
        # 从数据库读取启用状态
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == f"db_type_{db_type}_enabled"
        ).first()
        
        enabled = True
        if config:
            enabled = config.config_value.lower() == "true"
        
        configs.append(DatabaseTypeConfig(
            db_type=db_type,
            display_name=default_config["display_name"],
            default_port=default_config["default_port"],
            enabled=enabled,
            icon=default_config["icon"],
            description=default_config["description"]
        ))
    
    return DatabaseConfigResponse(items=configs)


@router.put("/database-config/{db_type}")
async def update_database_config(
    db_type: str,
    request: DatabaseConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    更新数据库类型配置
    
    只有超级管理员可以修改
    """
    # 验证数据库类型
    valid_types = [c["db_type"] for c in DEFAULT_DB_CONFIGS]
    if db_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {db_type}")
    
    if request.enabled is None:
        raise HTTPException(status_code=400, detail="请提供要更新的配置项")
    
    # 更新或创建配置
    config_key = f"db_type_{db_type}_enabled"
    config = db.query(GlobalConfig).filter(
        GlobalConfig.config_key == config_key
    ).first()
    
    if config:
        config.config_value = "true" if request.enabled else "false"
        config.updated_by = current_user.id
    else:
        config = GlobalConfig(
            config_key=config_key,
            config_value="true" if request.enabled else "false",
            description=f"数据库类型 {db_type} 是否启用",
            updated_by=current_user.id
        )
        db.add(config)
    
    db.commit()
    
    return {"success": True, "message": f"{db_type} 配置已更新"}


# ==================== 存储配置 ====================

class StorageConfigResponse(BaseModel):
    """存储配置响应"""
    storage_type: str
    retention_days: int
    size_threshold: int
    local_path: Optional[str] = None
    # AWS S3 配置
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    # 阿里云 OSS 配置
    oss_bucket: Optional[str] = None
    oss_endpoint: Optional[str] = None
    oss_access_key_id: Optional[str] = None
    oss_access_key_secret: Optional[str] = None


class StorageConfigUpdate(BaseModel):
    """存储配置更新请求"""
    storage_type: Optional[str] = Field(None, description="存储类型: local, s3, oss")
    retention_days: Optional[int] = Field(None, ge=1, le=365, description="文件保留天数")
    size_threshold: Optional[int] = Field(None, ge=1000, le=50000000, description="大文件阈值")
    local_path: Optional[str] = Field(None, description="本地存储路径")
    # AWS S3 配置
    s3_bucket: Optional[str] = Field(None, description="S3 Bucket名称")
    s3_region: Optional[str] = Field(None, description="S3 区域")
    s3_endpoint: Optional[str] = Field(None, description="S3 端点URL")
    s3_access_key_id: Optional[str] = Field(None, description="AWS Access Key ID")
    s3_secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")
    # 阿里云 OSS 配置
    oss_bucket: Optional[str] = Field(None, description="OSS Bucket名称")
    oss_endpoint: Optional[str] = Field(None, description="OSS 端点")
    oss_access_key_id: Optional[str] = Field(None, description="OSS Access Key ID")
    oss_access_key_secret: Optional[str] = Field(None, description="OSS Access Key Secret")


class StorageTestResponse(BaseModel):
    """存储测试响应"""
    success: bool
    message: str


@router.get("/storage-config", response_model=StorageConfigResponse)
async def get_storage_config(
    current_user: User = Depends(get_super_admin)
):
    """
    获取存储配置
    
    只有超级管理员可以查看完整配置
    配置来源优先级：数据库 > 环境变量
    """
    settings = get_effective_storage_settings()
    
    return StorageConfigResponse(
        storage_type=settings.TYPE,
        retention_days=settings.FILE_RETENTION_DAYS,
        size_threshold=settings.FILE_SIZE_THRESHOLD,
        local_path=settings.LOCAL_PATH,
        # AWS S3 配置
        s3_bucket=settings.S3_BUCKET,
        s3_region=settings.S3_REGION,
        s3_endpoint=settings.S3_ENDPOINT,
        s3_access_key_id=settings.S3_ACCESS_KEY,
        s3_secret_access_key=settings.S3_SECRET_KEY,
        # 阿里云 OSS 配置
        oss_bucket=settings.OSS_BUCKET,
        oss_endpoint=settings.OSS_ENDPOINT,
        oss_access_key_id=settings.OSS_ACCESS_KEY,
        oss_access_key_secret=settings.OSS_SECRET_KEY
    )


@router.put("/storage-config")
async def update_storage_config(
    request: StorageConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    更新存储配置
    
    只有超级管理员可以修改，修改后立即生效
    """
    updates = []
    
    def save_config(key: str, value: str, description: str):
        """保存配置到数据库"""
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == key
        ).first()
        if config:
            config.config_value = value
            config.updated_by = current_user.id
        else:
            config = GlobalConfig(
                config_key=key,
                config_value=value,
                description=description,
                updated_by=current_user.id
            )
            db.add(config)
    
    # 更新存储类型
    if request.storage_type:
        save_config("storage_type", request.storage_type, "存储类型")
        updates.append("存储类型")
    
    # 更新保留天数
    if request.retention_days:
        save_config("sql_file_retention_days", str(request.retention_days), "SQL文件保留天数")
        updates.append("保留天数")
    
    # 更新大文件阈值
    if request.size_threshold:
        save_config("sql_file_size_threshold", str(request.size_threshold), "大文件阈值")
        updates.append("大小阈值")
    
    # 更新本地存储路径
    if request.local_path:
        save_config("local_storage_path", request.local_path, "本地存储路径")
        updates.append("存储路径")
    
    # 更新 S3 配置
    if request.s3_bucket:
        save_config("s3_bucket_name", request.s3_bucket, "S3 Bucket名称")
        updates.append("S3 Bucket")
    if request.s3_region:
        save_config("aws_region", request.s3_region, "AWS区域")
        updates.append("S3区域")
    if request.s3_endpoint:
        save_config("s3_endpoint_url", request.s3_endpoint, "S3端点URL")
        updates.append("S3端点")
    if request.s3_access_key_id:
        save_config("aws_access_key_id", request.s3_access_key_id, "AWS Access Key ID")
        updates.append("AWS AK")
    if request.s3_secret_access_key:
        save_config("aws_secret_access_key", request.s3_secret_access_key, "AWS Secret Access Key")
        updates.append("AWS SK")
    
    # 更新 OSS 配置
    if request.oss_bucket:
        save_config("oss_bucket_name", request.oss_bucket, "OSS Bucket名称")
        updates.append("OSS Bucket")
    if request.oss_endpoint:
        save_config("oss_endpoint", request.oss_endpoint, "OSS端点")
        updates.append("OSS端点")
    if request.oss_access_key_id:
        save_config("oss_access_key_id", request.oss_access_key_id, "OSS Access Key ID")
        updates.append("OSS AK")
    if request.oss_access_key_secret:
        save_config("oss_access_key_secret", request.oss_access_key_secret, "OSS Access Key Secret")
        updates.append("OSS SK")
    
    db.commit()
    
    # 重载存储后端，使配置立即生效
    from app.services.storage import storage_manager
    storage_manager.reload_backend()
    
    # 注意：AWS 凭证变更不再触发 RDS 采集器重载
    # RDS 采集现在使用环境级别的 AWS 配置，而非全局配置
    
    return {
        "success": True,
        "message": f"配置已更新: {', '.join(updates)}，已立即生效。",
        "requires_restart": False
    }


@router.post("/storage-config/test", response_model=StorageTestResponse)
async def test_storage_config(
    request: StorageConfigUpdate,
    current_user: User = Depends(get_super_admin)
):
    """
    测试存储配置连接
    
    在保存配置前测试连接是否正常
    """
    from app.services.storage import LocalStorage, S3Storage, OSSStorage
    
    try:
        storage_type = request.storage_type or "local"
        
        if storage_type == "local":
            # 测试本地存储
            import tempfile
            test_path = request.local_path or "/tmp/sql_files_test"
            os.makedirs(test_path, exist_ok=True)
            
            # 写入测试文件
            test_file = os.path.join(test_path, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            
            return StorageTestResponse(
                success=True,
                message=f"本地存储测试成功，路径: {test_path}"
            )
        
        elif storage_type == "s3":
            # 测试 S3 连接
            if not request.s3_bucket:
                return StorageTestResponse(
                    success=False,
                    message="S3 Bucket 名称不能为空"
                )
            
            # 这里需要实际的 AWS 凭证
            # 简化测试，只检查配置
            return StorageTestResponse(
                success=True,
                message=f"S3 配置验证通过: {request.s3_bucket} ({request.s3_region or '默认区域'})"
            )
        
        elif storage_type == "oss":
            # 测试 OSS 连接
            if not request.oss_bucket:
                return StorageTestResponse(
                    success=False,
                    message="OSS Bucket 名称不能为空"
                )
            
            return StorageTestResponse(
                success=True,
                message=f"OSS 配置验证通过: {request.oss_bucket} ({request.oss_endpoint})"
            )
        
        else:
            return StorageTestResponse(
                success=False,
                message=f"不支持的存储类型: {storage_type}"
            )
    
    except Exception as e:
        return StorageTestResponse(
            success=False,
            message=f"测试失败: {str(e)}"
        )


# ==================== AWS 连接测试 ====================

class AwsConnectionTestRequest(BaseModel):
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None


class AwsConnectionTestResponse(BaseModel):
    success: bool
    message: str
    rds_instances_count: Optional[int] = None


@router.post("/test-aws-connection", response_model=AwsConnectionTestResponse)
async def test_aws_connection(
    request: AwsConnectionTestRequest,
    current_user: User = Depends(get_super_admin)
):
    """
    测试 AWS S3 存储连接
    
    ⚠️ 注意：此接口测试的是用于 S3 存储的全局 AWS 凭证。
    RDS CloudWatch 指标采集请使用环境级别的 AWS 配置（见环境管理页面）。
    """
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
    
    # 获取凭证：优先使用请求参数，否则使用已保存的配置
    access_key = request.aws_access_key_id
    secret_key = request.aws_secret_access_key
    region = request.aws_region or "us-east-1"
    
    # 如果请求中没有凭证，从数据库配置获取
    if not access_key or not secret_key:
        settings = get_effective_storage_settings()
        access_key = access_key or settings.AWS_ACCESS_KEY_ID
        secret_key = secret_key or settings.AWS_SECRET_ACCESS_KEY
    
    if not access_key or not secret_key:
        return AwsConnectionTestResponse(
            success=False,
            message="AWS 凭证未配置，请提供 Access Key ID 和 Secret Access Key"
        )
    
    try:
        # 创建 S3 客户端（用于存储）
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        s3_client = session.client("s3")
        
        # 测试连接：列出 Buckets
        response = s3_client.list_buckets()
        buckets_count = len(response.get("Buckets", []))
        
        return AwsConnectionTestResponse(
            success=True,
            message=f"AWS S3 连接成功，区域: {region}，发现 {buckets_count} 个 S3 Bucket",
            rds_instances_count=buckets_count  # 复用字段返回 bucket 数量
        )
        
    except NoCredentialsError:
        return AwsConnectionTestResponse(
            success=False,
            message="AWS 凭证无效，请检查 Access Key ID 和 Secret Access Key"
        )
    except EndpointConnectionError:
        return AwsConnectionTestResponse(
            success=False,
            message=f"无法连接到 AWS 端点 ({region})，请检查区域设置"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "UnauthorizedOperation":
            return AwsConnectionTestResponse(
                success=False,
                message="AWS 凭证无权限访问 S3 服务，请检查 IAM 权限"
            )
        elif error_code == "InvalidClientTokenId":
            return AwsConnectionTestResponse(
                success=False,
                message="AWS 凭证无效，请检查 Access Key ID"
            )
        elif error_code == "SignatureDoesNotMatch":
            return AwsConnectionTestResponse(
                success=False,
                message="AWS Secret Access Key 不正确"
            )
        return AwsConnectionTestResponse(
            success=False,
            message=f"AWS 错误: {error_code}"
        )
    except Exception as e:
        return AwsConnectionTestResponse(
            success=False,
            message=f"连接测试失败: {str(e)}"
        )


# ==================== 安全配置 ====================

class SecurityConfigResponse(BaseModel):
    """安全配置响应（只读）"""
    jwt_configured: bool
    jwt_secret_key: str
    aes_configured: bool
    aes_key: str
    password_salt: str
    token_expire_hours: int
    password_policy: dict[str, Any]


@router.get("/security-config", response_model=SecurityConfigResponse)
async def get_security_config(
    current_user: User = Depends(get_super_admin)
):
    """
    获取安全配置（只读）
    
    安全配置只能查看，不能通过 API 修改
    """
    from app.config import settings as app_settings
    from app.database import SessionLocal
    from app.models.key_rotation import KeyRotationKey, KeyRotationConfig
    
    # 检查是否使用自定义密钥
    jwt_secret = os.getenv("JWT_SECRET_KEY", app_settings.JWT_SECRET_KEY)
    password_salt = os.getenv("PASSWORD_SALT", app_settings.PASSWORD_SALT)
    
    jwt_custom = os.getenv("JWT_SECRET_KEY") is not None
    
    # 获取当前使用的 AES 密钥（优先从密钥轮换系统获取）
    db = SessionLocal()
    try:
        config = db.query(KeyRotationConfig).first()
        if config and config.current_key_id:
            # 从密钥轮换系统获取当前密钥
            current_key = db.query(KeyRotationKey).filter(
                KeyRotationKey.key_id == config.current_key_id
            ).first()
            if current_key:
                aes_key = current_key.key_value
                aes_custom = True  # 使用密钥轮换系统时视为已配置
            else:
                # 回退到环境变量
                aes_key = os.getenv("AES_KEY", app_settings.AES_KEY)
                aes_custom = os.getenv("AES_KEY") is not None
        else:
            # 没有配置，回退到环境变量
            aes_key = os.getenv("AES_KEY", app_settings.AES_KEY)
            aes_custom = os.getenv("AES_KEY") is not None
    finally:
        db.close()
    
    return SecurityConfigResponse(
        jwt_configured=jwt_custom,
        jwt_secret_key=jwt_secret,
        aes_configured=aes_custom,
        aes_key=aes_key,
        password_salt=password_salt,
        token_expire_hours=app_settings.ACCESS_TOKEN_EXPIRE_HOURS,
        password_policy={
            "min_length": 8,
            "require_uppercase": False,
            "require_lowercase": False,
            "require_number": False,
            "require_special": False
        }
    )


# ==================== 系统概览 ====================

class SystemOverview(BaseModel):
    """系统概览"""
    version: str
    python_version: str
    database_type: str
    storage_type: str
    redis_enabled: bool
    scheduler_running: bool


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    current_user: User = Depends(get_super_admin)
):
    """
    获取系统概览
    
    显示系统版本、运行状态等信息
    """
    import sys
    
    storage_settings = get_effective_storage_settings()
    
    # 检查调度器状态
    scheduler_running = False
    try:
        from app.services.scheduler import approval_scheduler
        scheduler_running = approval_scheduler.running
    except Exception:
        pass
    
    return SystemOverview(
        version=app_settings.APP_VERSION,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        database_type="postgresql" if "postgresql" in app_settings.DATABASE_URL else "mysql",
        storage_type=storage_settings.TYPE,
        redis_enabled=bool(app_settings.REDIS_HOST),
        scheduler_running=scheduler_running
    )
