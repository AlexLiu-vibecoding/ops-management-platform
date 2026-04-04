"""
后台任务调度管理 API
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.api.auth import get_current_user
from app.services.permission_service import PermissionService
from app.services.scheduler import approval_scheduler
from app.services.task_scheduler import task_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class JobInfo(BaseModel):
    """任务信息"""
    id: str
    name: str
    task_type: str  # system, scheduled, approval
    trigger_type: str  # cron, interval, date
    trigger_config: str
    next_run_time: Optional[datetime]
    status: str  # running, paused, pending
    handler: str
    description: str = ""


class SchedulerStatus(BaseModel):
    """调度器状态"""
    name: str
    is_running: bool
    job_count: int
    jobs: list[JobInfo]


class SchedulerOverview(BaseModel):
    """调度器概览"""
    approval_scheduler: SchedulerStatus
    task_scheduler: SchedulerStatus
    total_jobs: int
    running_jobs: int
    paused_jobs: int


class JobAction(BaseModel):
    """任务操作"""
    action: str  # pause, resume, trigger


def get_job_info(job, task_type: str) -> JobInfo:
    """将 APScheduler Job 转换为 JobInfo"""
    trigger = job.trigger
    
    # 确定触发器类型
    if hasattr(trigger, 'fields'):
        trigger_type = "cron"
        # fields 是一个列表，需要转换为字典
        fields_dict = {f.name: str(f) for f in trigger.fields}
        parts = [
            fields_dict.get('minute', '*'),
            fields_dict.get('hour', '*'),
            fields_dict.get('day', '*'),
            fields_dict.get('month', '*'),
            fields_dict.get('day_of_week', '*'),
        ]
        trigger_config = ' '.join(parts)
    elif hasattr(trigger, 'interval'):
        trigger_type = "interval"
        interval = trigger.interval
        total_seconds = int(interval.total_seconds())
        if total_seconds >= 3600:
            trigger_config = f"每 {total_seconds // 3600} 小时"
        elif total_seconds >= 60:
            trigger_config = f"每 {total_seconds // 60} 分钟"
        else:
            trigger_config = f"每 {total_seconds} 秒"
    elif hasattr(trigger, 'run_date'):
        trigger_type = "date"
        trigger_config = str(trigger.run_date)
    else:
        trigger_type = "unknown"
        trigger_config = str(trigger)
    
    # 确定任务状态
    next_run = job.next_run_time
    if next_run is None:
        status = "paused"
    else:
        status = "running"
    
    # 任务描述
    descriptions = {
        "check_scheduled_approvals": "检查定时审批工单",
        "cleanup_expired_files": "清理过期SQL文件",
        "rds_performance_collector": "RDS性能指标采集",
    }
    
    # 处理器名称
    handler = ""
    if job.func:
        if hasattr(job.func, '__name__'):
            handler = job.func.__name__
        elif hasattr(job.func, 'func'):
            handler = job.func.func.__name__ if hasattr(job.func.func, '__name__') else str(job.func.func)
        else:
            handler = str(job.func)
    
    return JobInfo(
        id=job.id,
        name=job.name or job.id,
        task_type=task_type,
        trigger_type=trigger_type,
        trigger_config=trigger_config,
        next_run_time=next_run,
        status=status,
        handler=handler,
        description=descriptions.get(job.id, "")
    )


@router.get("/overview", response_model=SchedulerOverview)
async def get_scheduler_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取调度器概览
    
    需要权限: scheduler:view
    """
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "scheduler:view")
    
    # 获取审批调度器状态
    approval_jobs = []
    approval_running = False
    if approval_scheduler.scheduler:
        approval_running = approval_scheduler.scheduler.running
        for job in approval_scheduler.scheduler.get_jobs():
            approval_jobs.append(get_job_info(job, "approval"))
    
    approval_status = SchedulerStatus(
        name="审批调度器",
        is_running=approval_running,
        job_count=len(approval_jobs),
        jobs=approval_jobs
    )
    
    # 获取任务调度器状态
    task_jobs = []
    task_running = False
    if task_scheduler.scheduler:
        task_running = task_scheduler.scheduler.running
        for job in task_scheduler.scheduler.get_jobs():
            task_jobs.append(get_job_info(job, "scheduled"))
    
    task_status = SchedulerStatus(
        name="任务调度器",
        is_running=task_running,
        job_count=len(task_jobs),
        jobs=task_jobs
    )
    
    # 统计
    all_jobs = approval_jobs + task_jobs
    running_count = sum(1 for j in all_jobs if j.status == "running")
    paused_count = sum(1 for j in all_jobs if j.status == "paused")
    
    return SchedulerOverview(
        approval_scheduler=approval_status,
        task_scheduler=task_status,
        total_jobs=len(all_jobs),
        running_jobs=running_count,
        paused_jobs=paused_count
    )


