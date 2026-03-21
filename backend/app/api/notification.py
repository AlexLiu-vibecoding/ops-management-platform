"""
通知管理API - 支持钉钉、企业微信、飞书、邮件等多种通知渠道
"""
import httpx
import hmac
import hashlib
import base64
import time
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models import DingTalkChannel, NotificationBinding, User, ScheduledTask
from app.schemas import MessageResponse
from app.utils.auth import aes_cipher
from app.deps import get_super_admin, get_current_user

router = APIRouter(prefix="/notification", tags=["通知管理"])


# ==================== Schemas ====================

class ChannelCreate(BaseModel):
    """创建通知通道"""
    name: str = Field(..., max_length=100)
    channel_type: str = Field("dingtalk", description="通道类型: dingtalk/wechat/feishu/email/webhook")
    webhook: Optional[str] = Field(None, description="Webhook地址")
    auth_type: str = Field("none", description="验证类型: none/keyword/sign/token")
    secret: Optional[str] = Field(None, description="密钥")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    # 邮件配置
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    description: Optional[str] = None


class ChannelUpdate(BaseModel):
    """更新通知通道"""
    name: Optional[str] = Field(None, max_length=100)
    webhook: Optional[str] = None
    auth_type: Optional[str] = None
    secret: Optional[str] = None
    keywords: Optional[List[str]] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class BindingCreate(BaseModel):
    """创建通知绑定"""
    channel_id: int
    notification_type: str = Field(..., description="通知类型: approval/alert/scheduled_task/operation")
    environment_id: Optional[int] = None
    instance_id: Optional[int] = None
    scheduled_task_id: Optional[int] = None


# ==================== Helper Functions ====================

def encrypt_secret(secret: str) -> str:
    """加密密钥"""
    return aes_cipher.encrypt(secret)


def decrypt_secret(encrypted_secret: str) -> str:
    """解密密钥"""
    return aes_cipher.decrypt(encrypted_secret)


def generate_dingtalk_sign(secret: str) -> tuple:
    """生成钉钉加签"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


# ==================== Constants ====================

CHANNEL_TYPE_LABELS = {
    "dingtalk": "钉钉",
    "wechat": "企业微信",
    "feishu": "飞书",
    "email": "邮件",
    "webhook": "自定义Webhook"
}

NOTIFICATION_TYPE_LABELS = {
    "approval": "审批通知",
    "alert": "告警通知",
    "scheduled_task": "定时任务通知",
    "operation": "操作通知"
}


# ==================== Channel Types ====================

@router.get("/channel-types")
async def get_channel_types():
    """获取支持的通道类型"""
    return [
        {"value": "dingtalk", "label": "钉钉", "icon": "ChatDotRound"},
        {"value": "wechat", "label": "企业微信", "icon": "ChatRound"},
        {"value": "feishu", "label": "飞书", "icon": "Message"},
        {"value": "email", "label": "邮件", "icon": "Message"},
        {"value": "webhook", "label": "自定义Webhook", "icon": "Link"}
    ]


@router.get("/notification-types")
async def get_notification_types():
    """获取通知类型列表"""
    return [
        {"value": "approval", "label": "审批通知"},
        {"value": "alert", "label": "告警通知"},
        {"value": "scheduled_task", "label": "定时任务通知"},
        {"value": "operation", "label": "操作通知"}
    ]


# ==================== Channel Management ====================

@router.get("/channels")
async def list_channels(
    channel_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知通道列表"""
    query = db.query(DingTalkChannel)
    channels = query.all()
    
    return [{
        "id": c.id,
        "name": c.name,
        "channel_type": "dingtalk",  # 默认钉钉类型，未来可扩展
        "channel_type_label": "钉钉",
        "auth_type": c.auth_type,
        "is_enabled": c.is_enabled,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in channels]


@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知通道详情"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    return {
        "id": channel.id,
        "name": channel.name,
        "channel_type": "dingtalk",
        "channel_type_label": "钉钉",
        "webhook": decrypt_secret(channel.webhook_encrypted) if channel.webhook_encrypted else None,
        "auth_type": channel.auth_type,
        "keywords": channel.keywords,
        "description": channel.description,
        "is_enabled": channel.is_enabled,
        "created_at": channel.created_at.isoformat() if channel.created_at else None
    }


