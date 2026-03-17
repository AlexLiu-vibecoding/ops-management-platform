"""
变更审批API
"""
import re
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    ApprovalRecord, ApprovalStatus, Instance, User, AuditLog
)
from app.schemas import (
    ApprovalCreate, ApprovalAction, ApprovalResponse,
    MessageResponse
)
from app.deps import get_approval_admin, get_current_user

router = APIRouter(prefix="/approvals", tags=["变更审批"])

# 大文件预览行数限制
PREVIEW_LINES = 100


def get_sql_preview(sql_content: str, max_lines: int = PREVIEW_LINES) -> str:
    """
    获取SQL预览内容（截取前N行）
    """
    lines = sql_content.split('\n')
    if len(lines) <= max_lines:
        return sql_content
    return '\n'.join(lines[:max_lines])


def analyze_sql_risk(sql: str, environment_id: int, db: Session) -> str:
    """
    分析SQL风险等级
    返回: critical/high/medium/low
    """
    sql_upper = sql.upper().strip()
    
    # 极高风险：删除数据库、截断表
    critical_patterns = [
        r'\bDROP\s+DATABASE\b',
        r'\bDROP\s+SCHEMA\b',
        r'\bTRUNCATE\s+TABLE\b',
        r'\bTRUNCATE\b',
    ]
    
    # 高风险：删除表、删除数据无WHERE
    high_patterns = [
        r'\bDROP\s+TABLE\b',
        r'\bDELETE\s+FROM\b.*(?<!WHERE\b)',  # DELETE无WHERE
        r'\bUPDATE\b.*(?<!WHERE\b)',  # UPDATE无WHERE
        r'\bALTER\s+TABLE\b.*\bDROP\b',
        r'\bALTER\s+TABLE\b.*\bMODIFY\b',
    ]
    
    # 中风险：ALTER、CREATE
    medium_patterns = [
        r'\bALTER\s+TABLE\b',
        r'\bCREATE\s+TABLE\b',
        r'\bCREATE\s+INDEX\b',
        r'\bDROP\s+INDEX\b',
        r'\bDELETE\s+FROM\b.*\bWHERE\b',
        r'\bUPDATE\b.*\bWHERE\b',
    ]
    
    # 检查极高风险
    for pattern in critical_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return "critical"
    
    # 检查高风险
    for pattern in high_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            # 特殊检查：是否有WHERE条件
            if 'DELETE' in sql_upper or 'UPDATE' in sql_upper:
                if 'WHERE' not in sql_upper:
                    return "critical"
            return "high"
    
    # 检查中风险
    for pattern in medium_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return "medium"
    
    return "low"


def format_approval_response(approval: ApprovalRecord, include_full_sql: bool = False) -> dict:
    """
    格式化审批响应，处理大SQL文件的预览
    """
    # 获取SQL预览
    sql_preview = get_sql_preview(approval.sql_content)
    total_lines = approval.sql_line_count or len(approval.sql_content.split('\n'))
    
    response = {
        "id": approval.id,
        "title": approval.title,
        "change_type": approval.change_type,
        "instance_id": approval.instance_id,
        "database_name": approval.database_name,
        "sql_content": approval.sql_content if include_full_sql else None,
        "sql_content_preview": sql_preview if total_lines > PREVIEW_LINES else None,
        "sql_line_count": total_lines,
        "sql_risk_level": approval.sql_risk_level,
        "status": approval.status,
        "requester_id": approval.requester_id,
        "requester_name": approval.requester.real_name if approval.requester else None,
        "approver_id": approval.approver_id,
        "approver_name": approval.approver.real_name if approval.approver else None,
        "approve_comment": approval.approve_comment,
        "scheduled_time": approval.scheduled_time,
        "created_at": approval.created_at,
        "approved_at": approval.approve_time,
        "instance_name": approval.instance.name if approval.instance else None
    }
    
    return response


