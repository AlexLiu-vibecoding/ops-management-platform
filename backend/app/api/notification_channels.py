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
from app.models import User, NotificationLog
from app.models.notification_new import NotificationChannel, ChannelSilenceRule
from app.models.permissions import PermissionCode
from app.deps import get_current_user, require_permissions
from app.utils.auth import aes_cipher
from app.services.notification import NotificationService


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
    keywords: Optional[list[str]] = None


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
    """加密通道配置中的敏感信息

    注意：只加密真正敏感的字段（如密钥、密码），webhook URL 明文存储
    因为 webhook URL 虽然包含 token，但需要频繁使用，加密会带来不必要的麻烦
    """
    config = config.copy()

    if channel_type == "dingtalk":
        # 只加密 secret（密钥），webhook URL 明文存储
        if config.get("secret"):
            config["secret_encrypted"] = encrypt_secret(config["secret"])
            del config["secret"]
        # webhook 保持明文
    elif channel_type == "email":
        # 只加密密码，其他保持明文
        if config.get("password"):
            config["password_encrypted"] = encrypt_secret(config["password"])
            del config["password"]
    elif channel_type == "webhook":
        # 自定义 webhook 的 URL 保持明文，不加密
        pass

    return config


def decrypt_channel_config(config: dict, channel_type: str) -> dict:
    """解密通道配置中的敏感信息

    注意：webhook URL 保持明文存储，不需要解密
    """
    config = config.copy() if config else {}

    if channel_type == "dingtalk":
        # 只解密 secret（密钥），webhook 保持明文
        if config.get("secret_encrypted"):
            config["secret"] = decrypt_secret(config["secret_encrypted"])
    elif channel_type == "email":
        # 只解密密码
        if config.get("password_encrypted"):
            config["password"] = decrypt_secret(config["password_encrypted"])
    # webhook 类型和自定义 webhook 都是明文存储，无需解密

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
    """测试通道 - 发送测试消息并记录到通知历史"""
    import logging
    logger = logging.getLogger(__name__)
    
    channel = db.query(NotificationChannel).filter_by(id=channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="通道不存在")
    
    if not channel.is_enabled:
        raise HTTPException(status_code=400, detail="通道已禁用，请先启用通道")
    
    # 解析配置
    config = channel.config
    if isinstance(config, str):
        config = json.loads(config)
    
    # 构建测试消息内容
    test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message_text = f"### OpsCenter 测试通知\n\n**通道名称**: {channel.name}\n\n**通道类型**: {CHANNEL_TYPE_LABELS.get(channel.channel_type, channel.channel_type)}\n\n**测试时间**: {test_time}\n\n**发送用户**: {current_user.username}\n\n---\n\n✅ 如果您收到此消息，说明通道配置正确，通知功能正常。"
    
    # 构建钉钉消息格式
    test_message = {
        "msgtype": "markdown",
        "markdown": {
            "title": "测试通知",
            "text": message_text
        }
    }
    
    # 创建通知日志记录（初始状态为 pending）
    log = NotificationService.create_notification_log(
        db=db,
        notification_type="scheduled_task",  # 使用 scheduled_task 类型表示测试/系统通知
        sub_type="channel_test",
        title=f"通道测试 - {channel.name}",
        content=message_text,
        channel_id=channel.id,
        channel_name=channel.name,
        status="pending"
    )
    
    # 根据通道类型发送测试消息
    if channel.channel_type == "dingtalk":
        # 钉钉通道测试
        webhook = config.get("webhook")
        auth_type = config.get("auth_type", "none")
        secret_encrypted = config.get("secret")
        keywords = config.get("keywords", [])
        
        if not webhook:
            # 更新日志为失败状态
            NotificationService.update_notification_log(
                db, log, status="failed",
                error_message="Webhook 地址未配置"
            )
            raise HTTPException(status_code=400, detail="Webhook 地址未配置")
        
        # 解密 secret
        secret = ""
        if secret_encrypted:
            secret = decrypt_secret(secret_encrypted)
        
        # 发送测试消息
        try:
            result = await _send_dingtalk_test(webhook, test_message, auth_type, secret, keywords)
            if result["success"]:
                # 更新日志为成功状态
                NotificationService.update_notification_log(
                    db, log, status="success",
                    response_code=200,
                    response_data=result.get('response_data', {})
                )
                return {
                    "message": "测试成功",
                    "detail": f"钉钉消息已发送，请检查接收情况\n钉钉返回: {result.get('response_data', {})}"
                }
            else:
                # 更新日志为失败状态
                NotificationService.update_notification_log(
                    db, log, status="failed",
                    error_message=result.get('error_message', '未知错误')
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"发送失败: {result.get('error_message', '未知错误')}"
                )
        except Exception as e:
            logger.error(f"钉钉测试消息发送失败: {e}")
            # 更新日志为失败状态
            NotificationService.update_notification_log(
                db, log, status="failed",
                error_message=str(e)
            )
            raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")
    
    elif channel.channel_type == "webhook":
        # 自定义 Webhook 测试
        webhook = config.get("webhook")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        
        if not webhook:
            NotificationService.update_notification_log(
                db, log, status="failed",
                error_message="Webhook 地址未配置"
            )
            raise HTTPException(status_code=400, detail="Webhook 地址未配置")
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                if method.upper() == "GET":
                    response = await client.get(webhook, headers=headers)
                else:
                    response = await client.post(webhook, json=test_message, headers=headers)
                
                # 更新日志状态
                status = "success" if response.status_code < 400 else "failed"
                NotificationService.update_notification_log(
                    db, log, status=status,
                    response_code=response.status_code
                )
                
                return {
                    "message": "测试完成",
                    "detail": f"Webhook 调用完成\nHTTP 状态: {response.status_code}\n响应: {response.text[:200]}"
                }
        except Exception as e:
            NotificationService.update_notification_log(
                db, log, status="failed",
                error_message=str(e)
            )
            raise HTTPException(status_code=500, detail=f"调用失败: {str(e)}")
    
    else:
        # 其他类型通道暂不支持测试
        NotificationService.update_notification_log(
            db, log, status="failed",
            error_message=f"暂不支持 {channel.channel_type} 类型的通道测试"
        )
        raise HTTPException(status_code=400, detail=f"暂不支持 {channel.channel_type} 类型的通道测试")


