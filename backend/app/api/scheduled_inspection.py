"""
定时巡检API - 定时巡检任务管理、执行、历史记录
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, Field
from croniter import croniter

from app.database import get_db
from app.models import (
    ScheduledInspection, InspectionExecution, RDBInstance, 
    Environment, User
)
from app.schemas import MessageResponse
from app.deps import get_current_user, get_operator
from app.services.inspection_service import InspectionService

router = APIRouter(prefix="/scheduled-inspections", tags=["定时巡检"])


# ==================== Schemas ====================

class ScheduledInspectionCreate(BaseModel):
    """创建定时巡检任务"""
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="描述")
    instance_scope: str = Field("all", description="实例范围: all/selected")
    instance_ids: Optional[List[int]] = Field(None, description="选中的实例ID列表")
    modules: Optional[List[str]] = Field(None, description="检查模块列表")
    cron_expression: str = Field(..., description="Cron表达式")
    timezone: str = Field("Asia/Shanghai", description="时区")
    notify_on_complete: bool = Field(True, description="完成时通知")
    notify_on_warning: bool = Field(True, description="发现警告时通知")
    notify_on_critical: bool = Field(True, description="发现严重问题时通知")
    notify_channels: Optional[str] = Field(None, description="通知通道ID列表")


class ScheduledInspectionUpdate(BaseModel):
    """更新定时巡检任务"""
    name: Optional[str] = None
    description: Optional[str] = None
    instance_scope: Optional[str] = None
    instance_ids: Optional[List[int]] = None
    modules: Optional[List[str]] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[str] = None
    notify_on_complete: Optional[bool] = None
    notify_on_warning: Optional[bool] = None
    notify_on_critical: Optional[bool] = None
    notify_channels: Optional[str] = None


class ValidateCronResponse(BaseModel):
    """验证Cron表达式响应"""
    valid: bool
    error: Optional[str] = None
    next_times: Optional[List[str]] = None


# ==================== APIs ====================

@router.get("", response_model=dict)
async def list_scheduled_inspections(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取定时巡检任务列表"""
    query = db.query(ScheduledInspection)
    
    if status:
        query = query.filter(ScheduledInspection.status == status)
    if search:
        query = query.filter(ScheduledInspection.name.ilike(f"%{search}%"))
    
    total = query.count()
    items = query.order_by(desc(ScheduledInspection.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取创建人名称
    user_ids = [i.created_by for i in items if i.created_by]
    users = {u.id: u.real_name or u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    return {
        "total": total,
        "items": [{
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "instance_scope": i.instance_scope,
            "instance_ids": i.instance_ids,
            "modules": i.modules,
            "cron_expression": i.cron_expression,
            "timezone": i.timezone,
            "status": i.status,
            "last_run_time": i.last_run_time.isoformat() if i.last_run_time else None,
            "last_run_status": i.last_run_status,
            "next_run_time": i.next_run_time.isoformat() if i.next_run_time else None,
            "run_count": i.run_count,
            "success_count": i.success_count,
            "fail_count": i.fail_count,
            "notify_on_complete": i.notify_on_complete,
            "notify_on_warning": i.notify_on_warning,
            "notify_on_critical": i.notify_on_critical,
            "notify_channels": i.notify_channels,
            "created_by": i.created_by,
            "created_by_name": users.get(i.created_by),
            "created_at": i.created_at.isoformat() if i.created_at else None
        } for i in items]
    }


@router.post("", response_model=MessageResponse)
async def create_scheduled_inspection(
    data: ScheduledInspectionCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """创建定时巡检任务"""
    # 验证Cron表达式
    try:
        croniter(data.cron_expression)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的Cron表达式: {str(e)}")
    
    # 计算下次执行时间
    cron = croniter(data.cron_expression, datetime.now())
    next_run_time = cron.get_next(datetime)
    
    task = ScheduledInspection(
        name=data.name,
        description=data.description,
        instance_scope=data.instance_scope,
        instance_ids=data.instance_ids,
        modules=data.modules,
        cron_expression=data.cron_expression,
        timezone=data.timezone,
        next_run_time=next_run_time,
        notify_on_complete=data.notify_on_complete,
        notify_on_warning=data.notify_on_warning,
        notify_on_critical=data.notify_on_critical,
        notify_channels=data.notify_channels,
        created_by=current_user.id
    )
    
    db.add(task)
    db.commit()
    
    return MessageResponse(message="创建成功")


@router.get("/{task_id}", response_model=dict)
async def get_scheduled_inspection(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取定时巡检任务详情"""
    task = db.query(ScheduledInspection).filter(ScheduledInspection.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    created_by_name = None
    if task.created_by:
        user = db.query(User).filter(User.id == task.created_by).first()
        created_by_name = user.real_name or user.username if user else None
    
    # 获取实例名称
    instance_names = []
    if task.instance_ids:
        instances = db.query(RDBInstance).filter(RDBInstance.id.in_(task.instance_ids)).all()
        instance_names = [{"id": i.id, "name": i.name} for i in instances]
    
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "instance_scope": task.instance_scope,
        "instance_ids": task.instance_ids,
        "instance_names": instance_names,
        "modules": task.modules,
        "cron_expression": task.cron_expression,
        "timezone": task.timezone,
        "status": task.status,
        "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
        "last_run_status": task.last_run_status,
        "next_run_time": task.next_run_time.isoformat() if task.next_run_time else None,
        "run_count": task.run_count,
        "success_count": task.success_count,
        "fail_count": task.fail_count,
        "notify_on_complete": task.notify_on_complete,
        "notify_on_warning": task.notify_on_warning,
        "notify_on_critical": task.notify_on_critical,
        "notify_channels": task.notify_channels,
        "created_by": task.created_by,
        "created_by_name": created_by_name,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }


@router.put("/{task_id}", response_model=MessageResponse)
async def update_scheduled_inspection(
    task_id: int,
    data: ScheduledInspectionUpdate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """更新定时巡检任务"""
    task = db.query(ScheduledInspection).filter(ScheduledInspection.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    if data.name is not None:
        task.name = data.name
    if data.description is not None:
        task.description = data.description
    if data.instance_scope is not None:
        task.instance_scope = data.instance_scope
    if data.instance_ids is not None:
        task.instance_ids = data.instance_ids
    if data.modules is not None:
        task.modules = data.modules
    if data.cron_expression is not None:
        try:
            croniter(data.cron_expression)
            task.cron_expression = data.cron_expression
            # 重新计算下次执行时间
            cron = croniter(data.cron_expression, datetime.now())
            task.next_run_time = cron.get_next(datetime)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的Cron表达式: {str(e)}")
    if data.timezone is not None:
        task.timezone = data.timezone
    if data.status is not None:
        task.status = data.status
    if data.notify_on_complete is not None:
        task.notify_on_complete = data.notify_on_complete
    if data.notify_on_warning is not None:
        task.notify_on_warning = data.notify_on_warning
    if data.notify_on_critical is not None:
        task.notify_on_critical = data.notify_on_critical
    if data.notify_channels is not None:
        task.notify_channels = data.notify_channels
    
    db.commit()
    return MessageResponse(message="更新成功")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_scheduled_inspection(
    task_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """删除定时巡检任务"""
    task = db.query(ScheduledInspection).filter(ScheduledInspection.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    db.delete(task)
    db.commit()
    return MessageResponse(message="删除成功")


@router.post("/{task_id}/toggle", response_model=MessageResponse)
async def toggle_scheduled_inspection(
    task_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """启用/禁用定时巡检任务"""
    task = db.query(ScheduledInspection).filter(ScheduledInspection.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    task.status = "disabled" if task.status == "enabled" else "enabled"
    
    # 如果启用，重新计算下次执行时间
    if task.status == "enabled":
        cron = croniter(task.cron_expression, datetime.now())
        task.next_run_time = cron.get_next(datetime)
    
    db.commit()
    return MessageResponse(message=f"任务已{'禁用' if task.status == 'disabled' else '启用'}")


@router.post("/{task_id}/run", response_model=dict)
async def run_scheduled_inspection(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动执行巡检任务"""
    task = db.query(ScheduledInspection).filter(ScheduledInspection.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    # 创建执行记录
    execution = InspectionExecution(
        scheduled_inspection_id=task.id,
        trigger_type="manual",
        triggered_by=current_user.id,
        status="running",
        start_time=datetime.now()
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # 异步执行巡检
    inspection_service = InspectionService(db)
    background_tasks.add_task(
        inspection_service.run_inspection,
        task,
        execution
    )
    
    return {
        "message": "巡检任务已开始执行",
        "execution_id": execution.id
    }


@router.post("/validate-cron", response_model=ValidateCronResponse)
async def validate_cron(
    cron_expression: str,
    current_user: User = Depends(get_current_user)
):
    """验证Cron表达式"""
    try:
        cron = croniter(cron_expression, datetime.now())
        next_times = [cron.get_next(datetime).isoformat() for _ in range(5)]
        return ValidateCronResponse(valid=True, next_times=next_times)
    except Exception as e:
        return ValidateCronResponse(valid=False, error=str(e))


# ==================== 执行记录 ====================

@router.get("/{task_id}/executions", response_model=dict)
async def list_executions(
    task_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取执行记录列表"""
    query = db.query(InspectionExecution).filter(InspectionExecution.scheduled_inspection_id == task_id)
    
    total = query.count()
    items = query.order_by(desc(InspectionExecution.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "items": [{
            "id": e.id,
            "trigger_type": e.trigger_type,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "duration": e.duration,
            "status": e.status,
            "total_instances": e.total_instances,
            "normal_count": e.normal_count,
            "warning_count": e.warning_count,
            "critical_count": e.critical_count,
            "error_count": e.error_count,
            "error_message": e.error_message,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in items]
    }


@router.get("/executions/{execution_id}", response_model=dict)
async def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取执行记录详情"""
    execution = db.query(InspectionExecution).filter(InspectionExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行记录不存在")
    
    return {
        "id": execution.id,
        "scheduled_inspection_id": execution.scheduled_inspection_id,
        "trigger_type": execution.trigger_type,
        "start_time": execution.start_time.isoformat() if execution.start_time else None,
        "end_time": execution.end_time.isoformat() if execution.end_time else None,
        "duration": execution.duration,
        "status": execution.status,
        "total_instances": execution.total_instances,
        "normal_count": execution.normal_count,
        "warning_count": execution.warning_count,
        "critical_count": execution.critical_count,
        "error_count": execution.error_count,
        "summary": execution.summary,
        "details": execution.details,
        "error_message": execution.error_message,
        "created_at": execution.created_at.isoformat() if execution.created_at else None
    }


@router.get("/modules/list")
async def get_modules():
    """获取巡检模块列表"""
    return [
        {"value": "slow_query", "label": "慢查询"},
        {"value": "index", "label": "索引分析"},
        {"value": "lock", "label": "锁等待"},
        {"value": "transaction", "label": "长事务"},
        {"value": "repl", "label": "主从复制"},
        {"value": "capacity", "label": "容量分析"}
    ]
