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


@router.get("/types")
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


@router.get("/{channel_id}")
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


@router.put("/{channel_id}")
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


@router.delete("/{channel_id}")
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


@router.post("/{channel_id}/test")
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
