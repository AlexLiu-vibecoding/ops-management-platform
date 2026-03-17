"""
审计日志API
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse, PaginatedResponse
from app.deps import get_current_user

router = APIRouter(prefix="/audit", tags=["审计日志"])


@router.get("/logs", response_model=PaginatedResponse)
async def list_audit_logs(
    user_id: Optional[int] = None,
    instance_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    operation_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审计日志列表"""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if instance_id:
        query = query.filter(AuditLog.instance_id == instance_id)
    if environment_id:
        query = query.filter(AuditLog.environment_id == environment_id)
    if operation_type:
        query = query.filter(AuditLog.operation_type == operation_type)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    
    # 普通用户只能看自己的日志
    if current_user.role.value == "readonly":
        query = query.filter(AuditLog.user_id == current_user.id)
    
    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        data=[AuditLogResponse.from_orm(log) for log in logs]
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审计日志详情"""
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审计日志不存在"
        )
    
    # 权限检查
    if current_user.role.value == "readonly" and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此日志"
        )
    
    return AuditLogResponse.from_orm(log)


@router.get("/operation-types", response_model=List[str])
async def get_operation_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有操作类型"""
    types = db.query(AuditLog.operation_type).distinct().all()
    return [t[0] for t in types if t[0]]


@router.get("/export")
async def export_audit_logs(
    user_id: Optional[int] = None,
    instance_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出审计日志"""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if instance_id:
        query = query.filter(AuditLog.instance_id == instance_id)
    if environment_id:
        query = query.filter(AuditLog.environment_id == environment_id)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    
    # 普通用户只能导出自己的日志
    if current_user.role.value == "readonly":
        query = query.filter(AuditLog.user_id == current_user.id)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(10000).all()
    
    # 转换为CSV格式
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow([
        'ID', '用户名', '实例', '环境', '操作类型', 
        '操作详情', '请求IP', '请求方法', '请求路径',
        '响应码', '响应消息', '执行时间(ms)', '创建时间'
    ])
    
    # 写入数据
    for log in logs:
        writer.writerow([
            log.id,
            log.username,
            log.instance_name,
            log.environment_name,
            log.operation_type,
            log.operation_detail[:200] if log.operation_detail else '',
            log.request_ip,
            log.request_method,
            log.request_path,
            log.response_code,
            log.response_message,
            log.execution_time,
            log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