async def _send_dingtalk_test(
    webhook: str,
    message: dict,
    auth_type: str = "none",
    secret: str = None,
    keywords: list = None
) -> dict:
    """发送钉钉测试消息"""
    import time
    import hmac
    import hashlib
    import base64
    import urllib.parse
    import httpx
    import logging
    
    logger = logging.getLogger(__name__)
    
    result = {
        "success": False,
        "response_code": None,
        "response_data": None,
        "error_message": None
    }
    
    # 构建完整 webhook URL（加签）
    full_webhook = webhook
    if auth_type == "signature" and secret:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        separator = "&" if "?" in webhook else "?"
        full_webhook = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
    
    # 处理关键词验证
    logger.info(f"处理钉钉消息: auth_type={auth_type}, keywords={keywords}")
    if auth_type == "keyword" and keywords and len(keywords) > 0:
        if message.get("msgtype") == "text":
            message["text"]["content"] += f" {keywords[0]}"
            logger.info(f"添加关键词到 text 消息: {keywords[0]}")
        elif message.get("msgtype") == "markdown":
            message["markdown"]["text"] += f"\n\n{keywords[0]}"
            logger.info(f"添加关键词到 markdown 消息: {keywords[0]}")
    else:
        logger.warning(f"未添加关键词: auth_type={auth_type}, keywords={keywords}")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(full_webhook, json=message)
            result["response_code"] = response.status_code
            
            if response.status_code == 200:
                response_data = response.json()
                result["response_data"] = response_data
                result["success"] = response_data.get("errcode") == 0
                if not result["success"]:
                    result["error_message"] = response_data.get("errmsg", "未知错误")
            else:
                result["error_message"] = f"HTTP {response.status_code}"
    except Exception as e:
        result["error_message"] = str(e)
    
    return result


# ==================== 通道绑定管理 ====================


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
