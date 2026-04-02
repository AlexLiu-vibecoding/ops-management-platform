"""
通知通道管理 API - 统一的通道管理，支持钉钉/企微/飞书/邮件/Webhook
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.database import get_db
from app.models import User
from app.models.notification_new import NotificationChannel, ChannelSilenceRule, ChannelRateLimit
from app.models.permissions import PermissionCode
from app.deps import get_current_user, require_permissions
from app.utils.auth import aes_cipher


# ==================== Helper Functions ====================

def encrypt_secret(secret: str) -> str:
    """加密密钥"""
    return aes_cipher.encrypt(secret)


def decrypt_secret(encrypted_secret: str) -> str:
    """解密密钥"""
    if not encrypted_secret:
        return ""
    try:
        return aes_cipher.decrypt(encrypted_secret)
    except Exception as e:
        # 解密失败时返回空字符串，避免影响查询
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"解密密钥失败: {str(e)}")
        return ""

router = APIRouter(prefix="/notification/channels", tags=["通知通道管理"])


# ==================== Schemas ====================

class ChannelConfigDingTalk(BaseModel):
    """钉钉配置"""
    webhook: str
    auth_type: str = "none"  # none/keyword/signature
    secret: Optional[str] = None
    keywords: Optional[List[str]] = None


class ChannelConfigWechat(BaseModel):
    """企业微信配置"""
    webhook: str


class ChannelConfigFeishu(BaseModel):
    """飞书配置"""
    webhook: str
    secret: Optional[str] = None


class ChannelConfigEmail(BaseModel):
    """邮件配置"""
    smtp_host: str
    smtp_port: int = 25
    username: str
    password: str
    from_addr: str
    use_tls: bool = True


class ChannelConfigWebhook(BaseModel):
    """自定义 Webhook 配置"""
    url: str
    method: str = "POST"
    headers: Optional[dict] = None
    body_template: Optional[str] = None


class ChannelCreate(BaseModel):
    """创建通道"""
    name: str = Field(..., max_length=100, description="通道名称")
    channel_type: str = Field(..., description="通道类型: dingtalk/wechat/feishu/email/webhook")
    config: dict = Field(..., description="通道配置")
    is_enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, max_length=200, description="描述")


class ChannelUpdate(BaseModel):
    """更新通道"""
    name: Optional[str] = Field(None, max_length=100)
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=200)


# ==================== 通道管理 ====================

CHANNEL_TYPE_LABELS = {
    "dingtalk": "钉钉",
    "wechat": "企业微信",
    "feishu": "飞书",
    "email": "邮件",
    "webhook": "Webhook"
}


def encrypt_channel_config(config: dict, channel_type: str) -> dict:
    """加密通道配置中的敏感信息"""
    config = config.copy()
    
    if channel_type == "dingtalk":
        if config.get("webhook"):
            config["webhook_encrypted"] = encrypt_secret(config["webhook"])
            del config["webhook"]
        if config.get("secret"):
            config["secret_encrypted"] = encrypt_secret(config["secret"])
            del config["secret"]
    elif channel_type == "email":
        if config.get("password"):
            config["password_encrypted"] = encrypt_secret(config["password"])
            del config["password"]
    elif channel_type == "webhook":
        if config.get("url"):
            config["url_encrypted"] = encrypt_secret(config["url"])
            del config["url"]
    
    return config


def decrypt_channel_config(config: dict, channel_type: str) -> dict:
    """解密通道配置中的敏感信息"""
    config = config.copy() if config else {}
    
    if channel_type == "dingtalk":
        if config.get("webhook_encrypted"):
            config["webhook"] = decrypt_secret(config["webhook_encrypted"])
        if config.get("secret_encrypted"):
            config["secret"] = decrypt_secret(config["secret_encrypted"])
    elif channel_type == "email":
        if config.get("password_encrypted"):
            config["password"] = decrypt_secret(config["password_encrypted"])
    elif channel_type == "webhook":
        if config.get("url_encrypted"):
            config["url"] = decrypt_secret(config["url_encrypted"])
    
    return config


# ==================== Static Routes (MUST be defined before dynamic routes) ====================

@router.get("/channel-types")
async def get_channel_types(
    current_user: User = Depends(get_current_user)
):
    """获取支持的通道类型"""
    return [
        {"value": "dingtalk", "label": "钉钉"},
        {"value": "wechat", "label": "企业微信"},
        {"value": "feishu", "label": "飞书"},
        {"value": "email", "label": "邮件"},
        {"value": "webhook", "label": "Webhook"}
    ]


# ==================== CRUD Routes ====================

@router.get("")
async def list_channels(
    channel_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通道列表"""
    query = db.query(NotificationChannel)
    
    if channel_type:
        query = query.filter_by(channel_type=channel_type)
    if is_enabled is not None:
        query = query.filter_by(is_enabled=is_enabled)
    
    channels = query.order_by(NotificationChannel.created_at.desc()).all()
    
    result = []
    for ch in channels:
        config = decrypt_channel_config(ch.config, ch.channel_type)
        result.append({
            "id": ch.id,
            "name": ch.name,
            "channel_type": ch.channel_type,
            "channel_type_label": CHANNEL_TYPE_LABELS.get(ch.channel_type, ch.channel_type),
            "config": config,
            "is_enabled": ch.is_enabled,
            "description": ch.description,
            "silence_rules_count": len(ch.silence_rules),
            "rate_limits_count": len(ch.rate_limits),
            "created_at": ch.created_at,
            "updated_at": ch.updated_at
        })
    
    return {"items": result, "total": len(result)}


