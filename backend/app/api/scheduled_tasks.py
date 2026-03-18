"""
定时任务管理API
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from app.database import get_db
from app.models import (
    ScheduledTask, Script, ScriptExecution,
    ExecutionStatus, TriggerType,
    User, UserRole
)
from app.schemas import MessageResponse
from app.deps import get_current_user
from app.services.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])


# ==================== Schemas ====================

class ScheduledTaskCreate(BaseModel):
    """创建定时任务"""
    name: str = Field(..., max_length=100)
    script_id: int
    cron_expression: str = Field(..., description="Cron表达式，如: 0 0 * * * (每天0点)")
    params: Optional[Dict[str, Any]] = Field(default={}, description="执行参数")
    timezone: str = Field("Asia/Shanghai", description="时区")
    max_history: int = Field(100, ge=1, le=1000, description="保留历史记录数")
    notify_on_success: bool = Field(False, description="成功时通知")
    notify_on_fail: bool = Field(True, description="失败时通知")
    notify_channels: Optional[str] = Field(None, description="通知通道ID，逗号分隔")


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务"""
    name: Optional[str] = Field(None, max_length=100)
    cron_expression: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None
    max_history: Optional[int] = Field(None, ge=1, le=1000)
    notify_on_success: Optional[bool] = None
    notify_on_fail: Optional[bool] = None
    notify_channels: Optional[str] = None
    status: Optional[str] = Field(None, description="enabled/disabled")


# ==================== API Endpoints ====================

@router.get("")
async def list_scheduled_tasks(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    script_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取定时任务列表"""
    # 只有管理员和运维可以查看定时任务
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.APPROVAL_ADMIN, UserRole.OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看定时任务"
        )
    
    query = db.query(ScheduledTask)
    
    # 非管理员只能看到自己创建的
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(ScheduledTask.created_by == current_user.id)
    
    if status:
        query = query.filter(ScheduledTask.status == status)
    
    if script_id:
        query = query.filter(ScheduledTask.script_id == script_id)
    
    if search:
        query = query.filter(ScheduledTask.name.contains(search))
    
    total = query.count()
    tasks = query.order_by(desc(ScheduledTask.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [{
            "id": t.id,
            "name": t.name,
            "script_id": t.script_id,
            "script_name": t.script.name if t.script else None,
            "cron_expression": t.cron_expression,
            "status": t.status,
            "timezone": t.timezone,
            "last_run_time": t.last_run_time.isoformat() if t.last_run_time else None,
            "last_run_status": t.last_run_status,
            "next_run_time": t.next_run_time.isoformat() if t.next_run_time else None,
            "run_count": t.run_count,
            "success_count": t.success_count,
            "fail_count": t.fail_count,
            "created_by": t.creator.username if t.creator else None,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in tasks]
    }


@router.post("", response_model=MessageResponse)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建定时任务"""
    # 检查权限
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.APPROVAL_ADMIN, UserRole.OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权创建定时任务"
        )
    
    # 检查脚本是否存在
    script = db.query(Script).filter(Script.id == task_data.script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="脚本不存在"
        )
    
    if not script.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="脚本已禁用"
        )
    
    # 验证 Cron 表达式
    try:
        trigger = CronTrigger.from_crontab(task_data.cron_expression)
        next_run = trigger.get_next_fire_time(None, datetime.now())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cron表达式无效: {str(e)}"
        )
    
    # 创建任务
    task = ScheduledTask(
        name=task_data.name,
        script_id=task_data.script_id,
        cron_expression=task_data.cron_expression,
        params=task_data.params,
        timezone=task_data.timezone,
        max_history=task_data.max_history,
        notify_on_success=task_data.notify_on_success,
        notify_on_fail=task_data.notify_on_fail,
        notify_channels=task_data.notify_channels,
        next_run_time=next_run,
        created_by=current_user.id
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 添加到调度器
    task_scheduler.add_job(task)
    
    return MessageResponse(message=f"定时任务创建成功，ID: {task.id}")


@router.get("/{task_id}")
async def get_scheduled_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取定时任务详情"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此任务"
        )
    
    return {
        "id": task.id,
        "name": task.name,
        "script_id": task.script_id,
        "script_name": task.script.name if task.script else None,
        "cron_expression": task.cron_expression,
        "params": task.params,
        "status": task.status,
        "timezone": task.timezone,
        "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
        "last_run_status": task.last_run_status,
        "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None,
        "run_count": task.run_count,
        "success_count": task.success_count,
        "fail_count": task.fail_count,
        "max_history": task.max_history,
        "notify_on_success": task.notify_on_success,
        "notify_on_fail": task.notify_on_fail,
        "notify_channels": task.notify_channels,
        "created_by": task.creator.username if task.creator else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }


