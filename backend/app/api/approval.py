"""
变更审批API
"""
import re
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
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
from app.services.notification import notification_service
from app.services.scheduler import approval_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["变更审批"])

# 大文件预览行数限制
PREVIEW_LINES = 100


@router.get("/preview-databases/{instance_id}")
async def preview_matched_databases(
    instance_id: int,
    pattern: Optional[str] = None,
    mode: str = "pattern",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    预览匹配的数据库列表
    
    - mode=pattern: 通配符匹配
    - mode=all: 返回所有数据库
    """
    # 检查实例是否存在
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # TODO: 实际连接数据库获取数据库列表
    # 这里模拟返回一些数据库用于演示
    # 实际实现需要使用 pymysql 连接到目标实例
    
    # 模拟数据库列表（实际应从实例查询）
    mock_databases = [
        "db_users", "db_orders", "db_products", "db_payments",
        "user_db_master", "user_db_slave1", "user_db_slave2",
        "order_db_2023", "order_db_2024", "order_db_2025",
        "information_schema", "mysql", "performance_schema", "sys"
    ]
    
    if mode == "all":
        # 返回所有数据库（排除系统库）
        filtered = [db for db in mock_databases if db not in ["information_schema", "mysql", "performance_schema", "sys"]]
        return {
            "mode": "all",
            "databases": filtered,
            "total": len(filtered)
        }
    
    if mode == "pattern" and pattern:
        # 通配符匹配
        import fnmatch
        # 将 SQL LIKE 模式转换为 fnmatch 模式
        # % -> *, _ -> ?
        fnmatch_pattern = pattern.replace("%", "*").replace("_", "?")
        matched = [db for db in mock_databases if fnmatch.fnmatch(db, fnmatch_pattern)]
        return {
            "mode": "pattern",
            "pattern": pattern,
            "databases": matched,
            "total": len(matched)
        }
    
    return {
        "mode": mode,
        "databases": [],
        "total": 0
    }


@router.post("/parse-sql-databases")
async def parse_sql_databases(
    sql_content: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从SQL中解析数据库引用
    
    支持的格式：
    - db.table
    - `db`.table
    - db.`table`
    - `db`.`table`
    """
    # 正则匹配 db.table 格式
    # 支持反引号包裹的数据库名和表名
    patterns = [
        r'`?(\w+)`?\.`?(\w+)`?',  # db.table 或 `db`.`table`
        r'FROM\s+`?(\w+)`?\.`?(\w+)`?',  # FROM db.table
        r'JOIN\s+`?(\w+)`?\.`?(\w+)`?',  # JOIN db.table
        r'INTO\s+`?(\w+)`?\.`?(\w+)`?',  # INTO db.table
        r'UPDATE\s+`?(\w+)`?\.`?(\w+)`?',  # UPDATE db.table
    ]
    
    databases = set()
    for pattern in patterns:
        matches = re.findall(pattern, sql_content, re.IGNORECASE)
        for match in matches:
            db_name = match[0] if isinstance(match, tuple) else match
            # 排除一些常见的非数据库名
            if db_name.lower() not in ['select', 'from', 'where', 'and', 'or', 'join', 'left', 'right', 'inner', 'outer']:
                databases.add(db_name)
    
    return {
        "databases": list(databases),
        "total": len(databases)
    }


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
    
    # 构建数据库目标描述
    database_target = ""
    if approval.database_mode == "all":
        database_target = "全部数据库"
    elif approval.database_mode == "pattern":
        database_target = approval.database_pattern
    elif approval.database_mode == "multiple":
        database_target = f"{len(approval.database_list or [])} 个数据库"
    elif approval.database_mode == "auto":
        database_target = "SQL自动解析"
    else:
        database_target = approval.database_name
    
    response = {
        "id": approval.id,
        "title": approval.title,
        "change_type": approval.change_type,
        "instance_id": approval.instance_id,
        "database_mode": approval.database_mode,
        "database_name": approval.database_name,
        "database_list": approval.database_list,
        "database_pattern": approval.database_pattern,
        "matched_database_count": approval.matched_database_count,
        "database_target": database_target,
        "sql_content": approval.sql_content if include_full_sql else None,
        "sql_content_preview": sql_preview if total_lines > PREVIEW_LINES else None,
        "sql_line_count": total_lines,
        "sql_risk_level": approval.sql_risk_level,
        "affected_rows_estimate": approval.affected_rows_estimate,
        "affected_rows_actual": approval.affected_rows_actual,
        "auto_execute": approval.auto_execute,
        "status": approval.status,
        "requester_id": approval.requester_id,
        "requester_name": approval.requester.real_name if approval.requester else None,
        "approver_id": approval.approver_id,
        "approver_name": approval.approver.real_name if approval.approver else None,
        "approve_comment": approval.approve_comment,
        "scheduled_time": approval.scheduled_time,
        "execute_time": approval.execute_time,
        "execute_result": approval.execute_result,
        "created_at": approval.created_at,
        "approved_at": approval.approve_time,
        "instance_name": approval.instance.name if approval.instance else None
    }
    
    return response


@router.get("")
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
    
    total = query.count()
    approvals = query.order_by(ApprovalRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [format_approval_response(a) for a in approvals]
    }


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
            detail="Approval record not found"
        )
    
    # 权限检查：只能查看自己的申请或作为审批人查看
    if (approval.requester_id != current_user.id and 
        current_user.role.value not in ["super_admin", "approval_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to view this approval"
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
            detail="Instance not found"
        )
    
    # 分析SQL风险等级
    risk_level = analyze_sql_risk(approval_data.sql_content, instance.environment_id, db)
    
    # 极高风险直接拒绝
    if risk_level == "critical":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Critical risk SQL detected, submission rejected"
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
        database_mode=approval_data.database_mode,
        database_name=approval_data.database_name,
        database_list=approval_data.database_list,
        database_pattern=approval_data.database_pattern,
        matched_database_count=approval_data.matched_database_count,
        sql_content=approval_data.sql_content,
        sql_line_count=sql_line_count,
        sql_risk_level=risk_level,
        affected_rows_estimate=approval_data.affected_rows_estimate or 0,
        auto_execute=approval_data.auto_execute or False,
        environment_id=instance.environment_id,
        requester_id=current_user.id,
        scheduled_time=approval_data.scheduled_time
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    # 构建数据库目标描述
    db_target_desc = ""
    if approval_data.database_mode == "all":
        db_target_desc = "全部数据库"
    elif approval_data.database_mode == "pattern":
        db_target_desc = f"通配符模式: {approval_data.database_pattern}"
    elif approval_data.database_mode == "multiple":
        db_target_desc = f"{len(approval_data.database_list or [])} 个数据库"
    elif approval_data.database_mode == "auto":
        db_target_desc = "SQL自动解析"
    else:
        db_target_desc = approval_data.database_name
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=instance.id,
        instance_name=instance.name,
        environment_id=instance.environment_id,
        operation_type="submit_approval",
        operation_detail=f"Submit approval: {approval_data.title}\nDatabase: {db_target_desc}\nSQL lines: {sql_line_count}lines",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    # 发送钉钉通知
    try:
        await notification_service.send_approval_notification(db, approval, "pending")
    except Exception as e:
        # 通知失败不影响创建，记录日志即可
        logger.warning(f"发送审批通知失败: {e}")
    
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
            detail="Approval record not found"
        )
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been processed"
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
        operation_detail=f"{'Approved' if action_data.approved else 'Rejected'} approval: {approval.title}",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval_id}/approve",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    # 发送钉钉通知给申请人
    try:
        await notification_service.send_approval_notification(db, approval, "approved" if action_data.approved else "rejected")
    except Exception as e:
        logger.warning(f"发送审批结果通知失败: {e}")
    
    # 如果通过，处理执行逻辑
    if action_data.approved:
        # 如果设置了定时执行时间，添加到调度器
        if approval.scheduled_time:
            try:
                approval_scheduler.schedule_approval_execution(
                    approval.id, 
                    approval.scheduled_time
                )
                logger.info(f"已添加定时执行任务: 审批ID={approval.id}, 执行时间={approval.scheduled_time}")
            except Exception as e:
                logger.error(f"添加定时执行任务失败: {e}")
        # 如果开启了自动执行且没有定时时间，立即执行
        elif approval.auto_execute:
            try:
                logger.info(f"审批通过且启用自动执行，开始执行: 审批ID={approval.id}")
                await approval_scheduler.execute_approval(approval.id, db)
            except Exception as e:
                logger.error(f"自动执行审批失败: {e}")
    
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
            detail="Approval record not found"
        )
    
    if approval.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval was not approved, cannot execute"
        )
    
    # 只有申请人可以执行
    if approval.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the applicant can execute this approval"
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
        operation_detail=f"Execute approval: {approval.title}\nSQL: {get_sql_preview(approval.sql_content, 20)}...",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval_id}/execute",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    return MessageResponse(message="审批执行成功")


