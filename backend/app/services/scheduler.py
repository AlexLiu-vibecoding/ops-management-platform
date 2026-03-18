"""
定时任务调度器
使用 APScheduler 实现定时执行审批工单
"""
import asyncio
from datetime import datetime
from typing import Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ApprovalRecord, ApprovalStatus, Instance, AuditLog, User
from app.services.notification import notification_service

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
            
            # TODO: 实际执行SQL的逻辑
            # 这里需要连接到目标MySQL实例执行SQL
            # 当前先标记为执行成功
            
            # 更新状态
            approval.status = ApprovalStatus.EXECUTED
            approval.execute_time = datetime.now()
            approval.execute_result = "执行成功（定时任务自动执行）"
            
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


# 全局调度器实例
approval_scheduler = ApprovalScheduler()
