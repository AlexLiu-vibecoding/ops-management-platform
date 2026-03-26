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
    ApprovalStatus, RDBInstance, RedisInstance, User, ScheduledTask, ScriptExecution
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
        import logging
        logger = logging.getLogger(__name__)
        
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
                logger.info(f"添加关键词到消息: {keywords[0]}")
        
        logger.info(f"发送钉钉消息: webhook={webhook[:50]}..., auth_type={auth_type}")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(full_webhook, json=message)
                logger.info(f"钉钉响应: status={response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"钉钉返回: {result}")
                    return result.get("errcode") == 0
                return False
        except Exception as e:
            logger.error(f"发送钉钉消息失败: {e}")
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
        # 获取实例信息 - 支持新的拆分表结构
        instance_name = "未知实例"
        if approval.rdb_instance_id:
            instance = db.query(RDBInstance).filter(RDBInstance.id == approval.rdb_instance_id).first()
            instance_name = instance.name if instance else "未知实例"
        elif approval.redis_instance_id:
            instance = db.query(RedisInstance).filter(RedisInstance.id == approval.redis_instance_id).first()
            instance_name = instance.name if instance else "未知实例"
        elif approval.instance_id:
            # 向后兼容
            instance = db.query(RDBInstance).filter(RDBInstance.id == approval.instance_id).first()
            if not instance:
                instance = db.query(RedisInstance).filter(RedisInstance.id == approval.instance_id).first()
            instance_name = instance.name if instance else "未知实例"
        
        # 获取申请人信息
        requester = db.query(User).filter(User.id == approval.requester_id).first()
        requester_name = requester.real_name if requester else "未知用户"
        
        # 构建数据库目标描述
        if approval.database_mode == "all":
            db_target = "全部数据库"
        elif approval.database_mode == "pattern":
            db_target = f"通配符: {approval.database_pattern}"
        elif approval.database_mode == "multiple":
            db_target = f"{len(approval.database_list or [])} 个数据库: {', '.join(approval.database_list or [])}"
        elif approval.database_mode == "auto":
            db_target = "SQL自动解析"
        else:
            db_target = approval.database_name or "未指定"
        
        # 风险等级映射
        risk_names = {
            "low": "低风险",
            "medium": "中风险",
            "high": "高风险",
            "critical": "极高风险"
        }
        risk_display = risk_names.get(approval.sql_risk_level, "未评估")
        
        # 变更类型映射
        change_type_names = {
            "DDL": "DDL(结构变更)",
            "DML": "DML(数据变更)",
            "OPERATION": "运维操作",
            "CUSTOM": "自定义变更",
            "REDIS": "Redis命令"
        }
        change_type_display = change_type_names.get(approval.change_type, approval.change_type)
        
        # 构建通知内容
        if notification_type == "new":
            title = "变更审批通知"
            
            # 构建影响行数显示
            affected_rows_info = "未知"
            if approval.affected_rows_estimate and approval.affected_rows_estimate > 0:
                affected_rows_info = f"{approval.affected_rows_estimate:,} 行"
            
            # 自动执行提示
            execute_mode = "手动执行"
            if approval.auto_execute and not approval.scheduled_time:
                execute_mode = "审批通过后立即执行"
            elif approval.scheduled_time:
                execute_mode = f"{approval.scheduled_time.strftime('%m-%d %H:%M')} 定时执行"
            
            content = f"""## {title}

**申请信息**
- 标题: {approval.title}
- 申请人: {requester_name}
- 提交时间: {approval.created_at.strftime('%m-%d %H:%M')}

**变更详情**
- 目标实例: {instance_name}
- 目标数据库: {db_target}
- 变更类型: {change_type_display}
- 风险等级: {risk_display}
- SQL行数: {approval.sql_line_count or 0} 行
- 影响行数: {affected_rows_info}
- 执行方式: {execute_mode}

[点击通过]({NotificationService.build_approval_url(approval.id, "approve")}) | [点击拒绝]({NotificationService.build_approval_url(approval.id, "reject")})"""
        elif notification_type == "approved":
            title = "审批通过通知"
            approver = db.query(User).filter(User.id == approval.approver_id).first()
            approver_name = approver.real_name if approver else "未知"
            
            # 执行状态提示
            execute_status = "等待申请人手动执行"
            if approval.auto_execute and not approval.scheduled_time:
                execute_status = "即将自动执行"
            elif approval.scheduled_time:
                execute_status = f"{approval.scheduled_time.strftime('%m-%d %H:%M')} 定时执行"
            
            content = f"""## {title}

**申请信息**
- 标题: {approval.title}
- 申请人: {requester_name}
- 审批人: {approver_name}

**变更详情**
- 目标实例: {instance_name}
- 目标数据库: {db_target}
- 变更类型: {change_type_display}
- 风险等级: {risk_display}

**审批信息**
- 审批意见: {approval.approve_comment or '无'}
- 审批时间: {approval.approve_time.strftime('%m-%d %H:%M') if approval.approve_time else '未知'}

执行状态: {execute_status}"""
        
        elif notification_type == "rejected":
            title = "审批拒绝通知"
            approver = db.query(User).filter(User.id == approval.approver_id).first()
            approver_name = approver.real_name if approver else "未知"
            content = f"""## {title}

**申请信息**
- 标题: {approval.title}
- 申请人: {requester_name}
- 审批人: {approver_name}

**变更详情**
- 目标实例: {instance_name}
- 目标数据库: {db_target}
- 变更类型: {change_type_display}
- 风险等级: {risk_display}

**拒绝原因**
{approval.approve_comment or '未填写原因'}

拒绝时间: {approval.approve_time.strftime('%m-%d %H:%M') if approval.approve_time else '未知'}"""
        elif notification_type == "executed":
            # 根据状态判断标题
            if approval.status and approval.status.value == "failed":
                title = "变更执行失败"
            else:
                title = "变更执行完成"
            
            # 实际影响行数
            affected_info = "未知"
            if approval.affected_rows_actual:
                affected_info = f"{approval.affected_rows_actual:,} 行"
            
            # 执行结果状态
            result_text = approval.execute_result or "执行完成"
            
            content = f"""## {title}

**申请信息**
- 标题: {approval.title}
- 申请人: {requester_name}

**变更详情**
- 目标实例: {instance_name}
- 目标数据库: {db_target}
- 变更类型: {change_type_display}
- 实际影响: {affected_info}

**执行结果**
- 状态: {result_text}
- 完成时间: {approval.execute_time.strftime('%m-%d %H:%M') if approval.execute_time else '未知'}"""
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

    @staticmethod
    async def send_scheduled_task_notification(
        db: Session,
        task: ScheduledTask,
        execution: ScriptExecution,
        success: bool
    ):
        """
        发送定时任务执行通知
        
        Args:
            db: 数据库会话
            task: 定时任务
            execution: 执行记录
            success: 是否执行成功
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 检查是否需要通知
        if success and not task.notify_on_success:
            logger.info(f"任务 {task.id} 成功但未配置成功通知，跳过")
            return
        if not success and not task.notify_on_fail:
            logger.info(f"任务 {task.id} 失败但未配置失败通知，跳过")
            return
        
        # 构建通知内容
        if success:
            title = "定时任务执行成功"
            status_text = "成功"
        else:
            title = "定时任务执行失败"
            status_text = "失败"
        
        content = f"""## {title}

**任务信息**
- 任务名称: {task.name}
- 执行脚本: {execution.script.name if execution.script else '未知脚本'}

**执行详情**
- 执行状态: {status_text}
- 执行耗时: {f'{execution.duration:.2f}秒' if execution.duration else '未知'}
- 退出码: {execution.exit_code if execution.exit_code is not None else 'N/A'}
- 开始时间: {execution.start_time.strftime('%m-%d %H:%M:%S') if execution.start_time else '未知'}
- 结束时间: {execution.end_time.strftime('%m-%d %H:%M:%S') if execution.end_time else '未知'}"""
        
        if not success and execution.error_output:
            # 截取错误信息前500字符
            error_preview = execution.error_output[:500]
            if len(execution.error_output) > 500:
                error_preview += "..."
            content += f"""

**错误信息**
{error_preview}"""
        
        # 获取通知绑定 - 定时任务类型
        bindings = db.query(NotificationBinding).filter(
            NotificationBinding.notification_type == "scheduled_task"
        ).all()
        
        logger.info(f"找到 {len(bindings)} 个定时任务通知绑定")
        
        if not bindings:
            logger.warning("没有找到定时任务通知绑定")
            return
        
        # 发送通知
        for binding in bindings:
            logger.info(f"处理绑定: channel_id={binding.channel_id}, scheduled_task_id={binding.scheduled_task_id}")
            
            channel = db.query(DingTalkChannel).filter(
                DingTalkChannel.id == binding.channel_id,
                DingTalkChannel.is_enabled == True
            ).first()
            
            if not channel:
                logger.warning(f"通道 {binding.channel_id} 不存在或未启用")
                continue
            
            # 如果绑定指定了特定任务，只发送给该任务
            if binding.scheduled_task_id:
                if binding.scheduled_task_id != task.id:
                    logger.info(f"绑定指定任务 {binding.scheduled_task_id}，当前任务 {task.id}，跳过")
                    continue
            
            logger.info(f"准备发送通知到通道: {channel.name}")
            
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
            
            result = await NotificationService.send_dingtalk_message(
                webhook, message, channel.auth_type, secret, channel.keywords
            )
            logger.info(f"通知发送结果: {result}")


# 全局通知服务实例
notification_service = NotificationService()
