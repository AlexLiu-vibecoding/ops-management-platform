"""
钉钉通知服务
"""
import hashlib
import hmac
import time
import urllib.parse
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    NotificationBinding, ApprovalRecord, 
    ApprovalStatus, RDBInstance, RedisInstance, User, ScheduledTask, ScriptExecution,
    NotificationLog
)
from app.models.notification_new import NotificationChannel
from app.utils.auth import aes_cipher


class NotificationService:
    """通知服务"""
    
    @staticmethod
    def render_template(db: Session, notification_type: str, sub_type: str = None, **kwargs) -> tuple:
        """
        渲染通知模板
        
        Args:
            db: 数据库会话
            notification_type: 通知类型
            sub_type: 细分类型
            **kwargs: 模板变量
        
        Returns:
            (title, content)
        """
        from app.models import NotificationTemplate
        
        # 查询匹配的模板
        query = db.query(NotificationTemplate).filter(
            NotificationTemplate.notification_type == notification_type,
            NotificationTemplate.is_enabled == True,
            NotificationTemplate.is_default == True
        )
        
        if sub_type:
            # 先尝试匹配细分类型
            template = query.filter(NotificationTemplate.sub_type == sub_type).first()
            if not template:
                # 如果没有细分类型的默认模板，使用通用默认模板
                template = query.first()
        else:
            template = query.first()
        
        if template:
            title_template = template.title_template
            content_template = template.content_template
        else:
            # 使用系统默认模板
            if notification_type == "approval":
                title_template = "变更审批通知"
                content_template = """## 变更审批通知

**申请信息**
- 标题: {title}
- 申请人: {requester_name}
- 提交时间: {created_at}

**变更详情**
- 目标实例: {instance_name}
- 变更类型: {change_type}
- 风险等级: {risk_level}

[点击通过]({approve_url}) | [点击拒绝]({reject_url})"""
            elif notification_type == "alert":
                title_template = "告警通知: {alert_title}"
                content_template = """## 告警通知

**告警详情**
- 告警标题: {alert_title}
- 告警级别: {alert_level}
- 目标实例: {instance_name}
- 指标: {metric_name}
- 当前值: {current_value}
- 阈值: {threshold}"""
            elif notification_type == "scheduled_task":
                title_template = "定时任务执行通知: {task_name}"
                content_template = """## 定时任务执行通知

**任务信息**
- 任务名称: {task_name}
- 执行脚本: {script_name}

**执行详情**
- 状态: {status}
- 耗时: {duration}
- 退出码: {exit_code}
- 开始时间: {start_time}
- 结束时间: {end_time}"""
            else:
                title_template = "通知"
                content_template = "通知内容"
        
        # 渲染模板
        try:
            title = title_template.format(**kwargs)
            content = content_template.format(**kwargs)
        except KeyError as e:
            # 如果缺少变量，使用简单替换（替换存在的变量，保留不存在的）
            title = title_template
            content = content_template
            for key, value in kwargs.items():
                var_pattern = "{" + key + "}"
                title = title.replace(var_pattern, str(value))
                content = content.replace(var_pattern, str(value))
        
        return title, content
    
    @staticmethod
    def create_notification_log(
        db: Session,
        notification_type: str,
        title: str,
        content: str = None,
        sub_type: str = None,
        channel_id: int = None,
        channel_name: str = None,
        rdb_instance_id: int = None,
        redis_instance_id: int = None,
        approval_id: int = None,
        alert_id: int = None,
        status: str = "pending"
    ) -> NotificationLog:
        """
        创建通知日志记录
        
        Args:
            db: 数据库会话
            notification_type: 通知类型 (approval/alert/scheduled_task)
            title: 通知标题
            content: 通知内容
            sub_type: 细分类型
            channel_id: 通道ID
            channel_name: 通道名称
            rdb_instance_id: RDB实例ID
            redis_instance_id: Redis实例ID
            approval_id: 审批记录ID
            alert_id: 告警记录ID
            status: 状态
        
        Returns:
            创建的日志记录
        """
        log = NotificationLog(
            notification_type=notification_type,
            title=title,
            content=content,
            sub_type=sub_type,
            channel_id=channel_id,
            channel_name=channel_name,
            rdb_instance_id=rdb_instance_id,
            redis_instance_id=redis_instance_id,
            approval_id=approval_id,
            alert_id=alert_id,
            status=status
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    
    @staticmethod
    def update_notification_log(
        db: Session,
        log: NotificationLog,
        status: str,
        error_message: str = None,
        response_code: int = None,
        response_data: dict = None
    ):
        """更新通知日志"""
        log.status = status
        log.error_message = error_message
        log.response_code = response_code
        log.response_data = response_data
        log.sent_at = datetime.now(timezone.utc)
        db.commit()
    
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
    def decrypt_secret(encrypted_secret: str) -> str:
        """解密密钥"""
        if not encrypted_secret:
            return ""
        try:
            return aes_cipher.decrypt(encrypted_secret)
        except Exception:
            return ""
    
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
    ) -> Dict[str, Any]:
        """
        发送钉钉消息
        
        Args:
            webhook: webhook 地址
            message: 消息内容
            auth_type: 验证类型
            secret: 密钥
            keywords: 关键词列表
        
        Returns:
            发送结果: {
                "success": bool,
                "response_code": int,
                "response_data": dict,
                "error_message": str
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        result = {
            "success": False,
            "response_code": None,
            "response_data": None,
            "error_message": None
        }
        
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
                result["response_code"] = response.status_code
                logger.info(f"钉钉响应: status={response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    result["response_data"] = response_data
                    logger.info(f"钉钉返回: {response_data}")
                    result["success"] = response_data.get("errcode") == 0
                    if not result["success"]:
                        result["error_message"] = response_data.get("errmsg", "未知错误")
                else:
                    result["error_message"] = f"HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"发送钉钉消息失败: {e}")
            result["error_message"] = str(e)
        
        return result
    
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
            channel = db.query(NotificationChannel).filter(
                NotificationChannel.id == binding.channel_id,
                NotificationChannel.is_enabled == True
            ).first()
            
            if not channel:
                continue
            
            # 检查环境过滤
            if binding.environment_id and approval.environment_id != binding.environment_id:
                continue
            
            # 获取通道配置
            config = channel.config or {}
            webhook = config.get("webhook")
            auth_type = config.get("auth_type", "none")
            secret_encrypted = config.get("secret")
            keywords = config.get("keywords", [])
            
            if not webhook:
                continue
            
            # 解密密钥
            secret = None
            if secret_encrypted:
                secret = NotificationService.decrypt_secret(secret_encrypted)
            
            # AI 分析增强（根据全局配置决定是否启用）
            final_content = content
            ai_analysis_enabled = False
            try:
                from sqlalchemy import select as sql_select
                from app.models import GlobalConfig
                config_stmt = sql_select(GlobalConfig).where(
                    GlobalConfig.config_key == "monitor_ai_analysis_enabled"
                )
                config_result = await db.execute(config_stmt)
                config = config_result.scalar_one_or_none()
                if config and config.config_value.lower() in ("true", "1", "yes"):
                    ai_analysis_enabled = True
            except Exception as e:
                logger.debug(f"读取 AI 分析配置失败: {e}")
            
            if ai_analysis_enabled:
                try:
                    from app.services.alert_ai_analyzer import analyze_alert, build_content_with_analysis
                    analysis = await analyze_alert(db, alert)
                    if analysis:
                        final_content = build_content_with_analysis(content, analysis)
                        logger.info(f"告警 {alert.id} AI 分析完成")
                except Exception as e:
                    logger.warning(f"AI 分析失败，使用原始内容: {e}")
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": final_content
                }
            }
            
            # 创建通知日志
            log = NotificationService.create_notification_log(
                db=db,
                notification_type="approval",
                title=title,
                content=content,
                sub_type=approval.change_type,
                channel_id=channel.id,
                channel_name=channel.name,
                rdb_instance_id=approval.rdb_instance_id,
                redis_instance_id=approval.redis_instance_id,
                approval_id=approval.id
            )
            
            # 发送通知
            result = await NotificationService.send_dingtalk_message(
                webhook, message, channel.auth_type, secret, channel.keywords
            )
            
            # 更新日志状态
            NotificationService.update_notification_log(
                db=db,
                log=log,
                status="success" if result["success"] else "failed",
                error_message=result.get("error_message"),
                response_code=result.get("response_code"),
                response_data=result.get("response_data")
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
        from app.models.notification_new import NotificationChannel
        
        logger = logging.getLogger(__name__)
        
        # 检查是否需要通知
        if success and not task.notify_on_success:
            logger.info(f"任务 {task.id} 成功但未配置成功通知，跳过")
            return
        if not success and not task.notify_on_fail:
            logger.info(f"任务 {task.id} 失败但未配置失败通知，跳过")
            return
        
        # 获取通知通道ID列表
        if not task.notify_channels:
            logger.info(f"任务 {task.id} 未配置通知通道，跳过")
            return
        
        channel_ids = [int(cid.strip()) for cid in task.notify_channels.split(",") if cid.strip().isdigit()]
        if not channel_ids:
            logger.info(f"任务 {task.id} 通知通道ID无效，跳过")
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
        
        # 使用新的通知通道系统
        channels = db.query(NotificationChannel).filter(
            NotificationChannel.id.in_(channel_ids),
            NotificationChannel.is_enabled == True
        ).all()
        
        logger.info(f"找到 {len(channels)} 个启用的通知通道")
        
        if not channels:
            logger.warning("没有找到有效的通知通道")
            return
        
        # 发送通知
        for channel in channels:
            try:
                logger.info(f"准备发送通知到通道: {channel.name} (类型: {channel.channel_type})")
                
                # 创建通知日志
                log = NotificationService.create_notification_log(
                    db=db,
                    notification_type="scheduled_task",
                    title=title,
                    content=content,
                    sub_type="success" if success else "failed",
                    channel_id=channel.id,
                    channel_name=channel.name,
                    status="pending"
                )
                
                # 根据通道类型发送通知
                if channel.channel_type == "dingtalk":
                    config = channel.config or {}
                    webhook = config.get("webhook")
                    auth_type = config.get("auth_type", "none")
                    secret_encrypted = config.get("secret")
                    keywords = config.get("keywords", [])
                    
                    if not webhook:
                        logger.warning(f"通道 {channel.name} 未配置 webhook")
                        NotificationService.update_notification_log(
                            db, log, status="failed",
                            error_message="Webhook 地址未配置"
                        )
                        continue
                    
                    # 解密 secret
                    secret = None
                    if secret_encrypted:
                        secret = NotificationService.decrypt_secret(secret_encrypted)
                    
                    # 构建消息
                    message = {
                        "msgtype": "markdown",
                        "markdown": {
                            "title": title,
                            "text": content
                        }
                    }
                    
                    # 发送钉钉消息
                    result = await NotificationService.send_dingtalk_message(
                        webhook, message, auth_type, secret, keywords
                    )
                    logger.info(f"通知发送结果: {result}")
                    
                    # 更新日志状态
                    NotificationService.update_notification_log(
                        db=db,
                        log=log,
                        status="success" if result["success"] else "failed",
                        error_message=result.get("error_message"),
                        response_code=result.get("response_code"),
                        response_data=result.get("response_data")
                    )
                    
                elif channel.channel_type == "webhook":
                    config = channel.config or {}
                    webhook = config.get("webhook")
                    method = config.get("method", "POST")
                    headers = config.get("headers", {})
                    
                    if not webhook:
                        logger.warning(f"通道 {channel.name} 未配置 webhook")
                        NotificationService.update_notification_log(
                            db, log, status="failed",
                            error_message="Webhook 地址未配置"
                        )
                        continue
                    
                    import httpx
                    async with httpx.AsyncClient(timeout=10) as client:
                        if method.upper() == "GET":
                            response = await client.get(webhook, headers=headers)
                        else:
                            payload = {"title": title, "content": content}
                            response = await client.post(webhook, json=payload, headers=headers)
                        
                        status_code = "success" if response.status_code < 400 else "failed"
                        NotificationService.update_notification_log(
                            db, log, status=status_code,
                            response_code=response.status_code
                        )
                        logger.info(f"Webhook通知发送完成: 状态={response.status_code}")
                        
                else:
                    # 其他类型通道暂不支持
                    logger.warning(f"不支持的通道类型: {channel.channel_type}")
                    NotificationService.update_notification_log(
                        db, log, status="failed",
                        error_message=f"暂不支持 {channel.channel_type} 类型的通道"
                    )
                    
            except Exception as e:
                logger.error(f"发送通知到通道 {channel.name} 失败: {e}")


    @staticmethod
    async def send_alert_notification(
        db: Session,
        alert,
        is_aggregated: bool = False
    ):
        """
        发送告警通知
        
        Args:
            db: 数据库会话
            alert: AlertRecord 对象
            is_aggregated: 是否为聚合后的告警
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 如果已发送通知且不是聚合告警，跳过
        if alert.notification_sent and not is_aggregated:
            logger.info(f"告警 {alert.id} 已发送通知，跳过")
            return
        
        # 1. 检查静默规则（非聚合告警才检查）
        if not is_aggregated:
            try:
                from app.services.alert_notification_control import AlertSilenceService
                if AlertSilenceService.check_silence(db, alert):
                    logger.info(f"告警 {alert.id} 命中静默规则，跳过发送")
                    return
            except Exception as e:
                logger.warning(f"检查静默规则失败: {e}")
        
        # 2. 检查频率限制（非聚合告警才检查）
        if not is_aggregated:
            try:
                from app.services.alert_notification_control import AlertRateLimitService
                allowed, reason = AlertRateLimitService.check_rate_limit(db, alert)
                if not allowed:
                    logger.warning(f"告警 {alert.id} 被频率限制: {reason}")
                    return
            except Exception as e:
                logger.warning(f"检查频率限制失败: {e}")
        
        # 获取实例信息
        instance_name = "未知实例"
        if alert.rdb_instance_id:
            from app.models import RDBInstance
            instance = db.query(RDBInstance).filter(RDBInstance.id == alert.rdb_instance_id).first()
            if instance:
                instance_name = instance.name
        elif alert.redis_instance_id:
            from app.models import RedisInstance
            instance = db.query(RedisInstance).filter(RedisInstance.id == alert.redis_instance_id).first()
            if instance:
                instance_name = instance.name
        
        # 指标类型映射
        metric_type_labels = {
            "slow_query": "慢查询",
            "cpu_sql": "高CPU SQL",
            "performance": "性能指标",
            "lock": "锁等待",
            "repl": "主从复制",
            "capacity": "容量告警"
        }
        metric_type_name = metric_type_labels.get(alert.metric_type, alert.metric_type)
        
        # 告警级别映射
        alert_level_labels = {
            "info": "信息",
            "warning": "警告",
            "critical": "严重"
        }
        alert_level_name = alert_level_labels.get(alert.alert_level, alert.alert_level)
        
        # 构建模板变量
        variables = {
            "alert_title": alert.alert_title,
            "instance_name": instance_name,
            "alert_level": alert_level_name,
            "metric_name": metric_type_name,
            "current_value": "-",
            "threshold": "-",
            "trigger_time": alert.created_at.strftime("%m-%d %H:%M") if alert.created_at else "-"
        }
        
        # 渲染模板
        title, content = NotificationService.render_template(
            db=db,
            notification_type="alert",
            sub_type=alert.alert_level,
            **variables
        )
        
        # 获取通知绑定 - 告警类型
        bindings = db.query(NotificationBinding).filter(
            NotificationBinding.notification_type == "alert"
        ).all()
        
        logger.info(f"找到 {len(bindings)} 个告警通知绑定")
        
        if not bindings:
            logger.warning("没有找到告警通知绑定")
            return
        
        # 发送通知
        for binding in bindings:
            logger.info(f"处理绑定: channel_id={binding.channel_id}")
            
            channel = db.query(NotificationChannel).filter(
                NotificationChannel.id == binding.channel_id,
                NotificationChannel.is_enabled == True
            ).first()
            
            if not channel:
                logger.warning(f"通道 {binding.channel_id} 不存在或未启用")
                continue
            
            # 检查环境过滤
            if binding.environment_id:
                env_id = None
                if alert.rdb_instance_id:
                    from app.models import RDBInstance
                    instance = db.query(RDBInstance).filter(RDBInstance.id == alert.rdb_instance_id).first()
                    if instance:
                        env_id = instance.environment_id
                elif alert.redis_instance_id:
                    from app.models import RedisInstance
                    instance = db.query(RedisInstance).filter(RedisInstance.id == alert.redis_instance_id).first()
                    if instance:
                        env_id = instance.environment_id
                
                if env_id and binding.environment_id != env_id:
                    logger.info(f"环境不匹配，跳过")
                    continue
            
            logger.info(f"准备发送告警通知到通道: {channel.name}")
            
            # 获取通道配置
            config = channel.config or {}
            webhook = config.get("webhook")
            auth_type = config.get("auth_type", "none")
            secret_encrypted = config.get("secret")
            keywords = config.get("keywords", [])
            
            if not webhook:
                logger.warning(f"通道 {channel.name} 未配置 webhook")
                continue
            
            # 解密密钥
            secret = None
            if secret_encrypted:
                secret = NotificationService.decrypt_secret(secret_encrypted)
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
            
            # 创建通知日志
            log = NotificationService.create_notification_log(
                db=db,
                notification_type="alert",
                title=title,
                content=content,
                sub_type=alert.alert_level,
                channel_id=channel.id,
                channel_name=channel.name,
                rdb_instance_id=alert.rdb_instance_id,
                redis_instance_id=alert.redis_instance_id,
                alert_id=alert.id
            )
            
            result = await NotificationService.send_dingtalk_message(
                webhook, message, channel.auth_type, secret, channel.keywords
            )
            logger.info(f"告警通知发送结果: {result}")
            
            # 更新日志状态
            NotificationService.update_notification_log(
                db=db,
                log=log,
                status="success" if result["success"] else "failed",
                error_message=result.get("error_message"),
                response_code=result.get("response_code"),
                response_data=result.get("response_data")
            )
        
        # 标记告警已发送通知
        alert.notification_sent = True
        db.commit()
        
        # 记录频率限制（用于下次检查）
        if not is_aggregated:
            try:
                from app.services.alert_notification_control import AlertRateLimitService
                AlertRateLimitService.record_notification_sent(db, alert)
            except Exception as e:
                logger.warning(f"记录频率限制失败: {e}")


# 全局通知服务实例
notification_service = NotificationService()