@router.get("", response_model=List[ApprovalResponse])
async def list_approvals(
    status_filter: Optional[ApprovalStatus] = None,
    requester_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审批列表"""
    query = db.query(ApprovalRecord)
    
    if status_filter:
        query = query.filter(ApprovalRecord.status == status_filter)
    if requester_id:
        query = query.filter(ApprovalRecord.requester_id == requester_id)
    if environment_id:
        query = query.filter(ApprovalRecord.environment_id == environment_id)
    
    # 普通用户只能看自己的申请
    if current_user.role.value == "readonly":
        query = query.filter(ApprovalRecord.requester_id == current_user.id)
    
    approvals = query.order_by(ApprovalRecord.created_at.desc()).offset(skip).limit(limit).all()
    return [format_approval_response(a) for a in approvals]


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审批详情"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审批记录不存在"
        )
    
    # 权限检查：只能查看自己的申请或作为审批人查看
    if (approval.requester_id != current_user.id and 
        current_user.role.value not in ["super_admin", "approval_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此审批"
        )
    
    # 详情返回完整SQL内容
    return format_approval_response(approval, include_full_sql=True)


@router.post("", response_model=ApprovalResponse)
async def create_approval(
    approval_data: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交审批申请"""
    # 检查实例是否存在
    instance = db.query(Instance).filter(Instance.id == approval_data.instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 分析SQL风险等级
    risk_level = analyze_sql_risk(approval_data.sql_content, instance.environment_id, db)
    
    # 极高风险直接拒绝
    if risk_level == "critical":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="检测到极高风险SQL，禁止提交审批"
        )
    
    # 计算SQL行数（如果前端没传）
    sql_line_count = approval_data.sql_line_count
    if not sql_line_count:
        sql_line_count = len(approval_data.sql_content.split('\n'))
    
    # 创建审批记录
    approval = ApprovalRecord(
        title=approval_data.title,
        change_type=approval_data.change_type,
        instance_id=approval_data.instance_id,
        database_name=approval_data.database_name,
        sql_content=approval_data.sql_content,
        sql_line_count=sql_line_count,
        sql_risk_level=risk_level,
        environment_id=instance.environment_id,
        requester_id=current_user.id,
        scheduled_time=approval_data.scheduled_time
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=instance.id,
        instance_name=instance.name,
        environment_id=instance.environment_id,
        operation_type="submit_approval",
        operation_detail=f"提交审批: {approval_data.title} ({sql_line_count}行SQL)",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    # TODO: 发送钉钉通知
    
    return format_approval_response(approval, include_full_sql=True)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_or_reject(
    approval_id: int,
    action_data: ApprovalAction,
    current_user: User = Depends(get_approval_admin),
    db: Session = Depends(get_db)
):
    """审批通过或拒绝"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审批记录不存在"
        )
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该审批已被处理"
        )
    
    # 更新审批状态
    approval.status = ApprovalStatus.APPROVED if action_data.approved else ApprovalStatus.REJECTED
    approval.approver_id = current_user.id
    approval.approve_time = datetime.now()
    approval.approve_comment = action_data.comment
    
    db.commit()
    db.refresh(approval)
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=approval.instance_id,
        instance_name=approval.instance.name if approval.instance else None,
        environment_id=approval.environment_id,
        operation_type="approve" if action_data.approved else "reject",
        operation_detail=f"{'通过' if action_data.approved else '拒绝'}审批: {approval.title}",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval_id}/approve",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    # TODO: 发送钉钉通知给申请人
    
    return format_approval_response(approval, include_full_sql=True)


@router.post("/{approval_id}/execute", response_model=MessageResponse)
async def execute_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行已通过的审批"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审批记录不存在"
        )
    
    if approval.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该审批未被通过，无法执行"
        )
    
    # 只有申请人可以执行
    if approval.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有申请人可以执行此审批"
        )
    
    # TODO: 实际执行SQL
    # 这里需要连接到目标MySQL实例执行SQL
    # 执行前需要生成快照（如果是DML操作）
    
    # 更新状态
    approval.status = ApprovalStatus.EXECUTED
    approval.execute_time = datetime.now()
    approval.execute_result = "执行成功"
    
    db.commit()
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=approval.instance_id,
        instance_name=approval.instance.name if approval.instance else None,
        environment_id=approval.environment_id,
        operation_type="execute_approval",
        operation_detail=f"执行审批: {approval.title}\nSQL: {get_sql_preview(approval.sql_content, 20)}...",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval_id}/execute",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    return MessageResponse(message="审批执行成功")