@router.get("/dingtalk-action", response_class=HTMLResponse)
async def dingtalk_approval_action(
    token: str,
    db: Session = Depends(get_db)
):
    """
    钉钉审批链接处理
    
    通过 token 验证并执行审批操作
    """
    # 验证 token
    token_data = notification_service.verify_approval_token(token)
    
    if not token_data:
        return HTMLResponse(content="""
        <html>
        <head><title>审批失败</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 操作失败</h1>
            <p>链接无效或已过期，请登录系统进行审批</p>
        </body>
        </html>
        """)
    
    approval_id = token_data["approval_id"]
    action = token_data["action"]
    
    # 获取审批记录
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    
    if not approval:
        return HTMLResponse(content="""
        <html>
        <head><title>审批失败</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 审批记录不存在</h1>
        </body>
        </html>
        """)
    
    if approval.status != ApprovalStatus.PENDING:
        status_text = {
            ApprovalStatus.APPROVED: "已通过",
            ApprovalStatus.REJECTED: "已拒绝",
            ApprovalStatus.EXECUTED: "已执lines",
            ApprovalStatus.FAILED: "执行失败"
        }.get(approval.status, "未知状态")
        
        return HTMLResponse(content=f"""
        <html>
        <head><title>审批已处理</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #e6a23c;">⚠️ 该审批已处理</h1>
            <p>当前状态: {status_text}</p>
        </body>
        </html>
        """)
    
    # 执行审批操作
    if action == "approve":
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = 0  # 钉钉审批，标记为系统
        approval.approve_time = datetime.now()
        approval.approve_comment = "通过钉钉链接审批"
        
        # 如果有定时执行时间，添加到调度器
        if approval.scheduled_time:
            approval_scheduler.schedule_approval_execution(
                approval.id, 
                approval.scheduled_time
            )
        
        db.commit()
        
        # 发送通知
        await notification_service.send_approval_notification(db, approval, "approved")
        
        return HTMLResponse(content="""
        <html>
        <head><title>审批通过</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #67c23a;">✅ 审批已通过</h1>
            <p>审批人: 钉钉审批</p>
        </body>
        </html>
        """)
    
    elif action == "reject":
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = 0
        approval.approve_time = datetime.now()
        approval.approve_comment = "通过钉钉链接拒绝"
        
        db.commit()
        
        # 发送通知
        await notification_service.send_approval_notification(db, approval, "rejected")
        
        return HTMLResponse(content="""
        <html>
        <head><title>审批拒绝</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 审批已拒绝</h1>
            <p>审批人: 钉钉审批</p>
        </body>
        </html>
        """)
    
    else:
        return HTMLResponse(content="""
        <html>
        <head><title>操作无效</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 无效的操作</h1>
        </body>
        </html>
        """)
