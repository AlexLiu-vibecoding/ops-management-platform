"""
钉钉通知服务
"""
import hashlib
import hmac
import time
import urllib.parse
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    DingTalkChannel, NotificationBinding, ApprovalRecord, 
    ApprovalStatus, Instance, User
)
from app.utils.auth import aes_cipher


class NotificationService:
    """通知服务"""
    
    @staticmethod
    def generate_approval_token(approval_id: int, action: str, expires_hours: int = 48) -> str:
        """
        生成审批令牌
        
        Args:
            approval_id: 审批ID
            action: 操作类型 (approve/reject)
            expires_hours: 过期时间（小时）
        
        Returns:
            加密的令牌
        """
        # 构建令牌数据
        expire_time = int((datetime.now() + timedelta(hours=expires_hours)).timestamp())
        token_data = f"{approval_id}:{action}:{expire_time}:{settings.SECRET_KEY[:16]}"
        
        # 生成签名
        signature = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # 构建最终令牌
        final_token = f"{approval_id}:{action}:{expire_time}:{signature}"
        
        # 加密令牌
        return aes_cipher.encrypt(final_token)
    
    @staticmethod
    def verify_approval_token(token: str) -> Optional[Dict[str, Any]]:
        """
        验证审批令牌
        
        Args:
            token: 加密的令牌
        
        Returns:
            解析后的数据，如果无效则返回 None
        """
        try:
            # 解密令牌
            decrypted = aes_cipher.decrypt(token)
            
            # 解析令牌
            parts = decrypted.split(":")
            if len(parts) != 4:
                return None
            
            approval_id = int(parts[0])
            action = parts[1]
            expire_time = int(parts[2])
            signature = parts[3]
            
            # 检查是否过期
            if datetime.now().timestamp() > expire_time:
                return None
            
            # 验证签名
            expected_data = f"{approval_id}:{action}:{expire_time}:{settings.SECRET_KEY[:16]}"
            expected_signature = hashlib.sha256(expected_data.encode()).hexdigest()[:32]
            
            if signature != expected_signature:
                return None
            
            return {
                "approval_id": approval_id,
                "action": action,
                "expire_time": expire_time
            }
        except Exception:
            return None
    
    @staticmethod
    def build_approval_url(approval_id: int, action: str) -> str:
        """
        构建审批链接
        
        Args:
            approval_id: 审批ID
            action: 操作类型 (approve/reject)
        
        Returns:
            完整的审批链接
        """
        token = NotificationService.generate_approval_token(approval_id, action)
        domain = getattr(settings, 'PROJECT_DOMAIN', '') or 'http://localhost:5000'
        return f"{domain}/api/approvals/dingtalk-action?token={token}"
    
    @staticmethod
    def decrypt_webhook(encrypted_webhook: str) -> str:
        """解密 webhook 地址"""
        return aes_cipher.decrypt(encrypted_webhook)
    
    @staticmethod
    def decrypt_secret(encrypted_secret: str) -> str:
        """解密密钥"""
        return aes_cipher.decrypt(encrypted_secret)
    
    @staticmethod
    def generate_dingtalk_sign(secret: str) -> tuple:
        """
        生成钉钉加签
        
        Returns:
            (timestamp, sign)
        """
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    @staticmethod
    async def send_dingtalk_message(
        webhook: str,
        message: Dict[str, Any],
        auth_type: str = "none",
        secret: str = None,
        keywords: List[str] = None
    ) -> bool:
        """
        发送钉钉消息
        
        Args:
            webhook: webhook 地址
            message: 消息内容
            auth_type: 验证类型
            secret: 密钥
            keywords: 关键词列表
        
        Returns:
            是否发送成功
        """
        # 构建完整 webhook URL
        full_webhook = webhook
        if auth_type == "sign" and secret:
            timestamp, sign = NotificationService.generate_dingtalk_sign(secret)
            separator = "&" if "?" in webhook else "?"
            full_webhook = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"
        
        # 处理关键词验证
        if auth_type == "keyword" and keywords:
            if message.get("msgtype") == "text":
                message["text"]["content"] += f" {keywords[0]}"
            elif message.get("msgtype") == "markdown":
                message["markdown"]["text"] += f"\n\n{keywords[0]}"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(full_webhook, json=message)
                if response.status_code == 200:
                    result = response.json()
                    return result.get("errcode") == 0
                return False
        except Exception as e:
            print(f"发送钉钉消息失败: {e}")
            return False
    
    @staticmethod
    async def send_approval_notification(
        db: Session,
        approval: ApprovalRecord,
        notification_type: str = "new"
    ):
        """
        发送审批通知
        
        Args:
            db: 数据库会话
            approval: 审批记录
            notification_type: 通知类型 (new/approved/rejected/executed)
        """
        # 获取实例信息
        instance = db.query(Instance).filter(Instance.id == approval.instance_id).first()
        instance_name = instance.name if instance else "未知实例"
        
        # 获取申请人信息
        requester = db.query(User).filter(User.id == approval.requester_id).first()
        requester_name = requester.real_name if requester else "未知用户"
        
        # 构建通知内容
        if notification_type == "new":
            title = "📝 新的变更审批申请"
            content = f"""
## {title}

**申请标题**: {approval.title}

**申请人**: {requester_name}

**实例**: {instance_name}

**变更类型**: {approval.change_type}

**风险等级**: {approval.sql_risk_level or '未评估'}

**SQL行数**: {approval.sql_line_count or 0} 行

**提交时间**: {approval.created_at.strftime('%Y-%m-%d %H:%M:%S')}

---

**请点击下方按钮进行审批**:
"""
            # 添加审批按钮
            approve_url = NotificationService.build_approval_url(approval.id, "approve")
            reject_url = NotificationService.build_approval_url(approval.id, "reject")
            
            content += f"""

[✅ 通过审批]({approve_url})

[❌ 拒绝审批]({reject_url})
"""
        elif notification_type == "approved":
            title = "✅ 审批已通过"
            approver = db.query(User).filter(User.id == approval.approver_id).first()
            approver_name = approver.real_name if approver else "未知"
            content = f"""
## {title}

**申请标题**: {approval.title}

**申请人**: {requester_name}

**审批人**: {approver_name}

**审批时间**: {approval.approve_time.strftime('%Y-%m-%d %H:%M:%S') if approval.approve_time else '未知'}

**审批意见**: {approval.approve_comment or '无'}
"""
            if approval.scheduled_time:
                content += f"\n**计划执行时间**: {approval.scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        elif notification_type == "rejected":
            title = "❌ 审批已拒绝"
            approver = db.query(User).filter(User.id == approval.approver_id).first()
            approver_name = approver.real_name if approver else "未知"
            content = f"""
## {title}

**申请标题**: {approval.title}

**申请人**: {requester_name}

**审批人**: {approver_name}

**审批时间**: {approval.approve_time.strftime('%Y-%m-%d %H:%M:%S') if approval.approve_time else '未知'}

**拒绝原因**: {approval.approve_comment or '无'}
"""
        elif notification_type == "executed":
            title = "🚀 变更已执行"
            content = f"""
## {title}

**申请标题**: {approval.title}

**申请人**: {requester_name}

**执行时间**: {approval.execute_time.strftime('%Y-%m-%d %H:%M:%S') if approval.execute_time else '未知'}

**执行结果**: {approval.execute_result or '执行完成'}
"""
        else:
            return
        
        # 获取通知绑定
        bindings = db.query(NotificationBinding).filter(
            NotificationBinding.notification_type == "approval"
        ).all()
        
        if not bindings:
            return
        
        # 发送通知
        for binding in bindings:
            channel = db.query(DingTalkChannel).filter(
                DingTalkChannel.id == binding.channel_id,
                DingTalkChannel.is_enabled == True
            ).first()
            
            if not channel:
                continue
            
            # 检查环境过滤
            if binding.environment_id and approval.environment_id != binding.environment_id:
                continue
            
            webhook = NotificationService.decrypt_webhook(channel.webhook_encrypted)
            secret = None
            if channel.auth_type == "sign" and channel.secret_encrypted:
                secret = NotificationService.decrypt_secret(channel.secret_encrypted)
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
            
            await NotificationService.send_dingtalk_message(
                webhook, message, channel.auth_type, secret, channel.keywords
            )


# 全局通知服务实例
notification_service = NotificationService()