@router.get("/jobs", response_model=list[JobInfo])
async def get_all_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有任务列表
    
    需要权限: scheduler:view
    """
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "scheduler:view")
    
    all_jobs = []
    
    # 从审批调度器获取
    if approval_scheduler.scheduler:
        for job in approval_scheduler.scheduler.get_jobs():
            all_jobs.append(get_job_info(job, "approval"))
    
    # 从任务调度器获取
    if task_scheduler.scheduler:
        for job in task_scheduler.scheduler.get_jobs():
            all_jobs.append(get_job_info(job, "scheduled"))
    
    # 按类型和下次执行时间排序
    def sort_key(job):
        # 系统任务优先
        type_order = {"approval": 0, "scheduled": 1, "system": 2}
        # 有执行时间的排前面
        if job.next_run_time:
            return (type_order.get(job.task_type, 3), 0, job.next_run_time)
        else:
            return (type_order.get(job.task_type, 3), 1, datetime.max)
    
    all_jobs.sort(key=sort_key)
    
    return all_jobs


@router.get("/jobs/{job_id}", response_model=JobInfo)
async def get_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取任务详情
    
    需要权限: scheduler:view
    """
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "scheduler:view")
    
    # 在两个调度器中查找
    if approval_scheduler.scheduler:
        job = approval_scheduler.scheduler.get_job(job_id)
        if job:
            return get_job_info(job, "approval")
    
    if task_scheduler.scheduler:
        job = task_scheduler.scheduler.get_job(job_id)
        if job:
            return get_job_info(job, "scheduled")
    
    raise HTTPException(status_code=404, detail="任务不存在")


@router.post("/jobs/{job_id}/action")
async def job_action(
    job_id: str,
    action: JobAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    执行任务操作
    
    支持操作:
    - pause: 暂停任务
    - resume: 恢复任务
    - trigger: 立即触发
    
    需要权限: scheduler:manage
    """
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "scheduler:manage")
    
    # 确定任务属于哪个调度器
    scheduler = None
    
    if approval_scheduler.scheduler:
        job = approval_scheduler.scheduler.get_job(job_id)
        if job:
            scheduler = approval_scheduler.scheduler
    
    if not scheduler and task_scheduler.scheduler:
        job = task_scheduler.scheduler.get_job(job_id)
        if job:
            scheduler = task_scheduler.scheduler
    
    if not scheduler:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    try:
        if action.action == "pause":
            scheduler.pause_job(job_id)
            return {"message": "任务已暂停", "job_id": job_id}
        
        elif action.action == "resume":
            scheduler.resume_job(job_id)
            return {"message": "任务已恢复", "job_id": job_id}
        
        elif action.action == "trigger":
            # 立即触发需要特殊处理
            # 对于定时脚本任务，使用 task_scheduler 的方法
            if job_id.startswith("scheduled_task_"):
                from app.models import ScheduledTask
                task_id = int(job_id.replace("scheduled_task_", ""))
                task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if task:
                    task_scheduler.trigger_now(task, current_user.id)
                    return {"message": "任务已触发执行", "job_id": job_id}
                else:
                    raise HTTPException(status_code=404, detail="定时任务不存在")
            else:
                # 对于系统任务，直接修改执行时间
                scheduler.modify_job(job_id, next_run_time=datetime.now())
                return {"message": "任务已触发执行", "job_id": job_id}
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {action.action}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.get("/health")
async def scheduler_health():
    """
    调度器健康检查
    
    无需权限，用于监控系统
    """
    approval_ok = approval_scheduler.scheduler is not None and approval_scheduler.scheduler.running
    task_ok = task_scheduler.scheduler is not None and task_scheduler.scheduler.running
    
    return {
        "approval_scheduler": {
            "status": "running" if approval_ok else "stopped",
            "running": approval_ok
        },
        "task_scheduler": {
            "status": "running" if task_ok else "stopped",
            "running": task_ok
        },
        "overall": "healthy" if (approval_ok and task_ok) else "degraded"
    }
