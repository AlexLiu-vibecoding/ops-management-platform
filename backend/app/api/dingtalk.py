"""
钉钉通道管理API
"""
import httpx
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DingTalkChannel, NotificationBinding, User
from app.schemas import (
    DingTalkChannelCreate, DingTalkChannelUpdate, 
    DingTalkChannelResponse, NotificationBindingCreate,
    MessageResponse
)
from app.utils.auth import encrypt_dingtalk_webhook, decrypt_dingtalk_webhook
from app.deps import get_super_admin, get_current_user

router = APIRouter(prefix="/dingtalk", tags=["钉钉通道"])


@router.get("/channels", response_model=List[DingTalkChannelResponse])
async def list_dingtalk_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取钉钉通道列表"""
    channels = db.query(DingTalkChannel).all()
    return [DingTalkChannelResponse.from_orm(c) for c in channels]


@router.get("/channels/{channel_id}", response_model=DingTalkChannelResponse)
async def get_dingtalk_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取钉钉通道详情"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钉钉通道不存在"
        )
    return DingTalkChannelResponse.from_orm(channel)


@router.post("/channels", response_model=DingTalkChannelResponse)
async def create_dingtalk_channel(
    channel_data: DingTalkChannelCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建钉钉通道（仅超级管理员）"""
    # 检查名称是否已存在
    if db.query(DingTalkChannel).filter(DingTalkChannel.name == channel_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="通道名称已存在"
        )
    
    channel = DingTalkChannel(
        name=channel_data.name,
        webhook_encrypted=encrypt_dingtalk_webhook(channel_data.webhook),
        description=channel_data.description
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    return DingTalkChannelResponse.from_orm(channel)


@router.put("/channels/{channel_id}", response_model=DingTalkChannelResponse)
async def update_dingtalk_channel(
    channel_id: int,
    channel_data: DingTalkChannelUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新钉钉通道（仅超级管理员）"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钉钉通道不存在"
        )
    
    # 更新字段
    if channel_data.name is not None:
        channel.name = channel_data.name
    if channel_data.webhook is not None:
        channel.webhook_encrypted = encrypt_dingtalk_webhook(channel_data.webhook)
    if channel_data.description is not None:
        channel.description = channel_data.description
    if channel_data.is_enabled is not None:
        channel.is_enabled = channel_data.is_enabled
    
    db.commit()
    db.refresh(channel)
    
    return DingTalkChannelResponse.from_orm(channel)


@router.delete("/channels/{channel_id}", response_model=MessageResponse)
async def delete_dingtalk_channel(
    channel_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除钉钉通道（仅超级管理员）"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钉钉通道不存在"
        )
    
    # 删除关联的通知绑定
    db.query(NotificationBinding).filter(
        NotificationBinding.channel_id == channel_id
    ).delete()
    
    db.delete(channel)
    db.commit()
    
    return MessageResponse(message="钉钉通道删除成功")


@router.post("/channels/{channel_id}/test", response_model=MessageResponse)
async def test_dingtalk_channel(
    channel_id: int,
    test_message: str = "这是一条测试消息",
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """测试钉钉通道"""
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钉钉通道不存在"
        )
    
    webhook = decrypt_dingtalk_webhook(channel.webhook_encrypted)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook,
                json={
                    "msgtype": "text",
                    "text": {
                        "content": f"[MySQL管理平台测试] {test_message}"
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    return MessageResponse(message="测试消息发送成功")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"发送失败: {result.get('errmsg', '未知错误')}"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"请求失败: HTTP {response.status_code}"
                )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送测试消息失败: {str(e)}"
        )


# ============ 通知绑定管理 ============

@router.get("/bindings", response_model=List[dict])
async def list_notification_bindings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取通知绑定列表"""
    bindings = db.query(NotificationBinding).all()
    result = []
    for b in bindings:
        channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == b.channel_id).first()
        result.append({
            "id": b.id,
            "channel_id": b.channel_id,
            "channel_name": channel.name if channel else None,
            "notification_type": b.notification_type,
            "environment_id": b.environment_id,
            "instance_id": b.instance_id,
            "created_at": b.created_at
        })
    return result


@router.post("/bindings", response_model=MessageResponse)
async def create_notification_binding(
    binding_data: NotificationBindingCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建通知绑定（仅超级管理员）"""
    # 检查通道是否存在
    channel = db.query(DingTalkChannel).filter(DingTalkChannel.id == binding_data.channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钉钉通道不存在"
        )
    
    # 检查是否已存在相同绑定
    existing = db.query(NotificationBinding).filter(
        NotificationBinding.channel_id == binding_data.channel_id,
        NotificationBinding.notification_type == binding_data.notification_type,
        NotificationBinding.environment_id == binding_data.environment_id,
        NotificationBinding.instance_id == binding_data.instance_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该通知绑定已存在"
        )
    
    binding = NotificationBinding(**binding_data.dict())
    db.add(binding)
    db.commit()
    
    return MessageResponse(message="通知绑定创建成功")


@router.delete("/bindings/{binding_id}", response_model=MessageResponse)
async def delete_notification_binding(
    binding_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除通知绑定（仅超级管理员）"""
    binding = db.query(NotificationBinding).filter(NotificationBinding.id == binding_id).first()
    if not binding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知绑定不存在"
        )
    
    db.delete(binding)
    db.commit()
    
    return MessageResponse(message="通知绑定删除成功")
