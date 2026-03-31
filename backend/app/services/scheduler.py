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
from app.models import ApprovalRecord, ApprovalStatus, RDBInstance, RedisInstance, AuditLog, User
from app.services.notification import notification_service
from app.services.sql_executor import sql_executor, redis_executor
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
        
        # 添加慢日志文件清理任务：每天凌晨3点执行
        self.scheduler.add_job(
            self.cleanup_expired_slow_log_files,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup_expired_slow_log_files",
            replace_existing=True
        )
        
        # 添加分析历史清理任务：每天凌晨4点执行
        self.scheduler.add_job(
            self.cleanup_expired_analysis_history,
            trigger=CronTrigger(hour=4, minute=0),
            id="cleanup_expired_analysis_history",
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
            
            # 获取实例信息 - 支持新的拆分表结构
            instance = None
            instance_type = None
            
            if approval.rdb_instance_id:
                instance = db.query(RDBInstance).filter(RDBInstance.id == approval.rdb_instance_id).first()
                instance_type = "rdb"
            elif approval.redis_instance_id:
                instance = db.query(RedisInstance).filter(RedisInstance.id == approval.redis_instance_id).first()
                instance_type = "redis"
            elif approval.instance_id:
                # 向后兼容：旧数据可能使用 instance_id
                # 尝试从两个表中查找
                instance = db.query(RDBInstance).filter(RDBInstance.id == approval.instance_id).first()
                if instance:
                    instance_type = "rdb"
                else:
                    instance = db.query(RedisInstance).filter(RedisInstance.id == approval.instance_id).first()
                    instance_type = "redis"
            
            if not instance:
                logger.error(f"实例不存在: approval_id={approval_id}")
                approval.status = ApprovalStatus.FAILED
                approval.execute_result = "实例不存在"
                db.commit()
                return
            
            # 根据 change_type 执行不同的逻辑
            if approval.change_type == "REDIS" or instance_type == "redis":
                # 执行 Redis 命令
                execute_result = await redis_executor.execute_for_approval(approval, instance)
                execution_success = sql_executor.check_execution_success(execute_result)
            else:
                # 执行 SQL
                success, execute_result, affected_rows = await sql_executor.execute_for_approval(approval, instance)
                approval.affected_rows_actual = affected_rows
                execution_success = sql_executor.check_execution_success(execute_result)
            
            # 更新状态
            if execution_success:
                approval.status = ApprovalStatus.EXECUTED
            else:
                approval.status = ApprovalStatus.FAILED
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
            # 发送失败通知
            try:
                if own_db:
                    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
                    if approval:
                        approval.status = ApprovalStatus.FAILED
                        approval.execute_time = datetime.now()
                        approval.execute_result = f"执行失败: {str(e)}"
                        db.commit()
                        await notification_service.send_approval_notification(db, approval, "executed")
            except Exception as notify_error:
                logger.error(f"发送失败通知失败: {notify_error}")
            if own_db:
                db.rollback()
        finally:
            if own_db:
                db.close()
    
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
    
    async def cleanup_expired_slow_log_files(self):
        """
        清理过期的慢日志文件
        
        上传的慢日志文件保留30天后自动删除
        同时删除关联的分析历史记录
        """
        from app.models import SlowLogFile, SQLAnalysisHistory
        import os
        
        db = SessionLocal()
        try:
            now = datetime.now()
            
            # 查找过期的慢日志文件（expire_at <= now）
            expired_files = db.query(SlowLogFile).filter(
                SlowLogFile.expire_at <= now
            ).all()
            
            logger.info(f"开始清理过期慢日志文件，共 {len(expired_files)} 个")
            
            cleaned_files = 0
            cleaned_history = 0
            
            for file in expired_files:
                try:
                    # 删除物理文件
                    if file.file_path and os.path.exists(file.file_path):
                        os.remove(file.file_path)
                        logger.debug(f"删除物理文件: {file.file_path}")
                    
                    # 删除关联的分析历史
                    history_count = db.query(SQLAnalysisHistory).filter(
                        SQLAnalysisHistory.source_file_id == file.id
                    ).delete()
                    cleaned_history += history_count
                    
                    # 删除数据库记录
                    db.delete(file)
                    cleaned_files += 1
                    
                except Exception as e:
                    logger.warning(f"清理慢日志文件失败: file_id={file.id}, error={e}")
            
            db.commit()
            logger.info(
                f"慢日志文件清理完成: 文件 {cleaned_files} 个, "
                f"分析历史 {cleaned_history} 条"
            )
            
        except Exception as e:
            logger.error(f"清理过期慢日志文件失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def cleanup_expired_analysis_history(self):
        """
        清理过期的分析历史记录
        
        分析历史保留1年后自动删除
        """
        from app.models import SQLAnalysisHistory
        
        db = SessionLocal()
        try:
            now = datetime.now()
            
            # 查找过期的分析历史（expire_at <= now）
            expired_history = db.query(SQLAnalysisHistory).filter(
                SQLAnalysisHistory.expire_at <= now
            ).all()
            
            logger.info(f"开始清理过期分析历史，共 {len(expired_history)} 条")
            
            cleaned_count = 0
            for history in expired_history:
                try:
                    db.delete(history)
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"清理分析历史失败: history_id={history.id}, error={e}")
            
            db.commit()
            logger.info(f"分析历史清理完成: {cleaned_count} 条")
            
        except Exception as e:
            logger.error(f"清理过期分析历史失败: {e}")
            db.rollback()
        finally:
            db.close()


# 全局调度器实例
approval_scheduler = ApprovalScheduler()