@router.put("/{task_id}", response_model=MessageResponse)
async def update_scheduled_task(
    task_id: int,
    task_data: ScheduledTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此任务"
        )
    
    # 更新字段
    need_reschedule = False
    
    if task_data.name is not None:
        task.name = task_data.name
    
    if task_data.cron_expression is not None:
        # 验证新的 Cron 表达式
        try:
            trigger = CronTrigger.from_crontab(task_data.cron_expression)
            next_run = trigger.get_next_fire_time(None, datetime.now())
            task.cron_expression = task_data.cron_expression
            task.next_run_time = next_run
            need_reschedule = True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cron表达式无效: {str(e)}"
            )
    
    if task_data.params is not None:
        task.params = task_data.params
    
    if task_data.timezone is not None:
        task.timezone = task_data.timezone
        need_reschedule = True
    
    if task_data.max_history is not None:
        task.max_history = task_data.max_history
    
    if task_data.notify_on_success is not None:
        task.notify_on_success = task_data.notify_on_success
    
    if task_data.notify_on_fail is not None:
        task.notify_on_fail = task_data.notify_on_fail
    
    if task_data.notify_channels is not None:
        task.notify_channels = task_data.notify_channels
    
    if task_data.status is not None:
        task.status = task_data.status
        need_reschedule = True
    
    db.commit()
    
    # 重新调度
    if need_reschedule:
        task_scheduler.update_job(task)
    
    return MessageResponse(message="定时任务更新成功")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_scheduled_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此任务"
        )
    
    # 从调度器移除
    task_scheduler.remove_job(task.id)
    
    # 删除数据库记录
    db.delete(task)
    db.commit()
    
    return MessageResponse(message="定时任务删除成功")


@router.post("/{task_id}/trigger", response_model=MessageResponse)
async def trigger_task_manually(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动触发定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权触发此任务"
        )
    
    # 立即执行
    task_scheduler.trigger_now(task, current_user.id)
    
    return MessageResponse(message="任务已触发执行")


@router.post("/{task_id}/pause", response_model=MessageResponse)
async def pause_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """暂停定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权暂停此任务"
        )
    
    task.status = "disabled"
    db.commit()
    
    task_scheduler.pause_job(task.id)
    
    return MessageResponse(message="任务已暂停")


@router.post("/{task_id}/resume", response_model=MessageResponse)
async def resume_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """恢复定时任务"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权恢复此任务"
        )
    
    task.status = "enabled"
    db.commit()
    
    task_scheduler.resume_job(task)
    
    return MessageResponse(message="任务已恢复")


@router.get("/{task_id}/history")
async def get_task_history(
    task_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务执行历史"""
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="定时任务不存在"
        )
    
    # 权限检查
    if current_user.role != UserRole.SUPER_ADMIN and task.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此任务历史"
        )
    
    query = db.query(ScriptExecution).filter(
        ScriptExecution.scheduled_task_id == task_id
    )
    
    total = query.count()
    executions = query.order_by(desc(ScriptExecution.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [{
            "id": e.id,
            "script_name": e.script.name if e.script else None,
            "status": e.status.value,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "duration": e.duration,
            "exit_code": e.exit_code,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in executions]
    }


@router.post("/validate-cron")
async def validate_cron_expression(
    cron_expression: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """验证Cron表达式并返回下几次执行时间"""
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        
        # 计算下5次执行时间
        next_times = []
        next_fire = None
        for _ in range(5):
            next_fire = trigger.get_next_fire_time(next_fire, datetime.now())
            if next_fire:
                next_times.append(next_fire.isoformat())
        
        return {
            "valid": True,
            "next_times": next_times
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
