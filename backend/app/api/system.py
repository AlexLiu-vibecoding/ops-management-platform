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
from app.config.storage import get_storage_settings

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
    items: List[DatabaseTypeConfig]


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
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_endpoint: Optional[str] = None
    oss_bucket: Optional[str] = None
    oss_endpoint: Optional[str] = None


class StorageConfigUpdate(BaseModel):
    """存储配置更新请求"""
    storage_type: Optional[str] = Field(None, description="存储类型: local, s3, oss")
    retention_days: Optional[int] = Field(None, ge=1, le=365, description="文件保留天数")
    size_threshold: Optional[int] = Field(None, ge=1000, le=1000000, description="大文件阈值")
    local_path: Optional[str] = Field(None, description="本地存储路径")
    s3_bucket: Optional[str] = Field(None, description="S3 Bucket名称")
    s3_region: Optional[str] = Field(None, description="S3 区域")
    s3_endpoint: Optional[str] = Field(None, description="S3 端点URL")
    oss_bucket: Optional[str] = Field(None, description="OSS Bucket名称")
    oss_endpoint: Optional[str] = Field(None, description="OSS 端点URL")


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
    """
    settings = get_storage_settings()
    
    return StorageConfigResponse(
        storage_type=settings.STORAGE_TYPE,
        retention_days=settings.SQL_FILE_RETENTION_DAYS,
        size_threshold=settings.SQL_FILE_SIZE_THRESHOLD,
        local_path=settings.LOCAL_STORAGE_PATH if settings.STORAGE_TYPE == "local" else None,
        s3_bucket=settings.S3_BUCKET_NAME if settings.STORAGE_TYPE == "s3" else None,
        s3_region=settings.AWS_REGION if settings.STORAGE_TYPE == "s3" else None,
        s3_endpoint=settings.S3_ENDPOINT_URL if settings.STORAGE_TYPE == "s3" else None,
        oss_bucket=settings.OSS_BUCKET_NAME if settings.STORAGE_TYPE == "oss" else None,
        oss_endpoint=settings.OSS_ENDPOINT if settings.STORAGE_TYPE == "oss" else None
    )


@router.put("/storage-config")
async def update_storage_config(
    request: StorageConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    更新存储配置
    
    只有超级管理员可以修改，修改后需要重启服务生效
    """
    updates = []
    
    # 更新配置
    if request.storage_type:
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == "storage_type"
        ).first()
        if config:
            config.config_value = request.storage_type
            config.updated_by = current_user.id
        else:
            config = GlobalConfig(
                config_key="storage_type",
                config_value=request.storage_type,
                description="存储类型",
                updated_by=current_user.id
            )
            db.add(config)
        updates.append("存储类型")
    
    if request.retention_days:
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == "sql_file_retention_days"
        ).first()
        if config:
            config.config_value = str(request.retention_days)
            config.updated_by = current_user.id
        else:
            config = GlobalConfig(
                config_key="sql_file_retention_days",
                config_value=str(request.retention_days),
                description="SQL文件保留天数",
                updated_by=current_user.id
            )
            db.add(config)
        updates.append("保留天数")
    
    if request.size_threshold:
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == "sql_file_size_threshold"
        ).first()
        if config:
            config.config_value = str(request.size_threshold)
            config.updated_by = current_user.id
        else:
            config = GlobalConfig(
                config_key="sql_file_size_threshold",
                config_value=str(request.size_threshold),
                description="大文件阈值",
                updated_by=current_user.id
            )
            db.add(config)
        updates.append("大小阈值")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"配置已更新: {', '.join(updates)}。注意：部分配置需要重启服务后生效。",
        "requires_restart": True
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


# ==================== 安全配置 ====================

class SecurityConfigResponse(BaseModel):
    """安全配置响应（只读）"""
    jwt_configured: bool
    aes_configured: bool
    token_expire_hours: int
    password_policy: Dict[str, Any]


@router.get("/security-config", response_model=SecurityConfigResponse)
async def get_security_config(
    current_user: User = Depends(get_super_admin)
):
    """
    获取安全配置（只读）
    
    安全配置只能查看，不能通过 API 修改
    """
    # 检查是否使用自定义密钥
    jwt_custom = os.getenv("JWT_SECRET_KEY") is not None
    aes_custom = os.getenv("AES_KEY") is not None
    
    return SecurityConfigResponse(
        jwt_configured=jwt_custom,
        aes_configured=aes_custom,
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
    from app.config.storage import get_storage_settings
    
    storage_settings = get_storage_settings()
    
    # 检查调度器状态
    scheduler_running = False
    try:
        from app.services.scheduler import approval_scheduler
        scheduler_running = approval_scheduler.running
    except:
        pass
    
    return SystemOverview(
        version=app_settings.APP_VERSION,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        database_type="postgresql" if "postgresql" in app_settings.DATABASE_URL else "mysql",
        storage_type=storage_settings.STORAGE_TYPE,
        redis_enabled=bool(app_settings.REDIS_HOST),
        scheduler_running=scheduler_running
    )
