"""
定时任务调度器
使用 APScheduler 实现定时执行审批工单和文件清理
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ApprovalRecord, ApprovalStatus, Instance, AuditLog, User
from app.services.notification import notification_service
from app.config.storage import get_storage_settings

logger = logging.getLogger(__name__)


class ApprovalScheduler:
    """审批定时执行调度器"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
    
    def start(self):
        """启动调度器"""
        if self.scheduler is not None:
            logger.warning("调度器已经在运行")
            return
        
        self.scheduler = AsyncIOScheduler()
        
        # 添加定时扫描任务：每分钟检查一次需要执行的工单
        self.scheduler.add_job(
            self.check_scheduled_approvals,
            trigger=IntervalTrigger(minutes=1),
            id="check_scheduled_approvals",
            replace_existing=True
        )
        
        # 添加文件清理任务：每天凌晨2点执行
        self.scheduler.add_job(
            self.cleanup_expired_files,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_expired_files",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("审批定时执行调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
            logger.info("审批定时执行调度器已停止")
    
    def schedule_approval_execution(self, approval_id: int, execute_time: datetime):
        """
        调度审批工单在指定时间执行
        
        Args:
            approval_id: 审批ID
            execute_time: 执行时间
        """
        if self.scheduler is None:
            logger.error("调度器未启动")
            return False
        
        job_id = f"approval_execute_{approval_id}"
        
        # 添加定时任务
        self.scheduler.add_job(
            self.execute_approval,
            trigger=DateTrigger(run_date=execute_time),
            id=job_id,
            args=[approval_id],
            replace_existing=True
        )
        
        logger.info(f"已调度审批工单 {approval_id} 在 {execute_time} 执行")
        return True
    
    def cancel_scheduled_execution(self, approval_id: int):
        """
        取消审批工单的定时执行
        
        Args:
            approval_id: 审批ID
        """
        if self.scheduler is None:
            return
        
        job_id = f"approval_execute_{approval_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已取消审批工单 {approval_id} 的定时执行")
        except Exception:
            pass
    
    async def check_scheduled_approvals(self):
        """
        检查需要定时执行的审批工单
        每分钟执行一次，确保没有遗漏
        """
        db = SessionLocal()
        try:
            # 查找已通过且到达执行时间的工单
            now = datetime.now()
            
            approvals = db.query(ApprovalRecord).filter(
                ApprovalRecord.status == ApprovalStatus.APPROVED,
                ApprovalRecord.scheduled_time != None,
                ApprovalRecord.scheduled_time <= now,
                ApprovalRecord.execute_time == None
            ).all()
            
            for approval in approvals:
                logger.info(f"发现需要执行的定时工单: {approval.id}")
                await self.execute_approval(approval.id, db)
            
        except Exception as e:
            logger.error(f"检查定时工单失败: {e}")
        finally:
            db.close()
    
    async def execute_approval(self, approval_id: int, db: Session = None):
        """
        执行审批工单
        
        Args:
            approval_id: 审批ID
            db: 数据库会话（可选）
        """
        own_db = db is None
        if own_db:
            db = SessionLocal()
        
        try:
            approval = db.query(ApprovalRecord).filter(
                ApprovalRecord.id == approval_id
            ).first()
            
            if not approval:
                logger.error(f"审批工单不存在: {approval_id}")
                return
            
            if approval.status != ApprovalStatus.APPROVED:
                logger.warning(f"审批工单状态不是已通过: {approval_id}, 状态: {approval.status}")
                return
            
            if approval.execute_time:
                logger.info(f"审批工单已执行: {approval_id}")
                return
            
            logger.info(f"开始执行审批工单: {approval_id} - {approval.title}")
            
            # 获取实例信息
            instance = db.query(Instance).filter(Instance.id == approval.instance_id).first()
            if not instance:
                logger.error(f"实例不存在: {approval.instance_id}")
                approval.status = ApprovalStatus.FAILED
                approval.execute_result = "实例不存在"
                db.commit()
                return
            
            # 根据 change_type 执行不同的逻辑
            if approval.change_type == "REDIS":
                # 执行 Redis 命令
                execute_result = await self._execute_redis_commands(approval, instance, db)
            else:
                # 执行 SQL
                from app.api.approval import execute_sql_for_approval
                success, result_msg, affected_rows = await execute_sql_for_approval(approval, instance)
                execute_result = result_msg
                approval.affected_rows_actual = affected_rows
            
            # 更新状态
            approval.status = ApprovalStatus.EXECUTED
            approval.execute_time = datetime.now()
            approval.execute_result = execute_result
            
            db.commit()
            
            # 记录审计日志
            audit_log = AuditLog(
                user_id=approval.requester_id,
                username="系统定时任务",
                instance_id=approval.instance_id,
                instance_name=approval.instance.name if approval.instance else None,
                environment_id=approval.environment_id,
                operation_type="scheduled_execute",
                operation_detail=f"定时执行审批: {approval.title}",
                request_ip="127.0.0.1",
                request_method="SCHEDULED",
                request_path=f"/api/approvals/{approval_id}/execute",
                response_code=200
            )
            db.add(audit_log)
            db.commit()
            
            # 发送执行完成通知
            await notification_service.send_approval_notification(db, approval, "executed")
            
            logger.info(f"审批工单执行完成: {approval_id}")
            
        except Exception as e:
            logger.error(f"执行审批工单失败: {approval_id}, 错误: {e}")
            if own_db:
                db.rollback()
        finally:
            if own_db:
                db.close()
    
    async def _execute_redis_commands(self, approval: ApprovalRecord, instance: Instance, db: Session) -> str:
        """
        执行 Redis 命令
        
        Args:
            approval: 审批记录
            instance: Redis 实例
            db: 数据库会话
        
        Returns:
            执行结果描述
        """
        from app.utils.redis_operations import RedisInstanceClient
        from app.utils.auth import decrypt_instance_password
        
        try:
            # 获取命令内容
            commands_content = approval.sql_content
            if not commands_content and approval.sql_file_path:
                from app.services.storage import storage_manager
                commands_content = await storage_manager.read_sql_file(approval.sql_file_path)
            
            if not commands_content:
                return "错误：无命令内容"
            
            # 解密密码
            password = None
            if instance.password_encrypted:
                password = decrypt_instance_password(instance.password_encrypted)
            
            # 创建 Redis 客户端
            client = RedisInstanceClient(
                host=instance.host,
                port=instance.port,
                password=password,
                db=instance.redis_db or 0,
                redis_mode=instance.redis_mode or "standalone"
            )
            
            # 解析并执行命令
            lines = commands_content.strip().split('\n')
            success_count = 0
            fail_count = 0
            results = []
            
            for line in lines:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#') or line.startswith('--'):
                    continue
                
                try:
                    # 解析命令
                    parts = line.split()
                    if not parts:
                        continue
                    
                    cmd = parts[0].upper()
                    args = parts[1:] if len(parts) > 1 else []
                    
                    # 执行命令
                    result = client.client.execute_command(cmd, *args)
                    success_count += 1
                    
                    # 记录结果（简化）
                    if success_count <= 10:  # 只记录前10条
                        results.append(f"✓ {line[:50]}...")
                        
                except Exception as e:
                    fail_count += 1
                    if fail_count <= 5:  # 只记录前5条错误
                        results.append(f"✗ {line[:30]}... 错误: {str(e)[:50]}")
            
            # 构建结果描述
            result_desc = f"执行完成: 成功 {success_count} 条, 失败 {fail_count} 条"
            if results:
                result_desc += "\n" + "\n".join(results[:10])
            
            return result_desc
            
        except Exception as e:
            logger.error(f"执行 Redis 命令失败: {e}")
            return f"执行失败: {str(e)}"
    
    async def cleanup_expired_files(self):
        """
        清理过期的SQL文件
        
        根据配置的保留天数清理过期的SQL文件
        保留数据库中的历史记录，只清理物理文件
        """
        from app.services.storage import storage_manager
        
        try:
            settings = get_storage_settings()
            retention_days = settings.SQL_FILE_RETENTION_DAYS
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            logger.info(f"开始清理过期SQL文件，保留天数: {retention_days}, 截止日期: {cutoff_date}")
            
            db = SessionLocal()
            try:
                # 查找过期的审批记录（只清理已执行/已拒绝的）
                expired_approvals = db.query(ApprovalRecord).filter(
                    ApprovalRecord.created_at < cutoff_date,
                    ApprovalRecord.status.in_([
                        ApprovalStatus.EXECUTED,
                        ApprovalStatus.REJECTED,
                        ApprovalStatus.FAILED
                    ]),
                    ApprovalRecord.sql_file_path != None
                ).all()
                
                cleaned_count = 0
                for approval in expired_approvals:
                    try:
                        # 删除SQL文件
                        if approval.sql_file_path:
                            await storage_manager.delete_sql_file(approval.sql_file_path)
                            approval.sql_file_path = None
                            cleaned_count += 1
                        
                        # 删除回滚SQL文件
                        if approval.rollback_file_path:
                            await storage_manager.delete_sql_file(approval.rollback_file_path)
                            approval.rollback_file_path = None
                        
                        # 保留数据库记录和预览
                        # sql_content 和 rollback_sql 如果存在则保留（小文件）
                        
                    except Exception as e:
                        logger.warning(f"清理文件失败: approval_id={approval.id}, error={e}")
                
                db.commit()
                logger.info(f"清理完成，共清理 {cleaned_count} 个SQL文件")
                
                # 如果是本地存储，额外清理孤立文件
                cleaned_orphans = await storage_manager.cleanup_expired_files()
                if cleaned_orphans > 0:
                    logger.info(f"清理孤立文件: {cleaned_orphans} 个")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"清理过期文件任务失败: {e}")


# 全局调度器实例
approval_scheduler = ApprovalScheduler()