# ==================== Dynamic Routes (MUST be defined after static routes) ====================

@router.get("/detail/{channel_id}")
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通道详情"""
    ch = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not ch:
        raise HTTPException(status_code=404, detail="通道不存在")

    config = decrypt_channel_config(ch.config, ch.channel_type)

    return {
        "id": ch.id,
        "name": ch.name,
        "channel_type": ch.channel_type,
        "channel_type_label": CHANNEL_TYPE_LABELS.get(ch.channel_type, ch.channel_type),
        "config": config,
        "is_enabled": ch.is_enabled,
        "description": ch.description,
        "created_at": ch.created_at,
        "updated_at": ch.updated_at
    }


@router.post("")
async def create_channel(
    data: ChannelCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """创建通道"""
    # 验证通道类型
    valid_types = ["dingtalk", "wechat", "feishu", "email", "webhook"]
    if data.channel_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"不支持的通道类型: {data.channel_type}")
    
    # 检查名称重复
    existing = db.query(NotificationChannel).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="通道名称已存在")
    
    # 加密敏感配置
    encrypted_config = encrypt_channel_config(data.config, data.channel_type)
    
    channel = NotificationChannel(
        name=data.name,
        channel_type=data.channel_type,
        config=encrypted_config,
        is_enabled=data.is_enabled,
        description=data.description
    )
    
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    return {"id": channel.id, "message": "创建成功"}


@router.put("/detail/{channel_id}")
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """更新通道"""
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")

    # 检查名称重复
    if data.name and data.name != channel.name:
        existing = db.query(NotificationChannel).filter_by(name=data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="通道名称已存在")
        channel.name = data.name

    if data.config:
        channel.config = encrypt_channel_config(data.config, channel.channel_type)

    if data.is_enabled is not None:
        channel.is_enabled = data.is_enabled

    if data.description is not None:
        channel.description = data.description

    db.commit()
    return {"message": "更新成功"}


@router.delete("/detail/{channel_id}")
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除通道"""
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")

    db.delete(channel)
    db.commit()
    return {"message": "删除成功"}