@router.post("/channels", response_model=MessageResponse)
async def create_channel(
    data: ChannelCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建通知通道"""
    # 检查名称是否已存在
    if db.query(DingTalkChannel).filter(DingTalkChannel.name == data.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="通道名称已存在")
    
    # 验证配置
    if data.channel_type in ["dingtalk", "wechat", "feishu", "webhook"]:
        if not data.webhook:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook地址不能为空")
    
    if data.auth_type == "sign" and not data.secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="加签验证必须提供密钥")
    
    if data.auth_type == "keyword" and not data.keywords:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="关键词验证必须提供关键词")
    
    channel = DingTalkChannel(
        name=data.name,
        webhook_encrypted=encrypt_secret(data.webhook) if data.webhook else None,
        auth_type=data.auth_type,
        secret_encrypted=encrypt_secret(data.secret) if data.secret else None,
        keywords=data.keywords,
        description=data.description
    )
    
    db.add(channel)
    db.commit()
    
    return MessageResponse(message="通知通道创建成功")


@router.put("/channels/{channel_id}", response_model=MessageResponse)
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新通知通道"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    if data.name is not None:
        channel.name = data.name
    if data.webhook is not None:
        channel.webhook_encrypted = encrypt_secret(data.webhook)
    if data.auth_type is not None:
        channel.auth_type = data.auth_type
    if data.secret is not None:
        channel.secret_encrypted = encrypt_secret(data.secret)
    if data.keywords is not None:
        channel.keywords = data.keywords
    if data.description is not None:
        channel.description = data.description
    if data.is_enabled is not None:
        channel.is_enabled = data.is_enabled
    
    db.commit()
    return MessageResponse(message="通知通道更新成功")


@router.delete("/channels/{channel_id}", response_model=MessageResponse)
async def delete_channel(
    channel_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除通知通道"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    # 删除关联的绑定
    db.query(NotificationBinding).filter(NotificationBinding.channel_id == channel_id).delete()
    
    db.delete(channel)
    db.commit()
    
    return MessageResponse(message="通知通道删除成功")


@router.post("/channels/{channel_id}/test")
async def test_channel(
    channel_id: int,
    test_message: str = "这是一条测试消息",
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """测试通知通道"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    try:
        webhook = decrypt_secret(channel.webhook_encrypted)
        
        # 构建完整URL
        if channel.auth_type == "sign" and channel.secret_encrypted:
            secret = decrypt_secret(channel.secret_encrypted)
            timestamp, sign = generate_dingtalk_sign(secret)
            separator = "&" if "?" in webhook else "?"
            webhook = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
        
        # 构建消息内容
        content = test_message
        if channel.auth_type == "keyword" and channel.keywords:
            content = f"{test_message} {channel.keywords[0]}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook,
                json={"msgtype": "text", "text": {"content": content}},
                timeout=10
            )
            result = response.json()
            if result.get("errcode") != 0:
                raise Exception(result.get("errmsg", "发送失败"))
        
        return {"success": True, "message": "测试消息发送成功"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"发送失败: {str(e)}")


# ==================== Binding Management ====================

@router.get("/bindings")
async def list_bindings(
    notification_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知绑定列表"""
    query = db.query(NotificationBinding)
    
    if notification_type:
        query = query.filter(NotificationBinding.notification_type == notification_type)
    
    bindings = query.all()
    
    result = []
    for b in bindings:
        channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == b.channel_id).first()
        result.append({
            "id": b.id,
            "channel_id": b.channel_id,
            "channel_name": channel.name if channel else None,
            "channel_type": "dingtalk",
            "notification_type": b.notification_type,
            "notification_type_label": NOTIFICATION_TYPE_LABELS.get(b.notification_type, b.notification_type),
            "environment_id": b.environment_id,
            "instance_id": b.instance_id,
            "scheduled_task_id": b.scheduled_task_id,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    
    return {
        "total": len(result),
        "items": result
    }


@router.post("/bindings", response_model=MessageResponse)
async def create_binding(
    data: BindingCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建通知绑定"""
    # 检查通道是否存在
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == data.channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    # 检查是否已存在相同绑定
    existing = db.query(NotificationBinding).filter(
        NotificationBinding.channel_id == data.channel_id,
        NotificationBinding.notification_type == data.notification_type,
        NotificationBinding.environment_id == data.environment_id,
        NotificationBinding.instance_id == data.instance_id,
        NotificationBinding.scheduled_task_id == data.scheduled_task_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该通知绑定已存在")
    
    binding = NotificationBinding(
        channel_id=data.channel_id,
        notification_type=data.notification_type,
        environment_id=data.environment_id,
        instance_id=data.instance_id,
        scheduled_task_id=data.scheduled_task_id
    )
    db.add(binding)
    db.commit()
    
    return MessageResponse(message="通知绑定创建成功")


@router.delete("/bindings/{binding_id}", response_model=MessageResponse)
async def delete_binding(
    binding_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除通知绑定"""
    binding = db.query(NotificationBinding).filter(NotificationBinding.id == binding_id).first()
    if not binding:
        raise HTTPException(status_code=404, detail="通知绑定不存在")
    
    db.delete(binding)
    db.commit()
    
    return MessageResponse(message="通知绑定删除成功")
