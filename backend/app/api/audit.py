"""
审计日志API
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse, PaginatedResponse
from app.deps import get_current_user, require_permission

router = APIRouter(prefix="/audit", tags=["审计日志"])


# 操作类型中英文映射
OPERATION_TYPE_MAP: dict[str, dict[str, str]] = {
    "login": {"zh": "登录", "en": "Login"},
    "logout": {"zh": "登出", "en": "Logout"},
    "create_instance": {"zh": "创建实例", "en": "Create Instance"},
    "update_instance": {"zh": "更新实例", "en": "Update Instance"},
    "delete_instance": {"zh": "删除实例", "en": "Delete Instance"},
    "execute_sql": {"zh": "执行SQL", "en": "Execute SQL"},
    "submit_approval": {"zh": "提交审批", "en": "Submit Approval"},
    "approve": {"zh": "审批通过", "en": "Approve"},
    "reject": {"zh": "审批拒绝", "en": "Reject"},
    "execute_approval": {"zh": "执行变更", "en": "Execute Change"},
    "scheduled_execute": {"zh": "定时执lines", "en": "Scheduled Execute"},
    "create_script": {"zh": "创建脚本", "en": "Create Script"},
    "update_script": {"zh": "更新脚本", "en": "Update Script"},
    "delete_script": {"zh": "删除脚本", "en": "Delete Script"},
    "execute_script": {"zh": "执行脚本", "en": "Execute Script"},
    "create_schedule": {"zh": "创建定时任务", "en": "Create Schedule"},
    "update_schedule": {"zh": "更新定时任务", "en": "Update Schedule"},
    "delete_schedule": {"zh": "删除定时任务", "en": "Delete Schedule"},
    "export_data": {"zh": "导出数据", "en": "Export Data"},
    "import_data": {"zh": "导入数据", "en": "Import Data"},
}


def get_operation_type_label(operation_type: str, lang: str = "zh") -> str:
    """获取操作类型的显示标签"""
    if operation_type in OPERATION_TYPE_MAP:
        return OPERATION_TYPE_MAP[operation_type].get(lang, operation_type)
    return operation_type


def format_log_response(log: AuditLog, lang: str = "zh") -> dict:
    """格式化日志响应，添加中文操作类型"""
    data = AuditLogResponse.model_validate(log).model_dump()
    data["operation_type_label"] = get_operation_type_label(log.operation_type, lang)
    return data


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
    current_user: User = Depends(require_permission("system:audit_log")),
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
        data=[format_log_response(log) for log in logs]
    )


@router.get("/logs/{log_id}")
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
            detail="Audit log not found"
        )
    
    # 权限检查
    if current_user.role.value == "readonly" and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to view this log"
        )
    
    return format_log_response(log)


@router.get("/operation-types")
async def get_operation_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有操作类型（带中文标签）"""
    types = db.query(AuditLog.operation_type).distinct().all()
    result = []
    for t in types:
        if t[0]:
            result.append({
                "value": t[0],
                "label": get_operation_type_label(t[0])
            })
    return result


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
            get_operation_type_label(log.operation_type),  # 使用中文操作类型
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