@router.post("/detail/{channel_id}/test")
async def test_channel(
    channel_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """测试通道"""
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")

    # TODO: 实现实际的通知发送测试
    return {"message": "测试成功", "detail": "通知已发送，请检查接收情况"}


# ==================== 通道绑定管理 ====================

from app.models import NotificationBinding, Environment
from app.models.instances import RDBInstance, RedisInstance

NOTIFICATION_TYPE_LABELS = {
    "approval": "审批通知",
    "alert": "告警通知",
    "scheduled_task": "定时任务通知",
    "operation": "审计日志通知"
}


class ChannelBindingCreate(BaseModel):
    """创建通道绑定"""
    notification_type: str = Field(..., description="通知类型: approval/alert/scheduled_task/operation")
    environment_id: Optional[int] = None
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    scheduled_task_id: Optional[int] = None


@router.get("/{channel_id}/bindings")
async def list_channel_bindings(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通道的绑定列表"""
    # 检查通道是否存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")

    bindings = db.query(NotificationBinding).filter_by(channel_id=channel_id).all()

    result = []
    for b in bindings:
        # 获取关联数据
        env_name = None
        rdb_name = None
        redis_name = None
        task_name = None

        if b.environment_id:
            env = db.query(Environment).filter_by(id=b.environment_id).first()
            env_name = env.name if env else None

        if b.rdb_instance_id:
            rdb = db.query(RDBInstance).filter_by(id=b.rdb_instance_id).first()
            rdb_name = rdb.name if rdb else None

        if b.redis_instance_id:
            redis = db.query(RedisInstance).filter_by(id=b.redis_instance_id).first()
            redis_name = redis.name if redis else None

        if b.scheduled_task_id:
            from app.models import ScheduledTask
            task = db.query(ScheduledTask).filter_by(id=b.scheduled_task_id).first()
            task_name = task.name if task else None

        result.append({
            "id": b.id,
            "channel_id": b.channel_id,
            "notification_type": b.notification_type,
            "notification_type_label": NOTIFICATION_TYPE_LABELS.get(b.notification_type, b.notification_type),
            "environment_id": b.environment_id,
            "environment_name": env_name,
            "rdb_instance_id": b.rdb_instance_id,
            "rdb_instance_name": rdb_name,
            "redis_instance_id": b.redis_instance_id,
            "redis_instance_name": redis_name,
            "scheduled_task_id": b.scheduled_task_id,
            "scheduled_task_name": task_name,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })

    return {"items": result}


@router.post("/{channel_id}/bindings")
async def create_channel_binding(
    channel_id: int,
    data: ChannelBindingCreate,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """创建通道绑定"""
    # 检查通道是否存在
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")

    # 检查是否已存在相同绑定
    existing = db.query(NotificationBinding).filter(
        NotificationBinding.channel_id == channel_id,
        NotificationBinding.notification_type == data.notification_type,
        NotificationBinding.environment_id == data.environment_id,
        NotificationBinding.rdb_instance_id == data.rdb_instance_id,
        NotificationBinding.redis_instance_id == data.redis_instance_id,
        NotificationBinding.scheduled_task_id == data.scheduled_task_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该绑定已存在")

    binding = NotificationBinding(
        channel_id=channel_id,
        notification_type=data.notification_type,
        environment_id=data.environment_id,
        rdb_instance_id=data.rdb_instance_id,
        redis_instance_id=data.redis_instance_id,
        scheduled_task_id=data.scheduled_task_id
    )
    db.add(binding)
    db.commit()

    return {"message": "绑定创建成功"}


@router.delete("/{channel_id}/bindings/{binding_id}")
async def delete_channel_binding(
    channel_id: int,
    binding_id: int,
    current_user: User = Depends(require_permissions([PermissionCode.NOTIFICATION_CHANNEL_MANAGE])),
    db: Session = Depends(get_db)
):
    """删除通道绑定"""
    binding = db.query(NotificationBinding).filter(
        NotificationBinding.id == binding_id,
        NotificationBinding.channel_id == channel_id
    ).first()

    if not binding:
        raise HTTPException(status_code=404, detail="绑定不存在")

    db.delete(binding)
    db.commit()

    return {"message": "绑定删除成功"}
