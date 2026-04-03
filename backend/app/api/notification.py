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
from app.models import NotificationBinding, User, ScheduledTask
from app.models.notification_new import NotificationChannel
from app.schemas import MessageResponse
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
    rdb_instance_id: Optional[int] = None
    redis_instance_id: Optional[int] = None
    scheduled_task_id: Optional[int] = None


# ==================== Helper Functions ====================

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
    "operation": "审计日志通知"
}


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
        channel = db.query(NotificationChannel).filter(NotificationChannel.id == b.channel_id).first()
        result.append({
            "id": b.id,
            "channel_id": b.channel_id,
            "channel_name": channel.name if channel else None,
            "channel_type": channel.channel_type if channel else "dingtalk",
            "notification_type": b.notification_type,
            "notification_type_label": NOTIFICATION_TYPE_LABELS.get(b.notification_type, b.notification_type),
            "environment_id": b.environment_id,
            "rdb_instance_id": b.rdb_instance_id,
            "redis_instance_id": b.redis_instance_id,
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
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == data.channel_id).first()
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知通道不存在")
    
    # 检查是否已存在相同绑定
    existing = db.query(NotificationBinding).filter(
        NotificationBinding.channel_id == data.channel_id,
        NotificationBinding.notification_type == data.notification_type,
        NotificationBinding.environment_id == data.environment_id,
        NotificationBinding.rdb_instance_id == data.rdb_instance_id,
        NotificationBinding.redis_instance_id == data.redis_instance_id,
        NotificationBinding.scheduled_task_id == data.scheduled_task_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Notification binding already exists")
    
    binding = NotificationBinding(
        channel_id=data.channel_id,
        notification_type=data.notification_type,
        environment_id=data.environment_id,
        rdb_instance_id=data.rdb_instance_id,
        redis_instance_id=data.redis_instance_id,
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
        raise HTTPException(status_code=404, detail="Notification binding not found")
    
    db.delete(binding)
    db.commit()
    
    return MessageResponse(message="通知绑定删除成功")
