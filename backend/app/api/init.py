"""
系统初始化API
"""
import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, engine, Base
from app.models import SystemConfig, SystemInitState, User, UserRole
from app.utils.auth import hash_password, aes_cipher

router = APIRouter(prefix="/init", tags=["系统初始化"])


class DatabaseConfig(BaseModel):
    """数据库配置"""
    db_type: str = Field("postgresql", description="数据库类型: postgresql/mysql")
    host: str = Field(..., description="主机地址")
    port: int = Field(5432, description="端口")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    database: str = Field(..., description="数据库名")


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = Field("localhost", description="主机地址")
    port: int = Field(6379, description="端口")
    password: Optional[str] = Field(None, description="密码")
    db: int = Field(0, description="数据库索引")


class AdminConfig(BaseModel):
    """管理员配置"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    real_name: str = Field(..., description="真实姓名")
    email: str = Field(..., description="邮箱")


class InitConfig(BaseModel):
    """初始化配置"""
    database: DatabaseConfig
    redis: Optional[RedisConfig] = None
    admin: AdminConfig


class InitStatus(BaseModel):
    """初始化状态"""
    is_initialized: bool
    current_step: Optional[str] = None
    steps: dict = {}


@router.get("/status", response_model=InitStatus)
async def get_init_status(db: Session = Depends(get_db)):
    """
    获取系统初始化状态
    
    检查系统是否已完成初始化配置
    """
    # 检查是否有已完成的初始化记录
    init_state = db.query(SystemInitState).filter(
        SystemInitState.step == "system_init",
        SystemInitState.status == "completed"
    ).first()
    
    if init_state:
        return InitStatus(is_initialized=True)
    
    # 检查各步骤状态
    steps = {}
    for state in db.query(SystemInitState).all():
        steps[state.step] = {
            "status": state.status,
            "error": state.error_message
        }
    
    # 如果没有任何初始化记录，说明是首次启动
    return InitStatus(
        is_initialized=False,
        steps=steps
    )


@router.post("/test-database")
async def test_database_connection(config: DatabaseConfig):
    """
    测试数据库连接
    
    在保存配置前验证连接是否正常
    """
    try:
        # 构建连接URL
        if config.db_type == "postgresql":
            url = f"postgresql+psycopg2://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        else:
            url = f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        
        # 尝试连接
        from sqlalchemy import create_engine
        test_engine = create_engine(url, pool_pre_ping=True)
        
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        test_engine.dispose()
        
        return {"success": True, "message": "数据库连接成功"}
    
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


@router.post("/test-redis")
async def test_redis_connection(config: RedisConfig):
    """
    测试Redis连接
    """
    try:
        import redis
        client = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.password if config.password else None,
            db=config.db,
            socket_timeout=5
        )
        client.ping()
        client.close()
        
        return {"success": True, "message": "Redis连接成功"}
    
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


@router.post("/save-config")
async def save_init_config(
    config: InitConfig,
    db: Session = Depends(get_db)
):
    """
    保存初始化配置
    
    保存数据库、Redis和管理员配置到系统配置表
    """
    # 检查是否已初始化
    init_state = db.query(SystemInitState).filter(
        SystemInitState.step == "system_init",
        SystemInitState.status == "completed"
    ).first()
    
    if init_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统已完成初始化，无法重复配置"
        )
    
    try:
        # 标记数据库配置步骤
        step_db = db.query(SystemInitState).filter(
            SystemInitState.step == "database_config"
        ).first()
        
        if not step_db:
            step_db = SystemInitState(step="database_config", status="pending")
            db.add(step_db)
        
        # 保存数据库配置（加密密码）
        db_configs = [
            ("db_type", config.database.db_type, False, "数据库类型"),
            ("db_host", config.database.host, False, "数据库主机"),
            ("db_port", str(config.database.port), False, "数据库端口"),
            ("db_username", config.database.username, False, "数据库用户名"),
            ("db_password", aes_cipher.encrypt(config.database.password), True, "数据库密码"),
            ("db_database", config.database.database, False, "数据库名"),
        ]
        
        for key, value, encrypted, desc in db_configs:
            existing = db.query(SystemConfig).filter(
                SystemConfig.config_key == key
            ).first()
            
            if existing:
                existing.config_value = value
                existing.is_encrypted = encrypted
            else:
                db.add(SystemConfig(
                    config_key=key,
                    config_value=value,
                    is_encrypted=encrypted,
                    description=desc
                ))
        
        step_db.status = "completed"
        step_db.completed_at = datetime.now()
        
        # 保存Redis配置
        if config.redis:
            step_redis = db.query(SystemInitState).filter(
                SystemInitState.step == "redis_config"
            ).first()
            
            if not step_redis:
                step_redis = SystemInitState(step="redis_config", status="pending")
                db.add(step_redis)
            
            redis_configs = [
                ("redis_host", config.redis.host, False, "Redis主机"),
                ("redis_port", str(config.redis.port), False, "Redis端口"),
                ("redis_password", aes_cipher.encrypt(config.redis.password) if config.redis.password else "", True, "Redis密码"),
                ("redis_db", str(config.redis.db), False, "Redis数据库"),
            ]
            
            for key, value, encrypted, desc in redis_configs:
                existing = db.query(SystemConfig).filter(
                    SystemConfig.config_key == key
                ).first()
                
                if existing:
                    existing.config_value = value
                    existing.is_encrypted = encrypted
                else:
                    db.add(SystemConfig(
                        config_key=key,
                        config_value=value,
                        is_encrypted=encrypted,
                        description=desc
                    ))
            
            step_redis.status = "completed"
            step_redis.completed_at = datetime.now()
        
        db.commit()
        
        return {"success": True, "message": "配置保存成功，请继续设置管理员账户"}
    
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"保存失败: {str(e)}"}


@router.post("/create-admin")
async def create_admin_account(
    admin_config: AdminConfig,
    db: Session = Depends(get_db)
):
    """
    创建管理员账户
    
    在配置完成后创建超级管理员账户
    """
    # 检查数据库配置是否完成
    step_db = db.query(SystemInitState).filter(
        SystemInitState.step == "database_config",
        SystemInitState.status == "completed"
    ).first()
    
    if not step_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完成数据库配置"
        )
    
    # 检查是否已有管理员
    existing_admin = db.query(User).filter(
        User.role == UserRole.SUPER_ADMIN
    ).first()
    
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员账户已存在"
        )
    
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == admin_config.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == admin_config.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    try:
        # 创建管理员账户
        admin = User(
            username=admin_config.username,
            password_hash=hash_password(admin_config.password),
            real_name=admin_config.real_name,
            email=admin_config.email,
            role=UserRole.SUPER_ADMIN,
            status=True
        )
        db.add(admin)
        
        # 标记管理员创建完成
        step_admin = db.query(SystemInitState).filter(
            SystemInitState.step == "admin_config"
        ).first()
        
        if not step_admin:
            step_admin = SystemInitState(step="admin_config", status="completed")
            db.add(step_admin)
        else:
            step_admin.status = "completed"
            step_admin.completed_at = datetime.now()
        
        # 标记系统初始化完成
        step_init = db.query(SystemInitState).filter(
            SystemInitState.step == "system_init"
        ).first()
        
        if not step_init:
            step_init = SystemInitState(
                step="system_init",
                status="completed",
                completed_at=datetime.now()
            )
            db.add(step_init)
        else:
            step_init.status = "completed"
            step_init.completed_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "管理员账户创建成功，系统初始化完成",
            "username": admin_config.username
        }
    
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"创建失败: {str(e)}"}


@router.post("/complete")
async def complete_initialization(db: Session = Depends(get_db)):
    """
    完成初始化
    
    标记系统初始化完成，生成必要的默认数据
    """
    # 检查所有必要步骤是否完成
    required_steps = ["database_config", "admin_config"]
    
    for step_name in required_steps:
        step = db.query(SystemInitState).filter(
            SystemInitState.step == step_name,
            SystemInitState.status == "completed"
        ).first()
        
        if not step:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"请先完成 {step_name} 步骤"
            )
    
    # 标记系统初始化完成
    step_init = db.query(SystemInitState).filter(
        SystemInitState.step == "system_init"
    ).first()
    
    if not step_init:
        step_init = SystemInitState(
            step="system_init",
            status="completed",
            completed_at=datetime.now()
        )
        db.add(step_init)
    else:
        step_init.status = "completed"
        step_init.completed_at = datetime.now()
    
    db.commit()
    
    return {"success": True, "message": "系统初始化完成"}
